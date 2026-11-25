"""One model call: retries, JSON validation, run log (PLAN.md 4.3)."""

import contextvars
import functools
import itertools
import json
import logging
import string
import threading
import time
import types
import typing
from datetime import datetime, timezone
from pathlib import Path

import openai
from openai.types.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# The SDK builds the strict json_schema block for a pydantic model here. It is what
# responses.parse() uses internally; we call responses.create() instead so that a
# reply that fails validation is still a Response we can log and quote back.
from openai.lib._parsing._responses import type_to_text_format_param

from . import cache, config

log = logging.getLogger(__name__)

TRANSIENT = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)

SAMPLE_CHARS = 60

# ponytail: one lock for every run log, so parallel calls (pick) cannot interleave
# half-written lines; a lock per path if a second lake ever shares a process.
_LOG_LOCK = threading.Lock()
# the question a run over many questions is serving in this thread, written into every
# log line so each call's seconds and tokens trace back to it (a latency study)
QUESTION: contextvars.ContextVar[str | None] = contextvars.ContextVar("question", default=None)


def carry(work: typing.Callable) -> typing.Callable:
    """`work` for a pool thread, which starts with no question: it gets this thread's."""
    question = QUESTION.get()

    def run(*args):
        QUESTION.set(question)
        return work(*args)

    return run


class ModelError(Exception):
    pass


@functools.lru_cache(maxsize=None)
def _client(url: str | None = None) -> openai.OpenAI:
    # 900 s: a flex request can sit in a queue for far longer than the SDK default.
    # max_retries 0: _request's loop owns the retries and logs them; the SDK's own two on
    # top made up to 9 requests of 900 s, over two hours, before an error.
    if url:  # a local model: no key, and a long thinking reply waits behind many others
        return openai.OpenAI(base_url=url, api_key="local", timeout=3600, max_retries=0)
    return openai.OpenAI(api_key=config.openai_api_key(), timeout=900, max_retries=0)


@functools.lru_cache(maxsize=None)
def _servers(urls: str) -> itertools.cycle:
    # a local model's URLs, comma-separated, when several servers serve it: each request,
    # and each retry, goes to the next, so a retry also gets past a server that is down
    return itertools.cycle(urls.split(","))


@functools.lru_cache(maxsize=1)
def models() -> tuple[str, ...]:
    """The priced models the endpoint serves, in the order of the price table."""
    served = {model.id for model in _client().models.list()}
    return tuple(name for name in config.LLM_PRICES if name in served)


EFFORT_ORDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


def thinking(model: str, asked: str) -> str:
    """The level a call thinks at: the page's choice, else the step's own. A level the model
    does not take goes at the highest one below it that it takes, else its lowest."""
    want = config.THINKING or asked
    levels = config.EFFORTS.get(model)
    if not levels or want in levels:
        return want
    on = [level for level in levels if level != "none"]
    below = [level for level in on if EFFORT_ORDER.index(level) <= EFFORT_ORDER.index(want)]
    return (below or on)[-1 if below else 0]


def _capped(local: str, model: str, messages: list[dict], fmt: dict, effort: str, budget: int):
    """A local model's reply whose thinking stops after `budget` tokens, shaped like a
    Response for the rest of this module: vLLM takes the cap on chat completions only."""
    reply = _client(local).chat.completions.create(
        model=model,
        messages=messages,
        reasoning_effort=effort,
        response_format={"type": "json_schema", "json_schema": {k: v for k, v in fmt.items() if k != "type"}},
        extra_body={"thinking_token_budget": budget},
    )
    usage = reply.usage
    thought = getattr(usage.completion_tokens_details, "reasoning_tokens", None) or 0
    return types.SimpleNamespace(
        id=reply.id,
        status="completed" if reply.choices[0].finish_reason == "stop" else "incomplete",
        service_tier=None,
        output_text=reply.choices[0].message.content or "",
        usage=types.SimpleNamespace(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            output_tokens_details=types.SimpleNamespace(reasoning_tokens=thought),
            total_tokens=usage.total_tokens,
        ),
    )


def _format(schema: type[BaseModel]) -> dict:
    """The JSON schema the reply must follow. Strict by default: every field is required. A
    schema with optional fields the prompt may leave out (`optional_fields`) is sent as is,
    so the model is not forced to fill fields its prompt says to omit."""
    if getattr(schema, "optional_fields", False):
        return {"type": "json_schema", "name": schema.__name__, "strict": False,
                "schema": schema.model_json_schema(by_alias=True)}
    return type_to_text_format_param(schema)


