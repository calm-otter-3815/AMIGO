"""From a question to the tables and columns that could answer it (PLAN.md 3.1 to 3.4)."""

import functools
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import numpy as np

from . import config, index, llm
from .probe import Probe

log = logging.getLogger(__name__)

# reciprocal rank fusion constant, Cormack, Clarke and Buettcher, SIGIR 2009
RRF_K = 60
SAMPLES = 5
# characters of a stored value shown in a note or a sample: a long free text, a forum post,
# would fill the prompt, and its words around the match are what tell its meaning
WIDTH = 80


@dataclass
class Stage1:
    """Everything Stage 1 produced."""

    entities: list[llm.Entity]
    column_scores: list[np.ndarray]  # lookup 2 cosines, one array per entity
    ranked: list[list[int]]
    order: list[int]
    bridges: set[int]
    details: dict[int, list[str]]
    not_found: list[tuple[str, list[int]]]
    # one entry per part of the question a column lookup searched for, in question order:
    # (entity index, "name" or "value", the columns found for it)
    found: list[tuple[int, str, list[int]]] = field(default_factory=list)
    # per entity whose text value names tables, "savings" the table savings: (entity
    # index, those tables)
    named: list[tuple[int, list[int]]] = field(default_factory=list)

    def leave_out(self, k: int) -> None:
        """Drop entity k and what is kept per entity; the entities after it move up one."""
        self.entities.pop(k)
        self.column_scores.pop(k)
        self.found = [(i - (i > k), kind, one) for i, kind, one in self.found if i != k]
        self.named = [(i - (i > k), one) for i, one in self.named if i != k]


def stage1(
    probe: Probe,
    question: str,
    log_path: Path,
    entities: list[llm.Entity] | None = None,
) -> Stage1:
    """entities: the question's parts when the user already checked them, else decompose runs."""
    if entities is None:
        entities = llm.decompose(question, log_path).entities
    log.info("decomposition: %d entities: %s", len(entities), [e.attribute for e in entities])

    ranked: list[list[int]] = []
    column_scores: list[np.ndarray] = []
    details: dict[int, list[str]] = defaultdict(list)
    not_found: list[tuple[str, list[int]]] = []
    found: list[tuple[int, str, list[int]]] = []
    named: list[tuple[int, list[int]]] = []
    # per entity with a literal: its value hits and the columns nearest it, if none hit
    misses: list[tuple[int, str, list[int], list[int]]] = []

    for k, entity in enumerate(entities):
        cards, scores = probe.search_cards(entity.attribute)
        column_scores.append(scores)
        survivors = [card["id"] for card in cards]
        log.info(
            "lookup 2 %r: %d of %d column cards survive",
            entity.attribute,
            len(survivors),
            len(probe.columns),
        )
        ranked.append(_tables_of(probe, survivors))
        found.append((k, "name", survivors))
        for column_id in survivors:
            details[column_id].append(f'matches "{entity.attribute}"')
        if entity.literal is None or config.ABLATE == "novalues":
            continue
        written = _as_written(entity.literal)
        if entity.literal.kind == "text":
            hit_details = text_hits(probe, entity.literal.text, written)
            hits = list(hit_details)
            log.info("lookup 3 %s: %d columns", written, len(hits))
            own = named_tables(probe, entity.literal.text, question)
            if own:
                named.append((k, own))
                ranked.append(own)
                log.info(
                    "lookup 3 %s names %s", written, [probe.path("table", t) for t in own]
                )
        else:
            # a number stored in a row, or a date range the column's dates overlap, in one
            # of the columns nearest the phrase
            nearest = [int(i) + 1 for i in np.argsort(-scores, kind="stable")[: config.COLUMNS_PER_PART]]
            if entity.literal.kind == "number":
                hits = [c for c in nearest if probe.stores(c, entity.literal.number)]
                hit_details = {column_id: f"contains {written}" for column_id in hits}
            else:
                hits = [c for c in nearest if _covers(probe.columns[c], entity.literal)]
                hit_details = {column_id: _range(probe.columns[column_id], written) for column_id in hits}
            log.info("lookup 4 %s: %d of %d columns", written, len(hits), len(nearest))
        hits.sort(key=lambda column_id: -scores[column_id - 1])
        ranked.append(_tables_of(probe, hits))
        found.append((k, "value", hits))
        for column_id in hits:
            details[column_id].append(hit_details[column_id])
        misses.append((k, written, hits, survivors))

    # a value that names a table is held by that table
    not_found += [
        (written, near)
        for k, written, hits, near in misses
        if not hits and k not in dict(named)
    ]

    order, bridges = order_tables(probe, ranked)
    return Stage1(
        entities=entities,
        column_scores=column_scores,
        ranked=ranked,
        order=order,
        bridges=bridges,
        details=details,
        not_found=not_found,
        found=found,
        named=named,
    )


