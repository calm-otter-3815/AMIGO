"""Before and after on the same questions, over the six lakes.

  .venv/bin/python experiments/eval_lakes.py sample          # the questions, once
  .venv/bin/python experiments/eval_lakes.py split           # each question's parts, once (paid)
  .venv/bin/python experiments/eval_lakes.py report TAG...   # the metrics, from saved records
  .venv/bin/python experiments/eval_lakes.py compare TAG...  # tables level, gold vs multi-valid
  .venv/bin/python experiments/eval_lakes.py amigo TAG       # stage 1, the judge (paid)
  .venv/bin/python experiments/eval_lakes.py score2 TAG W    # its answers within W bits, no calls
  .venv/bin/python experiments/eval_lakes.py widen TAG NEW W  # TAG searched again for answers up to W bits, no calls
  .venv/bin/python experiments/eval_lakes.py calib TAG       # how often AMIGO candidates are valid, by bits
  .venv/bin/python experiments/eval_lakes.py match TAG BASE... # AMIGO at each baseline's size, paired, no calls
  .venv/bin/python experiments/eval_lakes.py conformal TAG   # the window from a miss rate, checked, no calls
  .venv/bin/python experiments/eval_lakes.py hitl TAG W BASE...  # AMIGO asking a simulated person

The questions: bird_dev b001-b052 of pick_questions_bird100.jsonl, and 40 questions per
other lake drawn with random.Random(0) among those whose gold SQL runs. In each lake the
first half chooses settings and the second half checks them. The split runs once and
every tag reads it, so a difference is the code or the lake, not the split. A command
runs with the code of the folder this file sits in: a copy of this file in a checkout of
main gives main's numbers. EVAL_RUNS points both copies at one folder.
EVAL_EFFORT sets the split's reasoning effort (AMIGO's own by default; the baselines ran at
medium); each effort has its own split file, split.json being the high one.
EVAL_LABEL=plus reports against the multi-valid label (runs/labeler/LAKE/labels.jsonl) on
the lakes that have one; by default the label is the gold query alone. Baseline tags
(baselines/run.py) report the same way.

Gold is what SQLite reads when it prepares the gold SQL (its authorizer), never a
regex, and it is used for scoring only. Three levels, each recall, complete recall and
precision per question, then per lake, then the mean over lakes and the worst lake:
  columns: the gold columns against the picked columns;
  tables: the gold tables against the tables of every interpretation, complete when one
    interpretation holds every gold table;
  interpretation: the gold columns against one interpretation's columns (its bound
    columns and the columns of the links the SQL step is shown for it), taking the
    interpretation with the best recall, then the best precision.

Rules, written before any number was seen:
  1. A change to links, the fan-out or the clarify step wins when, on the check half, the
     tables and interpretation levels are each at least the lower of main's two runs
     (main1, main2) on recall, complete recall and precision, mean and worst lake.
  2. A join score is compared on the choose half; it is kept only if it holds rule 1
     there and raises table complete recall, and then holds rule 1 on the check half.
Raw files go to runs/eval/ (gitignored); reports to experiments/results/.
"""

import bisect
import itertools
import json
import logging
import math
import os
import pickle
import random
import re
import sqlite3
import string
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from statistics import mean

import numpy as np
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from amigo import answer, candidates, config, embed, index, interpret, judge, layer, llm, pick, serve, solve  # noqa: E402
from amigo import bundle as _bundle  # noqa: E402
from amigo.clock import CLOCK, Clock, lap  # noqa: E402
from amigo.probe import Probe  # noqa: E402

log = logging.getLogger("eval_lakes")

RUNS = Path(os.environ.get("EVAL_RUNS", ROOT / "runs" / "eval"))
QUESTIONS = Path(os.environ.get("EVAL_QUESTIONS", ROOT / "experiments" / "eval_questions.jsonl"))
# "plus": report against the multi-valid label instead of the gold query alone
LABEL = os.environ.get("EVAL_LABEL")
EFFORT = os.environ.get("EVAL_EFFORT", config.DECOMPOSE_REASONING_EFFORT)
config.DECOMPOSE_REASONING_EFFORT = EFFORT
# every split before EVAL_EFFORT ran at high and is split.json
SPLIT = RUNS / ("split.json" if EFFORT == "high" else f"split_{EFFORT}.json")
BIRD = ROOT / "experiments" / "pick_questions_bird100.jsonl"
LAKES = ["bird_dev", "spider_dev", "beaver_dw", "beaver_nw", "fiben", "mmqa"]
BIRD_COUNT = 52
PER_LAKE = 40
SQL_WORKERS = int(os.environ.get("EVAL_SQL_WORKERS", 8))  # 1 for a timing run
LEVELS = ("columns", "tables", "interpretation")
KEYS = ("recall", "complete", "precision")
# baselines whose `order` is a ranking of their own, so NDCG means something there: JAR
# picks one set of k tables and CORE-T one group, with no order of their own
RANKED = re.compile(r"bl_(dense|murre)_k\d+|bl_crush4sql_t\d+")


def _lines(path: Path) -> list[dict]:
    # split on "\n" only: splitlines() also breaks a line at characters such as U+0085 inside a string
    return [json.loads(line) for line in path.read_text().split("\n") if line] if path.exists() else []


def _load(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


def _databases(lake: str) -> dict[str, str]:
    with closing(layer.open_layer(lake)) as conn:
        return {row["name"]: row["path"] for row in conn.execute("SELECT name, path FROM databases")}


def reads(path: str, sql: str) -> tuple[set[str], set[tuple[str, str]]]:
    """The tables and (table, column) pairs SQLite reads for `sql`, lower case.

    The authorizer sees every read when the statement is prepared; EXPLAIN prepares it
    without running it. A read of no column (COUNT(*)) names the table only.
    """
    tables: set[str] = set()
    columns: set[tuple[str, str]] = set()

    def authorize(action, table, column, *_):
        if action == sqlite3.SQLITE_READ and table:
            tables.add(table.lower())
            if column:
                columns.add((table.lower(), column.lower()))
        return sqlite3.SQLITE_OK

    with closing(index.open_source(path)) as conn:
        conn.set_authorizer(authorize)
        while True:
            try:
                conn.execute("EXPLAIN " + sql)
                break
            except sqlite3.OperationalError as error:
                # A function SQLite lacks (MMQA gold uses MySQL's LPAD): EXPLAIN never calls
                # it, so a stand-in of that name is enough to see the reads.
                missing = re.match(r"no such function: (\w+)", str(error))
                if not missing:
                    raise
                conn.create_function(missing[1], -1, lambda *_: None)
    return tables, columns


class Gold:
    """Gold tables and columns as lake paths, database.table[.column]."""

    def __init__(self, lake: str):
        with closing(layer.open_layer(lake)) as conn:
            rows = conn.execute(
                "SELECT d.name AS db, d.path, t.name AS tab, c.name AS col FROM columns c"
                " JOIN tables t ON t.id = c.table_id JOIN databases d ON d.id = t.database_id"
            ).fetchall()
        self.paths = {row["db"]: row["path"] for row in rows}
        self.names: dict[tuple, str] = {}
        for row in rows:
            self.names[(row["db"], row["tab"].lower())] = f"{row['db']}.{row['tab']}"
            self.names[(row["db"], row["tab"].lower(), row["col"].lower())] = (
                f"{row['db']}.{row['tab']}.{row['col']}"
            )

    def __call__(self, db: str, sql: str) -> tuple[set[str], set[str]]:
        tables, columns = reads(self.paths[db], sql)
        return (
            {self.names[(db, t)] for t in tables if (db, t) in self.names},
            {self.names[(db, t, c)] for t, c in columns if (db, t, c) in self.names},
        )


# ---- sample and split, once


def _runs(path: str, sql: str) -> bool:
    try:
        answer.run_sql(path, sql)
    except sqlite3.Error:
        return False
    return True


def sample() -> None:
    rows = []
    for number, one in enumerate(_lines(BIRD)[:BIRD_COUNT], 1):
        rows.append(
            {"id": f"bird_dev-{number:03d}", "lake": "bird_dev", "db_id": one["db_id"],
             "question": one["question"], "gold_sql": one["gold_sql"],
             "question_id": one["bird_question_id"]}
        )
    for lake in LAKES[1:]:
        paths = _databases(lake)
        records = [r for r in config.questions(lake) if r["SQL"] and r.get("db_id") in paths]
        order = list(range(len(records)))
        random.Random(0).shuffle(order)
        kept = []
        for i in order:
            record = records[i]
            if _runs(paths[record["db_id"]], record["SQL"]):
                kept.append(record)
            if len(kept) == PER_LAKE:
                break
        for number, record in enumerate(kept, 1):
            rows.append(
                {"id": f"{lake}-{number:03d}", "lake": lake, "db_id": record["db_id"],
                 "question": record["question"], "gold_sql": record["SQL"],
                 "question_id": record["question_id"]}
            )
        log.info("%s: %d questions", lake, len(kept))
    QUESTIONS.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _half(rows: list[dict], which: str) -> list[dict]:
    """The choose or the check half, cut per lake; "all" keeps every question."""
    if which == "all":
        return rows
    by_lake = defaultdict(list)
    for row in rows:
        by_lake[row["lake"]].append(row)
    kept = []
    for lake_rows in by_lake.values():
        cut = len(lake_rows) // 2
        kept += lake_rows[:cut] if which == "choose" else lake_rows[cut:]
    return kept


def split() -> None:
    path = SPLIT
    done = _load(path)
    todo = [row for row in _lines(QUESTIONS) if "entities" not in done.get(row["id"], {})]

    def one(row):
        llm.QUESTION.set(row["id"])
        started = time.monotonic()
        try:
            got = llm.decompose(row["question"], SPLIT.with_suffix(".jsonl"))
            return row["id"], {"entities": [e.model_dump() for e in got.entities],
                               "seconds": _since(started)}
        except llm.ModelError as err:
            return row["id"], {"error": str(err)}

    with ThreadPoolExecutor(max_workers=SQL_WORKERS) as pool:
        for qid, got in pool.map(one, todo):
            done[qid] = got
    _save(path, done)
    log.info("split: %d questions, %d failed", len(done), sum("error" in v for v in done.values()))


def _entities(qid: str) -> list[llm.Entity] | None:
    got = _load(SPLIT).get(qid, {})
    return None if "entities" not in got else [llm.Entity.model_validate(e) for e in got["entities"]]


# ---- helpers of the runs


def _by_lake(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["lake"]].append(row)
    return grouped


def _since(started: float) -> float:
    return round(time.monotonic() - started, 3)


# ---- a fan-out as a plain record


def _joins(probe: Probe, one: solve.Interpretation) -> list[list[str]]:
    """The links the SQL step is shown for an interpretation, as column path pairs."""
    chosen = getattr(one, "joins", None)
    if chosen is not None:
        return [list(pair) for pair in chosen]
    tables = {probe.find(name)[1] for name in one.tables}
    pairs = []
    for link in probe.links:
        a, b = (probe.columns[link[end]]["table_id"] for end in ("from_column", "to_column"))
        if a != b and a in tables and b in tables:
            pairs.append([probe.path("column", link["from_column"]), probe.path("column", link["to_column"])])
    return pairs


def _record(probe: Probe, fan: solve.FanOut, picked: pick.Pick) -> dict:
    return {
        "picked": sorted({c.column for e in picked.entities for c in e.columns}),
        "interpretations": [
            {
                "tables": one.tables,
                "bound": [
                    c for b in one.bindings for c in b.columns if probe.find(c)[0] == "column"
                ],
                "values": [[b.column, b.value, [list(x) for x in b.also]] for b in one.bindings],
                "joins": _joins(probe, one),
            }
            for one in fan.interpretations
        ],
        "stopped": fan.stopped,
        "dropped": len(fan.dropped),
    }


# ---- report: the metrics from saved records, the same code for every tag


def _f1(recall: float, precision: float) -> float:
    return 2 * recall * precision / (recall + precision) if recall + precision else 0.0


def _triple(gold: set, got: set, complete: bool) -> dict:
    hit = gold & got
    # nothing to find is found whole
    recall = len(hit) / len(gold) if gold else 1.0
    precision = len(hit) / len(got) if got else 0.0
    return {
        "recall": recall,
        "complete": 1.0 if complete else 0.0,
        "precision": precision,
        "f1": _f1(recall, precision),
    }


def ndcg(relevant: set, order: list) -> float:
    """Binary NDCG of a ranked list against the relevant set, at the list's own length."""
    gain = sum(1 / math.log2(i + 2) for i, one in enumerate(order) if one in relevant)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(order), len(relevant))))
    return gain / ideal if ideal else 0.0


