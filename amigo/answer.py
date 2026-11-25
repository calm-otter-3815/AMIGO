"""Step 6 and 7: one query per interpretation, repair, presentation (PLAN.md 13.2)."""

import json
import logging
import re
import sqlite3
import string
import threading
from itertools import count
from contextlib import closing, contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import BaseModel

from . import bundle, config, index, llm, solve
from .probe import Probe

log = logging.getLogger(__name__)

CELL_CHARS = 40
# the answer in words quotes a cell whole: only a text body longer than this is cut
SAY_CELL_CHARS = 200
# ponytail: 60 values still fit in one prompt line; a wider column only gets its count
VALUE_LINES = 60

COLUMN_FIELDS = (
    "name",
    "readable",
    "type",
    "kind",
    "description",
    "value_description",
    "distinct_count",
    "empty_share",
    "samples",
    "is_unique",
    "is_pk",
    "min",
    "max",
    "date_format",
    "date_min",
    "date_max",
)


class Query(BaseModel):
    sentence: str
    sql: str


@dataclass
class Result:
    interpretation: solve.Interpretation
    sentence: str
    sql: str
    columns: list[str]
    rows: list[tuple]
    more: bool
    error: str | None
    said: str | None = None  # the answer in words, read off the rows


class Said(BaseModel):
    answer: str


@dataclass
class Answer:
    question: str
    entities: list[llm.Entity]
    fanout: solve.FanOut
    results: list[Result]


def _sql_name(probe: Probe, path: str) -> str:
    """A table or column path as the query writes it: the query runs against one
    database, so its name is left out."""
    kind, card_id = probe.find(path)
    if kind == "table":
        return probe.tables[card_id]["name"]
    column = probe.columns[card_id]
    return f"{probe.tables[column['table_id']]['name']}.{column['name']}"


def _card_text(probe: Probe, name: str) -> str:
    kind, card_id = probe.find(name)
    if kind == "column":
        column = probe.columns[card_id]
        fields = {field: column[field] for field in COLUMN_FIELDS}
        fields["samples"] = json.loads(column["samples"] or "[]")
        return "\n".join(f"{field}: {value}" for field, value in fields.items())
    table = probe.tables[card_id]
    return "\n".join(
        [
            f"name: {table['name']}",
            f"readable: {table['readable']}",
            f"description: {bundle._one_line(table['description'])}",
            f"rows: {table['row_count']}",
            f"primary key: {', '.join(json.loads(table['primary_key'])) or 'none'}",
            "columns: "
            + ", ".join(
                f"{table['name']}.{column['name']}"
                for column in probe.columns.values()
                if column["table_id"] == card_id
            ),
        ]
    )


def _join_lines(probe: Probe, joins: list[tuple[str, str]], either: list[list[tuple[str, str]]] = ()) -> list[str]:
    """One line per join; the parts of a composite key, which join one table pair, share it.
    A join that holds by any one of its links is one line of them joined by "or"."""
    grouped = [tuple(pair) for group in either for pair in group]
    lines = ["  " + " or ".join(f"{_join_side(probe, a)} -> {_join_side(probe, b)}" for a, b in group)
             for group in either]
    by_pair: dict[tuple[str, str], list[str]] = {}
    for a, b in joins:
        if (a, b) in grouped:
            continue
        pair = (a.rsplit(".", 1)[0], b.rsplit(".", 1)[0])
        by_pair.setdefault(pair, []).append(f"{_join_side(probe, a)} -> {_join_side(probe, b)}")
    return ["  " + " and ".join(parts) for parts in by_pair.values()] + lines


def _join_side(probe: Probe, path: str) -> str:
    return solve.join_side(probe, probe.find(path)[1], _sql_name(probe, path))


