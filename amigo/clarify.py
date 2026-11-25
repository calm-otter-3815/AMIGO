"""The clarify loop: where the live interpretations disagree, and one question about it."""

import logging
import string
from collections import Counter
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

from pydantic import BaseModel

from . import bundle as _bundle
from . import config, llm, solve
from .probe import Probe
from .solve import Interpretation

log = logging.getLogger(__name__)

LABEL_CHARS = 60
THROUGH_WAYS = 2  # table sets one option line names before "or N other ways"


@dataclass
class Option:
    id: str
    column: str | None  # the bound column; None for "leave this part out"
    value: str | None
    reason: str
    description: str = ""  # what the catalog says the bound column holds
    keeps: list[str] = field(default_factory=list)
    also: list[tuple[str, str | None]] = field(default_factory=list)  # solve.Binding.also
    kind: str = "column"  # "table" when being a row of that table is the whole meaning
    through: str = ""  # the tables and joins its interpretations use, when options differ in them


@dataclass
class Axis:
    key: str  # "e1", "e2", ...
    text: str
    options: list[Option]
    # every option keeps the same rows: never asked, and every interpretation runs
    same_rows: bool = False


@dataclass
class Question:
    axis: str
    text: str
    options: list[dict]  # [{"id", "label", "column", "value", "keeps"}], axis ids and order


class PhrasedOption(BaseModel):
    id: str
    label: str


class Phrasing(BaseModel):
    question: str
    options: list[PhrasedOption]


class SuggestedColumn(BaseModel):
    column: str
    label: str


class Suggestion(BaseModel):
    question: str
    options: list[SuggestedColumn]


class Replied(BaseModel):
    option: str | None
    question: str | None


@dataclass
class Reply:
    option: str | None  # the option the typed words named
    question: str | None  # the refined question the typed words asked for


def _described(probe: Probe, path: str) -> str:
    """What the catalog says the bound column or table holds."""
    kind, card_id = probe.find(path)
    if kind == "column":
        return _bundle._one_line(probe.columns[card_id]["description"])
    table = probe.tables[card_id]
    rows = f"{table['row_count']} rows" if table["row_count"] else "no rows stored"
    return f"table, {rows}: {_bundle._one_line(table['description'])}"


def _sampled(probe: Probe, path: str) -> str:
    """What the catalog says, and for a column three values it stores: an id column reads
    like the thing it points at in its description alone."""
    kind, card_id = probe.find(path)
    if kind != "column":
        return _described(probe, path)
    samples = _bundle._samples(probe.columns[card_id])[:3]
    stored = f"values like {', '.join(samples)}" if samples else "no values stored"
    return f"{_described(probe, path)}; {stored}"


def _through(live: list[Interpretation], options: list[Option]) -> None:
    """When the options reach the rest of the question through different tables, each
    option line says through which: a plain-looking column can sit on a join that
    changes the answer, as companies reached through the country a person was born in."""
    by_id = {one.id: one for one in live}
    ways = [
        list(dict.fromkeys(
            (tuple(sorted(by_id[name].tables)), tuple(sorted(map(tuple, by_id[name].joins))))
            for name in option.keeps
        ))
        for option in options
    ]
    if len({frozenset(tables for tables, _ in way) for way in ways}) < 2:
        return
    for option, way in zip(options, ways):
        shown = [
            "tables " + ", ".join(tables)
            + ("; joins " + ", ".join(f"{a} = {b}" for a, b in joins) if joins else "")
            for tables, joins in way[:THROUGH_WAYS]
        ]
        more = f" or {len(way) - THROUGH_WAYS} other ways" if len(way) > THROUGH_WAYS else ""
        option.through = " or ".join(shown) + more


def _components(probe: Probe) -> dict[int, int]:
    """Every linked column to one id standing for the whole component it sits in.

    The same key living in several tables is one meaning, not one option each, so the
    columns the lake's joins link transitively group together: only the links good
    enough to join on and not the join-only kinds, or a weak guess would merge two meanings.
    Two columns of one table in one component are two roles, like a skin colour and a
    hair colour that both point at one colour table, so each of those stays its own
    meaning.
    """
    root: dict[int, int] = {}

    def find(column_id: int) -> int:
        while root.setdefault(column_id, column_id) != column_id:
            column_id = root[column_id]
        return column_id

    for ways in solve.joins(probe, solve.MEANING_KINDS).values():
        for join in ways:
            for from_column, to_column in join.links:
                a, b = find(from_column), find(to_column)
                if a != b:
                    root[max(a, b)] = min(a, b)
    component = {column_id: find(column_id) for column_id in root}
    shared = Counter((probe.columns[c]["table_id"], one) for c, one in component.items())
    return {
        c: one
        for c, one in component.items()
        if shared[(probe.columns[c]["table_id"], one)] == 1
    }


