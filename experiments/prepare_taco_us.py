"""Derive the taco_us lake from the raw TACO release (benchmarks/TACO-Benchmark/us).

  .venv/bin/python experiments/prepare_taco_us.py

Writes benchmarks/taco_us/ (the raw folder is never touched):
  databases/<slug>/<slug>.sqlite   a link to each raw database that passes PRAGMA quick_check;
                                   the slug has no dots or spaces, so db.table.column paths parse
  dev.json                         the single-database questions kept, in the dev.json shape of
                                   the other lakes (question_id, db_id, question, SQL, evidence)
  dev_cross.json                   the cross-database questions kept, with db_ids, gold_tables
                                   and the SQL rewritten as "slug"."table" (run it after
                                   ATTACH DATABASE <path> AS <slug> for each db)
  dropped.json                     every dropped question file, with its reason (and the judge's
                                   votes and replies when the judge dropped it)
  SOURCE.md                        every count: what was kept and what was dropped, and why

A question is dropped when it has no question text, when its database is corrupt, when its
gold SQL fails or runs past TIMEOUT seconds, or when the judge (experiments/clean_taco_us.py,
runs/taco_us/clean.jsonl, when that file exists) found its text is about none of the tables the
gold SQL reads. A question with some tables "yes" stays: the judge is strict on tables used
only to filter or join. A question the judge has not seen stays in.
"""

import json
import os
import re
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "benchmarks" / "TACO-Benchmark" / "us"
OUT = ROOT / "benchmarks" / "taco_us"
JUDGED = ROOT / "runs" / "taco_us" / "clean.jsonl"
TIMEOUT = 60


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def healthy(path: Path) -> bool:
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            return conn.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"
    except sqlite3.DatabaseError:
        return False


def run(conn: sqlite3.Connection, sql: str) -> dict:
    """Status of `sql` (ok, empty, error, slow), its row count and the tables it reads."""
    tables: set[str] = set()

    def authorize(action, table, _column, db, *_):
        if action == sqlite3.SQLITE_READ and table and not table.startswith("sqlite_"):
            tables.add(table if db in ("main", None) else f"{db}.{table}")  # attached: slug.table; None: read for no column
        return sqlite3.SQLITE_OK

    conn.set_authorizer(authorize)
    timer = threading.Timer(TIMEOUT, conn.interrupt)
    timer.start()
    try:
        rows = conn.execute(sql).fetchmany(1001)
        out = {"status": "ok" if rows else "empty", "rows": len(rows)}
    except sqlite3.Error as error:
        out = {"status": "slow" if "interrupted" in str(error) else "error", "rows": 0, "error": str(error)[:200]}
    finally:
        timer.cancel()
        conn.set_authorizer(None)
    return {**out, "tables": sorted(tables)}


def connect(path: Path, attach: dict[str, Path] | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True) if attach is None else sqlite3.connect(":memory:")
    conn.text_factory = lambda b: b.decode(errors="replace")
    for name, db in (attach or {}).items():
        conn.execute(f'ATTACH DATABASE ? AS "{name}"', (f"file:{db}?mode=ro",))
    return conn


def cross_sql(sql: str, names: dict[str, str]) -> str:
    """The raw cross SQL spells a table "db.table" or "db"."table"; both become "slug"."table"."""
    for raw, short in names.items():
        sql = sql.replace(f'"{raw}.', f'"{short}"."').replace(f'"{raw}"."', f'"{short}"."')
    return sql