def context(
    probe: Probe, tables: list[str], columns: list[str], joins: list[tuple[str, str]] = (),
    either: list[list[tuple[str, str]]] = (),
) -> str:
    """The cards of an interpretation's tables and bound columns, and the joins it makes.
    A bound table is already among the table cards."""
    links = _join_lines(probe, list(joins), [list(map(tuple, group)) for group in either])
    # the table cards list column paths only, so the bound columns are shown in full
    cards = [_card_text(probe, name) for name in tables]
    cards += [
        f"COLUMN {_sql_name(probe, name)}\n" + _card_text(probe, name) + _values(probe, name)
        for name in dict.fromkeys(columns)
        if probe.find(name)[0] == "column"
    ]
    return "\n\n".join(cards) + "\n\nLINKS\n" + ("\n".join(links) or "  none")


def _values(probe: Probe, name: str) -> str:
    """Every value of a small bound text column, so the SQL can use the real spelling."""
    column_id = probe.find(name)[1]
    column = probe.columns[column_id]
    if column["kind"] != "text":
        return ""
    count = column["distinct_count"]
    if count is not None and count > VALUE_LINES:
        return f"\ndistinct values: {count}"
    values = probe.peek(column_id, VALUE_LINES)
    return "\nvalues: " + ", ".join(_sql_text(value) for value in values)


def _sql_text(value: str) -> str:
    """A stored value as the SQL literal that matches it: O'Brien is 'O''Brien', and the
    spaces of 'YES  ' stay. Python's repr would write "O'Brien", which SQLite reads as a
    column name."""
    return "'" + value.replace("'", "''") + "'"


# what a query may do: select, read and call functions; SQLite refuses anything else
READ_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}
NUMBER = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")


def reads(path: str, sql: str) -> set[tuple[str, str]]:
    """The (table, column) pairs a query reads, lower case; column "" for COUNT(*).

    SQLite's authorizer sees every read while it prepares the statement, and EXPLAIN
    prepares it without running it.
    """
    found = set()

    def authorize(action, table, column, *_):
        if action not in READ_ACTIONS:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_READ and table:
            found.add((table.lower(), (column or "").lower()))
        return sqlite3.SQLITE_OK

    with closing(index.open_source(path)) as conn:
        conn.set_authorizer(authorize)
        conn.execute("EXPLAIN " + sql)
    return found


def read_ids(probe: Probe, database: str, sql: str) -> tuple[list[int], list[int]]:
    """The table ids and column ids a query over one database reads, from `reads`: a
    CTE name, a subquery or a join with no alias is never taken for a table."""
    tables = {
        t["name"].lower(): table_id
        for table_id, t in probe.tables.items()
        if t["database"] == database
    }
    columns = {
        (c["table_id"], c["name"].lower()): column_id
        for column_id, c in probe.columns.items()
        if c["table_id"] in tables.values()
    }
    path = probe.tables[next(iter(tables.values()))]["database_path"]
    pairs = [(tables[t], c) for t, c in reads(path, sql) if t in tables]
    return (
        sorted({table_id for table_id, _ in pairs}),
        sorted({columns[pair] for pair in pairs if pair in columns}),
    )


def _name(probe: Probe, path: str) -> tuple[str, str]:
    """(table, column) of a column path, (table, "") of a table path, lower case."""
    kind, card_id = probe.find(path)
    if kind == "table":
        return probe.tables[card_id]["name"].lower(), ""
    column = probe.columns[card_id]
    return probe.tables[column["table_id"]]["name"].lower(), column["name"].lower()


def _mentions(sql: str, value: str) -> bool:
    """Whether the SQL holds this stored value as a quoted literal, or bare when a number."""
    if "'" + value.lower().replace("'", "''") + "'" in sql.lower():
        return True
    return bool(NUMBER.fullmatch(value)) and bool(
        re.search(rf"(?<![\w.']){re.escape(value)}(?![\w.'])", sql)
    )