def _meaning(probe: Probe, components: dict[int, int], path: str) -> int | str:
    """What makes two bindings the same option: the column's component, or the path itself."""
    kind, card_id = probe.find(path)
    return components.get(card_id, path) if kind == "column" else path


def _grouped(
    probe: Probe, pairs: list[tuple[str, tuple[str | None, str | None, list], str]]
) -> list[Option]:
    """One option per distinct (meaning, value), ids in order of first appearance."""
    components = _components(probe)
    options: dict[tuple, Option] = {}
    for name, (column, value, also), reason in pairs:
        key = (_meaning(probe, components, column), value, tuple(also))
        option = options.get(key)
        if option is None:
            option = options[key] = Option(
                f"o{len(options) + 1}", column, value, reason, _sampled(probe, column),
                also=list(also), kind=probe.find(column)[0],
            )
        option.keeps.append(name)
    return list(options.values())


def axes(
    live: list[Interpretation],
    entities: list[llm.Entity],
    probe: Probe,
    settled: frozenset[str] = frozenset(),
) -> list[Axis]:
    """One axis per place the live set disagrees, in question order; none for a `settled`
    key, where the person picked several options and so keeps the disagreement."""
    found = []
    for number, entity in enumerate(entities, start=1):
        key = f"e{number}"
        pairs = [
            (one.id, (binding.column, binding.value, binding.also), binding.reason)
            for one in live
            for binding in one.bindings
            if binding.entity == key
        ]
        options = _grouped(probe, pairs)
        if len(options) > 1:
            _through(live, options)
            found.append(Axis(key, entity.attribute, options, _same_rows(probe, options)))
    return [axis for axis in found + _role_axes(live, probe) if axis.key not in settled]


def _rows_query(probe: Probe, option: Option) -> str | None:
    """The query listing the rows of its table that an option's stored values keep."""
    kind, card_id = probe.find(option.column)
    if kind != "column":
        return None
    table_id = probe.columns[card_id]["table_id"]
    where = " AND ".join(
        f"{solve._column(probe, probe.find(column)[1])} = '{value.replace(chr(39), chr(39) * 2)}'"
        for column, value in [(option.column, option.value), *option.also]
        if value is not None
    )
    return f"SELECT {solve.row_key(probe, table_id)} FROM {solve._from(probe, table_id)} WHERE {where}"


def _same_rows(probe: Probe, options: list[Option]) -> bool:
    """Every option pins stored values of one table and keeps exactly the same rows of
    it: whichever the person picks, the answer is the same, so there is nothing to ask.
    The interpretations all stay, as if the person had picked every option."""
    if any(option.value is None for option in options) or len(
        {_table(option.column) for option in options}
    ) > 1:
        return False
    queries = [_rows_query(probe, option) for option in options]
    if None in queries:
        return False
    table_id = probe.columns[probe.find(options[0].column)[1]]["table_id"]
    path = probe.tables[table_id]["database_path"]
    return not any(solve._different_rows(path, queries[0], other) for other in queries[1:])


def _table(path: str) -> str:
    return path.rsplit(".", 1)[0]


def _role_axes(live: list[Interpretation], probe: Probe) -> list[Axis]:
    """One axis per table pair every live interpretation joins in more than one way.

    Eye colour and hair colour both point at one colour table: the bindings and the
    tables agree, and only the join says which colour is meant.
    """
    ways: dict[tuple[str, str], dict[str, set]] = {}
    for one in live:
        for join in one.joins:
            pair = tuple(sorted({_table(join[0]), _table(join[1])}))
            ways.setdefault(pair, {}).setdefault(one.id, set()).add(tuple(join))
    found = []
    for (a, b), sets in ways.items():
        joined = {name: tuple(sorted(join)) for name, join in sets.items()}
        # a pair some interpretation does not join cannot split all of them
        if len(joined) < len(live) or len(set(joined.values())) < 2:
            continue
        shared = set.intersection(*({*sum(join, ())} for join in joined.values()))
        options: dict[tuple, Option] = {}
        for name, join in joined.items():
            option = options.get(join)
            if option is None:
                columns = [c for pair in join for c in pair]
                column = next((c for c in columns if c not in shared), columns[0])
                option = options[join] = Option(
                    f"o{len(options) + 1}",
                    column,
                    None,
                    "joins " + " and ".join(f"{x} to {y}" for x, y in join),
                    _sampled(probe, column),
                )
            option.keeps.append(name)
        found.append(Axis(f"{a} {b}", f"which link joins {a} to {b}", list(options.values())))
    return found