def measure(gold: list[tuple[set[str], set[str]]], record: dict, ranked: bool = False) -> dict:
    """`gold` holds each query of the label as (tables, columns): one for the gold query,
    several for the multi-valid label. Recall and precision of the interpretation level
    are averaged over the queries; complete recall needs every query covered. The same on
    tables (interpretation_tables): each query's tables against the closest returned set, so
    a table retriever's list, one set, is scored too. Tables
    level: every returned table pooled against every table of the label; complete recall
    when the pool holds them all. Footprint level (`_footprints`): each table set of the
    label (a footprint) against each returned set (a baseline's list is one set), soft and
    exact. Effort is what a person reads until the first, and until the last, of the
    label's sets shows up. F1 is per question; NDCG, for a `ranked` record only, is of its
    table order against the tables of every query of the label."""
    picked = set(record["picked"])
    found = record["interpretations"]
    tables = {t for one in found for t in one["tables"]}
    spans = [set(one["bound"]) | {c for pair in one["joins"] for c in pair} for one in found]
    gold_tables = set().union(*(t for t, _ in gold))
    gold_columns = set().union(*(c for _, c in gold))
    valid = {frozenset(t) for t, _ in gold}
    scored = {
        "columns": _triple(gold_columns, picked, gold_columns <= picked),
        "tables": _triple(gold_tables, tables, gold_tables <= tables),
        "footprint": _footprints(valid, {frozenset(o["tables"]) for o in found if o["tables"]}),
        "interpretation": _nearest([c for _, c in gold], spans),
        "interpretation_tables": _nearest([t for t, _ in gold], [set(o["tables"]) for o in found]),
        "count": len(found),
        "size": len(tables),
        "effort": _effort(valid, found),
    }
    if ranked:
        scored["tables"]["ndcg"] = ndcg(gold_tables, record["order"])
    # a table retriever names no columns: it is scored at the table level only
    return {k: v for k, v in scored.items()
            if k in record.get("levels", LEVELS) or k in ("footprint", "interpretation_tables", "count", "size", "effort")}


def _nearest(queries: list[set], spans: list[set]) -> dict:
    """Each query of the label against the returned span closest to it (recall, then
    precision): recall and precision averaged over the queries, complete when every query
    is held whole by one span. set_precision is from the other side: each returned span,
    duplicates dropped, against the query it shares most of its share with, averaged over
    the spans, so a span close to no query counts too."""
    per_query = []
    for want in queries:
        best = {"recall": 0.0, "complete": 0.0, "precision": 0.0, "f1": 0.0}
        for span in spans:
            got = _triple(want, span, want <= span)
            if (got["recall"], got["precision"]) > (best["recall"], best["precision"]):
                best = got
        per_query.append(best)
    unique = {frozenset(span) for span in spans}
    return {"recall": mean(b["recall"] for b in per_query), "complete": min(b["complete"] for b in per_query),
            "precision": mean(b["precision"] for b in per_query), "f1": mean(b["f1"] for b in per_query),
            "set_precision": mean(max(len(span & want) / len(span) if span else 0.0 for want in queries)
                                  for span in unique) if unique else 0.0}


def _footprints(valid: set[frozenset], returned: set[frozenset]) -> dict:
    """Each table set of the label against each returned set, duplicates dropped. A hit is a
    returned set equal to the label's (exact) or holding it, extra tables allowed (soft).
    Recall: label sets hit; precision: returned sets that hit one; complete: every one hit."""
    out = {}
    for name, hits in (("soft", frozenset.issubset), ("exact", frozenset.__eq__)):
        found = sum(any(hits(v, r) for r in returned) for v in valid)
        recall = found / len(valid)
        precision = sum(any(hits(v, r) for v in valid) for r in returned) / len(returned) if returned else 0.0
        out[name] = {"recall": recall, "complete": float(found == len(valid)), "precision": precision,
                     "f1": _f1(recall, precision)}
    return out


def _effort(valid: set[frozenset], found: list[dict]) -> dict | None:
    """What a person reads, top to bottom, as (answers read, tables read): "least" until the
    first answer that holds one of the label's table sets, "most" until every set the
    answers hold at all has shown up. None when they hold none."""
    first = [i for i in (next((i for i, o in enumerate(found) if v <= set(o["tables"])), None) for v in valid)
             if i is not None]
    if not first:
        return None

    def read(i: int) -> tuple[int, int]:
        return i + 1, sum(len(o["tables"]) for o in found[:i + 1])
    return {"least": read(min(first)), "most": read(max(first))}


def _gold(rows: list[dict]) -> dict[str, tuple[set, set]]:
    gold, readers = {}, {}
    for row in rows:
        if row["lake"] not in readers:
            readers[row["lake"]] = Gold(row["lake"])
        try:
            if row["gold_sql"]:
                gold[row["id"]] = readers[row["lake"]](row["db_id"], row["gold_sql"])
            else:
                # Spider 2.0 hides most gold SQL and releases the gold tables: no columns
                names = readers[row["lake"]].names
                gold[row["id"]] = ({names[(row["db_id"], t.lower())] for t in row["tables"]}, set())
        except sqlite3.Error as error:  # a broken gold query (56 in MMQA): left out
            log.warning("%s: gold query does not run, left out: %s", row["id"], error)
    return gold


