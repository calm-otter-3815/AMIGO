"""Step 5: the fan-out from picks to fully bound interpretations (PLAN.md 13.2)."""

import functools
import json
import logging
import sqlite3
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, field

from . import bundle as _bundle
from . import config, index, links, llm, pick
from .probe import Probe

log = logging.getLogger(__name__)


@dataclass
class Binding:
    entity: str
    # a column path, or a table path when being a row of that table is the whole meaning:
    # "savings" held by the table savings
    column: str
    reason: str
    value: str | None
    # the other columns and stored values of a value split over one row: "Lewis" in
    # `column`, then ("...surname", "Hamilton"); with no value, a column the person picked
    # to show along with `column`: a name as the first name and the last name
    also: list[tuple[str, str | None]] = field(default_factory=list)

    @property
    def columns(self) -> list[str]:
        return [self.column, *(column for column, _ in self.also)]


@dataclass
class Interpretation:
    id: str
    bindings: list[Binding]
    tables: list[str]
    paths: int = 1
    # the links the query joins on, as (from column, to column) paths
    joins: list[tuple[str, str]] = field(default_factory=list)
    # the columns of the other roles between the same tables, which the query must not read
    avoid: list[str] = field(default_factory=list)
    # shown on its card: its odds, and whether it leaves out a part or was judged no
    note: str | None = None
    # shown on its card: a short name and what it means, written beside the others
    title: str | None = None
    summary: str | None = None
    # the parts of the question it does not use (E2, ...): nothing holds them or joins with them
    left_out: list[str] = field(default_factory=list)
    # groups of `joins` where rows join by any one link of the group, not by all (judge.ways "any")
    either: list[list[tuple[str, str]]] = field(default_factory=list)


@dataclass(frozen=True)
class Join:
    """One way to join two tables: one link, or every link of one composite foreign key."""

    links: tuple[tuple[int, int], ...]  # (from column id, to column id)
    quality: float


@dataclass
class Missing:
    entity: str
    closest: list[str]


@dataclass
class FanOut:
    interpretations: list[Interpretation]
    dropped: list[str]
    stopped: str | None
    note: str | None = None
    missing: Missing | None = None


def _checked(
    probe: Probe, name: str, entity: llm.Entity, picked: pick.PickedColumn
) -> tuple[list[Binding], str | None]:
    """One catalog column checked against the part's value: bindings or a reason."""
    literal = entity.literal
    column_id = probe.column_ids[picked.column]
    column = probe.columns[column_id]
    if literal is None:
        return [Binding(name, picked.column, picked.reason, None)], None
    if literal.kind in ("number", "date"):
        if column["kind"] not in ("number", "date"):
            # a year against a text column: no range to check it against
            return [Binding(name, picked.column, picked.reason, None)], None
        if not _bundle._covers(column, literal):
            low, high = _bundle._span(column)
            return [], (
                f"{picked.column} ranges {low}..{high}, which does not cover"
                f" {_bundle._as_written(literal)}."
            )
        return [Binding(name, picked.column, picked.reason, None)], None
    if column["kind"] != "text":
        return [], (
            f"{picked.column} is a {column['kind']} column; it cannot hold"
            f" {literal.text!r}."
        )
    stored = probe.stored_values(column_id, literal.text)
    whole = index.normalise(literal.text)
    held = any(index.normalise(value) == whole for value in stored)
    if not held:
        # not stored whole here, so it may be split over this column and others of its row
        groups = [
            group
            for group in probe.split_value(literal.text, column["table_id"])
            if column_id in dict(group)
        ]
        if groups:
            return [_split_binding(probe, name, picked.reason, one) for one in groups], None
    if not stored:
        return [], f"{picked.column} holds no value {literal.text!r}."
    # values that differ once normalised are different things, "Manchester United" and
    # "Manchester City" for "Manchester": one binding each, so the person is asked.
    # Spellings of one value leave the choice to the SQL step, which sees the values.
    spellings: dict[str, list[str]] = {}
    for value in stored:
        spellings.setdefault(index.normalise(value), []).append(value)
    # a value matched only in part ("Batman" for "Batman Beyond") is never used unseen
    return [
        Binding(
            name,
            picked.column,
            picked.reason
            if held
            else f"{picked.reason}; {literal.text!r} is not stored, the column holds {same[0]!r}",
            same[0] if len(same) == 1 else None,
        )
        for same in spellings.values()
    ], None


def _split_binding(
    probe: Probe, name: str, reason: str, group: list[tuple[int, str]]
) -> Binding:
    """One binding over every column of a split value, whichever of them was picked."""
    (first, value), *rest = [(probe.path("column", c), stored) for c, stored in group]
    return Binding(name, first, reason, value, rest)


# The links that can make columns of two tables one meaning in clarify. The semantic
# layer's links (by values alone, by name) are for joins only: a wide id space
# containing two keys would otherwise merge two meanings.
MEANING_KINDS = frozenset({"declared", "inferred"})