def _request(
    messages: list[dict],
    schema: type[BaseModel],
    label: str,
    effort: str,
    model: str,
    budget: int | None = None,
) -> tuple[Response, int, float]:
    text = {"format": _format(schema)}
    local = config.LOCAL_MODELS.get(model)
    if budget and not local:
        raise ModelError(f"{label}: a thinking budget needs a local model, not {model}")
    lane = {} if local else {"service_tier": config.LLM_SERVICE_TIER}
    for attempt in range(1, config.LLM_ATTEMPTS + 1):
        started = time.monotonic()
        url = next(_servers(local)) if local else None
        try:
            if budget:
                response = _capped(url, model, messages, text["format"], effort, budget)
            else:
                response = _client(url).responses.create(
                    model=model,
                    input=messages,
                    reasoning={"effort": effort},
                    text=text,
                    **lane,
                )
        except TRANSIENT as err:
            if attempt == config.LLM_ATTEMPTS:
                raise ModelError(
                    f"{label}: gave up after {attempt} attempts: {err!r}"
                ) from err
            log.warning(
                "%s: %s on attempt %d, retrying", label, type(err).__name__, attempt
            )
            time.sleep(2**attempt)
        except openai.APIError as err:
            # a refused request (a bad request, a wrong key) will not pass on a retry
            raise ModelError(f"{label}: {err!r}") from err
        else:
            return response, attempt, time.monotonic() - started
    raise AssertionError("unreachable")


def _validate(
    response: Response, schema: type[BaseModel]
) -> tuple[BaseModel | None, str | None]:
    if not response.output_text:
        return None, "the reply contained no text output"
    try:
        return schema.model_validate_json(response.output_text), None
    except ValidationError as err:
        return None, str(err)


def _usage(response: Response) -> dict:
    usage = response.usage
    # a bare Response (as some tests build) may skip input_tokens_details entirely
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", None) or 0
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.output_tokens_details.reasoning_tokens,
        "total_tokens": usage.total_tokens,
        "cached_tokens": cached,
    }


def append(log_path: Path, line: dict) -> None:
    """One run-log line; the lock keeps the lines of threads apart."""
    if QUESTION.get() is not None:
        line = {"question": QUESTION.get(), **line}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_LOCK, log_path.open("a") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def _log_call(
    log_path: Path,
    label: str,
    attempt: int,
    seconds: float,
    messages: list[dict],
    response: Response,
    parsed: BaseModel | None,
    effort: str,
    model: str,
) -> None:
    line = {
        "time": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "model": model,
        "response_id": response.id,
        "status": response.status,
        "service_tier": response.service_tier,
        "reasoning_effort": effort,
        "attempt": attempt,
        "seconds": round(seconds, 3),
        "prompt": messages,
        "output_text": response.output_text,
        "parsed": parsed.model_dump() if parsed is not None else None,
        "usage": _usage(response),
    }
    append(log_path, line)


def call(
    prompt: str,
    schema: type[BaseModel],
    log_path: Path,
    label: str,
    check: typing.Callable[[BaseModel], None] | None = None,
    effort: str | None = None,
    model: str | None = None,
    sample: int = 0,
    budget: int | None = None,
) -> BaseModel:
    """One call, with at most one re-ask: a reply off the schema, or one `check` refuses.

    The same prompt to the same model gets the reply it got the first time; `sample` n > 0
    is the n-th other reply to it, kept apart. `budget` caps its thinking, in tokens.
    """
    # read once: the GUI may switch the model while this call runs
    model = model or config.LLM_MODEL
    effort = thinking(model, effort or config.LLM_REASONING_EFFORT)
    asked = {
        "model": model,
        "effort": effort,
        "schema": schema.model_json_schema(),
        "prompt": prompt,
    }
    if sample:
        asked["sample"] = sample
    if budget:
        asked["budget"] = budget
    kept = cache.get("llm", asked)
    refused = False
    if kept is not None:
        parsed = schema.model_validate(kept)
        try:
            if check is not None:
                check(parsed)
        except ModelError:
            refused = True  # a kept reply the caller now refuses is asked again
        else:
            _log_kept(log_path, label, model, {"prompt": [{"role": "user", "content": prompt}], "parsed": kept})
            return parsed
    parsed = _call(prompt, schema, log_path, label, check, effort, model, budget)
    # another caller may have kept its reply to the same prompt meanwhile: both go on with that one
    return schema.model_validate(cache.put("llm", asked, parsed.model_dump(), replace=refused))


_ZERO = {
    "input_tokens": 0,
    "output_tokens": 0,
    "reasoning_tokens": 0,
    "total_tokens": 0,
    "cached_tokens": 0,
}


