"""A local page that watches one question move through the pipeline, step by step."""

import csv
import dataclasses
import io
import json
import logging
import queue
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import openai

from . import (answer, bundle, candidates, chats, clarify, config, guide, index, interpret, judge, lakemap, layer, llm, pick,
               route, solve)
from .probe import Probe

log = logging.getLogger(__name__)

CALL_KEYS = ("label", "model", "service_tier", "seconds", "usage", "prompt", "output_text", "parsed", "error")
WAIT = 15  # seconds /events sits on the run before writing a keep-alive comment
PAGE = 10  # rows per page of the content viewer
RESULT_PAGE = 50  # rows per page of a query's result
PEEK = 6  # rows shown of what one option of a fork reads
# the events after which a chat is saved: each pause, and the end
SAVED_AT = {"run", "route", "parts_paused", "places_paused", "fork", "interpretations", "paused",
            "rows", "done", "error", "cancelled"}


def _value(value: object) -> object:
    """One result cell as JSON takes it: a number, text or null; anything else as text."""
    return value if value is None or isinstance(value, (int, float, str)) else str(value)


def _cell(value: object) -> str | None:
    """One row cell as text, capped so a wide value does not blow up the panel."""
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= 80 else text[:79] + "…"


class Run:
    """One question in flight: the events so far, and the pause where the user chooses."""

    def __init__(
        self,
        number: int,
        lake: "Lake",
        question: str,
        offset: int,
        check: bool = False,
        replay: dict | None = None,
    ) -> None:
        self.number = number
        self.lake = lake
        self.question = question
        self.offset = offset
        self.check = check
        # the person's earlier decisions, when they change a later one: the run takes them
        # without asking ("parts", "places", "forks"), and asks from the first one left out
        self.replay = replay or {}
        self.started = time.monotonic()
        self.thread: threading.Thread | None = None
        # a stopped run's worker, still waiting on the calls it sent: this run starts after it
        self.after: threading.Thread | None = None
        self.events: list[dict] = []
        self.condition = threading.Condition()
        # the saved chat this run belongs to (chats.py); None once that chat is deleted
        self.uid = chats.new_id()
        self.chat: str | None = None
        self.saving = threading.Lock()
        self.finished = False
        self.cancelled = threading.Event()
        self.kept: dict[str, solve.Interpretation] = {}
        self.waiting = False
        self.chosen = threading.Event()
        self.selected: list[str] = []
        # what a follow-up needs off this run once it is finished
        self.entities: list[llm.Entity] = []
        self.results: list[answer.Result] = []
        self.chosen_id: str | None = None
        # the log size before this run's route call, so the run it starts counts that call
        self.route_offset: int | None = None
        # a routed follow-up: the event to emit, and for a rewrite what to query again
        self.route: dict | None = None
        self.rewrite: (
            tuple[list[llm.Entity], solve.Interpretation, str, str] | None
        ) = None
        # a rewrite's earlier question and the SQL that answered it, for the SQL step
        self.earlier: tuple[str, str] | None = None
        # the person picked the rewrite, not the router: its SQL may read new columns
        self.chosen_rewrite = False
        # the interpretations the person can tick, and the follow-up turns so far
        self.live: list[str] = []
        self.turns: list[dict] = []
        # the first pause, check mode only: the user fixes the question's parts
        self.checking = False
        self.checked = threading.Event()
        self.parts: list[llm.Entity] = []
        # the parts and their scores, so the person's own choice of places can be searched again
        self.stage: bundle.Stage1 | None = None
        self.fan: solve.FanOut | None = None
        # guided mode: the person's actions at a fork (guide.py), and the answers so far
        self.actions: queue.Queue = queue.Queue()
        self.guiding = False
        self.back_to: int | None = None
        self.fork_step = 0
        self.fork_ids: list[str] = []
        # the fork on screen and its options as worded, for a look at the rows each one reads
        self.fork_now: tuple[guide.Fork, clarify.Axis] | None = None
        # guided mode: the pause after the judge, and per part the (table, column) places kept
        self.approving = False
        self.approved = threading.Event()
        self.keep: list[set] | None = None

    def emit(self, kind: str, **payload) -> None:
        if self.cancelled.is_set() and kind != "cancelled":
            return
        event = {"type": kind, "t": round(time.monotonic() - self.started, 1), **payload}
        with self.condition:
            self.events.append(event)
            if kind in ("done", "error", "cancelled"):
                self.finished = True
            self.condition.notify_all()
        if kind in SAVED_AT:
            # the events are read under the lock, so a later save never loses to an earlier one
            with self.saving:
                if self.chat is not None:
                    try:
                        chats.save(self.chat, self.lake.name, self.uid, self.question, list(self.events))
                    except OSError as err:
                        log.warning("chat %s not saved: %s", self.chat, err)


class Events(logging.Handler):
    """Turns the pipeline's own log records into events of one run."""

    def __init__(self, run: Run) -> None:
        super().__init__(logging.INFO)
        self.run = run

    def emit(self, record: logging.LogRecord) -> None:
        if record.msg == "sql %s try %d: %s":
            name, attempt, error = record.args
            self.run.emit("sql", id=name, attempt=attempt, error=error)
        elif record.msg == "sql %s try %d: %d rows":
            name, attempt, count = record.args
            self.run.emit("sql", id=name, attempt=attempt, rows=count)
        else:
            self.run.emit("log", text=record.getMessage())


def _bundle_event(probe: Probe, stage: bundle.Stage1) -> dict:
    return {
        "entities": [
            {
                "attribute": entity.attribute,
                "literal": None if entity.literal is None else entity.literal.model_dump(),
            }
            for entity in stage.entities
        ],
        "tables": [
            {
                "id": table_id,
                "path": probe.path("table", table_id),
                "readable": probe.tables[table_id]["readable"],
                "database": probe.tables[table_id]["database"],
                "database_readable": probe.tables[table_id]["database_readable"],
                "rows": probe.tables[table_id]["row_count"],
                "bridge": table_id in stage.bridges,
                "columns": [
                    {
                        "id": column_id,
                        "name": column["name"],
                        "readable": column["readable"],
                        "details": stage.details[column_id],
                    }
                    for column_id, column in probe.columns.items()
                    if column["table_id"] == table_id and column_id in stage.details
                ],
            }
            for table_id in stage.order
        ],
        "not_found": [
            {
                "written": written,
                "near": [probe.path("column", column_id) for column_id in near],
            }
            for written, near in stage.not_found
        ],
    }