def _label(rows: list[dict]) -> tuple[dict[str, list[tuple[set, set]]], list[str]]:
    """The multi-valid label of each question: the gold query and every query the labeler
    kept (runs/labeler/LAKE/labels.jsonl), as (tables, columns). Queries that read the same
    tables and columns count once. Also the questions with no label yet."""
    gold, missing = {}, []
    for lake, lake_rows in _by_lake(rows).items():
        folder = ROOT / "runs" / "labeler" / lake
        ids = {q["question_id"]: q["id"] for q in _lines(folder / "questions.jsonl")}
        labels = {one["id"]: one for one in _lines(folder / "labels.jsonl")}
        read = Gold(lake)
        for row in lake_rows:
            # taco single and cross questions share question_ids: the row id first
            one = labels.get(row["id"]) or labels.get(ids.get(row["question_id"]))
            if one is None:
                missing.append(row["id"])
                continue
            try:
                queries = [read(row["db_id"], row["gold_sql"])]
            except sqlite3.Error as error:  # a broken gold query (56 in MMQA): left out
                log.warning("%s: gold query does not run, left out: %s", row["id"], error)
                continue
            for group in one.get("interpretations") or []:
                for q in group:
                    if q["name"] != "gold" and q.get("sql"):
                        try:
                            pair = read(q["db"], q["sql"])
                        except sqlite3.Error:
                            continue
                        if pair not in queries:
                            queries.append(pair)
            gold[row["id"]] = queries
    return gold, missing


def summary(scored: dict[str, dict], rows: list[dict]) -> dict:
    """Per lake the mean over its questions; then the mean over lakes and the worst lake."""
    out = {}
    for lake, lake_rows in _by_lake(rows).items():
        one = [scored[row["id"]] for row in lake_rows if row["id"] in scored]
        out[lake] = {
            level: {key: mean(s[level][key] for s in one) for key in one[0][level]}
            for level in LEVELS
            if all(level in s for s in one)
        }
        for key in ("count", "size"):
            out[lake][key] = mean(s[key] for s in one)
        out[lake]["questions"] = len(one)
    lakes = [out[lake] for lake in out]
    for name, pool in (("mean", mean), ("worst", min)):
        out[name] = {
            level: {key: pool(one[level][key] for one in lakes) for key in lakes[0][level]}
            for level in LEVELS
            if all(level in one for one in lakes)
        }
        # the worst lake returns the most
        for key in ("count", "size"):
            out[name][key] = (mean if name == "mean" else max)(one[key] for one in lakes)
        out[name]["questions"] = sum(one["questions"] for one in lakes)
    return out


def holds(new: dict, bases: list[dict], levels=("tables", "interpretation")) -> bool:
    """Rule 1: at least the lower of the base runs, mean and worst lake, every key."""
    return all(
        new[pool][level][key] >= min(base[pool][level][key] for base in bases) - 1e-9
        for pool in ("mean", "worst")
        for level in levels
        for key in KEYS
    )


def _table(summaries: dict[str, dict], level: str) -> list[str]:
    tags = list(summaries)
    head = "| lake | " + " | ".join(f"{t} R / CR / P" for t in tags) + " |"
    lines = [head, "|" + "---|" * (len(tags) + 1)]
    for lake in list(next(iter(summaries.values()))):
        cells = []
        for tag in tags:
            one = summaries[tag][lake].get(level)
            cells.append(" / ".join(f"{one[key]:.0%}" for key in KEYS) if one else "--")
        lines.append(f"| {lake} | " + " | ".join(cells) + " |")
    return lines


def _diverse(found: list[dict], n: int) -> list[dict]:
    """n interpretations that show every binding of the list before any repeats: each one,
    in order, that holds a (column or table, value) no earlier pick holds, then the first
    of the rest; in their order in the list."""
    kept, seen = [], set()
    for i, one in enumerate(found):
        keys = {(binding[0], json.dumps(binding[1])) for binding in one["values"]}
        if len(kept) < n and keys - seen:
            kept.append(i)
            seen |= keys
    kept += [i for i in range(len(found)) if i not in kept][: n - len(kept)]
    return [found[i] for i in sorted(kept)]


def _covering(found: list[dict], n: int) -> list[str]:
    """The n tables most likely to hold a whole interpretation (AMIGO records): each one's odds
    are 2^-cost, and n tables hold the odds of every interpretation inside them. Tables
    are nodes and interpretations weighted hyperedges, so this is a densest k-subhypergraph
    problem (NP-hard): greedy by odds gained per table added, tried from each table set that
    fits, as for budgeted coverage (Khuller, Moss and Naor 1999). Free places left go to the
    tables in the most odds. Tables in the order taken, the likeliest first within a set."""
    best = min(one["cost"] for one in found)
    odds, each = defaultdict(float), defaultdict(float)
    for one in found:
        odds[frozenset(one["tables"])] += 2 ** (best - one["cost"])
        for t in one["tables"]:
            each[t] += 2 ** (best - one["cost"])

    small = [(tables, p) for tables, p in odds.items() if len(tables) <= n]  # the only ones that fit

    def held(taken: set) -> float:
        return sum(p for tables, p in small if tables <= taken)

    added: dict[frozenset, tuple] = {}

    def after(taken: frozenset) -> tuple:
        """The sets the greedy adds from `taken` on (the same from the same tables, so kept):
        the odds a set gains are those of the sets it completes, found by what they lack."""
        if taken not in added:
            fits = [s for s, _ in small if not s <= taken and len(taken | s) <= n]
            lack = defaultdict(float)
            for tables, p in small:
                if not tables <= taken:
                    lack[tables - taken] += p

            def gain(s: frozenset) -> float:
                rest = sorted(s - taken)
                return sum(lack.get(frozenset(c), 0.0) for k in range(1, len(rest) + 1)
                           for c in itertools.combinations(rest, k)) / len(rest)

            s = max(fits, key=gain) if fits else None
            added[taken] = () if s is None else (s,) + after(taken | s)
        return added[taken]

    def grow(first: frozenset) -> list[str]:
        order, taken = sorted(first, key=lambda t: (-each[t], t)), first
        for s in after(first):
            order += sorted(s - taken, key=lambda t: (-each[t], t))
            taken |= s
        return order

    order = max((grow(s) for s, _ in small), key=lambda o: held(set(o)), default=[])
    return order + sorted(set(each) - set(order), key=lambda t: (-each[t], t))[: n - len(order)]


def cut(record: dict, how: str) -> dict:
    """An AMIGO record cut down after the run. firstN keeps its first N interpretations (the
    likeliest column choices come first) and diverseN N of them by _diverse; both are scored
    on the columns their interpretations bind. kN keeps the first N tables met walking the
    interpretations in order, coverN the N tables of _covering; both scored like a table
    retriever's top N. union is one interpretation holding every table of the answer."""
    kind, n = re.fullmatch(r"(first|diverse|k|cover|union)(\d*)", how).groups()
    found = record["interpretations"]
    if kind == "union":
        every = {t for one in found for t in one["tables"]}
        return {"picked": [], "interpretations": [{"tables": sorted(every), "bound": [], "joins": []}],
                "levels": ["tables"]}
    n = int(n)
    if kind in ("k", "cover"):
        if kind == "k":
            order = list(dict.fromkeys(t for one in found for t in one["tables"]))[:n]
        else:
            order = _covering(found, n) if found else []
        return {
            "picked": [],
            "interpretations": [{"tables": sorted(order), "bound": [], "joins": []}],
            "levels": ["tables"],
            "order": order,
        }
    kept = found[:n] if kind == "first" else _diverse(found, n)
    return {**record, "picked": sorted({c for one in kept for c in one["bound"]}), "interpretations": kept}


def scored_tag(name: str, rows: list[dict], gold: dict) -> dict[str, dict]:
    """`tag`, `tag@threshold` or either with `:cut` (see `cut`); threshold 0.4 when none is
    given. A baseline's tag holds records.json (baselines/run.py). `gold` maps an id to its
    label's queries."""
    name, _, how = name.partition(":")
    tag, _, threshold = name.partition("@")
    path = RUNS / tag / "records.json"
    if threshold or not path.exists():
        path = RUNS / tag / f"records_{float(threshold or 0.4)}.json"
    records = _load(path)
    ranked = bool(RANKED.fullmatch(tag)) or how.startswith(("k", "cover"))
    return {
        row["id"]: measure(gold[row["id"]], cut(one, how) if how else one, ranked)
        for row in rows
        if row["id"] in gold and "error" not in (one := records.get(row["id"], {"error": "missing"}))
    }


def report(names: list[str]) -> None:
    """EVAL_LABEL=plus scores against the multi-valid label, on the lakes that have one."""
    rows = _lines(QUESTIONS)
    if LABEL == "plus":
        rows = [row for row in rows if (ROOT / "runs" / "labeler" / row["lake"]).is_dir()]
        gold, unlabeled = _label(rows)
        print(f"multi-valid label; no label yet: {unlabeled or 'none'}")
    else:
        gold = {qid: [pair] for qid, pair in _gold(rows).items()}
    scored = {name: scored_tag(name, rows, gold) for name in names}
    # every tag is scored on the questions all of them ran
    common = set.intersection(*(set(s) for s in scored.values()))
    missing = sorted({row["id"] for row in rows} - common)
    print(f"{len(common)} of {len(rows)} questions ran in every tag; left out: {missing or 'none'}\n")
    for half in ("choose", "check", "all"):
        kept = [row for row in _half(rows, half) if row["id"] in common]
        summaries = {name: summary(scored[name], kept) for name in names}
        print(f"## {half if half == 'all' else half + ' half'}, {len(kept)} questions\n")
        for level in LEVELS:
            print(f"### {level}\n")
            print("\n".join(_table(summaries, level)) + "\n")
        counts = ", ".join(f"{n} {summaries[n]['mean']['count']:.1f}" for n in names)
        print(f"interpretations per question, mean over lakes: {counts}\n")