def _log_kept(log_path: Path, label: str, model: str, fields: dict) -> None:
    """A reply given back from the cache: logged so the run reads whole, and costs nothing."""
    line = {
        "time": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "model": model,
        "cached": True,
        "seconds": 0.0,
        **fields,
        "usage": _ZERO,
    }
    append(log_path, line)


def _call(
    prompt: str,
    schema: type[BaseModel],
    log_path: Path,
    label: str,
    check: typing.Callable[[BaseModel], None] | None,
    effort: str,
    model: str,
    budget: int | None = None,
) -> BaseModel:
    messages: list[dict] = [{"role": "user", "content": prompt}]
    for is_reask in (False, True):
        try:
            response, attempt, seconds = _request(messages, schema, label, effort, model, budget)
        except ModelError as err:
            # a request that got no reply still leaves its line
            append(log_path, {
                "time": datetime.now(timezone.utc).isoformat(), "label": label,
                "model": model, "prompt": messages, "error": str(err), "usage": _ZERO,
            })
            raise
        parsed, error = _validate(response, schema)
        _log_call(log_path, label, attempt, seconds, messages, response, parsed, effort, model)
        if parsed is not None and check is None:
            return parsed
        if parsed is not None:
            try:
                check(parsed)
            except ModelError as err:
                # the JSON is well formed but breaks a rule of the task itself
                error = str(err)
                complaint = f"Your answer broke a rule: {error}."
            else:
                return parsed
        else:
            complaint = f"Your answer did not match the required JSON schema: {error}."
        if is_reask:
            break
        log.warning("%s: %s re-asking", label, complaint)
        messages = [
            *messages,
            {"role": "assistant", "content": response.output_text},
            {
                "role": "user",
                "content": complaint + " Answer again with only the corrected JSON.",
            },
        ]
    raise ModelError(f"{label}: reply did not match {schema.__name__} after a re-ask: {error}")


class ColumnDescription(BaseModel):
    name: str
    description: str


class TableDescription(BaseModel):
    table_description: str
    columns: list[ColumnDescription]


def _sample(value: object) -> str:
    text = str(value)
    return text if len(text) <= SAMPLE_CHARS else text[: SAMPLE_CHARS - 1] + "…"


def describe_table(
    database: str, table: str, n_rows: int, columns: list[dict], log_path: Path
) -> TableDescription:
    template = string.Template((config.PROMPTS_DIR / "describe_table.txt").read_text())
    lines = "\n".join(
        "{name} | {type} | {distinct} distinct | {samples}".format(
            name=column["name"],
            type=column["type"],
            distinct=column["distinct_count"],
            samples=", ".join(_sample(value) for value in column["samples"]),
        )
        for column in columns
    )
    label = f"describe {database}.{table}"
    want = {column["name"] for column in columns}

    def check(result: TableDescription) -> None:
        # wide tables lose a column and 100-character names get misspelt; the re-ask fixes both
        got = {described.name for described in result.columns}
        if got != want:
            raise ModelError(
                f"model returned columns {sorted(got)} but table has {sorted(want)}"
            )

    return call(
        template.substitute(
            database=database, table=table, n_rows=n_rows, columns=lines
        ),
        TableDescription,
        log_path,
        label,
        check=check,
    )


class Literal(BaseModel):
    kind: typing.Literal["text", "number", "date"]
    text: str | None = None
    number: float | None = None
    date_start: str | None = None
    date_end: str | None = None


class Entity(BaseModel):
    attribute: str
    literal: Literal | None


class Decomposition(BaseModel):
    entities: list[Entity]


_FIELDS_OF_KIND = {
    "text": {"text"},
    "number": {"number"},
    "date": {"date_start", "date_end"},
}


def _check_literal(entity: Entity) -> None:
    literal = entity.literal
    if literal is None:
        return
    filled = {
        name
        for name in ("text", "number", "date_start", "date_end")
        if getattr(literal, name) is not None
    }
    want = _FIELDS_OF_KIND[literal.kind]
    if literal.kind == "date":
        # a date range may be open on one side, so either date field alone is enough
        ok = bool(filled) and filled <= want
    else:
        ok = filled == want
    if not ok:
        raise ModelError(
            f"decompose: entity {entity.attribute!r} is kind {literal.kind} but filled"
            f" {sorted(filled) or 'no field'}"
        )
    if literal.kind == "date":
        for value in (literal.date_start, literal.date_end):
            if value is None:
                continue
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as error:
                raise ModelError(
                    f"decompose: concept {entity.attribute!r} has date {value!r},"
                    " which is not YYYY-MM-DD"
                ) from error
        if (
            literal.date_start is not None
            and literal.date_end is not None
            and literal.date_start > literal.date_end
        ):
            raise ModelError(
                f"decompose: concept {entity.attribute!r} goes from {literal.date_start}"
                f" to {literal.date_end}, which ends before it starts"
            )


