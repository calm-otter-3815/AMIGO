"""Draw the questions and anchor their gold (step 1, no LLM call).

  LABEL_RUN=pilot .venv/bin/python -m labeler.sample              the pilot, 10 per lake
  LABEL_RUN=bird_dev .venv/bin/python -m labeler.sample bird_dev  every question of one lake
  LABEL_RUN=taco_us .venv/bin/python -m labeler.sample taco_us --one-per-sql
                                                  one question per gold SQL, in random order

Every question of a lake: all of them, in file order, with the pilot's id when the pilot
drew it (the LLM cache then serves its calls). Pilot:
Per lake, questions are shuffled with random.Random(SEED) and taken in order, skipping
those AMIGO has seen (the text appears in runs/ or experiments/). The gold SQL is run and
its health kept (ok, empty, error, slow): a broken or empty gold is flagged, not dropped.
Writes runs/labeler/<run>/questions.jsonl and prints, per lake, the gold health and the share of
questions whose literals are all found (the gate is 95%).
"""

import json
import random
import sys
import sqlite3
from collections import Counter

from labeler import LAKES, OUT, ROOT, RUN, cross_questions, databases, questions
from labeler.gold import anchor, result

SEED = 2026
PER_LAKE = 10
SEEN_SUFFIXES = {".json", ".jsonl", ".log", ".md", ".txt"}


def seen_text() -> str:
    """Every question AMIGO may have met: all text under runs/ and experiments/."""
    parts = []
    for folder in (ROOT / "runs", ROOT / "experiments"):
        for path in folder.rglob("*"):
            if path.suffix in SEEN_SUFFIXES and path.is_file() and OUT not in path.parents:
                parts.append(path.read_text(errors="ignore"))
    return "\n".join(parts)


def safe_anchor(path, sql: str) -> dict:
    """anchor(), or empty gold sets when SQLite cannot even prepare the gold SQL."""
    try:
        return anchor(path, sql)
    except sqlite3.Error:
        return {"tables": [], "columns": [], "literals": []}


def record(lake: str, id_: str, path, q: dict) -> dict:
    """`path` is a dict name -> path for a question across databases (its `db_ids`)."""
    return {"id": id_, "lake": lake, "db_id": q.get("db_id"), **({"db_ids": q["db_ids"]} if "db_ids" in q else {}),
            "question_id": q["question_id"], "question": q["question"],
            "evidence": q.get("evidence", ""), "gold_sql": q["SQL"], "gold": result(path, q["SQL"]), **safe_anchor(path, q["SQL"])}


def whole(lake: str, one_per_sql: bool = False) -> None:
    """Every question of `lake`, gold anchored, written as the run's questions; then its
    questions across databases (taco_us), ids <lake>-x<question_id>. `one_per_sql`: one
    question per gold SQL of a database (or set of databases), all drawn and ordered at random
    (SEED), so the labels of a run stopped early are a random sample."""
    from tqdm import tqdm

    paths = databases(lake)
    pilot = {(r["lake"], r["question_id"]): r["id"] for r in map(json.loads, (OUT / "pilot" / "questions.jsonl").open())}
    todo = [(pilot.get((lake, q["question_id"]), f"{lake}-q{q['question_id']}"), paths[q["db_id"]], q)
            for q in questions(lake) if q["SQL"] and q.get("db_id") in paths]
    todo += [(f"{lake}-x{q['question_id']}", {d: paths[d] for d in q["db_ids"]}, q)
             for q in cross_questions(lake) if q["SQL"] and all(d in paths for d in q["db_ids"])]
    if one_per_sql:
        random.Random(SEED).shuffle(todo)
        seen, kept = set(), []
        for one in todo:
            key = (one[2].get("db_id") or tuple(one[2]["db_ids"]), " ".join(one[2]["SQL"].split()).rstrip("; "))  # spacing and a last ";" aside
            if key not in seen:
                seen.add(key)
                kept.append(one)
        todo = kept
    rows = [record(lake, id_, path, q) for id_, path, q in tqdm(todo, desc="gold", colour="cyan", dynamic_ncols=True)]
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{lake}: {len(rows)} questions; gold {dict(Counter(r['gold']['status'] for r in rows))}")


def main() -> None:
    if len(sys.argv) > 1:
        return whole(sys.argv[1], "--one-per-sql" in sys.argv)
    seen = seen_text()
    rows = []
    for lake in LAKES:
        paths = databases(lake)
        records = [r for r in questions(lake) if r["SQL"] and r.get("db_id") in paths]
        random.Random(SEED).shuffle(records)
        skipped = 0
        kept = 0
        for record_ in records:
            text = record_["question"]
            if text in seen or json.dumps(text)[1:-1] in seen:
                skipped += 1
                continue
            path = paths[record_["db_id"]]
            kept += 1
            rows.append(record(lake, f"{lake}-{kept:02d}", path, record_))
            if kept == PER_LAKE:
                break
        health = Counter(r["gold"]["status"] for r in rows if r["lake"] == lake)
        print(f"{lake}: kept {kept}, skipped {skipped} seen; gold {dict(health)}")
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print("\nlake         questions  with literals  all found  share")
    for lake in LAKES:
        mine = [r for r in rows if r["lake"] == lake]
        with_lit = [r for r in mine if r["literals"]]
        ok = [r for r in with_lit if all(x["route"] for x in r["literals"])]
        share = f"{100 * len(ok) / len(with_lit):.0f}%" if with_lit else "n/a"
        print(f"{lake:12} {len(mine):9}  {len(with_lit):13}  {len(ok):9}  {share}")


if __name__ == "__main__":
    main()