def text_hits(probe: Probe, text: str, written: str) -> dict[int, str]:
    """The columns that store a text value, each with what it holds; the first way that
    finds any wins, but a word inside a longer value is looked for in every database where
    the ways before found nothing."""
    hits = {c: f"contains {written}" for c in probe.lookup_value(text)}
    # a value split over several columns of one row: "Lewis Hamilton" as two names
    for group in probe.split_value(text):
        for c, _ in group:
            hits.setdefault(c, _split_detail(probe, group, c, written))
    # the other number of the last word, "saving" for "savings", before the words search
    # that free text nearly always answers, the order probe.stored_values checks in; only
    # when nothing matched, as tried every time it finds one-letter codes ("B" for "Bs")
    for other in index.inflections(text):
        if hits:
            break
        hits = {c: f'contains "{other}" (for {written})' for c in probe.lookup_value(other)}
    # the column often stores more than the question says: "Alphabet Inc."; in each database
    # where nothing matched so far: one stores a person as "Reid", another as "Elliot Reid"
    matched = frozenset(_database(probe, c) for c in hits)
    for c, values in probe.lookup_words(text, matched).items():
        hits[c] = _words_detail(values, written)
    # the question saying more than the column stores, "Alameda County"
    for shorter in index.variants(text):
        if hits:
            break
        detail = f'contains "{shorter}" (for {written})'
        hits = {c: detail for c in probe.lookup_value(shorter)}
    return hits


def _database(probe: Probe, column_id: int) -> str:
    return probe.tables[probe.columns[column_id]["table_id"]]["database"]


def _folded(text: str) -> list[frozenset[str]]:
    """Each word of a text with its other number, so a word matches its singular or its
    plural: "branches" matches branch, "movie" matches movies."""
    return [frozenset([word, *index.inflections(word)]) for word in index.words(text)]


def _within(words: list[frozenset[str]], other: list[frozenset[str]]) -> bool:
    return all(any(word & one for one in other) for word in words)


@functools.lru_cache(maxsize=None)
def _table_words(probe: Probe) -> dict[int, list[frozenset[str]]]:
    """Each table's readable name as folded words, digit-only words dropped, so customer_1
    reads as customer."""
    return {
        table_id: _folded(" ".join(w for w in index.words(table["readable"]) if not w.isdigit()))
        for table_id, table in probe.tables.items()
    }


def named_tables(probe: Probe, text: str, question: str) -> list[int]:
    """The tables a text value names: every word of the value is in the table's name, and
    every word of the name is in the question, either number. "savings" names the table
    savings; "loans" names book loans only when the question says book too; "vm 22" names
    no table vm."""
    value = _folded(text)
    said = _folded(question) + value
    return [
        table_id
        for table_id, name in _table_words(probe).items()
        if value and name and _within(value, name) and _within(name, said)
    ]


def _words_detail(values: list[str], written: str) -> str:
    """Why a column holds a value the question names in part."""
    more = f" and {len(values) - 1} more" if len(values) > 1 else ""
    return f'contains "{_excerpt(values[0], written)}"{more} (for {written})'


def order_tables(probe: Probe, ranked: list[list[int]]) -> tuple[list[int], set[int]]:
    """Membership and reciprocal rank fusion order, bridges last (PLAN.md 3.4)."""
    in_bundle = {table_id for one in ranked for table_id in one}
    bridges = _bridges(probe, in_bundle)
    fused = _fuse(ranked)
    order = sorted(in_bundle, key=lambda t: (-fused[t], t)) + sorted(
        bridges, key=lambda t: (-fused[t], t)
    )
    return order, bridges


def _tables_of(probe: Probe, column_ids: list[int]) -> list[int]:
    """The tables of a ranked column list, each at the rank of its best column."""
    tables: list[int] = []
    for column_id in column_ids:
        table_id = probe.columns[column_id]["table_id"]
        if table_id not in tables:
            tables.append(table_id)
    return tables


def _fuse(ranked: list[list[int]]) -> dict[int, float]:
    fused: dict[int, float] = defaultdict(float)
    for one in ranked:
        for rank, table_id in enumerate(one, start=1):
            fused[table_id] += 1 / (RRF_K + rank)
    return fused


def _adjacency(probe: Probe) -> dict[int, set[int]]:
    linked: dict[int, set[int]] = defaultdict(set)
    for link in probe.links:
        a = probe.columns[link["from_column"]]["table_id"]
        b = probe.columns[link["to_column"]]["table_id"]
        # a foreign key inside one table is not an edge between two tables
        if a != b:
            linked[a].add(b)
            linked[b].add(a)
    return linked


def _connected(tables: set[int], linked: dict[int, set[int]]) -> bool:
    stack = [next(iter(tables))]
    seen = set(stack)
    while stack:
        for other in (linked[stack.pop()] & tables) - seen:
            seen.add(other)
            stack.append(other)
    return seen == tables