def choose_axis(found: list[Axis]) -> Axis | None:
    """The axis that removes the most on average: its most popular option keeps the fewest.
    An axis whose options keep the same rows is never asked."""
    found = [axis for axis in found if not axis.same_rows]
    if not found:
        return None
    # len(live) is the same for every axis, so the largest len(live) - max(keeps) is the
    # smallest max(keeps); min keeps the earlier axis on a tie
    return min(found, key=lambda axis: max(len(option.keeps) for option in axis.options))


def same_answer(live: list[Interpretation], probe: Probe) -> bool:
    """Every interpretation answers what the one with the fewest tables does: they differ
    only by linked copies of one id, looked up through keys (solve.reads_as)."""
    narrowest = min(live, key=lambda one: len(one.tables))
    return all(one is narrowest or solve.reads_as(probe, one, narrowest) for one in live)


def narrow(
    live: list[Interpretation], axis: Axis, answer: str
) -> list[Interpretation]:
    """The live interpretations that carry the answer, in their original order. An answer
    is one option id, or several joined by "+" when the person picked several."""
    ids = answer.split("+")
    keeps = {name for option in axis.options if option.id in ids for name in option.keeps}
    return [one for one in live if one.id in keeps]


def shown_together(entity: llm.Entity, options: list[Option]) -> bool:
    """Several picked columns for a part with no value to test are one thing to show:
    a name as the first name and the last name. A part with a value, or a table, is not:
    each picked option then stays its own interpretation."""
    return entity.literal is None and all(
        option.kind == "column" and option.column and option.value is None and not option.also
        for option in options
    )


def combine(
    live: list[Interpretation], key: str, groups: list[set[str]]
) -> tuple[list[Interpretation], list[Interpretation]]:
    """The columns the person picked together for part `key`, read by one interpretation.

    `groups` holds the ids of the live interpretations each picked option keeps. The ones
    that agree on every other binding merge, one from each group. Those that cannot (their
    tables are joined along different paths) stay as they are. Returns the new live set and the merged interpretations in it.
    """

    def rest(one: Interpretation) -> tuple:
        return tuple(
            (b.entity, b.column, b.value, tuple(b.also)) for b in one.bindings if b.entity != key
        )

    by_rest: dict[tuple, list[list[Interpretation]]] = {}
    out: list[Interpretation] = []
    for one in live:
        slot = next((i for i, ids in enumerate(groups) if one.id in ids), None)
        if slot is None:
            out.append(one)
        else:
            by_rest.setdefault(rest(one), [[] for _ in groups])[slot].append(one)
    made: list[Interpretation] = []
    for slots in by_rest.values():
        merged = [] if not all(slots) else [
            one for combo in product(*slots) if (one := _merged(key, combo)) is not None
        ]
        made += merged
        out += merged or [one for slot in slots for one in slot]
    return out, made


def _merged(key: str, combo: tuple[Interpretation, ...]) -> Interpretation | None:
    """One interpretation that reads every one of `combo`'s columns for part `key`."""
    bound = [next(b for b in one.bindings if b.entity == key) for one in combo]
    if any(b.value is not None or b.also for b in bound):
        return None
    # every combo member must read the same rows: one path holds every other's tables and
    # joins, and only adds tables for its own column. Two different paths (one through the
    # holdings, one through the country) would ask for both facts at once.
    def path(one: Interpretation) -> tuple[set, set]:
        return set(one.tables), {frozenset(join) for join in one.joins}

    widest = max(combo, key=lambda one: len(path(one)[1]))
    tables, links = path(widest)
    if any(not (path(one)[0] <= tables and path(one)[1] <= links) for one in combo):
        return None
    joins = [tuple(join) for join in widest.joins]
    binding = solve.Binding(
        key, bound[0].column, "picked together by the person", None,
        also=[(b.column, None) for b in bound[1:]],
    )
    bindings = [binding if b.entity == key else b for b in combo[0].bindings]
    read = {c for b in bindings for c in b.columns} | {c for join in joins for c in join}
    avoid = sorted({c for one in combo for c in one.avoid} - read)
    return Interpretation(
        "+".join(one.id for one in combo), bindings, list(widest.tables), widest.paths, joins,
        avoid, left_out=list(combo[0].left_out),
    )