def _hits(probe: Probe, entity: llm.Entity, column_id: int) -> list[str]:
    """The values of a column that match the part's own value, as the place list shows them."""
    literal, column = entity.literal, probe.columns[column_id]
    if literal is None:
        return []
    if literal.kind == "text" and literal.text and column["kind"] == "text":
        found = probe.stored_values(column_id, literal.text)[:2]
        for word in [] if found else index.words(literal.text):
            found += probe.word_values(column_id, word)[:1]
        return [str(value) for value in found]
    if literal.kind == "number" and column["kind"] == "number" and probe.stores(column_id, literal.number):
        return [f"{literal.number:g}"]
    return []


def _places_event(probe: Probe, stage: bundle.Stage1, shown: list, grades: list[dict] | None) -> dict:
    """Per part, every place the judge was shown, in its order, with its yes or no (None
    before the judge has answered), its cosine to the part, and what the page shows on its card."""
    parts = []
    for j, (entity, mine) in enumerate(zip(stage.entities, shown)):
        items = []
        for h in mine:
            table = probe.tables[h.table]
            item = {
                "table": h.table, "column": h.column,
                "yes": None if grades is None else bool(grades[j][(h.table, h.column)]),
                "score": round(h.score, 3), "why": h.why,
                "database": table["database"], "table_name": table["name"], "rows": table["row_count"],
                # the path an interpretation's bindings name it by
                "path": probe.path("column", h.column),
            }
            column = probe.columns[h.column]
            item.update(name=column["name"], distinct=column["distinct_count"],
                        empty=column["empty_share"] or 0, hit=_hits(probe, entity, h.column))
            items.append(item)
        parts.append({"part": entity.attribute, "items": items})
    return {"parts": parts}