def link_quality(probe: Probe, link) -> float:
    """links.quality of one link of the probe."""
    return links.quality(link, probe.columns[link["from_column"]], probe.columns[link["to_column"]])


def reads_as(probe: Probe, wide: Interpretation, narrow: Interpretation) -> bool:
    """Whether `wide` answers what `narrow` does: it holds narrow's tables and joins, each
    of its other joins looks a row up by a unique key holding every value that points at
    it, from a column with no empty value (so it drops no row and repeats none), and its joins make each part's column equal
    to narrow's, with the same value. A student id bound in the students table, in the
    registrations or in the addresses is one id, once those joins make them equal."""
    own = {tuple(pair) for pair in narrow.joins}
    if not (set(narrow.tables) <= set(wide.tables) and own <= {tuple(p) for p in wide.joins}):
        return False
    extra = [tuple(pair) for pair in wide.joins if tuple(pair) not in own]
    if len(extra) != len(set(wide.tables) - set(narrow.tables)):
        return False
    by_pair = {(link["from_column"], link["to_column"]): link for link in probe.links}
    for a, b in extra:
        (_, x), (_, y) = probe.find(a), probe.find(b)
        link, key = by_pair.get((x, y)), probe.columns[y]
        if (
            b.rsplit(".", 1)[0] in narrow.tables
            or link is None
            or link["kind"] not in MEANING_KINDS
            or link["score"] < 1.0
            or probe.columns[x]["empty_share"] > 0
            or not (key["is_unique"] or key["is_pk"])
        ):
            return False
    root: dict[str, str] = {}

    def find(path: str) -> str:
        while root.setdefault(path, path) != path:
            path = root[path]
        return path

    for a, b in wide.joins:
        root[find(a)] = find(b)
    return len(wide.bindings) == len(narrow.bindings) and all(
        (one.value, one.also) == (other.value, other.also) and find(one.column) == find(other.column)
        for one, other in zip(wide.bindings, narrow.bindings)
    )


def joins(probe: Probe, kinds: frozenset | None = None) -> dict[tuple[int, int], list[Join]]:
    """Per table pair, in both orders, every way to join them good enough to join on,
    from links of the given kinds, or all.

    Where the schema declares how two tables join, an inferred link between the same two
    tables is a guess the declaration already answers, so it is left out.
    """
    table = {c: column["table_id"] for c, column in probe.columns.items()}
    groups: dict[tuple, list] = defaultdict(list)
    declared = set()
    for number, link in enumerate(probe.links):
        a, b = table[link["from_column"]], table[link["to_column"]]
        # a foreign key inside one table is not an edge between two tables
        if a == b or (kinds is not None and link["kind"] not in kinds):
            continue
        if link["kind"] == "declared":
            declared.add(frozenset((a, b)))
        grp = link.get("grp")
        groups[("grp", grp) if grp is not None else ("link", number)].append(link)
    found: dict[tuple[int, int], dict[frozenset, Join]] = defaultdict(dict)
    for group in groups.values():
        a, b = table[group[0]["from_column"]], table[group[0]["to_column"]]
        if group[0]["kind"] != "declared" and frozenset((a, b)) in declared:
            continue
        join = Join(
            tuple(sorted((link["from_column"], link["to_column"]) for link in group)),
            min(link_quality(probe, link) for link in group),
        )
        if join.quality < config.MIN_EDGE_QUALITY:
            continue
        # one pair of columns linked both ways is one join
        same = frozenset(c for pair in join.links for c in pair)
        for pair in ((a, b), (b, a)):
            if same not in found[pair] or found[pair][same].quality < join.quality:
                found[pair][same] = join
    return {pair: list(ways.values()) for pair, ways in found.items()}


def _column(probe: Probe, column_id: int) -> str:
    card = probe.columns[column_id]
    return f"t{card['table_id']}.{index._quote(card['name'])}"


def row_key(probe: Probe, table_id: int) -> str:
    """What names one row of a table, in plain SQL on any engine: a column the data shows
    unique (the declared key first), else all its columns. Two rows equal in every column
    hold the same facts, so the whole row names a row as well as any hidden id would."""
    columns = [c for c, card in probe.columns.items() if card["table_id"] == table_id]
    unique = sorted((c for c in columns if probe.columns[c]["is_unique"]),
                    key=lambda c: not probe.columns[c]["is_pk"])
    return ", ".join(_column(probe, c) for c in unique[:1] or columns)


def stores_decimals(probe: Probe, column_id: int) -> bool:
    """A text column holding whole numbers written as decimals ("149.0"): links.whole
    linked it on the numbers, so it joins as a number, not as the text "149.0"."""
    card = probe.columns[column_id]
    samples = json.loads(card["samples"] or "[]")
    return card["kind"] == "text" and bool(samples) and all(
        links.WHOLE.fullmatch(str(value)) for value in samples
    )