def compare(names: list[str]) -> None:
    """One line per tag at the tables level, on the questions every tag ran that have a
    multi-valid label: R / CR / P / F1 / NDCG against the gold query, then against the
    label, and the tables returned per question. The mean over lakes, then the worst lake
    when there are several. NDCG only for ranked answers (RANKED, AMIGO's kN)."""
    rows = [row for row in _lines(QUESTIONS) if (ROOT / "runs" / "labeler" / row["lake"]).is_dir()]
    plus, unlabeled = _label(rows)
    rows = [row for row in rows if row["id"] in plus]
    gold = {qid: [pair] for qid, pair in _gold(rows).items()}
    scored = {
        name: (scored_tag(name, rows, gold), scored_tag(name, rows, plus)) for name in names
    }
    common = set.intersection(*(set(g) & set(p) for g, p in scored.values()))
    kept = [row for row in rows if row["id"] in common]
    out = sorted({row["id"] for row in rows} - common)
    print(f"{len(kept)} questions; no label: {len(unlabeled)}; left out by some tag: "
          f"{len(out)} {out[:10] if out else ''}\n")
    pools = ["mean"] + (["worst"] if len(_by_lake(kept)) > 1 else [])
    keys = ("recall", "complete", "precision", "f1", "ndcg")
    for pool in pools:
        print(f"### {pool if len(pools) > 1 else kept[0]['lake']}\n")
        head = " | ".join(f"{label} {k}" for label in ("gold", "multi") for k in ("R", "CR", "P", "F1", "NDCG"))
        print(f"| tag | {head} | tables |")
        print("|---" * 12 + "|")
        for name, pair in scored.items():
            sums = [summary(one, kept)[pool]["tables"] for one in pair]
            cells = [f"{one[k]:.1%}" if k in one else "--" for one in sums for k in keys]
            size = summary(pair[0], kept)[pool]["size"]
            print(f"| {name} | " + " | ".join(cells) + f" | {size:.2f} |")
        print()


# ---- paired: two tags, question by question


def paired(names: list[str]) -> None:
    """Pairs of tags (A B ...), question by question at the tables level, gold then label,
    on each half and all: questions only A or only B gets complete, a two-sided sign test
    on them, and A's mean F1 lead with a 95% paired bootstrap interval."""
    rows = [row for row in _lines(QUESTIONS) if (ROOT / "runs" / "labeler" / row["lake"]).is_dir()]
    plus, _ = _label(rows)
    rows = [row for row in rows if row["id"] in plus]
    gold = {qid: [pair] for qid, pair in _gold(rows).items()}
    draw = random.Random(0)
    for a, b in zip(names[::2], names[1::2]):
        for against, truth in (("gold", gold), ("multi", plus)):
            sa, sb = scored_tag(a, rows, truth), scored_tag(b, rows, truth)
            for half in ("choose", "check", "all"):
                ids = [row["id"] for row in _half(rows, half) if row["id"] in sa and row["id"] in sb]
                if not ids:  # a tag run on one half only
                    continue
                print(f"{a} vs {b} | {against} | {half} {len(ids)} | {_versus(sa, sb, ids, draw)}")


def _paired(sa: dict, sb: dict, ids: list[str], draw: random.Random) -> dict:
    """A against B at the tables level, question by question: the questions only one of
    them gets complete, a two-sided sign test on them, and A's mean lead in F1, complete
    recall and precision, each with a 95% paired bootstrap interval."""
    won = sum(sa[q]["tables"]["complete"] > sb[q]["tables"]["complete"] for q in ids)
    lost = sum(sa[q]["tables"]["complete"] < sb[q]["tables"]["complete"] for q in ids)
    tail = sum(math.comb(won + lost, i) for i in range(min(won, lost) + 1))
    out = {"cr_won": won, "cr_lost": lost, "sign_p": min(1.0, 2 * tail / 2 ** (won + lost))}
    for name, key in (("f1", "f1"), ("cr", "complete"), ("p", "precision")):
        lead = [sa[q]["tables"][key] - sb[q]["tables"][key] for q in ids]
        means = sorted(mean(draw.choices(lead, k=len(lead))) for _ in range(2000))
        out |= {f"{name}_lead": mean(lead), f"{name}_low": means[50], f"{name}_high": means[1949]}
    return out


def _versus(sa: dict, sb: dict, ids: list[str], draw: random.Random) -> str:
    v = _paired(sa, sb, ids, draw)
    return (f"complete won {v['cr_won']} lost {v['cr_lost']} p={v['sign_p']:.3f} | "
            f"F1 {v['f1_lead']:+.1%} [{v['f1_low']:+.1%}, {v['f1_high']:+.1%}]")


# ---- AMIGO: the search, the judge, the search again (amigo/judge.py)

AMIGO_WORKERS = int(os.environ.get("EVAL_WORKERS", 16))  # more for a local model


def run_amigo(tag: str) -> None:
    """AMIGO on the questions of EVAL_HALF (choose, check or all): stage 1 on the
    question's saved parts (no LLM call), then the two judge calls. Saves RUNS/TAG/ID.amigo.pkl:
    the candidates, the places shown, their grades, the candidates before the whole grades
    and those grades, the question's parts and stage 1 (to search again without a call),
    the seconds, and the error when a judge call failed (the candidates are then the
    search's own, or the place grades' own). Questions saved already are skipped."""
    embed._model()  # once, before the threads: threads loading it at once crash Python
    folder = RUNS / tag
    folder.mkdir(parents=True, exist_ok=True)
    rows = _half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))
    for lake, lake_rows in _by_lake(rows).items():
        todo = [row for row in lake_rows if not (folder / f"{row['id']}.amigo.pkl").exists()]
        if not todo:
            continue
        started = time.monotonic()
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        log.info("%s %s: load %.1f s", tag, lake, time.monotonic() - started)

        def one(row):
            entities = _entities(row["id"])
            if entities is None:
                log.warning("%s: no split, left out", row["id"])
                return
            llm.QUESTION.set(row["id"])
            clock = Clock()
            CLOCK.set(clock)
            error = None
            stage = _bundle.stage1(probe, row["question"], folder / "stage1.jsonl", entities=entities)
            lap("lookups")
            try:
                found, shown, grades, placed, wholes = judge.interpret(
                    probe, graph, stage, row["question"], folder / "judge.jsonl")
            except llm.ModelError as err:  # the search's own order, and the failure counted
                found = candidates.candidates(probe, graph, stage, judge.MOST)[:judge.MOST]
                shown, grades, error = [], [], str(err)
                placed, wholes = found, []
            if wholes is None:
                error = "judge wholes failed"
            (folder / f"{row['id']}.amigo.pkl").write_bytes(
                pickle.dumps({"found": found, "shown": shown, "grades": grades, "placed": placed, "wholes": wholes,
                              "entities": stage.entities, "stage": stage,
                              "seconds": {"total": _since(clock.started), **clock.seconds},
                              "error": error}))

        with ThreadPoolExecutor(max_workers=AMIGO_WORKERS) as pool:
            list(pool.map(one, todo))
        log.info("%s %s: %d questions", tag, lake, len(todo))
    lines = _lines(folder / "judge.jsonl") if (folder / "judge.jsonl").exists() else []
    cost = serve.usage_totals(lines)
    saved = {p.name: pickle.loads(p.read_bytes()) for p in folder.glob("*.amigo.pkl")}
    failed = [n for n, got in saved.items() if got["error"]]
    empty = sum(not got["found"] for got in saved.values())
    relaxed = sum(bool(got["found"]) and bool(got["found"][0].left_out) for got in saved.values())
    capped = sum(len(got["placed"]) >= judge.MOST for got in saved.values())
    refused = sum(bool(got["found"]) and bool(got["found"][0].extra.get("judged_no")) for got in saved.values())
    print(f"{tag}: {cost['calls']} judge calls, ${cost['dollars']:.3f}; judge failed on {failed or 'none'}; "
          f"{empty} of {len(saved)} questions have no interpretation; "
          f"{relaxed} have only relaxed ones, leaving out parts; "
          f"{capped} reach the cap of {judge.MOST} interpretations; "
          f"{refused} have every interpretation judged no as a whole, all returned, marked")