def _check_literals(reply: BaseModel) -> None:
    # every question talks about something: an empty split leaves nothing to search for
    if not reply.entities:
        raise ModelError("decompose: no concept, but the question talks about at least one thing")
    for entity in reply.entities:
        _check_literal(entity)


class Concept(BaseModel):
    """One concept of the split, with at most one value (prompts/decompose.txt)."""

    model_config = ConfigDict(populate_by_name=True)
    concept: str
    text: str | None = None
    number: float | None = None
    start: str | None = Field(None, alias="from")
    end: str | None = Field(None, alias="to")


class Concepts(BaseModel):
    optional_fields: typing.ClassVar[bool] = True  # a concept carries only the value it has
    concepts: list[Concept]


def _entity(one: Concept) -> Entity:
    """A concept as the entity the rest of AMIGO reads; more than one kind of value is refused."""
    kinds = [kind for kind, filled in (("text", one.text is not None), ("number", one.number is not None),
                                       ("date", one.start is not None or one.end is not None)) if filled]
    if len(kinds) > 1:
        raise ModelError(f"decompose: concept {one.concept!r} has more than one value: {kinds}")
    if not kinds:
        return Entity(attribute=one.concept, literal=None)
    return Entity(attribute=one.concept, literal=Literal(kind=kinds[0], text=one.text, number=one.number,
                                                         date_start=one.start, date_end=one.end))


def decompose(question: str, log_path: Path) -> Decomposition:
    template = string.Template((config.PROMPTS_DIR / "decompose.txt").read_text())

    def check(reply: Concepts) -> None:
        _check_literals(Decomposition(entities=[_entity(one) for one in reply.concepts]))

    reply = call(
        template.substitute(question=question),
        Concepts,
        log_path,
        f"decompose {question[:60]}",
        check=check,
        effort=config.DECOMPOSE_REASONING_EFFORT,
    )
    return Decomposition(entities=[_entity(one) for one in reply.concepts])


# Up to 6aec78f (prompts/old/decompose.txt): the reply was the Decomposition itself.
# def decompose(question: str, log_path: Path) -> Decomposition:
#     template = string.Template((config.PROMPTS_DIR / "decompose.txt").read_text())
#     return call(
#         template.substitute(question=question),
#         Decomposition,
#         log_path,
#         f"decompose {question[:60]}",
#         check=_check_literals,
#         effort=config.DECOMPOSE_REASONING_EFFORT,
#     )


class NameWords(BaseModel):
    name: str
    words: str


class NameSplits(BaseModel):
    names: list[NameWords]


def split_names(pieces: list[str], log_path: Path) -> dict[str, str]:
    """The words of each glued name piece, checked to spell the piece letter for letter."""
    template = string.Template((config.PROMPTS_DIR / "split_names.txt").read_text())

    def check(result: NameSplits) -> None:
        got = {one.name: one.words for one in result.names}
        if set(got) != set(pieces):
            raise ModelError(f"model returned pieces {sorted(got)} but was given {sorted(pieces)}")
        bad = [name for name, words in got.items() if words.replace(" ", "").lower() != name]
        if bad:
            raise ModelError(f"these words do not spell their piece letter for letter: {bad}")

    result = call(
        template.substitute(names="\n".join(pieces)),
        NameSplits,
        log_path,
        f"split {len(pieces)} names",
        check=check,
    )
    return {one.name: " ".join(one.words.lower().split()) for one in result.names}


class PointsTo(BaseModel):
    points_to: list[int]


def judge_link(database: str, column: str, candidates: list[str], log_path: Path) -> list[int]:
    """The candidates, numbered from 1, a column points to; none is an answer too."""
    template = string.Template((config.PROMPTS_DIR / "judge_link.txt").read_text())

    def check(result: PointsTo) -> None:
        bad = [n for n in result.points_to if not 1 <= n <= len(candidates)]
        if bad:
            raise ModelError(f"candidates are numbered 1 to {len(candidates)}, not {bad}")

    result = call(
        template.substitute(
            database=database,
            column=column,
            candidates="\n".join(f"{n}. {text}" for n, text in enumerate(candidates, 1)),
        ),
        PointsTo,
        log_path,
        f"judge {column.split(' ', 1)[0]}",
        check=check,
    )
    return sorted(set(result.points_to))
