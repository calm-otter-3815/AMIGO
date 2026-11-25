"""Judged cleanup of taco_us: is each question really about the tables its gold SQL reads?

  .venv/bin/python experiments/clean_taco_us.py            every question of dev.json and dev_cross.json
  .venv/bin/python experiments/clean_taco_us.py pilot 40   40 questions drawn at random, verdicts printed

TACO writes the question text from the SQL in four model steps, so some questions ask about
data their gold tables do not hold. One Qwen call per question (the labeler's local judge,
labeler/llm.py, replies cached): the judge sees the question, the gold SQL and each gold
table with its columns and sample values, and says per table whether the question is about
it. Writes runs/taco_us/clean.jsonl; experiments/prepare_taco_us.py then drops every
question whose tables were all voted "no". Extra filters, dates or wishes in the text are not a "no":
TACO adds those on purpose.
"""

import json
import os
import random
import sqlite3
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("LABEL_CACHE", "cache-taco_us.jsonl")  # the taco_us label run's replies
from labeler import llm, run  # noqa: E402

LAKE = ROOT / "benchmarks" / "taco_us"
OUT = ROOT / "runs" / "taco_us"
LIMIT = 8_000  # tokens per call; the last retry gets the full room
SHOWN_COLUMNS = 40
NAME_CUT = 60

PROMPT = """You check a benchmark of questions over government open-data tables. Each question comes with a reference SQL query. The question text was written by a model from the SQL and sometimes drifts: it asks about data the query's tables do not hold. Your task: for each table the query reads, decide whether this question is about the data that table holds.

Say "yes" when the question asks for the kind of records the table holds, even if the question adds filters, dates, sorting, extra columns or wishes the query ignores, or describes the records loosely.
Say "no" when the question's subject is something else: another kind of record, another topic, which this table does not hold. A table of one topic does not become "yes" because the question mentions that topic in passing while asking about another.
The texts were written in a Chinese setting, so a question may name a place the table does not cover (Beijing, a district, "our province"). A wrong place is not a "no": judge the kind of record, not the place.
Judge each table on its own, from its name, its columns and its values.

Example
Question: "I want a list of every ferry sailing out of Brest last summer with its departure time and the ship used, sorted by date, so I can plan a timetable study."
SQL: SELECT "sailings"."ship", "sailings"."departure_time" FROM "sailings" WHERE "sailings"."origin" = 'Brest'
Tables:
1. sailings (12,400 rows) columns: ship, origin, destination, departure_time, arrival_time; origin values: Brest, Plymouth, Santander; ship values: Armorique, Pont-Aven
Output Format:
{{"tables": {{"1": "yes"}}, "why": "The question asks for sailings out of Brest, which this table holds; the summer and the sort are extra."}}

Example
Question: "List the public libraries in Hangzhou with their opening hours and the number of seats, for a study of reading rooms in the city."
SQL: SELECT "public_libraries"."name", "public_libraries"."opening_hours" FROM "public_libraries"
Tables:
1. public_libraries (41 rows) columns: name, district, opening_hours, seats, phone; name values: Part-Dieu, Croix-Rousse, Guillotiere; district values: Lyon 3e, Lyon 4e
Output Format:
{{"tables": {{"1": "yes"}}, "why": "The question asks for public libraries with their hours and seats, which this table holds; Hangzhou is a place mismatch, not a different kind of record."}}

Example
Question: "Please summarise the fishing catch landed at Brest by species over 2019, so we can compare it with the ferry traffic."
SQL: SELECT "sailings"."origin", COUNT(*) FROM "sailings" JOIN "crew" ON "sailings"."ship" = "crew"."ship_id" GROUP BY "sailings"."origin"
Tables:
1. sailings (12,400 rows) columns: ship, origin, destination, departure_time, arrival_time; origin values: Brest, Plymouth, Santander
2. crew (380 rows) columns: crew_id, ship_id, name, rank, birth_city; ship_id values: 14, 22, 7
Output Format:
{{"tables": {{"1": "no", "2": "no"}}, "why": "The question asks for fish landings by species; neither sailings nor crew records hold that, and ferry traffic is only mentioned in passing."}}

Now this one.
Question: "{question}"
SQL: {sql}
Tables:
{tables}

Output Format: a JSON object with "tables" (exactly one key per table number above, "1" to "{n}", each "yes" or "no") and "why" (one sentence). No other text.
Return an answer only in this exact Output Format."""


def schema(n: int) -> dict:
    keys = [str(i) for i in range(1, n + 1)]
    return {"type": "object", "required": ["tables", "why"], "additionalProperties": False,
            "properties": {"tables": {"type": "object", "required": keys, "additionalProperties": False,
                                      "properties": {k: {"enum": ["yes", "no"]} for k in keys}},
                           "why": {"type": "string"}}}


_conns: dict[str, sqlite3.Connection] = {}
_cards: dict[tuple[str, str], tuple[int, list[str]]] = {}
_lock = threading.Lock()  # one connection per database, shared by the threads


def connect(db: str) -> sqlite3.Connection:
    if db not in _conns:
        conn = sqlite3.connect(f"file:{LAKE}/databases/{db}/{db}.sqlite?mode=ro", uri=True, check_same_thread=False)
        conn.text_factory = lambda b: b.decode(errors="replace")
        _conns[db] = conn
    return _conns[db]