def widen(tag: str, new: str, within: float) -> None:
    """The AMIGO run `tag` searched again with no LLM call, on each question's saved place and
    whole grades, keeping every interpretation the answer
    at `within` bits could hold; saved as the run `new`."""
    folder = RUNS / new
    folder.mkdir(parents=True, exist_ok=True)
    rows = _half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))
    widest = 0
    for lake, lake_rows in _by_lake(rows).items():
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        for row in lake_rows:
            path = RUNS / tag / f"{row['id']}.amigo.pkl"
            if not path.exists():
                continue
            saved = pickle.loads(path.read_bytes())
            stage = saved["stage"]
            costs = judge.graded(saved["shown"], saved["grades"]) if saved["grades"] else None
            placed = candidates.candidates(probe, graph, stage, 1, graded=costs, bits=within)
            if not placed and costs:
                placed = judge.relaxed(probe, graph, stage, costs, 1, within)
            if costs:
                placed = judge.split(placed, costs)
            widest = max(widest, len(placed))
            saved = {**saved, "placed": placed, "found": judge.kept(placed, saved.get("wholes") or [])}
            (folder / path.name).write_bytes(pickle.dumps(saved))
    print(f"{new}: {tag} searched again for answers up to {within:g} bits; at most {widest} candidates")


ABLATIONS = ("nojudge2", "norelaxed", "nojudge", "nojudge1", "nojudgedlinks")


def _ablated(saved: dict, how: str) -> list:
    """The interpretations of a saved AMIGO answer with no LLM call: nojudge2 skips the
    whole grades, norelaxed answers nothing where only relaxed interpretations were found."""
    if how == "nojudge2":
        return saved["placed"]
    found = saved["found"]
    return [] if found and found[0].left_out else found


def ablate(tag: str, new: str, how: str) -> None:
    """The AMIGO run `tag` with one part removed (night plan 5.4), saved as the run `new`:
    nojudge2 and norelaxed (_ablated), nojudge (every place kept, then the search with its
    relaxed fallback, no whole grades), nojudge1 (every place kept, then the search and the
    whole grades), nojudgedlinks (no LLM-judged join link,
    the saved place grades, then the search and the whole grades). A saved answer with an
    error is copied as it is."""
    if how not in ABLATIONS:
        sys.exit(f"ablate: {how!r} is not one of {ABLATIONS}")
    folder = RUNS / new
    folder.mkdir(parents=True, exist_ok=True)
    rows = _half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))
    kinds = frozenset({"declared", "inferred", "values", "name"}) if how == "nojudgedlinks" else None
    copied = 0
    for lake, lake_rows in _by_lake(rows).items():
        todo = [row for row in lake_rows if (RUNS / tag / f"{row['id']}.amigo.pkl").exists()
                and not (folder / f"{row['id']}.amigo.pkl").exists()]
        if not todo:
            continue
        probe = Probe(lake)
        graph = candidates.Graph(probe, kinds)

        def one(row) -> bool:
            path = RUNS / tag / f"{row['id']}.amigo.pkl"
            saved = pickle.loads(path.read_bytes())
            if saved["error"]:
                (folder / path.name).write_bytes(path.read_bytes())
                return True
            llm.QUESTION.set(row["id"])
            stage, shown = saved["stage"], saved["shown"]
            out = {k: v for k, v in saved.items() if k != "seconds"}
            if how in ("nojudge2", "norelaxed"):
                out |= {"found": _ablated(saved, how), "seconds": saved["seconds"]}
            else:
                grades = saved["grades"] if how == "nojudgedlinks" else \
                    [{(h.table, h.column): True for h in mine} for mine in shown]
                places = judge.graded(shown, grades)
                found = candidates.candidates(probe, graph, stage, judge.MOST, graded=places)
                if not found:
                    found = judge.relaxed(probe, graph, stage, places, judge.MOST, None)
                placed = judge.split(found, places)
                try:
                    wholes = [] if how == "nojudge" or any(c.left_out for c in placed) else judge.whole_grades(
                        probe, graph, row["question"], stage, placed, folder / "judge.jsonl")
                except llm.ModelError as err:
                    log.warning("%s: judge wholes failed: %s", row["id"], err)
                    wholes = None
                out |= {"found": judge.kept(placed, wholes or []), "grades": grades, "placed": placed,
                        "wholes": wholes, "error": "judge wholes failed" if wholes is None else None}
            (folder / path.name).write_bytes(pickle.dumps(out))
            return False

        with ThreadPoolExecutor(max_workers=AMIGO_WORKERS) as pool:
            copied += sum(pool.map(one, todo))
    print(f"{new}: {tag} with {how}; {copied} answers with an error copied as they were")


def run_joins(source: str, new: str) -> None:
    """The saved interpretations of the run `source` (a folder, or a run in RUNS), each once
    per way to link its joins, with the ways a person could not mean dropped by one LLM call
    per question (judge.chosen); saved as the run `new`. A saved answer with an error is copied
    as it is; a call that fails keeps every way, the cheapest MOST, and is counted."""
    folder = RUNS / new
    folder.mkdir(parents=True, exist_ok=True)
    rows = _half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))
    copied, failed = 0, []
    for lake, lake_rows in _by_lake(rows).items():
        todo = [row for row in lake_rows if (RUNS / source / f"{row['id']}.amigo.pkl").exists()
                and not (folder / f"{row['id']}.amigo.pkl").exists()]
        if not todo:
            continue
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        memo: dict = {}

        def one(row) -> bool:
            path = RUNS / source / f"{row['id']}.amigo.pkl"
            saved = pickle.loads(path.read_bytes())
            if saved["error"]:
                (folder / path.name).write_bytes(path.read_bytes())
                return True
            llm.QUESTION.set(row["id"])
            started, error = time.monotonic(), None
            try:
                found, info = judge.chosen(probe, graph, row["question"], saved["stage"], saved["found"], memo,
                                           folder / "judge.jsonl")
            except llm.ModelError as err:
                found, info, error = judge.ways(probe, graph, saved["found"], memo)[:judge.MOST], {}, str(err)
                failed.append(row["id"])
            seconds = dict(saved["seconds"])
            seconds["llm judge joins"] = _since(started)
            seconds["total"] = round(seconds["total"] + seconds["llm judge joins"], 3)
            (folder / path.name).write_bytes(pickle.dumps(
                saved | {"found": found, "joins": info, "seconds": seconds, "error": error}))
            return False

        with ThreadPoolExecutor(max_workers=AMIGO_WORKERS) as pool:
            copied += sum(pool.map(one, todo))
    saved = [pickle.loads(p.read_bytes()) for p in folder.glob("*.amigo.pkl")]
    infos = [got["joins"] for got in saved if got.get("joins")]
    cost = serve.usage_totals(_lines(folder / "judge.jsonl")) if (folder / "judge.jsonl").exists() else {"calls": 0}
    print(f"{new}: {source} with join choices; {cost['calls']} calls; {copied} answers with an error copied; "
          f"call failed on {failed or 'none'}; "
          + "; ".join(f"{k} {sum(i[k] for i in infos)}" for k in ("joins", "refused", "ways", "capped"))
          + f"; {sum(i['joins'] > 0 for i in infos)} questions asked")


def _literal(entity: llm.Entity):
    one = entity.literal
    if one.kind == "text":
        return one.text
    if one.kind == "number":
        return one.number
    return [one.date_start, one.date_end]


def _amigo_record(probe: Probe, graph: candidates.Graph, entities: list, found: list) -> dict:
    """The eval record of AMIGO's interpretations: each one's tables, the columns holding its
    parts, its values and the columns of its joins (the links chosen, judge.ways, else the
    best link of each join; a missing link names none)."""
    interpretations = []
    for one in found:
        held = [h for h in one.holders if h is not None]
        joins = []
        for a, b in one.edges:
            ways = graph.ways.get((a, b))
            if "ways" in one.extra:
                links = [link for join in one.extra["ways"][(a, b)][1] for link in join.links]
            else:
                links = max(ways, key=lambda j: j.quality).links if ways else []
            joins += [[probe.path("column", x), probe.path("column", y)] for x, y in links]
        interpretations.append({
            "tables": sorted(probe.path("table", t) for t in one.tables),
            "bound": sorted({probe.path("column", h.column) for h in held}),
            "values": [
                [probe.path("column", h.column),
                 _literal(entities[h.part]), []]
                for h in held if entities[h.part].literal is not None
            ],
            "joins": joins,
            "cost": round(one.cost, 3),
        })
    return {"picked": sorted({c for one in interpretations for c in one["bound"]}),
            "interpretations": interpretations}


def score_amigo(tag: str, within: float) -> None:
    """RUNS/TAG/records_W.json: per question of EVAL_HALF, the interpretations at most W
    bits above the cheapest (odds at least 1 to 2^W against it), never none. A
    question the run has no answer for (its split failed) is an empty answer, a miss."""
    records, splits = {}, _load(SPLIT)
    for lake, rows in _by_lake(_half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))).items():
        probe, graph = None, None
        for row in rows:
            path = RUNS / tag / f"{row['id']}.amigo.pkl"
            if not path.exists():
                records[row["id"]] = {"picked": [], "interpretations": [], "judge_error": "no answer"}
                continue
            if probe is None:
                probe = Probe(lake)
                graph = candidates.Graph(probe)
            got = pickle.loads(path.read_bytes())
            found = got["found"]
            # an old pkl saved the total alone; the split's seconds are added, so the total is the question's
            seconds = got.get("seconds")
            seconds = dict(seconds) if isinstance(seconds, dict) else {"total": seconds}
            split_seconds = splits.get(row["id"], {}).get("seconds")
            if split_seconds is not None and seconds["total"] is not None:
                seconds = {"llm split": split_seconds, **seconds, "total": round(seconds["total"] + split_seconds, 3)}
            records[row["id"]] = _amigo_record(probe, graph, got["entities"], interpret.within(found, within)) | {
                "seconds": seconds, "judge_error": got["error"]}
    _save(RUNS / tag / f"records_{within}.json", records)