def departures(
    probe: Probe,
    interpretation: solve.Interpretation,
    sql: str,
    found: set[tuple[str, str]],
    earlier: set[tuple[str, str]] | None = None,
    chosen: bool = False,
) -> list[str]:
    """Where a query leaves its interpretation, one line each; empty when it follows it.

    It may read only the interpretation's tables, and no column another role of the
    same join stands for. It must use every bound column, every column of the joins
    the interpretation makes, and every stored value a binding fixes. A rewrite may
    drop a binding the new question no longer needs, but reads nothing the `earlier`
    query did not: a new column is for pick and clarify to choose, not the SQL. When the
    person chose the rewrite themselves (`chosen`), it may read any column of those tables.
    """
    one = interpretation
    tables = {_name(probe, path)[0] for path in one.tables}
    read = {table for table, _ in found}
    problems = [
        f"it reads the table {table}, which is not one of the tables in the context"
        for table in sorted(read - tables)
    ]
    problems += [
        f"it uses {_sql_name(probe, path)}, which is not the join this interpretation makes"
        for path in one.avoid
        if _name(probe, path) in found
    ]
    if earlier is not None and chosen:
        return problems
    if earlier is not None:
        return problems + [
            f"it uses {table}.{column}, which the earlier query did not: a follow-up"
            " may only change that query's filters, aggregates, grouping, order or limit"
            for table, column in sorted(found - earlier)
            # COUNT(*) reads a table with no column: a follow-up "how many?" is not new
            if column
        ]
    needed = [c for b in one.bindings for c in b.columns] + [c for j in one.joins for c in j]
    for path in dict.fromkeys(needed):
        table, column = _name(probe, path)
        if table not in read or (column and (table, column) not in found):
            problems.append(
                f"it never uses {_sql_name(probe, path)}, which a binding or a link names"
            )
    for binding in one.bindings:
        for path, value in [(binding.column, binding.value), *binding.also]:
            if value is not None and not _mentions(sql, value):
                problems.append(
                    f"it never compares {_sql_name(probe, path)} with the stored value"
                    f" {_sql_text(value)}"
                )
    return problems


STEPS_PER_CHECK = 10_000


@contextmanager
def _reading(path: str, sql: str):
    """A cursor over one statement, read-only, stopped past SQL_MAX_STEPS."""
    if not sql.strip():
        raise sqlite3.OperationalError("the query is empty")
    checks = count(1)
    with closing(index.open_source(path)) as conn:
        # a read-only connection still lets VACUUM INTO write a copy of the database
        conn.set_authorizer(
            lambda action, *_: sqlite3.SQLITE_OK if action in READ_ACTIONS else sqlite3.SQLITE_DENY
        )
        # the handler runs every STEPS_PER_CHECK steps; a non-zero return interrupts the
        # statement, which raises OperationalError
        conn.set_progress_handler(
            lambda: 1 if next(checks) * STEPS_PER_CHECK > config.SQL_MAX_STEPS else 0,
            STEPS_PER_CHECK,
        )
        yield conn.execute(sql)


def run_sql(path: str, sql: str) -> tuple[list[str], list[tuple], bool]:
    """Run one statement read-only, keep at most SQL_MAX_ROWS rows, flag if more."""
    with _reading(path, sql) as cursor:
        rows = cursor.fetchmany(config.SQL_MAX_ROWS + 1)
        columns = [described[0] for described in cursor.description or []]
    return columns, rows[: config.SQL_MAX_ROWS], len(rows) > config.SQL_MAX_ROWS


def _holds(row: tuple, text: str) -> bool:
    """Whether some cell of the row, read as text (null as "null"), holds `text`, ignoring case."""
    return any(text in ("null" if v is None else str(v)).lower() for v in row)


def every_row(path: str, sql: str, text: str = ""):
    """The columns of a statement's result and every row of it, one at a time, or only the
    rows holding `text` in some cell; read-only."""
    text = text.lower()
    with _reading(path, sql) as cursor:
        yield [described[0] for described in cursor.description or []]
        for row in cursor:
            if not text or _holds(row, text):
                yield row


