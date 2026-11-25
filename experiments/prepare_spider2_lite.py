"""Derive the spider2_lite lake from the raw Spider 2.0-Lite release (benchmarks/spider2_raw).

  .venv/bin/python experiments/prepare_spider2_lite.py

The raw folder holds a sparse clone of github.com/xlang-ai/Spider2 (spider2-lite/ and
methods/gold-tables/) and local_sqlite/, the unzipped local_sqlite.zip that the Spider2
README links on Google Drive. Only the local SQLite part of Spider 2.0-Lite is used: the
BigQuery and Snowflake parts need cloud accounts.

Writes benchmarks/spider2_lite/ (the raw folder is never touched):
  databases/<db>/<db>.sqlite   each raw database that passes PRAGMA quick_check: a link, or a
                               copy where each view that runs is saved as a table of its rows
                               under its own name (a lake holds tables; every view, not only
                               gold ones, so the lake gives no hint); a view that fails is
                               dropped from the copy
  dev.json                     the local questions, in the dev.json shape of the other lakes
                               (question_id, db_id, question, SQL, evidence) plus gold_tables
                               (the release's ground-truth tables, every question has them) and
                               external_knowledge (a file name under documents/, or null);
                               when a gold table is a view, the release also lists the tables
                               it reads; that is two answers, so gold_tables keeps the view
                               without them and gold_tables_alt has them without the view
  documents/                   the external knowledge files the questions name
  SOURCE.md                    every count: what was kept and why

Spider 2.0 releases gold SQL for only a few questions; SQL is "" for the others, and scoring
reads their gold_tables. A gold SQL is kept when it runs within TIMEOUT seconds.
"""

import json
import os
import shutil
import sqlite3
import threading
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "benchmarks" / "spider2_raw"
LITE = RAW / "spider2-lite"
OUT = ROOT / "benchmarks" / "spider2_lite"
TIMEOUT = 60


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def healthy(path: Path) -> bool:
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            return conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    except sqlite3.Error:
        return False


def tables_of(path: Path) -> dict[str, str]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")]
    return {name.lower(): name for name in names}


def views_of(path: Path) -> dict[str, list[str] | None]:
    """Each view, by its name in lower case, and the tables it reads; None when it fails."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        out = {}
        for (view,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall():
            read: set[str] = set()

            def authorize(action, table, *_):
                if action == sqlite3.SQLITE_READ and table in tables:
                    read.add(table)
                return sqlite3.SQLITE_OK

            conn.set_authorizer(authorize)
            try:
                conn.execute(f'SELECT * FROM "{view}" LIMIT 0').fetchall()
                out[view.lower()] = sorted(read)
            except sqlite3.Error as error:
                print(f"{path.stem}.{view}: view fails, dropped: {error}")
                out[view.lower()] = None
            conn.set_authorizer(None)
        return out
    finally:
        conn.close()


def saved(raw: Path, copy: Path, views: dict[str, list[str] | None]) -> None:
    """A copy of the database with each view that runs saved as a table of its rows.

    Every view is saved before any is dropped (a view may read another), and all are dropped
    before the renames (a rename checks the views left, and a broken one fails it).
    A copy with no view left is finished and kept: saving the views runs for over an hour.
    """
    if copy.exists() and not copy.is_symlink():
        with sqlite3.connect(copy) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'view'").fetchone():
                return
        copy.unlink()
    shutil.copy(raw, copy)
    with sqlite3.connect(copy) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'")]
        kept = [v for v in names if views[v.lower()] is not None]
        for view in kept:
            conn.execute(f'CREATE TABLE "{view}__rows" AS SELECT * FROM "{view}"')
        for view in names:
            conn.execute(f'DROP VIEW "{view}"')
        for view in kept:
            conn.execute(f'ALTER TABLE "{view}__rows" RENAME TO "{view}"')


def runs(path: Path, sql: str) -> str | None:
    """None when the query runs within TIMEOUT seconds, else why not."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    timer = threading.Timer(TIMEOUT, conn.interrupt)
    timer.start()
    try:
        conn.execute(sql).fetchmany(1)
        return None
    except sqlite3.Error as error:
        return str(error)
    finally:
        timer.cancel()
        conn.close()