def tree(
    live: list[Interpretation],
    entities: list[llm.Entity],
    probe: Probe,
    settled: frozenset[str] = frozenset(),
) -> dict:
    """Every question the loop would ask, down every answer, so the page can draw them all.

    A node holds the live ids; a node the loop asks at also holds its axis and one option
    per answer, each with the node that answer leads to. Code only: no wording.
    """
    node: dict = {"ids": [one.id for one in live]}
    axis = choose_axis(axes(live, entities, probe, settled)) if len(live) > 1 else None
    if axis is not None:
        node["axis"], node["text"] = axis.key, axis.text
        node["options"] = [
            {
                "id": option.id,
                "column": option.column,
                "value": option.value,
                "also": option.also,
                "child": tree(narrow(live, axis, option.id), entities, probe, settled),
            }
            for option in axis.options
        ]
    return node


def _path(option: Option) -> str:
    if option.kind == "database":
        return f"database {option.column}"
    if option.kind == "leave":
        return f'leave out the part "{option.column}"'
    if option.kind == "join":
        return f"through {option.through}" if option.through else f"through tables {option.column}"
    if option.column is None:
        return "no table"
    return f"table {option.column}" if option.kind == "table" else option.column


def _written(option: Option) -> str:
    text = _path(option)
    if option.value is not None:
        text += f" = '{option.value}'"
    return "".join(
        [
            text,
            *(
                f" and {column}" + ("" if value is None else f" = '{value}'")
                for column, value in option.also
            ),
        ]
    )


def fallback(axis: Axis) -> Question:
    """The question code writes for itself when the phrasing call failed."""
    return Question(
        axis.key,
        f'Which one do you mean for "{axis.text}"?',
        [
            {
                "id": option.id,
                "label": _written(option),
                "column": option.column,
                "value": option.value,
                "also": option.also,
                "keeps": list(option.keeps),
            }
            for option in axis.options
        ],
    )


def _option_line(option: Option) -> str:
    parts = [option.id, _path(option)]
    if option.value is not None:
        parts.append(f"value {option.value}")
    parts += [
        f"and {column}" + ("" if value is None else f" value {value}")
        for column, value in option.also
    ]
    if option.reason:
        parts.append(option.reason)
    if option.description:
        parts.append(option.description)
    parts.append(f"keeps {len(option.keeps)}")
    if option.through and option.kind != "join":  # a join option's path already says it
        parts.append(f"through {option.through}")
    return "  " + " | ".join(parts)


def _check_phrasing(wanted: list[str]):
    def check(result: Phrasing) -> None:
        got = [one.id for one in result.options]
        if sorted(got) != sorted(wanted):
            raise llm.ModelError(
                f"model returned option ids {got} but they must be exactly {wanted}"
            )
        for one in result.options:
            if not one.label.strip() or len(one.label) > LABEL_CHARS:
                raise llm.ModelError(
                    f"option {one.id} has label {one.label!r}, which must hold text and"
                    f" be at most {LABEL_CHARS} characters"
                )
        _check_distinct([one.label for one in result.options])

    return check


def _check_distinct(labels: list[str]) -> None:
    """Two buttons that read the same but mean different things are no question."""
    if len({label.strip().lower() for label in labels}) != len(labels):
        raise llm.ModelError(f"two options share a label in {labels}")


