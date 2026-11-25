"""Sample 100 BIRD dev questions, stratified proportionally by db_id, seeded.

  .venv/bin/python experiments/sample_bird100.py

Writes experiments/pick_questions_bird100.jsonl (b001..b100). Skips questions
already used verbatim in pick_questions.jsonl, and any sampled query whose gold
SQL yields no gold columns via gold_columns() -- those are replaced with
another question from the same db (same seed).
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from amigo.probe import Probe  # noqa: E402
from pick_prompt import gold_columns, schema_of  # noqa: E402

DEV = ROOT / "benchmarks" / "bird" / "dev.json"
EXISTING = ROOT / "experiments" / "pick_questions.jsonl"
OUT = ROOT / "experiments" / "pick_questions_bird100.jsonl"
N = 100


def quota(counts: dict[str, int], total: int) -> dict[str, int]:
    """Largest-remainder rounding: proportional shares that sum to exactly `total`."""
    raw = {db: n * total / sum(counts.values()) for db, n in counts.items()}
    share = {db: int(r) for db, r in raw.items()}
    for db in sorted(raw, key=lambda db: raw[db] - share[db], reverse=True)[: total - sum(share.values())]:
        share[db] += 1
    return share


def main() -> None:
    rows = json.loads(DEV.read_text())
    by_db = defaultdict(list)
    for row in rows:
        by_db[row["db_id"]].append(row)
    shares = quota({db: len(v) for db, v in by_db.items()}, N)

    existing = {
        json.loads(line)["question"]
        for line in EXISTING.read_text().splitlines()
        if json.loads(line)["source"] == "bird"
    }

    probe = Probe("bird_dev")
    rng = Random(0)
    out_rows, resamples = [], 0
    for db in sorted(shares):
        pool = [r for r in by_db[db] if r["question"] not in existing]
        rng.shuffle(pool)
        kept = []
        for row in pool:
            if len(kept) == shares[db]:
                break
            _, cols = gold_columns(row["SQL"], schema_of(probe, db))
            if not cols:
                resamples += 1
                continue
            kept.append(row)
        if len(kept) < shares[db]:
            raise RuntimeError(f"{db}: only {len(kept)}/{shares[db]} usable questions")
        out_rows.append((db, kept))

    lines, n = [], 1
    for db, kept in out_rows:
        for row in kept:
            lines.append(
                json.dumps(
                    {
                        "id": f"b{n:03d}",
                        "question": row["question"],
                        "source": "bird",
                        "db_id": db,
                        "gold_sql": row["SQL"],
                        "bird_question_id": row["question_id"],
                        "difficulty": row["difficulty"],
                    }
                )
            )
            n += 1
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {n - 1} questions to {OUT}, {resamples} resample(s)")
    for db, kept in out_rows:
        print(f"  {db}: {len(kept)}")


if __name__ == "__main__":
    main()