def main() -> None:
    questions = [r for r in lines(LITE / "spider2-lite.jsonl") if r["instance_id"].startswith("local")]
    gold_tables = {r["instance_id"]: r["gold_tables"] for r in lines(RAW / "methods" / "gold-tables" / "spider2-lite-gold-tables.jsonl")}
    gold_sql = LITE / "evaluation_suite" / "gold" / "sql"
    # database copies are kept across runs (see saved); everything else is written fresh
    for old in (OUT / "documents", OUT / "dev.json", OUT / "SOURCE.md"):
        if old.is_dir():
            shutil.rmtree(old)
        elif old.exists():
            old.unlink()
    (OUT / "documents").mkdir(parents=True)

    counts: Counter = Counter()
    good = {}
    for raw in sorted((RAW / "local_sqlite").glob("*.sqlite")):
        if not healthy(raw):
            counts["databases corrupt"] += 1
            continue
        folder = OUT / "databases" / raw.stem
        folder.mkdir(parents=True, exist_ok=True)
        views = views_of(raw)
        if views:
            saved(raw, folder / raw.name, views)
            counts["views saved as tables"] += sum(v is not None for v in views.values())
            counts["views dropped (fail to run)"] += sum(v is None for v in views.values())
        elif not (folder / raw.name).is_symlink():
            os.symlink(raw, folder / raw.name)
        good[raw.stem] = (tables_of(raw), views)
        counts["databases kept"] += 1

    records = []
    for q in questions:
        qid, db = q["instance_id"], q["db"]
        if db not in good:
            counts["questions dropped: database corrupt or missing"] += 1
            continue
        named = gold_tables.get(qid, [])
        # the release writes gold tables as table names, any case
        names, views = good[db]
        if len([t for t in named if t.lower() in names]) != len(named):
            counts["questions with a gold table not in the database"] += 1
        found = [names[t.lower()] for t in named if t.lower() in names]
        alt = None
        if any(views.get(t.lower()) for t in found):
            # the release lists a gold view next to the tables it reads: two answers in one set,
            # split into the view (without its tables) and its tables (without the view)
            read = {x for t in found for x in views.get(t.lower()) or []}
            alt = list(dict.fromkeys(x for t in found for x in views.get(t.lower()) or [t]))
            found = [t for t in found if t not in read]
            counts["questions with a gold view (a second answer: the tables it reads)"] += 1
        sql = ""
        if (gold_sql / f"{qid}.sql").exists():
            text = (gold_sql / f"{qid}.sql").read_text().strip().rstrip(";")
            why = runs(RAW / "local_sqlite" / f"{db}.sqlite", text)
            if why is None:
                sql = text
                counts["gold SQL kept"] += 1
            else:
                counts["gold SQL dropped (does not run)"] += 1
                print(f"{qid}: gold SQL does not run: {why}")
        if q["external_knowledge"]:
            shutil.copy(LITE / "resource" / "documents" / q["external_knowledge"], OUT / "documents")
            counts["questions with external knowledge"] += 1
        records.append({"question_id": qid, "db_id": db, "question": q["question"], "SQL": sql, "evidence": "",
                        "gold_tables": found, "gold_tables_alt": alt,
                        "external_knowledge": q["external_knowledge"]})
    counts["questions kept"] = len(records)
    (OUT / "dev.json").write_text(json.dumps(records, indent=1) + "\n")

    commit = (RAW / ".git" / "shallow").read_text().strip() if (RAW / ".git" / "shallow").exists() else "?"
    lines_out = [
        "# spider2_lite: the local SQLite part of Spider 2.0-Lite",
        "",
        f"Source: github.com/xlang-ai/Spider2 at commit {commit} (spider2-lite/ and",
        "methods/gold-tables/), and local_sqlite.zip (435 MB) from the Google Drive link in",
        "spider2-lite/README.md, downloaded 2026-10-28. Built by experiments/prepare_spider2_lite.py.",
        "",
        f"Questions in spider2-lite.jsonl: {len(lines(LITE / 'spider2-lite.jsonl'))}; local (SQLite): {len(questions)}.",
        "",
        *(f"- {name}: {n}" for name, n in sorted(counts.items())),
        "",
        "Spider 2.0 keeps most gold SQL hidden; every question has the released gold tables.",
        "Table-level scoring works for every question; column-level and SQL scoring only where",
        "SQL is set.",
    ]
    (OUT / "SOURCE.md").write_text("\n".join(lines_out) + "\n")
    print("\n".join(lines_out))


if __name__ == "__main__":
    main()