def _rows(probe: Probe, table_id: int, column_id: int | None, text: str, page: int) -> dict:
    """One page of a table, or of one of its columns, read from its source database: the
    rows holding `text` in any shown column when it is given, and how many there are."""
    table = probe.tables[table_id]
    with closing(index.open_source(table["database_path"])) as source:
        names = [row[1] for row in source.execute(f"PRAGMA table_info({index._quote(table['name'])})")]
        if column_id is not None:
            names = [probe.columns[column_id]["name"]]
        shown = ", ".join(index._quote(name) for name in names)
        where, args = "", []
        if text:
            where = " WHERE " + " OR ".join(f"CAST({index._quote(name)} AS TEXT) LIKE ? ESCAPE '\\'" for name in names)
            pattern = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            args = [pattern] * len(names)
        source_table = index._quote(table["name"])
        matched = source.execute(f"SELECT count(*) FROM {source_table}{where}", args).fetchone()[0]
        pages = max(1, -(-matched // PAGE))
        page = min(max(page, 0), pages - 1)
        rows = source.execute(f"SELECT {shown} FROM {source_table}{where} LIMIT ? OFFSET ?",
                              [*args, PAGE, page * PAGE]).fetchall()
    return {"columns": names, "rows": [[None if v is None else str(v) for v in row] for row in rows],
            "matched": matched, "total": table["row_count"], "page": page, "pages": pages}


def _rows_event(result: answer.Result) -> dict:
    return {
        "sentence": result.sentence,
        "said": result.said,
        "sql": result.sql,
        "columns": result.columns,
        "rows": [
            [cell if cell is None or isinstance(cell, (int, float, str)) else str(cell) for cell in row]
            for row in result.rows
        ],
        "more": result.more,
        "error": result.error,
    }


def _work(run: Run) -> None:
    lake = run.lake
    if run.after is not None:
        # a call already sent cannot be taken back; once they are all in, the stopped
        # run's log lines and log records cannot be taken for this run's own
        while run.after.is_alive():
            run.emit("held")
            run.after.join(30)
        run.after = None
        run.offset = lake.log_path.stat().st_size if lake.log_path.exists() else 0
        if run.cancelled.is_set():
            return
    package = logging.getLogger("amigo")
    level, handler = package.level, Events(run)
    # the events come from INFO records, whatever level the process itself logs at
    package.setLevel(logging.INFO)
    package.addHandler(handler)
    try:
        run.emit("run", question=run.question, lake=lake.name, chat=run.chat)
        if run.route is not None:
            run.emit("route", **run.route)
        query_them = False
        if run.rewrite is not None:
            # a rewrite skips to the SQL step: the tables and the bindings are already settled
            run.entities, one, earlier_question, earlier_sql = run.rewrite
            run.earlier = (earlier_question, earlier_sql)
            run.kept = {one.id: one}
            run.selected = [one.id]
            run.fan = solve.FanOut([one], [], None)
            query_them = True
        else:
            entities = llm.decompose(run.question, lake.log_path).entities
            if run.cancelled.is_set():
                return
            if run.check and run.replay.get("parts"):
                try:
                    entities = _read_parts(run.replay["parts"])
                    _log_parts(run, entities)
                except (ValueError, llm.ModelError) as err:
                    log.warning("run %d: the earlier parts do not hold, asking again: %s", run.number, err)
                    run.replay = {}
            if run.check and not run.replay.get("parts"):
                run.checking = True
                run.emit("parts_paused", entities=[one.model_dump() for one in entities])
                run.checked.wait()
                if run.cancelled.is_set():
                    return
                entities = run.parts
            stage = bundle.stage1(lake.probe, run.question, lake.log_path, entities=entities)
            # cancel can land mid-step: the step runs to its end, then the run drops here
            if run.cancelled.is_set():
                return
            run.emit("bundle", **_bundle_event(lake.probe, stage))
            run.stage = stage
            # the search asks at each fork, then waits for ticks (guide.py)
            if _guided(run) is None:
                return
            query_them = bool(run.live)
        # kept on the run as they come, so the page can read a result's rows while others run
        results: list[answer.Result] = []
        run.results = results
        if query_them:
            kept = {}
            if run.rewrite is not None:
                # the page starts the follow-up blank: this is what its SQL follows
                kept = {
                    "interpretations": [dataclasses.asdict(one) for one in run.kept.values()],
                    "entities": [one.model_dump() for one in run.entities],
                }
            run.emit("selected", ids=run.selected, **kept)
            # the interpretations do not wait on each other, so their SQL is written at
            # the same time; their rows still come in the order they were selected
            with ThreadPoolExecutor(max_workers=pick.WORKERS) as pool:
                futures = []
                for name in run.selected:
                    run.emit("querying", id=name)
                    futures.append(
                        pool.submit(
                            answer.answered,
                            lake.probe,
                            run.question,
                            run.entities,
                            run.kept[name],
                            lake.log_path,
                            rewrite=run.earlier,
                            stop=run.cancelled,
                            chosen=run.chosen_rewrite,
                        )
                    )
                for name, future in zip(run.selected, futures):
                    result = future.result()
                    if run.cancelled.is_set():
                        pool.shutdown(cancel_futures=True)
                        return
                    results.append(result)
                    run.emit("rows", id=name, **_rows_event(result))
        run.emit(
            "done",
            text=answer.present(
                answer.Answer(run.question, run.entities, run.fan, results)
            ),
        )
    except Exception as err:
        log.exception("run %d failed", run.number)
        run.emit("error", text=f"{type(err).__name__}: {err}")
    finally:
        package.removeHandler(handler)
        package.setLevel(level)


NOTHING = "No interpretation in this lake, even leaving out parts of the question."


def _trail(answers: list[guide.Answer]) -> list[dict]:
    return [{"n": n, "text": a.text} for n, a in enumerate(answers)]


def _preset(run: Run, forks: list[dict], n: int, allowed: tuple) -> dict | None:
    """The person's earlier answer at fork `n`, taken again without asking; None when there is
    none, or when it no longer fits this fork: then it and every later one are asked again."""
    if n >= len(forks):
        return None
    one = forks[n]
    what, ids = one.get("action"), list(one.get("ids") or [])
    if what in allowed and (what != "pick" or ids and set(ids) <= set(run.fork_ids)):
        return {"action": what, "ids": ids, "to": 0, "text": ""}
    del forks[n:]
    run.emit("guide_note", step=n, text="Your earlier answer does not fit this question any more: answer it again")
    return None


def _read_parts(given: list) -> list[llm.Entity]:
    """The parts the person wrote, checked; ValueError or ModelError when one does not hold."""
    entities = [llm.Entity.model_validate(one) for one in given]
    for entity in entities:
        if not entity.attribute.strip():
            raise llm.ModelError("a part has no words")
        llm._check_literal(entity)
    if not entities:
        raise ValueError("keep at least one part")
    return entities


def _log_parts(run: Run, entities: list[llm.Entity]) -> None:
    line = {"kind": "parts", "question": run.question, "entities": [one.model_dump() for one in entities]}
    with run.lake.log_path.open("a") as handle:
        handle.write(json.dumps(line) + "\n")


def _approved(run: Run, keep: list | None) -> bool:
    """The places approved: as judged when `keep` is None, else per part the [table, column or
    null] places kept. ValueError when `keep` does not give one list per part."""
    if keep is not None:
        if len(keep) != len(run.stage.entities):
            raise ValueError(f"give one list per part ({len(run.stage.entities)}), not {len(keep)}")
        run.keep = [{(int(t), None if c is None else int(c)) for t, c in mine} for mine in keep]
    run.approving = False
    run.emit("approved", kept=None if run.keep is None else sum(len(one) for one in run.keep), keep=keep)
    run.approved.set()
    return True


def _guided(run: Run) -> solve.FanOut | None:
    """Guided mode (guide.py): the place judge and the person's review of its answers, then
    AMIGO's candidates as a tree walked from the top. At each fork the person picks, says
    any or none of these, types words, walks back to any earlier fork, or stops asking; then
    ticks the interpretations left, or walks back from there. A fork is shown at once in
    plain code words, and again once one LLM call has worded it. None when the run was
    cancelled, or restarts with the question the typed words asked for."""
    lake, stage = run.lake, run.stage
    probe, graph = lake.probe, lake.graph()
    shown = [candidates.holders(probe, stage, j) for j in range(len(stage.entities))]
    # the places go to the page before the judge call, so it shows them while the judge reads
    run.emit("candidates", **_places_event(probe, stage, shown, None))
    grades = judge.judge(probe, graph, run.question, stage, shown, lake.log_path)
    if run.cancelled.is_set():
        return None
    run.emit("places", **_places_event(probe, stage, shown, grades))
    # the person keeps or drops places against the judge's answers, then approves
    try:
        replayed = "places" in run.replay and _approved(run, run.replay["places"])
    except ValueError as err:
        log.warning("guide: the earlier places do not hold, asking again: %s", err)
        replayed = False
    if not replayed:
        run.replay = {}
        run.approving = True
        run.emit("places_paused")
        run.approved.wait()
        if run.cancelled.is_set():
            return None
    if run.keep is not None:
        grades = [{key: key in mine for key in part} for mine, part in zip(run.keep, grades)]
        run.emit("places", edited=True, **_places_event(probe, stage, shown, grades))
    # the tree is built once, from the candidates of the automatic answer
    places = judge.graded(shown, grades)
    tree = guide.build(guide.automatic(probe, graph, stage, run.question, places, lake.log_path))
    if run.cancelled.is_set():
        return None
    run.entities = stage.entities
    entities = [one.model_dump() for one in stage.entities]
    answers: list[guide.Answer] = []
    forks = list(run.replay.get("forks") or [])  # the earlier answers to take, by step
    worded: dict = {}  # a fork, by its node and the options shown, -> its worded question
    asked: set = set()  # the forks whose wording call was sent
    on_screen: dict = {}  # the fork on screen -> how to show it again

    def key_of(fork: guide.Fork) -> tuple:
        return id(fork.node), tuple(o.n for o in fork.options)

    def word(axis: clarify.Axis, key: tuple) -> None:
        """One LLM call words the fork, in the background, once; the fork on screen shows
        again in plain words when it comes back."""
        if key in asked:
            return
        asked.add(key)

        def call() -> None:
            try:
                worded[key] = clarify.phrase(axis, run.question, lake.log_path)
            except llm.ModelError as err:
                log.warning("guide: wording failed, the code words stay: %s", err)
                return
            show = on_screen.get(key)
            if show is not None and run.guiding:
                show(worded[key], True)

        threading.Thread(target=llm.carry(call), daemon=True).start()

    def ahead(before: list, fork: guide.Fork) -> None:
        """The fork each option of `fork` leads to, worded ahead (no LLM call to find it)."""
        for option in fork.options:
            if run.cancelled.is_set() or not run.guiding:
                return
            nxt = guide.step(tree, before + [guide.Answer("pick", frozenset({option.n}))]).fork
            if nxt is not None:
                word(guide.axis(probe, graph, stage, nxt), key_of(nxt))
    while True:
        step = guide.step(tree, answers)
        fork = step.fork
        if fork is None:
            leaves = step.leaves
            cards = [interpret._card(probe, graph, stage, one, n, leaves[0].cost)
                     for n, one in enumerate(leaves, start=1)]
            if cards:
                # one call that sees every card, so each card says what sets it apart
                cards = answer.summaries(probe, run.question, stage.entities,
                                         cards[:config.MAX_INTERPRETATIONS], lake.log_path) + cards[config.MAX_INTERPRETATIONS:]
                if run.cancelled.is_set():
                    return None
            stopped = NOTHING if any(places) else guide.nothing(run.lake.name, stage, list(range(len(places))))
            fan = run.fan = solve.FanOut(cards, [], None if cards else stopped)
            run.kept = {one.id: one for one in cards}
            run.live = [one.id for one in cards]
            run.emit("interpretations", entities=entities, trail=_trail(answers), guided=True,
                     **dataclasses.asdict(fan))
            if not cards:
                return fan
            # even one interpretation waits: the person may still walk back
            run.back_to, run.waiting = None, True
            run.chosen.clear()
            run.emit("paused", ids=run.live, guided=True)
            run.chosen.wait()
            if run.cancelled.is_set():
                return None
            if run.back_to is not None:
                answers = answers[:run.back_to]
                del forks[run.back_to:]
                continue
            return run.fan
        n = len(answers)
        axis = guide.axis(probe, graph, stage, fork)
        key = key_of(fork)

        def show(question: clarify.Question, words: bool, n=n, fork=fork, answers=list(answers), replayed=False):
            run.emit("fork", step=n, fork=fork.kind, part=fork.part, about=guide.about(stage, fork),
                     question=question.text, worded=words, more=fork.more, trail=_trail(answers),
                     replayed=replayed,
                     options=[{"id": o["id"], "label": o["label"], "share": round(opt.share, 3),
                               # the tables the option's likeliest interpretation reads, for the map
                               "tables": sorted({probe.path("table", h.table) for h in opt.best.holders if h is not None})}
                              for o, opt in zip(question.options, fork.options)])

        run.fork_step, run.fork_ids = n, [option.id for option in axis.options]
        run.fork_now = fork, axis
        action = _preset(run, forks, n, ("pick", "any", "none", "stop"))
        run.guiding = action is None
        on_screen.clear()
        on_screen[key] = show
        show(worded.get(key) or clarify.fallback(axis), key in worded, replayed=action is not None)
        if action is None:
            word(axis, key)
            # while the person reads, the fork each of their answers leads to is found and worded
            threading.Thread(target=llm.carry(ahead), args=(list(answers), fork), daemon=True).start()
            action = run.actions.get()
        run.guiding = False
        if run.cancelled.is_set():
            return None
        what = action["action"]
        question = worded.get(key) or clarify.fallback(axis)
        if what == "back":
            answers = answers[:action["to"]]
            del forks[action["to"]:]
            continue
        if what == "text":
            try:
                reply = clarify.map_reply(question, [], run.question, action["text"], lake.log_path)
            except llm.ModelError as err:
                log.warning("guide: reading the reply failed: %s", err)
                reply = clarify.Reply(None, None)
            if reply.question:
                run.emit("restart", question=reply.question)
                run.emit("done", text=f"Starting over with: {reply.question}")
                return None
            if reply.option is None:
                run.emit("guide_note", step=n, text=f'"{action["text"]}" matches no option; pick one, or say it another way')
                continue
            what, action = "pick", {"ids": [reply.option]}
        about = guide.about(stage, fork)
        if what == "pick":
            picked = [k for k, o in enumerate(question.options) if o["id"] in action["ids"]]
            if not picked:
                run.emit("guide_note", step=n, text="Pick one of the options shown")
                continue
            said = " or ".join(question.options[k]["label"] for k in picked)
            answers.append(guide.Answer("pick", frozenset(fork.options[k].n for k in picked), f"{about}: {said}"))
        else:
            said = {"any": "any of these", "none": "none of these", "stop": "show what is left"}[what]
            answers.append(guide.Answer(what, text=f"{about}: {said}" if what != "stop" else "Show what is left"))
        run.emit("answered", step=n, action=what, ids=list(action.get("ids") or []), text=answers[-1].text)


def usage_totals(lines: list[dict]) -> dict:
    """Add up one batch of logged call lines into call/token/dollar totals."""
    # a reply given back from the cache is no call
    calls = sum(not line.get("cached") for line in lines)
    input_tokens = sum(line["usage"]["input_tokens"] for line in lines)
    cached_tokens = sum(line["usage"].get("cached_tokens", 0) for line in lines)
    output_tokens = sum(line["usage"]["output_tokens"] for line in lines)
    reasoning_tokens = sum(line["usage"]["reasoning_tokens"] for line in lines)
    return {
        "calls": calls,
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "dollars": sum(map(_dollars, lines)),
    }


def _dollars(line: dict) -> float:
    """An LLM line is priced by its model and the lane it was served on; a model with no
    price (a local one) costs GPU time only."""
    lanes = config.LLM_PRICES.get(line.get("model"))
    if lanes is None:
        return 0.0
    served = line.get("service_tier", config.LLM_SERVICE_TIER)
    # "priority" is the fast lane's old name, which the API still takes
    lane = lanes.get("fast" if served == "priority" else served, lanes["default"])
    cached = line["usage"].get("cached_tokens", 0)
    tokens = (line["usage"]["input_tokens"] - cached, cached, line["usage"]["output_tokens"])
    return sum(count * price for count, price in zip(tokens, lane)) / 1e6


def _lake_event(probe: Probe, lake_name: str) -> dict:
    databases: dict[str, dict] = {}
    for table_id, table in probe.tables.items():
        entry = databases.setdefault(
            table["database"],
            {"name": table["database"], "readable": table["database_readable"], "tables": []},
        )
        entry["tables"].append(
            {
                "id": table_id,
                "name": table["name"],
                "readable": table["readable"],
                "path": probe.path("table", table_id),
                "rows": table["row_count"],
            }
        )
    for entry in databases.values():
        entry["tables"].sort(key=lambda table: table["name"])
    return {
        "name": lake_name,
        "databases": sorted(databases.values(), key=lambda entry: entry["readable"]),
    }


class Lake:
    """One served lake: everything a run on it needs, loaded once."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.probe = Probe(name)
        self.log_path = config.RUNS_DIR / f"ask_{name}.jsonl"
        # lines before this belong to an earlier session; /usage's "session" totals start here
        self.start_offset = self.log_path.stat().st_size if self.log_path.exists() else 0
        records = config.questions(name)
        self.questions = [record["question"] for record in records]
        # the rest of each record is a label: /gold shows it to the person watching, a run never reads it
        self.labels = {record["question"]: record for record in records}
        self.sources = {path.stem: path for path in config.lake(name)["databases"]}
        self._map: dict | None = None
        self._columns: list[dict] | None = None
        self._graph: candidates.Graph | None = None

    def graph(self) -> candidates.Graph:
        """The lake's join graph for the search, built on first use."""
        if self._graph is None:
            self._graph = candidates.Graph(self.probe)
        return self._graph

    def map(self) -> dict:
        """The lake on the page's 2D map, laid out on first use."""
        if self._map is None:
            self._map = lakemap.lake_map(self.probe)
        return self._map

    def columns(self) -> list[dict]:
        """The lake's columns on the same map, laid out on first use."""
        if self._columns is None:
            self._columns = lakemap.lake_columns(self.probe)
        return self._columns

    def where(self) -> dict[int, tuple[float, float]]:
        return {table["id"]: table["xy"] for table in self.map()["tables"]}


class Site(ThreadingHTTPServer):
    """The server and every lake it serves, each loaded once."""

    def __init__(self, lake_names: list[str], port: int, host: str = "127.0.0.1") -> None:
        self.lakes = {name: Lake(name) for name in lake_names}
        self.current: Run | None = None
        self.runs = 0
        self.lock = threading.Lock()
        super().__init__((host, port), Handler)


class Handler(BaseHTTPRequestHandler):
    server: Site

    def do_GET(self) -> None:
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/":
            page = config.ROOT / "ui" / "index.html"
            if not page.exists():
                self._send(404, "text/plain; charset=utf-8", f"no page at {page}".encode())
            else:
                self._send(200, "text/html; charset=utf-8", page.read_bytes())
        elif url.path == "/lakes":
            self._json(200, list(self.server.lakes))
        elif url.path == "/questions":
            lake = self._named(query.get("lake", [""])[0])
            if lake is not None:
                self._json(200, lake.questions)
        elif url.path == "/lake":
            lake = self._named(query.get("lake", [""])[0])
            if lake is not None:
                self._json(200, _lake_event(lake.probe, lake.name))
        elif url.path == "/map":
            lake = self._named(query.get("lake", [""])[0])
            if lake is not None:
                self._json(200, lake.columns() if query.get("columns") else lake.map())
        elif url.path == "/gold":
            lake = self._named(query.get("lake", [""])[0])
            if lake is not None:
                self._json(200, self._gold(lake, query.get("question", [""])[0]))
        elif url.path == "/table":
            lake = self._named(query.get("lake", [""])[0])
            if lake is not None:
                raw_id = query.get("id", [""])[0]
                try:
                    payload = self._table(lake, raw_id)
                except (KeyError, sqlite3.Error, OSError) as err:
                    self._json(400, {"error": f"table {raw_id!r}: {err}"})
                else:
                    if payload is None:
                        self._json(400, {"error": f"unknown table {raw_id!r}"})
                    else:
                        self._json(200, payload)
        elif url.path == "/chats":
            current = self.server.current
            self._json(200, {
                "chats": chats.listing(), "folders": chats.folders(),
                "current": None if current is None or current.chat is None
                else {"chat": current.chat, "live": not current.finished},
            })
        elif url.path.startswith("/chats/"):
            try:
                data = chats.load(url.path[len("/chats/"):])
            except ValueError:
                data = None
            if data is None:
                self._json(404, {"error": "no such chat"})
            else:
                current = self.server.current
                # the server's current run, when it is this chat's: the page follows it live
                data["live_run"] = current.uid if current is not None and current.chat == data["id"] else None
                self._json(200, data)
        elif url.path == "/rows":
            lake = self._named(query.get("lake", [""])[0])
            if lake is not None:
                one = lambda key: query.get(key, [""])[0]
                try:
                    payload = _rows(lake.probe, int(one("table")), int(one("column")) if one("column") else None,
                                    one("q"), int(one("page") or 0))
                except (KeyError, ValueError, sqlite3.Error, OSError) as err:
                    self._json(400, {"error": f"rows: {err}"})
                else:
                    self._json(200, payload)
        elif url.path in ("/result", "/export"):
            one = lambda key: query.get(key, [""])[0]
            found = self._result(one("id"))
            if found is not None:
                result, path = found
                try:
                    if url.path == "/result":
                        page = answer.page_of(path, result.sql, int(one("page") or 0), RESULT_PAGE, one("q"))
                        page["rows"] = [[_value(v) for v in row] for row in page["rows"]]
                        self._json(200, page)
                    else:
                        self._export(result, path, one("format"), one("q"))
                except (ValueError, sqlite3.Error, OSError) as err:
                    self._json(400, {"error": f"result: {err}"})
        elif url.path == "/peek":
            self._peek(query.get("option", [""])[0])
        elif url.path == "/events":
            self._events()
        elif url.path == "/calls":
            self._json(200, self._calls())
        elif url.path == "/usage":
            self._json(200, self._usage())
        elif url.path == "/settings":
            self._json(200, self._settings())
        else:
            self._json(404, {"error": f"no endpoint {self.path}"})

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"] or 0)) or b"{}")
        run = self.server.current
        # a tab left on an older run names it, and must not act on the run after it
        if self.path not in ("/ask", "/settings") and run is not None and body.get("run") not in (None, run.number):
            self._json(409, {"error": f"this page shows run {body['run']}, not the current run"
                             f" {run.number}; reload the page"})
            return
        if self.path == "/ask":
            lake = self._named((body.get("lake") or "").strip())
            if lake is not None:
                self._ask(
                    lake,
                    (body.get("question") or "").strip(),
                    bool(body.get("check")),
                    chat=(body.get("chat") or "").strip() or None,
                    replay=body.get("replay") if isinstance(body.get("replay"), dict) else None,
                )
        elif self.path == "/guide":
            self._guide(body)
        elif self.path == "/approve":
            self._approve(body.get("keep"))
        elif self.path == "/parts":
            self._parts(body.get("entities") or [])
        elif self.path == "/cancel":
            self._cancel()
        elif self.path == "/query":
            self._query(body.get("ids") or [])
        elif self.path == "/route":
            self._route((body.get("text") or "").strip())
        elif self.path == "/follow":
            self._follow(
                (body.get("question") or "").strip(),
                (body.get("route") or "").strip(),
                bool(body.get("check")),
                bool(body.get("chosen")),
                (body.get("said") or "").strip(),
            )
        elif self.path == "/choose":
            self._choose((body.get("id") or "").strip())
        elif self.path == "/settings":
            self._set(body.get("model") or "", body.get("lane") or "", body.get("thinking", ...))
        elif self.path in ("/chats/move", "/chats/delete", "/folders"):
            self._chats(self.path, body)
        else:
            self._json(404, {"error": f"no endpoint {self.path}"})

    def _chats(self, path: str, body: dict) -> None:
        """Move a saved chat to a folder, delete one or all, or add, rename or delete a folder."""
        try:
            if path == "/chats/move":
                chats.move((body.get("id") or "").strip(), body.get("folder") or None)
            elif path == "/chats/delete":
                chat = None if body.get("all") else (body.get("id") or "").strip()
                if chat == "":
                    raise ValueError("delete needs an id, or all")
                with self.server.lock:
                    current = self.server.current
                    if current is not None and (chat is None or current.chat == chat):
                        with current.saving:
                            current.chat = None
                        if not current.finished:
                            self._stop(current)  # its chat is gone, and nothing could reach it again
                    chats.delete(chat)
            else:
                chats.edit_folder(body.get("action") or "", body.get("name") or "", body.get("to"))
        except (ValueError, OSError) as err:
            self._json(400, {"error": str(err)})
            return
        self._json(200, {"chats": chats.listing(), "folders": chats.folders()})

    def _named(self, name: str) -> Lake | None:
        """The lake a request names, the first served one when it names none, or None after a 400."""
        if not name:
            return next(iter(self.server.lakes.values()))
        lake = self.server.lakes.get(name)
        if lake is None:
            self._json(400, {"error": f"lake {name!r} is not served"})
        return lake

    def _ask(
        self,
        lake: Lake,
        question: str,
        check: bool = False,
        routed: dict | None = None,
        rewrite: tuple | None = None,
        chosen: bool = False,
        turns: list[dict] | None = None,
        offset: int | None = None,
        chat: str | None = None,
        replay: dict | None = None,
    ) -> None:
        if not question:
            self._json(400, {"error": "no question"})
            return
        previous = self.server.current
        if previous is not None and previous.finished and previous.thread is not None:
            # a cancelled run leaves its pause at once; a step in flight runs to its end
            previous.thread.join(1)
        with self.server.lock:
            current = self.server.current
            if current is not None and not current.finished:
                self._json(409, {"error": "a run is in progress"})
                return
            self.server.runs += 1
            if offset is None:
                offset = lake.log_path.stat().st_size if lake.log_path.exists() else 0
            run = Run(self.server.runs, lake, question, offset, check, replay)
            run.route, run.rewrite = routed, rewrite
            run.chosen_rewrite = chosen and rewrite is not None
            if current is not None and current.thread is not None and current.thread.is_alive():
                run.after = current.thread
            run.turns = list(turns or [])
            # a new question opens a new chat unless it goes on in a saved one
            try:
                run.chat = chat if chat and chats.load(chat) is not None else chats.new_id()
            except ValueError:
                run.chat = chats.new_id()
            run.thread = threading.Thread(target=_work, args=(run,), daemon=True)
            self.server.current = run
        run.thread.start()
        self._json(200, {"run": run.number})

    def _parts(self, given: list) -> None:
        """The user hands back the question's parts, fixed by hand, and the run goes on."""
        run = self.server.current
        if run is None or not run.checking:
            self._json(409, {"error": "no run is waiting for its parts"})
            return
        try:
            entities = _read_parts(given)
        except (ValueError, llm.ModelError) as error:
            self._json(400, {"error": str(error)})
            return
        _log_parts(run, entities)
        run.parts = entities
        run.checking = False
        run.checked.set()
        self._json(200, {"entities": [one.model_dump() for one in entities]})

    def _cancel(self) -> None:
        """The user drops the run in flight, so the next one can start right away."""
        with self.server.lock:
            run = self.server.current
            if run is None or run.finished:
                self._json(409, {"error": "no run is in progress"})
                return
            self._stop(run)
        self._json(200, {"run": run.number})

    def _stop(self, run: Run) -> None:
        run.cancelled.set()
        run.emit("cancelled")
        # whichever pause the run sits at, it wakes and exits
        run.chosen.set()
        run.checked.set()
        run.approved.set()
        run.actions.put({"action": "cancel"})

    def _guide(self, body: dict) -> None:
        """The person's action at a fork of the guided search, or a walk back from the
        interpretations left."""
        run = self.server.current
        what = body.get("action")
        if run is None:
            self._json(409, {"error": "no guided run is in progress"})
            return
        if what == "back" and run.waiting:
            run.back_to, run.waiting = int(body.get("to", 0)), False
            run.chosen.set()
            self._json(200, {"action": what})
            return
        if not run.guiding:
            self._json(409, {"error": "no fork is waiting for an answer"})
            return
        if what not in ("pick", "any", "none", "stop", "back", "text"):
            self._json(400, {"error": f"no guide action {what!r}"})
            return
        ids = body.get("ids") or []
        if what == "pick" and (not ids or any(i not in run.fork_ids for i in ids)):
            self._json(400, {"error": f"pick among {run.fork_ids}, not {ids}"})
            return
        if what == "back" and not 0 <= int(body.get("to", -1)) <= run.fork_step:
            self._json(400, {"error": f"walk back to a step from 0 to {run.fork_step}"})
            return
        if what == "text" and not (body.get("text") or "").strip():
            self._json(400, {"error": "no words typed"})
            return
        run.guiding = False
        run.actions.put({"action": what, "ids": ids, "to": int(body.get("to", 0)),
                         "text": (body.get("text") or "").strip()})
        self._json(200, {"action": what})

    def _peek(self, name: str) -> None:
        """One option of the fork on screen: where it places the part, what the catalog says
        of that place, the tables and joins of its likeliest interpretation, and the first
        rows that interpretation reads, with how many there are (None past the step limit)."""
        run = self.server.current
        if run is None or not run.guiding or run.fork_now is None:
            self._json(409, {"error": "no question with options is waiting"})
            return
        fork, axis = run.fork_now
        names = [option.id for option in axis.options]
        if name not in names:
            self._json(400, {"error": f"no option {name!r}; the options are {names}"})
            return
        k = names.index(name)
        option, best = axis.options[k], fork.options[k].best
        probe, graph, stage = run.lake.probe, run.lake.graph(), run.stage
        sql, headers = guide.peek_query(probe, graph, stage, best)
        path = probe.tables[min(best.tables)]["database_path"]
        rows, count, slow = [], None, False
        try:
            rows = solve.first_rows(path, sql, PEEK)
        except sqlite3.Error:
            slow = True  # past the step limit: no rows to show, which is not "no rows"
        if not slow:
            try:
                count = solve.first_rows(path, f"SELECT count(*) FROM ({sql})", 1)[0][0]
            except sqlite3.Error:
                pass  # rows shown, too many to count quickly
        placed = [j for j, h in enumerate(best.holders) if h is not None]
        held = best.holders[fork.part] if fork.part is not None else None
        # a table fork is about the table, whichever of its columns is likeliest
        column = None if held is None or fork.kind == "table" else held.column
        self._json(200, {
            "option": name,
            "slow": slow,
            "kind": fork.kind,
            "part": None if fork.part is None else stage.entities[fork.part].attribute,
            "place": option.column if fork.kind in ("table", "column") else None,
            "value": option.value,
            "reason": option.reason,
            "description": option.description,
            "database": best.database,
            "tables": sorted(probe.path("table", t) for t in best.tables),
            "joins": guide._links(probe, graph, best),
            "columns": headers,
            "rows": [[_cell(v) for v in row] for row in rows],
            "count": count,
            # the column of the part the question is about, and where to read its whole table
            "highlight": placed.index(fork.part) if held is not None else None,
            "table": None if held is None else held.table,
            "column": column,
            "table_name": None if held is None else probe.tables[held.table]["name"],
            "table_rows": None if held is None else probe.tables[held.table]["row_count"],
            "column_name": None if column is None else probe.columns[column]["name"],
            "distinct": None if column is None else probe.columns[column]["distinct_count"],
            "left_out": [stage.entities[j].attribute for j in best.left_out],
        })

    def _approve(self, keep: list | None) -> None:
        """The person approves the places after the judge: as judged when `keep` is null, else
        per part the [table, column or null] places kept, the rest dropped."""
        run = self.server.current
        if run is None or not run.approving or run.stage is None:
            self._json(409, {"error": "no run is waiting for its places"})
            return
        try:
            _approved(run, keep)
        except ValueError as error:
            self._json(400, {"error": str(error)})
            return
        self._json(200, {"approved": True})

    def _query(self, ids: list[str]) -> None:
        run = self.server.current
        if run is None or not run.waiting:
            self._json(409, {"error": "no run is waiting for a selection"})
            return
        if not ids or any(name not in run.live for name in ids):
            self._json(400, {"error": f"choose among the live interpretations {run.live}, not {ids}"})
            return
        run.selected = list(ids)
        run.waiting = False
        run.chosen.set()
        self._json(200, {"selected": run.selected})

    def _result(self, name: str) -> tuple[answer.Result, str] | None:
        """A query result of the run in view, by its interpretation id, with the database it
        reads; None after a 404."""
        run = self.server.current
        for result in run.results if run is not None else []:
            if result.interpretation.id == name and result.error is None:
                probe = run.lake.probe
                table = probe.find(result.interpretation.tables[0])[1]
                return result, probe.tables[table]["database_path"]
        self._json(404, {"error": f"no result {name!r} in the run in view"})
        return None

    def _export(self, result: answer.Result, path: str, form: str, text: str) -> None:
        """Every row of a result (or those holding `text`) as a CSV or JSON file, written as
        it is read, so a large result is never held whole."""
        if form not in ("csv", "json"):
            self._json(400, {"error": f"export as csv or json, not {form!r}"})
            return
        rows = answer.every_row(path, result.sql, text)
        columns = next(rows)
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8" if form == "csv" else "application/json")
        self.send_header("Content-Disposition", f'attachment; filename="amigo_{result.interpretation.id}.{form}"')
        self.end_headers()
        if form == "csv":
            out = io.TextIOWrapper(self.wfile, encoding="utf-8", newline="", write_through=True)
            writer = csv.writer(out)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(["" if v is None else v for v in row])
            out.detach()
            return
        # one object per row; a name used twice gets _2, _3 after it
        keys, seen = [], {}
        for name in columns:
            seen[name] = seen.get(name, 0) + 1
            keys.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
        self.wfile.write(b"[")
        for n, row in enumerate(rows):
            line = json.dumps(dict(zip(keys, (_value(v) for v in row))), ensure_ascii=False)
            self.wfile.write(((",\n" if n else "\n") + line).encode())
        self.wfile.write(b"\n]\n")

    def _finished_run(self) -> Run | None:
        """The run a follow-up builds on, or None after a 409."""
        run = self.server.current
        if run is None or not run.finished or run.cancelled.is_set():
            self._json(409, {"error": "no finished run to follow up on"})
            return None
        return run

    def _answered(self) -> tuple[Run, answer.Result] | None:
        """The finished run and the one result a follow-up builds on, or None after a 409."""
        run = self._finished_run()
        if run is None:
            return None
        if run.chosen_id is not None:
            picked = [one for one in run.results if one.interpretation.id == run.chosen_id]
            if not picked or picked[0].error is not None:
                self._json(
                    409,
                    {"error": f"the chosen interpretation {run.chosen_id} answered nothing to follow up on"},
                )
                return None
            return run, picked[0]
        got = [result for result in run.results if result.error is None]
        if not got:
            self._json(409, {"error": "the finished run answered nothing to follow up on"})
            return None
        if len(got) > 1:
            self._json(409, {"error": "pick an interpretation first"})
            return None
        return run, got[0]

    def _route(self, text: str) -> None:
        """Typed words after a finished run: one call says whether only the SQL has to change."""
        if not text:
            self._json(400, {"error": "route needs text"})
            return
        answered = self._answered()
        if answered is None:
            return
        run, result = answered
        run.route_offset = (
            run.lake.log_path.stat().st_size if run.lake.log_path.exists() else 0
        )
        try:
            decision = route.decide(
                run.lake.probe, run.question, run.turns, result, text, run.lake.log_path
            )
        except llm.ModelError as err:
            self._json(502, {"error": str(err)})
            return
        self._json(200, decision)

    def _follow(
        self, question: str, which: str, check: bool, chosen: bool = False, said: str = "",
    ) -> None:
        """The routed follow-up runs: a rewrite queries the same interpretation, a restart is
        cold. The check toggle is the page's now, not the old run's; `chosen`
        says the person picked the route, not the router."""
        if which not in route.WHY:
            self._json(400, {"error": f"no route {which!r}"})
            return
        if not question:
            self._json(400, {"error": "follow needs a question"})
            return
        carried = route.BANNED.findall(question)
        if carried:
            self._json(400, {"error": f"the question carries {carried}"})
            return
        rewrite = None
        if which == "rewrite":
            answered = self._answered()
            if answered is None:
                return
            run, result = answered
            rewrite = (run.entities, result.interpretation, run.question, result.sql)
        else:
            run = self._finished_run()
            if run is None:
                return
        event = {"route": which, "question": question, "why": route.WHY[which]}
        with run.lake.log_path.open("a") as handle:
            handle.write(json.dumps({"kind": "route", "original": run.question, **event}) + "\n")
        if said:
            event["said"] = said  # what the person typed, for the saved chat
        self._ask(
            run.lake,
            question,
            check,
            routed=event,
            rewrite=rewrite,
            chosen=chosen,
            turns=run.turns,
            offset=run.route_offset,
            chat=run.chat,
        )

    def _gold(self, lake: Lake, question: str) -> dict:
        """The benchmark label of one listed question, for the person watching only."""
        item = lake.labels.get(question)
        if item is None:
            return {}
        probe = lake.probe
        sql = item["SQL"].strip().rstrip(";")
        tables: list[str] = []
        try:
            table_ids, _ = answer.read_ids(probe, item["db_id"], sql)
            tables = [probe.path("table", table_id) for table_id in table_ids]
            with closing(index.open_source(str(lake.sources[item["db_id"]]))) as conn:
                cursor = conn.execute(f"SELECT * FROM ({sql}) LIMIT 5")
                result = {
                    "columns": [column[0] for column in cursor.description],
                    "rows": [list(row) for row in cursor.fetchall()],
                    "count": conn.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0],
                }
        except (KeyError, sqlite3.Error, OSError) as err:
            result = {"error": str(err)}
        return {
            "database": item["db_id"],
            "tables": tables,
            "sql": item["SQL"],
            "evidence": item.get("evidence", ""),
            "answer": result,
        }

    def _table(self, lake: Lake, raw_id: str) -> dict | None:
        """One table's card plus 5 real rows from its source database, for the table viewer."""
        probe = lake.probe
        try:
            table_id = int(raw_id)
        except ValueError:
            return None
        table = probe.tables.get(table_id)
        if table is None:
            return None
        columns = [
            {
                "name": column["name"],
                "readable": column["readable"],
                "kind": column["kind"],
                "description": column["description"],
                "value_description": column["value_description"],
                "distinct_count": column["distinct_count"],
                "empty_share": column["empty_share"],
                "is_unique": bool(column["is_unique"]),
                "samples": json.loads(column["samples"] or "[]"),
            }
            for column in probe.columns.values()
            if column["table_id"] == table_id
        ]
        with closing(index.open_source(table["database_path"])) as source:
            cursor = source.execute(f'SELECT * FROM "{table["name"]}" LIMIT 5')
            header = [column[0] for column in cursor.description]
            rows = [[_cell(value) for value in row] for row in cursor.fetchall()]
        return {
            "name": table["name"],
            "readable": table["readable"],
            "description": table["description"],
            "row_count": table["row_count"],
            "database": table["database"],
            "columns": columns,
            "header": header,
            "rows": rows,
        }

    def _choose(self, name: str) -> None:
        """The user says which interpretation is the answer; the run log keeps it."""
        run = self.server.current
        if run is None or name not in run.kept:
            self._json(409, {"error": f"no interpretation {name} in this run"})
            return
        run.chosen_id = name
        # the id alone names different columns in two runs, so the line says what it is
        one = run.kept[name]
        llm.append(
            run.lake.log_path,
            {
                "kind": "chosen",
                "question": run.question,
                "id": name,
                "tables": one.tables,
                "bindings": {binding.entity: binding.columns for binding in one.bindings},
            },
        )
        run.emit("chosen", id=name)
        self._json(200, {"id": name})

    def _log_lines(self, lake: Lake, offset: int) -> list[dict]:
        if not lake.log_path.exists():
            return []
        with lake.log_path.open("rb") as handle:
            handle.seek(offset)
            # the last line can still be half written, so keep whole lines only
            lines = handle.read().split(b"\n")[:-1]
        # the log also holds the user's `chosen` lines; only model calls carry usage
        return [line for line in map(json.loads, lines) if "usage" in line]

    def _calls(self) -> list[dict]:
        run = self.server.current
        if run is None:
            return []
        return [
            {key: line[key] for key in CALL_KEYS if key in line}
            for line in self._log_lines(run.lake, run.offset)
        ]

    def _usage(self) -> dict:
        run = self.server.current
        lake = run.lake if run is not None else next(iter(self.server.lakes.values()))
        run_lines = self._log_lines(lake, run.offset) if run is not None else []
        return {
            "run": usage_totals(run_lines),
            "session": usage_totals(self._log_lines(lake, lake.start_offset)),
        }

    def _settings(self) -> dict:
        """The model and lane the next LLM call uses, and the ones it may switch to."""
        # a local model has one lane and no price per token: it costs GPU time only
        models = {name: {"flex": None} for name in config.LOCAL_MODELS}
        try:
            models |= {name: config.LLM_PRICES[name] for name in llm.models()}
        except openai.OpenAIError as err:
            log.warning("could not list the endpoint's models: %s", err)
        return {
            "model": config.LLM_MODEL,
            "lane": config.LLM_SERVICE_TIER,
            "thinking": config.THINKING,
            "models": models,
            "efforts": {name: config.EFFORTS.get(name) for name in models},
        }

    def _set(self, model: str, lane: str, thinking=...) -> None:
        """A field left out keeps its value, so a tab that missed another tab's switch cannot
        undo it; a model without the lane in use falls back to flex, which every one has, and
        one without the thinking level in use goes back to each step's own level."""
        model = model or config.LLM_MODEL
        levels = config.EFFORTS.get(model)
        if thinking is ...:
            thinking = config.THINKING if config.THINKING in (levels or ()) else None
        if thinking is not None and thinking not in (levels or ()):
            self._json(400, {"error": f"{model} has no thinking level {thinking} to offer"})
            return
        lanes = self._settings()["models"].get(model, {})
        if not lane:
            lane = config.LLM_SERVICE_TIER if config.LLM_SERVICE_TIER in lanes else "flex"
        if lane not in lanes:
            self._json(400, {"error": f"{model} has no {lane} lane to offer"})
            return
        # read at each call, so the switch holds from the next LLM call on, in a run too
        config.LLM_MODEL, config.LLM_SERVICE_TIER, config.THINKING = model, lane, thinking
        log.info("LLM calls now go to %s on the %s lane, thinking %s", model, lane, thinking or "at each step's level")
        self._json(200, self._settings())

    def _events(self) -> None:
        run = self.server.current
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if run is None:
            self._event({"type": "idle"})
            return
        seen = 0
        try:
            while True:
                event = None
                with run.condition:
                    while seen >= len(run.events):
                        if run.finished:
                            return
                        if not run.condition.wait(timeout=WAIT):
                            break  # nothing new: the keep-alive says whether the page is still there
                    if seen < len(run.events):
                        event = run.events[seen]
                        seen += 1
                if event is None:
                    self.wfile.write(b": keep-alive\n\n")
                    continue
                self._event(event)
                if event["type"] in ("done", "error", "cancelled"):
                    return
        except (BrokenPipeError, ConnectionResetError):
            return  # the page closed the stream; the run carries on without it

    def _event(self, event: dict) -> None:
        self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())

    def _json(self, status: int, payload: object) -> None:
        self._send(status, "application/json", json.dumps(payload).encode())

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # a request line logged here would land in the run's own event stream
        pass


def built_lakes() -> list[str]:
    """The lakes of lakes.json whose layer and embeddings are both on disk, in file order."""
    names = []
    for name in json.loads(config.LAKE_DEFS.read_text()):
        if all(path.exists() for path in layer.paths(name)):
            names.append(name)
        else:
            log.info("serve: skipping %s, not built", name)
    return names


def run(lake_names: list[str], port: int, host: str = "127.0.0.1") -> None:
    names = lake_names or built_lakes()
    if not names:
        raise RuntimeError("serve: no lake is built; run `python -m amigo build <lake>` first")
    site = Site(names, port, host)
    log.info("serve: lakes %s on http://%s:%d", ", ".join(names), *site.server_address[:2])
    site.serve_forever()