def minimal_sets(
    terminals: set[int], tables: set[int], linked: dict[int, set[int]], plain=None
) -> list[set[int]]:
    """Connected subsets of tables holding every terminal, none inside another (PLAN.md 4.2).

    Each one is a solution's table set: the terminals are the tables that carry a
    binding, the rest are join tables the link graph forces. Only a set `plain` accepts
    (all, when it is None) stops the search for bigger ones.
    """
    if not terminals:
        return []
    # extra tables outside the terminals' component can never join a connected
    # candidate, so a connected superset of terminals within `tables` only ever
    # uses reachable tables; dropping the rest doesn't change the result.
    reachable = set(terminals)
    stack = list(terminals)
    while stack:
        for other in (linked[stack.pop()] & tables) - reachable:
            reachable.add(other)
            stack.append(other)
    extra = sorted(reachable - terminals)
    found: list[set[int]] = []
    # ponytail: every subset of the extra tables up to config.MAX_JOIN_TABLES of
    # them, C(n, 3) combinations at most instead of 2^n over the terminals' whole
    # linked component (mmqa databases run past 30 linked tables). Also stops
    # once a bigger size can no longer beat the smallest set found by more than
    # one join table. Steiner enumeration if deeper joins ever matter.
    for size in range(min(len(extra), config.MAX_JOIN_TABLES) + 1):
        cut = [kept for kept in found if plain is None or plain(kept)]
        if cut and size > min(len(kept) for kept in cut) - len(terminals) + 1:
            break
        for more in combinations(extra, size):
            candidate = terminals | set(more)
            if any(kept <= candidate for kept in found):
                continue
            if _connected(candidate, linked):
                found.append(candidate)
    return found


def _bridges(probe: Probe, in_bundle: set[int]) -> set[int]:
    linked = _adjacency(probe)
    found = set()
    for table_id in probe.tables:
        if table_id in in_bundle:
            continue
        near = sorted(linked[table_id] & in_bundle)
        if any(b not in linked[a] for a, b in combinations(near, 2)):
            found.add(table_id)
    return found


def _as_written(literal: llm.Literal) -> str:
    if literal.kind == "text":
        return f'"{literal.text}"'
    if literal.kind == "number":
        number = literal.number
        return str(int(number) if number == int(number) else number)
    start, end = literal.date_start, literal.date_end
    if start == end:
        return start
    if start and end:
        return f"{start}..{end}"
    return f"from {start}" if start else f"up to {end}"


def _split_detail(
    probe: Probe, group: list[tuple[int, str]], column_id: int, written: str
) -> str:
    """`contains "Lewis", with surname "Hamilton" on the same row (for "Lewis Hamilton")`."""
    others = ", ".join(
        f'{probe.columns[c]["name"]} "{value}"' for c, value in group if c != column_id
    )
    return f'contains "{dict(group)[column_id]}", with {others} on the same row (for {written})'


def _one_line(text: str | None) -> str:
    return re.sub(r"\s+", " ", text).strip() if text else ""


def _excerpt(value: str, near: str = "") -> str:
    """A value on one line, cut to WIDTH characters around the first word of `near` it
    holds (its start when none)."""
    value = _one_line(value)
    if len(value) <= WIDTH:
        return value
    folded = value.lower()
    at = min((i for i in (folded.find(w) for w in index.words(near)) if i >= 0), default=0)
    start = max(0, min(at - WIDTH // 2, len(value) - WIDTH))
    cut = value[start:start + WIDTH].strip()
    return ("..." if start else "") + cut + ("..." if start + WIDTH < len(value) else "")


def _samples(column: dict) -> list[str]:
    # a sample can hold newlines, and one column must stay on one line
    values = json.loads(column["samples"] or "[]")[:SAMPLES]
    return [_excerpt(str(value)) for value in values]


def _covers(column: dict, literal: llm.Literal) -> bool:
    if literal.kind == "number":
        return column["kind"] == "number" and column["min"] <= literal.number <= column["max"]
    if column["kind"] == "number":
        # a date literal against a plain year column: compare years. Only a column of
        # years can hold one, whole numbers from 1000 to 2999: an amount or an id whose
        # range happens to span the year holds no date
        low, high = column["min"], column["max"]
        if not _years(low, high):
            return False
        start = int(literal.date_start[:4]) if literal.date_start else None
        end = int(literal.date_end[:4]) if literal.date_end else None
    elif column["kind"] == "date":
        # compare at the column's own precision: a format with a time of day leaves the
        # time in date_min and date_max, and a month column (%Y%m) stores each month as
        # its first day, so 2013-11 holds 2013-11-15
        size = 10 if "%d" in column["date_format"] else 7
        low, high = column["date_min"][:size], column["date_max"][:size]
        start = literal.date_start and literal.date_start[:size]
        end = literal.date_end and literal.date_end[:size]
    else:
        return False
    return (end is None or low <= end) and (start is None or high >= start)


def _years(low, high) -> bool:
    return (
        low is not None
        and high is not None
        and float(low).is_integer()
        and float(high).is_integer()
        and 1000 <= low <= high <= 2999
    )


def _span(column: dict) -> tuple:
    """The low and high end of a number or date column."""
    if column["kind"] == "date":
        return column["date_min"], column["date_max"]
    return column["min"], column["max"]


def _range(column: dict, written: str) -> str:
    low, high = _span(column)
    return f"range {low}..{high} covers {written}"

