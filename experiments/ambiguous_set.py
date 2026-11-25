"""Candidate values for the made-up ambiguous test set.

How experiments/ambiguous_questions.jsonl was made:
  1. This script (code only, no LLM call, sqlite opened read-only) lists, per lake with 2 or more
     databases, the text values that sit in rows of at least 2 different tables in at least
     2 different databases of that lake. It skips values of 3 characters or fewer, pure numbers,
     dates, and values found in more than 20 rows of the lake. It then samples 60 of them over
     those lakes with random.Random(0).
  2. An agent that had never read AMIGO's prompts or ask code took those 60 values, dropped the
     ones that are not names of things, wrote a natural question per name, picked the intended
     place with random.Random(0) (seeded once, in id order), wrote and ran a gold SQL for it, and
     listed the other places as "others". Only 28 of the 60 values were names of things that
     have a shared attribute in 2 places, so the file has 28 questions (amb-001 to amb-028):
     20 spider_dev, 7 beaver_nw, 1 bird_dev. The rest were codes, ids, first names with no
     common attribute, or values with only one answerable place.

Cap: a text column is scanned in full, but only values of 4 to 60 characters and with at most
20 rows in that column are kept (long free text is never a name).

  .venv/bin/python experiments/ambiguous_set.py
"""

import random
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_LEN, MAX_LEN, MAX_ROWS, SAMPLE = 4, 60, 20, 60
NUMBER = re.compile(r"^[\s\d.,:/+\-()%$eE]*$")
DATE = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}([ T]\d.*)?$")


def databases(lake: str) -> dict[str, str]:
    with closing(sqlite3.connect(f"file:{ROOT / 'lakes' / lake / 'layer.sqlite'}?mode=ro", uri=True)) as conn:
        return dict(conn.execute("SELECT name, path FROM databases ORDER BY name"))


def scan(lake: str) -> dict[str, dict[tuple, int]]:
    """value -> {(db, table, column): rows} for the values kept in this lake."""
    found: dict[str, dict[tuple, int]] = defaultdict(dict)
    for db, path in databases(lake).items():
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            conn.text_factory = lambda b: b.decode("utf-8", "replace")
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                for _, col, kind, *_ in conn.execute(f'PRAGMA table_info("{table}")').fetchall():
                    if kind and not re.search(r"CHAR|TEXT|CLOB", kind.upper()):
                        continue
                    sql = (f'SELECT "{col}", COUNT(*) FROM "{table}" WHERE typeof("{col}")=\'text\' '
                           f'AND length("{col}") BETWEEN {MIN_LEN} AND {MAX_LEN} '
                           f'GROUP BY "{col}" HAVING COUNT(*) <= {MAX_ROWS}')
                    try:
                        for value, n in conn.execute(sql):
                            if not NUMBER.match(value) and not DATE.match(value.strip()):
                                found[value][(db, table, col)] = n
                    except sqlite3.Error:
                        continue
    return found


def shared(found: dict[str, dict[tuple, int]]) -> dict[str, dict[tuple, int]]:
    return {v: p for v, p in found.items()
            if len({k[0] for k in p}) >= 2 and sum(p.values()) <= MAX_ROWS}


def main() -> None:
    pool = []
    for lake in sorted(p.name for p in (ROOT / "lakes").iterdir() if p.is_dir()):
        if len(databases(lake)) < 2:
            continue
        kept = shared(scan(lake))
        print(f"# {lake}: {len(kept)} values", flush=True)
        pool += [(lake, v, kept[v]) for v in sorted(kept)]
    for lake, value, places in random.Random(0).sample(pool, min(SAMPLE, len(pool))):
        print(f"\n{lake}  {value!r}")
        paths = databases(lake)
        for (db, table, col), n in sorted(places.items()):
            with closing(sqlite3.connect(f"file:{paths[db]}?mode=ro", uri=True)) as conn:
                conn.text_factory = lambda b: b.decode("utf-8", "replace")
                row = conn.execute(f'SELECT * FROM "{table}" WHERE "{col}" = ? LIMIT 1', (value,)).fetchone()
            print(f"  {db}.{table}.{col}  rows={n}  e.g. {str(row)[:150]}")


if __name__ == "__main__":
    main()