def phrase(axis: Axis, question: str, log_path: Path) -> Question:
    """One call that words the question and the option labels. The options themselves are fixed."""
    template = string.Template((config.PROMPTS_DIR / "clarify.txt").read_text())
    result = llm.call(
        template.substitute(
            question=question,
            axis=axis.text,
            options="\n".join(_option_line(option) for option in axis.options),
        ),
        Phrasing,
        log_path,
        f"clarify {axis.key}",
        check=_check_phrasing([option.id for option in axis.options]),
        # wording only: thinking first makes it some 6 times slower and no better
        effort="none",
    )
    labels = {one.id: one.label for one in result.options}
    return Question(
        axis.key,
        result.question,
        [
            {
                "id": option.id,
                "label": labels[option.id],
                "column": option.column,
                "value": option.value,
                "also": option.also,
                "keeps": list(option.keeps),
            }
            for option in axis.options
        ],
    )


def _check_suggestion(paths: list[str]):
    def check(result: Suggestion) -> None:
        columns = [one.column for one in result.options]
        if len(columns) > 4:
            raise llm.ModelError(
                f"model returned {len(columns)} columns, which must be at most 4"
            )
        if len(set(columns)) != len(columns):
            raise llm.ModelError(f"model returned a column twice in {columns}")
        for one in result.options:
            if one.column not in paths:
                raise llm.ModelError(
                    f"model returned column {one.column!r}, which is not one of the"
                    " candidate columns printed in the prompt"
                )
            if not one.label.strip() or len(one.label) > LABEL_CHARS:
                raise llm.ModelError(
                    f"column {one.column} has label {one.label!r}, which must hold text"
                    f" and be at most {LABEL_CHARS} characters"
                )
        _check_distinct([one.label for one in result.options])

    return check


def suggest(
    written: str, question: str, candidates: list[tuple[str, str]], log_path: Path
) -> tuple[str, list[tuple[str, str]]]:
    """One call that picks the columns a person could have meant, and words the question."""
    template = string.Template((config.PROMPTS_DIR / "did_you_mean.txt").read_text())
    result = llm.call(
        template.substitute(
            question=question,
            written=written,
            candidates="\n".join(
                f"  {path} | {description}" for path, description in candidates
            ),
        ),
        Suggestion,
        log_path,
        f"did you mean {written[:40]}",
        check=_check_suggestion([path for path, _ in candidates]),
    )
    return result.question, [(one.column, one.label) for one in result.options]


def turn_lines(turns: list[dict]) -> str:
    """The turns so far, one line each: what was asked, what was on offer, what came back."""
    if not turns:
        return "  none"
    lines = []
    for turn in turns:
        # the server stores options as {"id", "label"} dicts and the answer as an id;
        # the page sends plain labels and the chosen label, so both shapes are read here
        options = [
            option if isinstance(option, dict) else {"id": option, "label": option}
            for option in turn["options"]
        ]
        labels = [option["label"] for option in options]
        answered = next(
            (option["label"] for option in options if option["id"] == turn["answer"]),
            turn["answer"] or turn["typed"] or "nothing",
        )
        lines.append(
            f'  asked: {turn["question"]} | options: {", ".join(labels)}'
            f" | they answered: {answered}"
        )
    return "\n".join(lines)


def map_reply(
    question: Question, turns: list[dict], original: str, reply: str, log_path: Path
) -> Reply:
    """What the typed words do: name one option, refine the question into a new one, or neither.

    With no option on the table (the stateless refine call) only a question can come back.
    """
    template = string.Template((config.PROMPTS_DIR / "clarify_reply.txt").read_text())
    ids = [option["id"] for option in question.options]

    def check(result: Replied) -> None:
        if result.option is not None and result.question is not None:
            raise llm.ModelError(
                "the typed words either name an option or ask a new question, never both"
            )
        if result.option is not None and result.option not in ids:
            raise llm.ModelError(
                f"model returned option {result.option!r}, which is not one of {ids}"
            )
        if result.question is not None and (
            not result.question.strip() or result.question.strip() == original.strip()
        ):
            raise llm.ModelError(
                "a refined question must hold text and differ from the original question"
            )
        if not ids and result.question is None:
            raise llm.ModelError("no option is on offer, so only a new question can answer")

    result = llm.call(
        template.substitute(
            original=original,
            turns=turn_lines(turns),
            question=question.text or "no question is on the table",
            options="\n".join(
                f'  {option["id"]} | {option["label"]}' for option in question.options
            )
            or "  none",
            reply=reply,
        ),
        Replied,
        log_path,
        f"clarify reply {reply[:40]}",
        check=check,
        effort="none",
    )
    return Reply(result.option, result.question)