def page_of(path: str, sql: str, page: int, size: int, text: str = "") -> dict:
    """One page of a statement's result (the rows holding `text` when given): its columns,
    rows, how many rows match, and the page count. The statement runs again for each page,
    so no result is held in memory; a page past the last gives the last."""
    rows = every_row(path, sql, text)
    columns, kept, matched = next(rows), [], 0
    for row in rows:
        if page * size <= matched < (page + 1) * size:
            kept.append(row)
        matched += 1
    pages = max(1, -(-matched // size))
    if page >= pages and matched:
        return page_of(path, sql, pages - 1, size, text)
    return {"columns": columns, "rows": kept, "matched": matched, "page": min(page, pages - 1), "pages": pages}


PREVIOUS = """Previous attempt, which failed:
{sql}

SQLite error:
{error}
"""

STRAYED = """Previous attempt, which does not follow the interpretation:
{sql}

What is wrong with it:
{problems}
"""

NO_ROWS = """Previous attempt, which ran without error but returned no rows:
{sql}

Check every compared value against the stored spelling shown in the bindings and the
values listed in the context. If the SQL is already right and the data simply holds no
such rows, return the same SQL unchanged.
"""

REWRITE = """This is a rewrite. The earlier question was:
{question}

The SQL that answered it:
{sql}

The bindings above were made for that earlier question. Rewrite the SQL for the
question asked now: keep the bindings it still asks for, drop every binding and every
condition it no longer asks for, and add what it newly asks for from the columns shown
in the context. Nothing outside the context may be used.
"""


def _entity(entities: list[llm.Entity], binding: solve.Binding) -> llm.Entity:
    return entities[int(binding.entity[1:]) - 1]


def _binding_line(probe: Probe, entities: list[llm.Entity], binding: solve.Binding) -> str:
    """`e1: county = "Alameda" -> california_schools.schools.County = 'Alameda'`, or
    `e2: account type = "savings" -> table savings`."""
    entity = _entity(entities, binding)
    line = f"{binding.entity}: {entity.attribute}"
    if entity.literal is not None:
        line += f" = {bundle._as_written(entity.literal)}"
    table = "table " if probe.find(binding.column)[0] == "table" else ""
    line += f" -> {table}{_sql_name(probe, binding.column)}"
    if binding.value is not None:
        line += f" = {_sql_text(binding.value)}"
    # a value split over one row: every column of it is tested
    return "".join(
        [
            line,
            *(
                f" and {_sql_name(probe, column)}"
                + ("" if value is None else f" = {_sql_text(value)}")
                for column, value in binding.also
            ),
        ]
    )


def _left_lines(entities: list[llm.Entity], one: solve.Interpretation) -> list[str]:
    """`e2: character = "Batman" -> left out`: a part this interpretation does not use, so
    the query, its answer and its card never claim it."""
    lines = []
    for name in one.left_out:
        entity = entities[int(name[1:]) - 1]
        literal = "" if entity.literal is None else f" = {bundle._as_written(entity.literal)}"
        lines.append(f"{name}: {entity.attribute}{literal} -> left out")
    return lines


def _spelled_as_stored(
    probe: Probe, entities: list[llm.Entity], interpretation: solve.Interpretation, sql: str
) -> bool:
    """Whether the query writes every value of the question as stored: each part with a
    value is a text value code found in the data, written exactly so, or a table that
    holds it. A number, a date or a value left to the SQL step can still be written wrong."""
    for binding in interpretation.bindings:
        literal = _entity(entities, binding).literal
        if literal is None or probe.find(binding.column)[0] == "table":
            continue
        values = [binding.value, *(value for _, value in binding.also)]
        if literal.kind != "text" or None in values:
            return False
        if not all(_sql_text(value) in sql for value in values):
            return False
    return True


def query(
    probe: Probe,
    question: str,
    entities: list[llm.Entity],
    interpretation: solve.Interpretation,
    log_path: Path,
    rewrite: tuple[str, str] | None = None,
    stop: threading.Event | None = None,
    chosen: bool = False,
) -> Result:
    """One SQL call per interpretation, repaired from the SQLite error up to SQL_MAX_TRIES;
    none once `stop` is set. No rows is retried once, for a value spelled the wrong way,
    unless every value is already written as stored."""
    template = string.Template((config.PROMPTS_DIR / "sql.txt").read_text())
    # Connectivity has already checked that all the tables sit in one database
    path = probe.tables[probe.find(interpretation.tables[0])[1]]["database_path"]
    text = context(
        probe,
        interpretation.tables,
        [c for b in interpretation.bindings for c in b.columns],
        interpretation.joins,
        interpretation.either,
    )
    # a rewrite starts from the SQL that answered the earlier question, not from a failure,
    # and a repair keeps that block, or it would work from the old question's bindings
    rewritten = ""
    if rewrite is not None:
        rewritten = REWRITE.format(question=rewrite[0], sql=rewrite[1]) + "\n"
    previous = rewritten
    earlier = None if rewrite is None else reads(path, rewrite[1])
    reply, error = Query(sentence="", sql=""), ""
    # the first query that follows the interpretation but finds no rows, and what it reads
    empty: tuple[Result, set] | None = None
    for attempt in range(1, config.SQL_MAX_TRIES + 1):
        if stop is not None and stop.is_set():
            return Result(interpretation, reply.sentence, reply.sql, [], [], False, "stopped")
        label = f"sql {interpretation.id} {question[:40]}"
        if attempt > 1:
            label += f" repair {attempt - 1}"
        try:
            reply = llm.call(
                template.substitute(
                    question=question,
                    bindings="\n".join(
                        [_binding_line(probe, entities, b) for b in interpretation.bindings]
                        + _left_lines(entities, interpretation)
                    ),
                    context=text,
                    previous=previous,
                ),
                Query,
                log_path,
                label,
            )
        except llm.ModelError as err:
            # one interpretation without a query must not end the whole run
            return Result(interpretation, "", reply.sql, [], [], False, str(err))
        try:
            found = reads(path, reply.sql)
            problems = departures(probe, interpretation, reply.sql, found, earlier, chosen)
            if not problems:
                columns, rows, more = run_sql(path, reply.sql)
        except sqlite3.Error as err:
            error = str(err)
            log.info("sql %s try %d: %s", interpretation.id, attempt, error)
            previous = rewritten + PREVIOUS.format(sql=reply.sql, error=error)
            continue
        if problems:
            error = "the query does not follow the interpretation: " + "; ".join(problems)
            log.info("sql %s try %d: %s", interpretation.id, attempt, error)
            previous = rewritten + STRAYED.format(
                sql=reply.sql, problems="\n".join(f"- {one}" for one in problems)
            )
            continue
        if empty is not None and not found <= empty[1]:
            # the retry was for a spelling: reading something new asks something else
            log.info(
                "sql %s try %d: %d rows, not kept: it reads %s, which the query with no rows did not",
                interpretation.id, attempt, len(rows), ", ".join(f"{t}.{c}" for t, c in sorted(found - empty[1])),
            )
            return empty[0]
        log.info("sql %s try %d: %d rows", interpretation.id, attempt, len(rows))
        # no rows is not an error, but it is usually a value spelled the wrong way
        if not rows and empty is None:
            empty = Result(interpretation, reply.sentence, reply.sql, columns, [], False, None), found
            if _spelled_as_stored(probe, entities, interpretation, reply.sql):
                # no spelling is left to repair: a retry could only change what it asks
                return empty[0]
            previous = rewritten + NO_ROWS.format(sql=reply.sql)
            continue
        return Result(interpretation, reply.sentence, reply.sql, columns, rows, more, None)
    if empty is not None:
        return empty[0]
    tries = f"{config.SQL_MAX_TRIES} tries, the last one: {error}"
    return Result(interpretation, reply.sentence, reply.sql, [], [], False, tries)


# a number that starts a word, with its sign: not the 2 of "e2" or the 1 of "T1"
SAID_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")


def _numbers(text: str) -> list[str]:
    return [one.replace(",", "") for one in SAID_NUMBER.findall(text)]


def unshown(said: str, shown: list[str]) -> list[str]:
    """The numbers in an answer that nothing shown holds; rounding one is allowed,
    converting it is not: 41.8166 may be said 41.82, 0.4167 may not be said 42%."""
    known = [float(one) for text in shown for one in _numbers(text)]

    def rounds_to(k: float, one: str) -> bool:
        # half away from zero, as people round: 42.5 may be said 43
        return abs(k - float(one)) <= 0.5 * 10 ** -len(one.partition(".")[2]) + 1e-9

    return [one for one in _numbers(said) if not any(rounds_to(k, one) for k in known)]


def say(
    probe: Probe, question: str, entities: list[llm.Entity], result: Result, log_path: Path
) -> str | None:
    """The answer in words, read off the rows: one call, or none when there is nothing to
    read. Every number it says must be one the rows, the question or the bindings show."""
    if result.error is not None:
        return None
    if not result.rows:
        return "No rows match this interpretation."
    bindings = "\n".join(
        [_binding_line(probe, entities, b) for b in result.interpretation.bindings]
        + _left_lines(entities, result.interpretation)
    )
    count = f"more than {len(result.rows)}" if result.more else str(len(result.rows))
    rows = "\n".join(_grid(result.columns, result.rows, SAY_CELL_CHARS))
    shown = [question, bindings, result.sentence, count, rows]

    def check(reply: Said) -> None:
        if not reply.answer.strip():
            raise llm.ModelError("the answer holds no text")
        missing = unshown(reply.answer, shown)
        if missing:
            raise llm.ModelError(
                f"the answer says {missing}, which no row, the question or a binding shows"
            )

    template = string.Template((config.PROMPTS_DIR / "say.txt").read_text())
    try:
        reply = llm.call(
            template.substitute(
                question=question,
                bindings=bindings,
                sentence=result.sentence or "not given",
                count=count,
                rows=rows,
            ),
            Said,
            log_path,
            f"say {result.interpretation.id} {question[:40]}",
            check=check,
            effort=config.SAY_REASONING_EFFORT,
        )
    except llm.ModelError as err:
        # the rows are the answer; the words only help read them
        log.warning("say %s: %s", result.interpretation.id, err)
        return None
    return reply.answer.strip()


class Summary(BaseModel):
    id: str
    title: str
    meaning: str


class Summaries(BaseModel):
    interpretations: list[Summary]


def _place_line(probe: Probe, path: str) -> str:
    """What a table or column holds, for a person: its readable name, description and fill."""
    kind, card_id = probe.find(path)
    if kind == "table":
        table = probe.tables[card_id]
        return (f"table {table['name']}: {table['readable']}; "
                f"{bundle._one_line(table['description'])}; {table['row_count']} rows")
    column = probe.columns[card_id]
    return (f"{_sql_name(probe, path)}: {column['readable']}; {bundle._one_line(column['description'] or '')}; "
            f"empty on {column['empty_share']:.0%} of rows; {column['distinct_count']} distinct values")


def summaries(
    probe: Probe, question: str, entities: list[llm.Entity], cards: list[solve.Interpretation], log_path: Path
) -> list[solve.Interpretation]:
    """The cards with a short title and meaning each, written in one call that sees them all,
    so each says what sets it apart. What every card shares is listed once, apart. The cards
    as they were when the call fails: the page then names them by their differing columns."""
    own = {
        one.id: [_binding_line(probe, entities, b) for b in one.bindings]
        + _left_lines(entities, one)
        + [f"table {_sql_name(probe, t)}" for t in one.tables]
        + [line.strip() for line in _join_lines(probe, one.joins, one.either)]
        for one in cards
    }
    # one card shares nothing: all of it is its own
    shared = set.intersection(*(set(lines) for lines in own.values())) if len(cards) > 1 else set()
    blocks = ["Same in every interpretation:", *(f"  {line}" for line in own[cards[0].id] if line in shared)]
    for one in cards:
        blocks += ["", f"{one.id}:", *(f"  {line}" for line in own[one.id] if line not in shared)]
    places = [b.column for one in cards for b in one.bindings]
    places += [c for one in cards for b in one.bindings for c, _ in b.also]
    places += [t for one in cards for t in one.tables] + [c for one in cards for pair in one.joins for c in pair]
    ids = [one.id for one in cards]

    def check(reply: Summaries) -> None:
        if [s.id for s in reply.interpretations] != ids:
            raise llm.ModelError(f"the reply names {[s.id for s in reply.interpretations]}, not {ids} in order")
        if any(not s.title.strip() or not s.meaning.strip() for s in reply.interpretations):
            raise llm.ModelError("a title or meaning holds no text")

    template = string.Template((config.PROMPTS_DIR / "summaries.txt").read_text())
    try:
        reply = llm.call(
            template.substitute(
                question=question,
                interpretations="\n".join(blocks),
                places="\n".join(_place_line(probe, path) for path in dict.fromkeys(places)),
            ),
            Summaries, log_path, f"summaries {question[:40]}", check=check,
            effort=config.SAY_REASONING_EFFORT,
        )
    except llm.ModelError as err:
        log.warning("summaries: %s", err)
        return cards
    return [replace(one, title=s.title.strip(), summary=s.meaning.strip())
            for one, s in zip(cards, reply.interpretations)]


def answered(
    probe: Probe,
    question: str,
    entities: list[llm.Entity],
    interpretation: solve.Interpretation,
    log_path: Path,
    rewrite: tuple[str, str] | None = None,
    stop: threading.Event | None = None,
    chosen: bool = False,
) -> Result:
    """One interpretation's query, then its answer in words; no new call once `stop` is set."""
    result = query(probe, question, entities, interpretation, log_path, rewrite, stop, chosen)
    if stop is None or not stop.is_set():
        result.said = say(probe, question, entities, result, log_path)
    return result


def _cell(value: object, width: int = CELL_CHARS) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # a whole number stored as REAL reads 1925, not 1925.0
    text = "" if value is None else bundle._one_line(str(value))
    return text if len(text) <= width else text[: width - 1] + "…"


def _grid(columns: list[str], rows: list[tuple], width: int = CELL_CHARS) -> list[str]:
    if not columns:
        return []
    cells = [[_cell(name, width) for name in columns]] + [[_cell(v, width) for v in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(columns))]
    return [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in cells
    ]


def _count(result: Result) -> str:
    if result.error is not None:
        return f"no working query: {result.error}"
    return f"rows: more than {config.SQL_MAX_ROWS}" if result.more else f"rows: {len(result.rows)}"


def _about(answer: Answer, one: solve.Interpretation) -> list[str]:
    lines = [
        f"  {binding.entity} {_entity(answer.entities, binding).attribute} ->"
        f" {' and '.join(binding.columns)} ({binding.reason})"
        for binding in one.bindings
    ]
    return lines + ["  tables: " + ", ".join(one.tables)]


def _block(answer: Answer, result: Result) -> list[str]:
    lines = [f"{result.interpretation.id}: {result.sentence}"]
    if result.said:
        lines.append(f"  answer: {result.said}")
    lines += _about(answer, result.interpretation)
    lines += ["  " + line for line in result.sql.splitlines()]
    lines.append("  " + _count(result))
    lines += ["  " + line for line in _grid(result.columns, result.rows)]
    return lines


def present(answer: Answer) -> str:
    lines = [f"QUESTION: {answer.question}", ""]
    for result in answer.results:
        lines += _block(answer, result) + [""]
    if answer.fanout.note is not None and not answer.results:
        lines += [f"NOT RUN: {answer.fanout.note}. Narrow the question, or choose on the page.", ""]
        for one in answer.fanout.interpretations:
            lines += [f"{one.id}:", *_about(answer, one), ""]
    if answer.fanout.dropped:
        lines.append("DROPPED")
        lines += [f"  {reason}" for reason in answer.fanout.dropped]
        lines.append("")
    if answer.fanout.stopped is not None:
        lines.append("STOPPED: " + answer.fanout.stopped)
    return "\n".join(lines).rstrip() + "\n"