def reads(record: dict) -> tuple[list[tuple[str, str]], set[tuple[str, str, str]]]:
    """The (db, table) pairs and (db, table, column) triples the gold SQL reads, from SQLite's authorizer."""
    tables: set[tuple[str, str]] = set()
    columns: set[tuple[str, str, str]] = set()
    dbs = record.get("db_ids") or [record["db_id"]]

    def authorize(action, table, column, db, *_):
        if action == sqlite3.SQLITE_READ and table and not table.startswith("sqlite_"):
            name = dbs[0] if db in ("main", None) else db  # None: a table read for no column
            tables.add((name, table))
            if column:
                columns.add((name, table, column))
        return sqlite3.SQLITE_OK

    if len(dbs) == 1:  # single-database SQL names bare tables
        conn = sqlite3.connect(f"file:{LAKE}/databases/{dbs[0]}/{dbs[0]}.sqlite?mode=ro", uri=True)
    else:  # cross-database SQL names "slug"."table"
        conn = sqlite3.connect(":memory:")
        for db in dbs:
            conn.execute(f'ATTACH DATABASE ? AS "{db}"', (f"file:{LAKE}/databases/{db}/{db}.sqlite?mode=ro",))
    conn.set_authorizer(authorize)
    conn.execute("EXPLAIN " + record["SQL"])
    conn.close()
    return sorted(tables), columns


def cut(name: str) -> str:
    name = " ".join(name.split())
    return name if len(name) <= NAME_CUT else name[: NAME_CUT - 3] + "..."


def card(db: str, table: str, read_columns: list[str]) -> str:
    """`table (N rows) columns: ...; col values: a, b, c` with the read columns first and sampled."""
    with _lock:
        return _card(db, table, read_columns)


def _card(db: str, table: str, read_columns: list[str]) -> str:
    conn = connect(db)
    if (db, table) not in _cards:
        n = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        names = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
        _cards[(db, table)] = (n, names)
    n, names = _cards[(db, table)]
    order = read_columns + [c for c in names if c not in read_columns]
    shown = ", ".join(cut(c) for c in order[:SHOWN_COLUMNS])
    if len(order) > SHOWN_COLUMNS:
        shown += f", ... {len(order) - SHOWN_COLUMNS} more"
    samples = []
    for c in read_columns[:4]:
        values = [str(r[0])[:40] for r in conn.execute(
            f'SELECT "{c}" FROM "{table}" WHERE "{c}" IS NOT NULL AND "{c}" != \'\' LIMIT 3')]
        if values:
            samples.append(f"{cut(c)} values: {', '.join(values)}")
    return f"{table} ({n:,} rows) columns: {shown}" + ("; " + "; ".join(samples) if samples else "")


def judge(record: dict) -> dict:
    tables, columns = reads(record)
    cards = [card(db, t, sorted(c for d, tt, c in columns if (d, tt) == (db, t))) for db, t in tables]
    shown = "\n".join(f"{i}. {c}" for i, c in enumerate(cards, 1))
    prompt = PROMPT.format(question=record["question"], sql=" ".join(record["SQL"].split()), tables=shown, n=len(cards))
    replies = [vote(prompt, len(cards), 0, record["id"])]
    if replies[0] and any(v == "no" for v in replies[0]["tables"].values()):  # a "no" gets two more votes
        replies += [vote(prompt, len(cards), seed, record["id"]) for seed in (1, 2)]
    replies = [r for r in replies if r]
    votes = {}
    for i, (db, t) in enumerate(tables, 1):
        yes = sum(r["tables"].get(str(i)) == "yes" for r in replies)
        votes[f"{db}.{t}"] = None if not replies else "yes" if yes * 2 > len(replies) else "no"
    return {"id": record["id"], "source": record["source"], "tables": votes, "votes": len(replies),
            "keep": all(v == "yes" for v in votes.values()) if replies else None,
            "why": [r["why"] for r in replies]}


def vote(prompt: str, n: int, seed: int, qid: str) -> dict | None:
    """One seeded reply; a call that runs out of room is retried with another seed, then with the full room."""
    for s, limit in ((seed, LIMIT), (seed + 3, LIMIT), (seed + 3, None)):
        try:
            return llm.ask_json(prompt, s, schema(n), tag=f"clean {qid}", limit=limit)
        except (ValueError, KeyError, TypeError):
            continue
    return None


def records() -> list[dict]:
    out = []
    for name in ("dev.json", "dev_cross.json"):
        for r in json.loads((LAKE / name).read_text()):
            out.append({**r, "id": f"taco_us-{'x' if 'db_ids' in r else 'q'}{r['question_id']}"})
    return out


def main() -> None:
    rows = records()
    if len(sys.argv) > 1 and sys.argv[1] == "pilot":
        rows = random.Random(2026).sample(rows, int(sys.argv[2]) if len(sys.argv) > 2 else 40)
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(32) as pool:
            outs = list(pool.map(judge, rows))
        for r, out in zip(rows, outs):
            print(f"\n{'KEEP' if out['keep'] else 'DROP'} {out['id']} votes {out['votes']} {out['tables']}\n  why: {out['why'][0]}\n  Q: {r['question'][:300]}")
        print(f"\ncalls {llm.used['calls']} cached {llm.used['cached']} tokens {llm.used['tokens']} cut {llm.used['cut']}")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    import labeler
    labeler.RUN = OUT  # labeler.run writes <RUN>/<name>.jsonl
    run("clean", rows, judge, threads=64, note=lambda: f"calls {llm.used['calls']} cached {llm.used['cached']} open {llm.used['open']} cut {llm.used['cut']}")


if __name__ == "__main__":
    main()