def stores_padded(probe: Probe, column_id: int) -> bool:
    """A text column whose values carry spaces at the ends (" APG"): links.normalise linked
    it without them, so it joins trimmed, or no row would ever match."""
    card = probe.columns[column_id]
    samples = json.loads(card["samples"] or "[]")
    return card["kind"] == "text" and any(
        isinstance(value, str) and value != value.strip() for value in samples
    )


def join_side(probe: Probe, column_id: int, name: str) -> str:
    """A join column as the link step compared it."""
    if stores_decimals(probe, column_id):
        return f"CAST({name} AS INTEGER)"
    return f"TRIM({name})" if stores_padded(probe, column_id) else name


def _on(probe: Probe, x: int, y: int) -> str:
    """One join condition. Against a number cast this way, SQLite reads the other side's
    text "149" as the number too."""
    return f"{join_side(probe, x, _column(probe, x))} = {join_side(probe, y, _column(probe, y))}"


def _from(probe: Probe, table_id: int) -> str:
    return f"{index._quote(probe.tables[table_id]['name'])} AS t{table_id}"


def _joined(probe: Probe, join: Join, pair: tuple[int, int]) -> str:
    """The query listing the pairs of rows one join matches."""
    a, b = pair
    on = " AND ".join(_on(probe, x, y) for x, y in join.links)
    return f"SELECT {row_key(probe, a)}, {row_key(probe, b)} FROM {_from(probe, a)} JOIN {_from(probe, b)} ON {on}"


def _roles(probe: Probe, ways: list[Join], pair: tuple[int, int]) -> list[Join]:
    """The joins between two tables that mean different things, best first.

    A join that matches different pairs of rows is its own role, so its own
    interpretation: eye colour and hair colour both reach colour.id, and a customer's
    branch id and its state both reach a bank. Keeping only the best one would quietly
    pick one, and a junk link that ties the real key could win. Joins that match the
    same pairs of rows fold into the best one: an alternate key, or two columns equal
    on every row.
    """
    kept: list[Join] = []
    for join in sorted(ways, key=lambda join: (-join.quality, join.links)):
        mine = _joined(probe, join, pair)
        # the database is only opened once there is a second join to compare
        if all(
            _different_rows(probe.tables[pair[0]]["database_path"], mine, _joined(probe, other, pair))
            for other in kept
        ):
            kept.append(join)
    return kept


def _first_row(path: str, query: str):
    """The query's first row, or None; sqlite3.Error once it runs past SAME_ROWS_STEPS."""
    rows = first_rows(path, query, 1)
    return rows[0] if rows else None


def first_rows(path: str, query: str, n: int) -> list:
    """The query's first n rows; sqlite3.Error once it runs past SAME_ROWS_STEPS."""
    steps = 0

    def tick() -> int:
        nonlocal steps
        steps += 1
        return 1 if steps > config.SAME_ROWS_STEPS else 0

    with closing(index.open_source(path)) as source:
        source.set_progress_handler(tick, 1000)
        return source.execute(query).fetchmany(n)


@functools.lru_cache(maxsize=1024)
def _different_rows(path: str, one: str, other: str) -> bool:
    """True unless the two queries return the same rows; a check that cannot finish,
    or fails, says they differ, so the two stay apart."""
    try:
        row = _first_row(
            path,
            f"SELECT 1 FROM ({one} EXCEPT {other})"
            f" UNION ALL SELECT 1 FROM ({other} EXCEPT {one}) LIMIT 1",
        )
    except sqlite3.Error:
        return True
    return row is not None


def keyed(probe: Probe, ways: dict[tuple[int, int], list[Join]]) -> dict[tuple[int, int], bool]:
    """Per table pair (a, b), whether every way to join them points columns of a that are
    not a key of a at a key of b: many rows of a reach one row of b.

    A key is one unique column or the whole primary key. One part of a composite primary
    key is not a key by itself: takes points at section through all four parts of its
    key, and section reaches many rows of takes through the same four."""

    def flag(column_id: int, name: str) -> bool:
        column = probe.columns[column_id]
        return name in column.keys() and bool(column[name])

    primary: dict[int, set[int]] = defaultdict(set)
    for column_id, column in probe.columns.items():
        if flag(column_id, "is_pk"):
            primary[column["table_id"]].add(column_id)

    def key(table_id: int, columns: set[int]) -> bool:
        whole = primary[table_id]
        return any(flag(c, "is_unique") for c in columns) or bool(whole) and whole <= columns

    found = {}
    for (a, b), found_ways in ways.items():
        sides = [
            zip(*(pair if probe.columns[pair[0]]["table_id"] == a else pair[::-1] for pair in join.links))
            for join in found_ways
        ]
        found[(a, b)] = all(not key(a, set(xs)) and key(b, set(ys)) for xs, ys in sides)
    return found