def calibration(tag: str) -> None:
    """How often an AMIGO candidate is valid, by how many bits above the cheapest it is:
    each new table set of a question's candidates, valid when it equals the tables of a
    query of the multi-valid label. Shows whether the costs read as odds."""
    rows = [row for row in _lines(QUESTIONS) if (RUNS / tag / f"{row['id']}.amigo.pkl").exists()]
    label, _ = _label(rows)
    counts = defaultdict(lambda: [0, 0])
    for lake, lake_rows in _by_lake(rows).items():
        probe = Probe(lake)
        for row in lake_rows:
            found = pickle.loads((RUNS / tag / f"{row['id']}.amigo.pkl").read_bytes())["found"]
            if row["id"] not in label or not found:
                continue
            valid = {frozenset(tables) for tables, _ in label[row["id"]]}
            seen = set()
            for one in found:
                tables = frozenset(probe.path("table", t) for t in one.tables)
                if tables in seen:
                    continue
                seen.add(tables)
                bits = "best" if not seen - {tables} else f"+{min(int(one.cost - found[0].cost), 6)}"
                counts[bits][0] += tables in valid
                counts[bits][1] += 1
    print(f"{sum(row['id'] in label for row in rows)} questions\n")
    print("| bits dearer than the best | table sets | valid |")
    print("|---|---|---|")
    for bits in ["best"] + [f"+{d}" for d in range(7)]:
        valid, n = counts[bits]
        print(f"| {bits}{' or more' if bits == '+6' else ''} | {n} | {valid / max(n, 1):.0%} |")


def _amigo_answers(tag: str, rows: list[dict]) -> dict[str, list[tuple[float, frozenset]]]:
    """Per question of an AMIGO run: each candidate's bits above the cheapest, rounded so that
    equal costs summed in another order stay equal, and its tables, cheapest first. A
    question the run has no answer for (its split failed) gets none, a miss."""
    out = {}
    for lake, lake_rows in _by_lake(rows).items():
        probe = Probe(lake)
        for row in lake_rows:
            path = RUNS / tag / f"{row['id']}.amigo.pkl"
            found = pickle.loads(path.read_bytes())["found"] if path.exists() else []
            out[row["id"]] = [(round(one.cost - found[0].cost, 6), frozenset(probe.path("table", t) for t in one.tables))
                              for one in found]
    return out


def _tables_record(found: list[tuple[float, frozenset]], within: float, one_list: bool = False) -> dict:
    """An AMIGO answer, the candidates at most `within` bits above the cheapest, as a record
    scored at the tables level; `one_list` merges them into one list of tables, the way a
    table retriever's answer is scored."""
    kept = [t for bits, t in found if bits <= within]
    kept = [frozenset().union(*kept)] if one_list and kept else kept
    return {"picked": [], "levels": ["tables"],
            "interpretations": [{"tables": sorted(t), "bound": [], "joins": []} for t in kept]}


def match(tag: str, names: list[str]) -> None:
    """The AMIGO run `tag` at each baseline's size: the largest W, among the candidates' own
    bits, at which its answers hold no more tables per question, on average, than the
    baseline's on the questions of EVAL_HALF (all by default), found from the answers alone
    (no label read); W = 0 when even the first answer holds more. Then the two against the
    gold and the multi-valid label, question by question as in `paired`; "one list" scores
    AMIGO's answer as one list of tables, the rule the baseline gets."""
    rows = [row for row in _half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))
            if (ROOT / "runs" / "labeler" / row["lake"]).is_dir()]
    plus, _ = _label(rows)
    rows = [row for row in rows if row["id"] in plus]
    gold = {qid: [pair] for qid, pair in _gold(rows).items()}
    found = _amigo_answers(tag, rows)
    for name in names:
        draw = random.Random(0)
        # a baseline, or another AMIGO run at a fixed W (`tag@W`, from score2)
        other, _, at = name.partition("@")
        base = _load(RUNS / other / (f"records_{float(at)}.json" if at else "records.json"))
        ids = [row["id"] for row in rows if row["id"] in found and "error" not in base.get(row["id"], {"error": 1})]

        def size(w: float) -> float:
            return mean(len({t for bits, tables in found[q] if bits <= w for t in tables}) for q in ids)

        target = mean(len({t for one in base[q]["interpretations"] for t in one["tables"]}) for q in ids)
        steps = sorted({bits for q in ids for bits, _ in found[q]})
        fits = bisect.bisect_right(steps, target, key=size)
        w = steps[fits - 1] if fits else 0.0
        print(f"{name}: {target:.2f} tables; {tag} at W = {w:.3f}: {size(w):.2f} tables ({len(ids)} questions, "
              f"{sum(not found[q] for q in ids)} with no answer from {tag})")
        for against, truth, one_list in (("gold", gold, False), ("multi", plus, False), ("multi, one list", plus, True)):
            sa = {q: measure(truth[q], _tables_record(found[q], w, one_list)) for q in ids}
            sb = {q: measure(truth[q], base[q]) for q in ids}
            means = [" / ".join(f"{mean(s[q]['tables'][k] for q in ids):.1%}" for k in ("recall", "complete", "precision"))
                     for s in (sa, sb)]
            print(f"  {against}: R / CR / P {tag} {means[0]}, {name} {means[1]} | {_versus(sa, sb, ids, draw)}")
            whole = [" / ".join(f"{mean(s[q]['footprint']['soft'][k] for q in ids):.1%}" for k in ("recall", "complete", "precision"))
                     for s in (sa, sb)]
            print(f"    interpretations R / CR / P {tag} {whole[0]}, {name} {whole[1]}")
            both = [q for q in ids if sa[q]["effort"] and sb[q]["effort"]]
            if both:
                for end in ("least", "most"):
                    read = [" / ".join(f"{mean(s[q]['effort'][end][k] for q in both):.2f}" for k in (0, 1)) for s in (sa, sb)]
                    print(f"    effort, {end}, on the {len(both)} questions where both hold a valid set, answers / tables "
                          f"read: {tag} {read[0]}, {name} {read[1]}")


def cascade(fast: str, slow: str, w_fast: float, w_slow: float, thresholds: list[float]) -> None:
    """Think only when unsure: the fast run's answer at w_fast, or the slow run's at w_slow
    for the questions where the fast one has no candidate, its judge failed, or its doubt
    about the tables returned is above T bits: the entropy of its candidates' table sets,
    each weighed 2^-cost (as `interpret.questions`). Per T (by default the T that send on
    0, 10, ..., 100% of the questions of EVAL_HALF): the share sent on, then against the
    gold and the label, the cascade against the slow run alone as in `match`."""
    rows = [row for row in _half(_lines(QUESTIONS), os.environ.get("EVAL_HALF", "all"))
            if (ROOT / "runs" / "labeler" / row["lake"]).is_dir()]
    plus, _ = _label(rows)
    rows = [row for row in rows if row["id"] in plus]
    gold = {qid: [pair] for qid, pair in _gold(rows).items()}
    quick, sure = _amigo_answers(fast, rows), _amigo_answers(slow, rows)
    ids = [row["id"] for row in rows if row["id"] in quick and row["id"] in sure]
    failed = {q for q in ids if not quick[q] or pickle.loads((RUNS / fast / f"{q}.amigo.pkl").read_bytes())["error"]}
    doubt = {q: interpret._entropy([t for _, t in quick[q]], [2.0 ** -bits for bits, _ in quick[q]])
             for q in ids if q not in failed}
    ranked = sorted(doubt.values(), reverse=True)
    thresholds = thresholds or [ranked[0] + 1] + [ranked[min(len(ranked), round(s * len(ids))) - 1] for s in
                                                  [i / 10 for i in range(1, 10)]] + [-1.0]
    def size(answer: dict) -> float:
        return mean(len({t for one in answer[q]["interpretations"] for t in one["tables"]}) for q in ids)

    alone = {q: _tables_record(sure[q], w_slow) for q in ids}
    print(f"{len(ids)} questions; the fast run has no candidate or its judge failed on {len(failed)}; "
          f"{slow} alone {size(alone):.2f} tables")
    for t in thresholds:
        sent = failed | {q for q, d in doubt.items() if d > t}
        answer = {q: alone[q] if q in sent else _tables_record(quick[q], w_fast) for q in ids}
        print(f"T = {t:.3f} bits: sent on {len(sent) / len(ids):.1%}, {size(answer):.2f} tables")
        for against, truth in (("gold", gold), ("multi", plus)):
            draw = random.Random(0)
            sa = {q: measure(truth[q], answer[q]) for q in ids}
            sb = {q: measure(truth[q], alone[q]) for q in ids}
            means = [" / ".join(f"{mean(s[q]['tables'][k] for q in ids):.1%}" for k in ("recall", "complete", "precision"))
                     for s in (sa, sb)]
            print(f"  {against}: R / CR / P cascade {means[0]}, {slow} {means[1]} | {_versus(sa, sb, ids, draw)}")