def main() -> None:
    raw_dbs = {d.name: d / f"{d.name}.db" for d in sorted((RAW / "databases").iterdir()) if d.is_dir()}
    names = {raw: slug(raw) for raw in raw_dbs}
    good = {raw: path for raw, path in raw_dbs.items() if healthy(path)}
    corrupt = sorted(set(raw_dbs) - set(good))
    for raw, path in good.items():
        folder = OUT / "databases" / names[raw]
        folder.mkdir(parents=True, exist_ok=True)
        link = folder / f"{names[raw]}.sqlite"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(os.path.relpath(path, folder))

    files = sorted((RAW / "natural_language_queries").glob("*/*.json"))
    records = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        text = data.get("natural_language_query")
        records.append({
            "source": str(path.relative_to(RAW)), "cross": path.parent.name == "cross_database",
            "dbs": data.get("databases") or [data.get("database")], "sql": data.get("sql", ""),
            "question": text.strip() if isinstance(text, str) else "",
        })

    by_db: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_db["cross" if r["cross"] else r["dbs"][0]].append(r)

    def run_group(key: str) -> None:
        if key == "cross":
            for r in by_db[key]:
                if any(db not in good for db in r["dbs"]):
                    r["run"] = {"status": "corrupt_db", "rows": 0, "tables": []}
                    continue
                conn = connect(Path(), {names[db]: good[db] for db in r["dbs"]})
                r["sql"] = cross_sql(r["sql"], {db: names[db] for db in r["dbs"]})
                r["run"] = run(conn, r["sql"])
                conn.close()
            return
        if key not in good:
            for r in by_db[key]:
                r["run"] = {"status": "corrupt_db", "rows": 0, "tables": []}
            return
        conn = connect(good[key])
        for r in by_db[key]:
            r["run"] = run(conn, r["sql"])
        conn.close()

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(run_group, sorted(by_db)))

    verdicts, judged = {}, {}
    if JUDGED.exists():
        for line in JUDGED.read_text().splitlines():
            one = json.loads(line)
            votes = one["tables"].values()  # None: no reply; dropped only when no gold table fits the text
            verdicts[one["source"]] = None if one["keep"] is None else not all(v == "no" for v in votes)
            judged[one["source"]] = {"tables": one["tables"], "why": one["why"]}
    dropped: Counter = Counter()
    gone = []
    kept_single, kept_cross = [], []
    for r in records:
        why = ("no question text" if not r["question"] else "corrupt database" if r["run"]["status"] == "corrupt_db"
               else "gold SQL fails" if r["run"]["status"] == "error" else f"gold SQL slower than {TIMEOUT} s"
               if r["run"]["status"] == "slow" else "text about no gold table (judge)"
               if verdicts.get(r["source"]) is False else "")
        if why:
            dropped[("cross" if r["cross"] else "single", why)] += 1
            gone.append({"source": r["source"], "reason": why, "dbs": r["dbs"], "question": r["question"],
                         "SQL": r["sql"], **({"judge": judged[r["source"]]} if why.endswith("(judge)") else {})})
            continue
        (kept_cross if r["cross"] else kept_single).append(r)

    groups: dict[str, int] = {}
    for n, r in enumerate(kept_single, 1):
        group = groups.setdefault(r["sql"], len(groups) + 1)
        r["out"] = {"question_id": n, "db_id": names[r["dbs"][0]], "question": r["question"], "SQL": r["sql"],
                    "evidence": "", "sql_group": group, "gold_rows": r["run"]["rows"], "source": r["source"]}
    cross_groups: dict[str, int] = {}
    for n, r in enumerate(kept_cross, 1):
        group = cross_groups.setdefault(r["sql"], len(cross_groups) + 1)
        r["out"] = {"question_id": n, "db_ids": [names[db] for db in r["dbs"]], "question": r["question"],
                    "SQL": r["sql"], "gold_tables": r["run"]["tables"], "evidence": "", "sql_group": group,
                    "gold_rows": r["run"]["rows"], "source": r["source"]}
    (OUT / "dev.json").write_text(json.dumps([r["out"] for r in kept_single], indent=1, ensure_ascii=False))
    (OUT / "dev_cross.json").write_text(json.dumps([r["out"] for r in kept_cross], indent=1, ensure_ascii=False))
    (OUT / "dropped.json").write_text(json.dumps(gone, indent=1, ensure_ascii=False))

    lines = [
        "# taco_us: derived from the TACO release, US part only",
        "", f"Built by experiments/prepare_taco_us.py on {time.strftime('%Y-%m-%d')} from benchmarks/TACO-Benchmark/us",
        "(see its SOURCE.md for the release checksums). The raw folder is never edited.", "",
        "## Databases", "",
        f"- {len(good)} linked (databases/<slug>/<slug>.sqlite -> the raw .db): " + ", ".join(sorted(names[d] for d in good)),
        f"- {len(corrupt)} dropped, corrupt in both public mirrors (TACO issue 3): " + ", ".join(corrupt), "",
        "## Questions", "",
        f"- single-database: {len(kept_single)} kept of {sum(not r['cross'] for r in records)} files,"
        f" {len(groups)} distinct gold SQLs (sql_group numbers the files sharing one SQL)",
        f"- cross-database: {len(kept_cross)} kept of {sum(r['cross'] for r in records)} files, {len(cross_groups)} distinct gold SQLs;"
        " kept apart in dev_cross.json because their SQL spans databases", "",
        "Dropped, by reason:", "",
        *[f"- {kind}: {why}: {n}" for (kind, why), n in sorted(dropped.items())], "",
        "Gold tables are what SQLite reads when it prepares the gold SQL. The release's own `tables` field is the",
        "schema shown to the generating model, not the gold, and is not kept.", "",
        f"Judge verdicts read from {JUDGED.relative_to(ROOT)}: {len(verdicts)} questions judged,"
        f" {sum(v is None for v in verdicts.values())} without a verdict (kept)."
        if verdicts else "No judge verdicts yet (runs/taco_us/clean.jsonl missing): text that does not match its SQL is still in.",
        "TACO writes the text from a guessed business scenario, four model steps away from the SQL, so the judge",
        "asks per gold table whether the question is about the records it holds; extra filters and wishes pass.",
        "A question is dropped only when every gold table got a no; the ones with some yes stay.",
        "Gold joins on unrelated id columns are not cleaned.",
    ]
    (OUT / "SOURCE.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