def needed(found: list[tuple[float, frozenset]], valid: list[frozenset]) -> float:
    """The window an answer needs to hold every valid query inside one interpretation: over
    the valid queries, the most bits above the cheapest of the first candidate holding its
    tables; inf when no candidate holds one."""
    return max(min((bits for bits, tables in found if v <= tables), default=math.inf) for v in valid)


def conformal_window(scores: list[float], alpha: float) -> float:
    """Split conformal prediction (Vovk, Gammerman and Shafer 2005), for sets that must hold
    every true label (Cauchois, Gupta and Duchi 2021): the ceil((n + 1)(1 - alpha))-th
    smallest of n calibration scores. A new question exchangeable with the calibration
    ones needs at most this window with probability at least 1 - alpha; inf when that rank
    is past n."""
    k = math.ceil((len(scores) + 1) * (1 - alpha) - 1e-9)
    return sorted(scores)[k - 1] if k <= len(scores) else math.inf


def conformal(tag: str) -> None:
    """The window from a miss rate alpha: each question's score is the window it needs
    (`needed`, against the multi-valid label) and W is `conformal_window` of the
    calibration questions' scores. Checked on 1000 random splits of the check half
    (calibration and test exchangeable), then calibrated on the choose half and tested on
    the check half (other databases, so not exchangeable)."""
    rows = [row for row in _lines(QUESTIONS) if (ROOT / "runs" / "labeler" / row["lake"]).is_dir()]
    plus, _ = _label(rows)
    rows = [row for row in rows if row["id"] in plus]
    found = _amigo_answers(tag, rows)
    score = {q: needed(found[q], [frozenset(t) for t, _ in plus[q]]) for q in found}
    sizes: dict[tuple[str, float], int] = {}

    def size(q: str, w: float) -> int:
        if (q, w) not in sizes:
            sizes[(q, w)] = len({t for bits, tables in found[q] if bits <= w for t in tables})
        return sizes[(q, w)]

    halves = {half: [row["id"] for row in _half(rows, half) if row["id"] in score] for half in ("choose", "check")}
    for half, ids in halves.items():
        print(f"{half} half, {len(ids)} questions: a valid query no candidate holds in "
              f"{mean(math.isinf(score[q]) for q in ids):.1%}")
    check, draw = halves["check"], random.Random(0)
    print(f"\n1000 random splits of the check half: calibrate on {len(check) // 2}, test on the rest\n")
    print("| alpha | W, median | test complete, mean | splits at 1 - alpha or more | tables, mean |")
    print("|---|---|---|---|---|")
    for alpha in (0.1, 0.15, 0.2, 0.25, 0.3):
        ws, held, tables = [], [], []
        for _ in range(1000):
            ids = draw.sample(check, len(check))
            cal, test = ids[:len(check) // 2], ids[len(check) // 2:]
            w = conformal_window([score[q] for q in cal], alpha)
            ws.append(w)
            held.append(mean(score[q] <= w and score[q] < math.inf for q in test))
            tables.append(mean(size(q, w) for q in test))
        print(f"| {alpha:.2f} | {np.median(ws):.2f} | {mean(held):.1%} | {mean(h >= 1 - alpha for h in held):.0%} "
              f"| {mean(tables):.2f} |")
    print("\nCalibrated on the choose half, tested on the check half\n")
    print("| alpha | W | check complete | tables, mean |")
    print("|---|---|---|---|")
    for alpha in (0.1, 0.15, 0.2, 0.25, 0.3):
        w = conformal_window([score[q] for q in halves["choose"]], alpha)
        print(f"| {alpha:.2f} | {w:.2f} | {mean(score[q] <= w and score[q] < math.inf for q in check):.1%} "
              f"| {mean(size(q, w) for q in check):.2f} |")


def _answered(found: list, j: int, options: list, ticked: set) -> list:
    if ANSWERS == "drop":
        return [one for one in found if interpret.answer_of(one, j, options) in ticked] or found
    return interpret.answered(found, j, options, ticked)


def _groups(rows: list[dict]) -> dict[str, list[tuple[list[tuple[set, set]], str, str]]]:
    """Per question, the interpretations of its multi-valid label: each a group of queries
    that return the same rows, as (tables, columns), with the database and SQL of one of
    them (the gold query's in its group); the gold query's group first."""
    out = {}
    for lake, lake_rows in _by_lake(rows).items():
        folder = ROOT / "runs" / "labeler" / lake
        ids = {q["question_id"]: q["id"] for q in _lines(folder / "questions.jsonl")}
        labels = {one["id"]: one for one in _lines(folder / "labels.jsonl")}
        read = Gold(lake)
        for row in lake_rows:
            # taco single and cross questions share question_ids: the row id first
            one = labels.get(row["id"]) or labels.get(ids.get(row["question_id"]))
            if one is None:
                continue
            gold = read(row["db_id"], row["gold_sql"])
            groups = []
            for group in one.get("interpretations") or []:
                queries, texts = [], []
                for q in group:
                    pair = gold if q["name"] == "gold" else read(q["db"], q["sql"]) if q.get("sql") else None
                    if pair is not None and pair not in queries:
                        queries.append(pair)
                        texts.append((row["db_id"], row["gold_sql"]) if pair == gold else (q["db"], q["sql"]))
                if queries:
                    db, sql = texts[queries.index(gold)] if gold in queries else texts[0]
                    groups.append((queries, db, sql))
            groups.sort(key=lambda g: gold not in g[0])
            if not groups or gold not in groups[0][0]:
                groups.insert(0, ([gold], row["db_id"], row["gold_sql"]))
            out[row["id"]] = groups
    return out


def _question(found: list, within: float, asked: set = frozenset()):
    """The part to ask about and the places shown (interpret.questions), or None when no
    answer would change the tables returned; ASK chooses among the questions worth
    asking: the most information gain (AMIGO's), the first part, or a random one."""
    worth = interpret.questions(found, within, asked, _answered) if found else []
    if not worth:
        return None
    if ASK == "first":
        _, j, options = worth[0]
    elif ASK == "random":
        _, j, options = random.Random(f"{found[0].cost} {sorted(asked)}").choice(worth)
    else:
        _, j, options = max(worth, key=lambda e: e[0])
    return j, options


class Places(BaseModel):
    places: list[int]
    unsure: bool
    why: str


def _llm_person(probe: Probe, row: dict, stage, db: str, sql: str, log_path: Path):
    """The LLM person for one question and the query they meant: `said(j, options)` is the
    set they tick, empty when they are unsure or the call fails (counted in `failed`)."""
    template = string.Template(PERSON_PROMPT.read_text())
    failed = []

    def said(j: int, options: list) -> set:
        def check(reply: Places) -> None:
            bad = [n for n in reply.places if not 0 <= n <= len(options)]
            if bad:
                raise llm.ModelError(f"places are 0 to {len(options)}, not {bad}")

        prompt = template.substitute(question=row["question"], db=db, sql=sql,
                                     asked=interpret.wording(probe, stage, j, options))
        try:
            reply = llm.call(prompt, Places, log_path, "person", check=check, effort="low", model=PERSON_MODEL)
        except llm.ModelError as err:
            failed.append(str(err))
            return set()
        return set() if reply.unsure else {"none" if n == 0 else options[n - 1] for n in reply.places}

    said.failed = failed
    return said


def _person(probe: Probe, found: list, j: int, options: list, meant: list[tuple[set, set]], said=None) -> set:
    """The answers the person ticks: the places shown, or none of these, that lead to the
    interpretation closest to the one they meant (the most of its tables, then the fewest
    others). The label names the columns a query reads but not which part each one
    holds, so the person is judged by where an answer leads, not by a column name.
    With PERSON "columns", a stricter person: the places shown that their query reads (a
    column it reads, or a table it reads for a table place), else none of these. With
    PERSON "llm", `said` (_llm_person) answers, and may be unsure (nothing ticked). With
    SLIP, the person answers wrong that share of the time: one other option, at random."""
    if PERSON == "llm":
        return said(j, options)
    if PERSON == "columns":
        tables = set().union(*(t for t, _ in meant))
        columns = set().union(*(c for _, c in meant))
        ticked = {o for o in options if (probe.path("column", o[1]) in columns if o[1] is not None
                                         else probe.path("table", o[0]) in tables)} or {"none"}
    else:
        def closeness(one) -> tuple[float, float]:
            tables = {probe.path("table", t) for t in one.tables}
            return max((len(t & tables) / len(t), len(t & tables) / len(tables)) for t, _ in meant)

        best: dict = {}
        for one in found:
            answer = interpret.answer_of(one, j, options)
            best[answer] = max(best.get(answer, (-1.0, -1.0)), closeness(one))
        top = max(best.values())
        ticked = {answer for answer, value in best.items() if value == top}
    chance = random.Random(f"slip {found[0].cost} {j} {sorted(map(str, ticked))} {sorted(sorted(t) for t, _ in meant)}")
    wrong = [o for o in options + ["none"] if o not in ticked]
    return {chance.choice(wrong)} if wrong and chance.random() < SLIP else ticked


def _closest(meant: list[tuple[set, set]], record: dict) -> dict:
    """An answer's tables scored against the query of the meant interpretation it comes
    closest to: its queries return the same rows, so any one of them serves the person."""
    return max((measure([q], record) for q in meant), key=lambda m: (m["tables"]["recall"], m["tables"]["precision"]))


def _after_none(probe: Probe, found: list, shown: list, within: float, meant: list, said=None) -> dict:
    """When no interpretation shown holds what the person meant: AMIGO's questions, then
    the interpretations of the new answer not shown before; against reading on down the
    candidates for as many items as that took. Each option of a question read counts as
    an item, up to the last one ticked (all of them and none of these when none is)."""
    def key(one) -> tuple:
        return one.tables, tuple(None if h is None else (h.table, h.column) for h in one.holders), one.edges

    def holds(one) -> bool:
        tables = {probe.path("table", t) for t in one.tables}
        return any(t <= tables for t, _ in meant)

    seen = {key(one) for one in shown}
    now, asked, read = found, set(), 0
    while len(asked) < interpret.BUDGET and (question := _question(now, within, asked)) is not None:
        j, options = question
        asked.add(j)
        ticked = _person(probe, now, j, options, meant, said)
        answers = options + [interpret.NONE]
        read += max(answers.index(a) + 1 for a in ticked) if ticked else len(answers)
        now = _answered(now, j, options, ticked) if ticked else now
    new = [one for one in interpret.within(now, within) if key(one) not in seen]
    at = next((i for i, one in enumerate(new, 1) if holds(one)), 0)
    read += at or len(new)
    on = next((i for i, one in enumerate((one for one in found if key(one) not in seen), 1) if holds(one)), 0)
    return {"none": 1, "questions": len(asked), "asking finds": at > 0, "read": read, "reading on finds": 0 < on <= read}


def run_hitl(tag: str, within: float, bases: list[str]) -> None:
    """Per question and per interpretation of its label as the one the person meant: AMIGO's
    answer after 0 to interpret.BUDGET questions, against that interpretation alone (_closest),
    tables level; and each base tag's answer against it too. Each question weighs one, its
    interpretations share that weight. Twice: the person meant the gold query's
    interpretation, and the person meant any. EVAL_PERSON sets how the person answers,
    EVAL_SLIP how often they answer wrong, EVAL_ANSWERS what an answer does."""
    rows = [row for row in _lines(QUESTIONS) if (RUNS / tag / f"{row['id']}.amigo.pkl").exists()]
    groups = _groups(rows)
    rows = [row for row in rows if row["id"] in groups]
    base_records = {}
    for name in bases:
        n, _, threshold = name.partition("@")
        path = RUNS / n / "records.json"
        if threshold or not path.exists():
            path = RUNS / n / f"records_{float(threshold or 0.4)}.json"
        base_records[name] = _load(path)
    rows = [row for row in rows if all(row["id"] in r and "error" not in r[row["id"]] for r in base_records.values())]
    keys = ("recall", "complete", "precision", "f1")
    totals = {who: defaultdict(lambda: defaultdict(float)) for who in ("gold", "any")}
    asked = {who: defaultdict(float) for who in ("gold", "any")}
    unsure, failed = Counter(), []
    for lake, lake_rows in _by_lake(rows).items():
        probe = Probe(lake)
        graph = candidates.Graph(probe)

        def one(row) -> list[tuple]:
            """This question's sums, as (who, line, key, value) to add."""
            llm.QUESTION.set(row["id"])
            got = pickle.loads((RUNS / tag / f"{row['id']}.amigo.pkl").read_bytes())
            mine, out = groups[row["id"]], []
            for who, meant_all in (("gold", mine[:1]), ("any", mine)):
                share = 1 / len(meant_all)
                for meant, db, sql in meant_all:
                    said = _llm_person(probe, row, got["stage"], db, sql, RUNS / tag / "person.jsonl") if PERSON == "llm" else None
                    found, count, parts = got["found"], 0, set()
                    for n in range(interpret.BUDGET + 1):
                        if n:
                            question = _question(found, within, parts) if found else None
                            if question is not None:
                                j, options = question
                                parts.add(j)
                                ticked = _person(probe, found, j, options, meant, said)
                                found = _answered(found, j, options, ticked) if ticked else found
                                count += 1
                                out.append((who, "unsure", "n", share * (not ticked)))
                        record = _amigo_record(probe, graph, got["entities"], interpret.within(found, within))
                        scored = _closest(meant, record)["tables"]
                        line = f"AMIGO asks {n}"
                        out += [(who, line, k, share * scored[k]) for k in keys]
                        # interpretations read, best first, up to the first holding a meant
                        # query's tables, or all of them when none does (Cooper's search length)
                        spans = [set(o["tables"]) for o in record["interpretations"]]
                        reached = next((i for i, span in enumerate(spans, 1) if any(t <= span for t, _ in meant)), 0)
                        out.append((who, line, "read", share * (reached or len(spans))))
                        out.append((who, line, "size", share * len({t for o in record["interpretations"] for t in o["tables"]})))
                        out.append((who, line, "asked", share * count))
                        if n == 0:
                            # no question: the person picks from the list, the first
                            # interpretation holding a meant query's tables, else none of
                            # these and the answer stays
                            picked = {**record, "interpretations": record["interpretations"][reached - 1:reached]} if reached else record
                            scored = _closest(meant, picked)["tables"]
                            out += [(who, "AMIGO picks", k, share * scored[k]) for k in keys]
                            out.append((who, "AMIGO picks", "read", share * (reached or len(spans))))
                            out.append((who, "AMIGO picks", "size", share * len({t for o in picked["interpretations"] for t in o["tables"]})))
                            out.append((who, "AMIGO picks", "asked", 0.0))
                            if not reached:
                                shown = interpret.within(found, within)
                                out += [(who, "after none", k, share * v)
                                        for k, v in _after_none(probe, found, shown, within, meant, said).items()]
                    for name, records in base_records.items():
                        scored = _closest(meant, records[row["id"]])
                        out += [(who, name, k, share * scored["tables"][k]) for k in keys]
                        out.append((who, name, "size", share * scored["size"]))
                        out.append((who, name, "asked", 0.0))
                    if said is not None:
                        failed.extend(said.failed)
            return out

        with ThreadPoolExecutor(max_workers=AMIGO_WORKERS) as pool:
            for out in pool.map(one, lake_rows):
                for who, line, k, value in out:
                    if line == "unsure":
                        unsure[who] += value
                    elif k == "asked":
                        asked[who][line] += value
                    else:
                        totals[who][line][k] += value
    print(f"{len(rows)} questions, answers within {within} bits, person {PERSON}, wrong {SLIP:.0%} of the time, "
          f"answers {ANSWERS}\n")
    if PERSON == "llm":
        print(f"person {PERSON_MODEL}: unsure (nothing ticked) {unsure['any'] / len(rows):.2f} times per question "
              f"on average; person calls failed {len(failed)} times (counted as unsure)\n")
    for who in ("gold", "any"):
        print(f"### the person meant {'the gold query' if who == 'gold' else 'any interpretation of the label'}\n")
        print("| method | R | CR | P | F1 | tables | questions asked | interpretations read |")
        print("|---|---|---|---|---|---|---|---|")
        for name, sums in totals[who].items():
            if name == "after none":
                continue
            cells = " | ".join(f"{sums[k] / len(rows):.1%}" for k in keys)
            read = f"{sums['read'] / len(rows):.2f}" if "read" in sums else "--"
            print(f"| {name} | {cells} | {sums['size'] / len(rows):.2f} | {asked[who][name] / len(rows):.2f} | {read} |")
        none = totals[who]["after none"]
        if none["none"]:
            print(f"\nNone of the first answer holds it: {none['none'] / len(rows):.1%} of the time. Then "
                  f"{none['questions'] / none['none']:.2f} questions and the new interpretations find it "
                  f"{none['asking finds'] / none['none']:.1%} of those times, after {none['read'] / none['none']:.2f} "
                  f"items read; reading on as many items finds it {none['reading on finds'] / none['none']:.1%}.")
        print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    command, args = sys.argv[1], sys.argv[2:]
    if command == "sample":
        sample()
    elif command == "split":
        split()
    elif command == "report":
        report(args)
    elif command == "compare":
        compare(args)
    elif command == "paired":
        paired(args)
    elif command == "amigo":
        run_amigo(args[0])
    elif command == "widen":
        widen(args[0], args[1], float(args[2]))
    elif command == "ablate":
        ablate(args[0], args[1], args[2])
    elif command == "joins":
        run_joins(args[0], args[1])
    elif command == "score2":
        score_amigo(args[0], float(args[1]))
    elif command == "calib":
        calibration(args[0])
    elif command == "match":
        match(args[0], args[1:])
    elif command == "cascade":
        cascade(args[0], args[1], float(args[2]), float(args[3]), [float(t) for t in args[4:]])
    elif command == "conformal":
        conformal(args[0])
    elif command == "hitl":
        run_hitl(args[0], float(args[1]), args[2:])
    else:
        raise SystemExit(f"unknown command {command!r}")
