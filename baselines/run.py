"""Run one baseline on the eval questions and save its records for the scorer.

  .venv/bin/python -m baselines.run METHOD [NAME=VALUE ...] [--lake LAKE] [--limit N]

METHOD is a module of this package with run(lake, question, log_path, **settings) -> record.
NAME=VALUE pairs are its settings (numbers are read as numbers) and name the tag; sql=1
also writes SQL over the returned tables (baselines/sql.py), scored at all three levels:
`dense k=3` writes runs/eval/bl_dense_k3/records.json. The questions are those of
experiments/eval_lakes.py (EVAL_QUESTIONS, EVAL_RUNS), so its `report` scores the tag:
  .venv/bin/python experiments/eval_lakes.py report codes bl_dense_k3
Questions already in the records are skipped; a failure is kept as {"error": ...} and listed.
Latency: each record keeps "seconds", the question's total and its steps (lake.lap; steps
named "llm ..." hold LLM calls), wall time with WORKERS questions at once, so a step may
include waiting for the shared embedder. Each line of llm.jsonl names its question and
holds the call's own seconds and tokens; a reply reused from the cache is marked "cached"
and takes no time, so latency is read from the first run of a prompt.
A timing run makes every call real, on the standard lane, one question at a time, into a
folder with no earlier records (EVAL_RUNS picks another), so no other question's wait is in its seconds:
  LLM_SERVICE_TIER=default AMIGO_CACHE=off .venv/bin/python -m baselines.run dense k=3 --workers 1
"""

import argparse
import collections
import importlib
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from amigo import embed, llm, serve

from . import sql
from .lake import CLOCK, Clock, Lake

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import eval_lakes  # noqa: E402

WORKERS = 8
log = logging.getLogger("baselines")


def _value(text: str):
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("method")
    parser.add_argument("settings", nargs="*")
    parser.add_argument("--lake", action="append", help="only these lakes (default: every lake)")
    parser.add_argument("--limit", type=int, help="only the first N questions per lake (a smoke test)")
    parser.add_argument("--workers", type=int, default=WORKERS, help="questions at once (1 for a timing run)")
    args = parser.parse_args()
    settings = {k: _value(v) for k, v in (s.split("=", 1) for s in args.settings)}
    method = importlib.import_module(f"baselines.{args.method}")
    # sql=1: one LLM call then writes SQL over the returned tables (all three levels)
    run_settings = {k: v for k, v in settings.items() if k != "sql"}
    then_sql = bool(settings.get("sql"))
    tag = "bl_" + "_".join([args.method, *(f"{k}{v}" for k, v in settings.items())])
    folder = eval_lakes.RUNS / tag
    path, log_path = folder / "records.json", folder / "llm.jsonl"
    records = eval_lakes._load(path)

    embed._model()  # loaded once, so the first question's time does not hold it
    rows = eval_lakes._lines(eval_lakes.QUESTIONS)
    for lake_name, lake_rows in eval_lakes._by_lake(rows).items():
        if args.lake and lake_name not in args.lake:
            continue
        todo = [r for r in lake_rows[: args.limit] if "error" in records.get(r["id"], {"error": 1})]
        if not todo:
            continue
        lake = Lake(lake_name)

        def one(row):
            llm.QUESTION.set(row["id"])
            clock = Clock()
            CLOCK.set(clock)
            try:
                got = method.run(lake, row["question"], log_path, **run_settings)
                if then_sql:
                    got = sql.after(lake, got, row["question"], log_path)
            except Exception as err:  # noqa: BLE001 - every failure is kept and listed
                log.exception("%s failed", row["id"])
                return row["id"], {"error": f"{type(err).__name__}: {err}"}
            total = round(time.monotonic() - clock.started, 3)
            return row["id"], got | {"seconds": {"total": total, **clock.seconds}}

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for qid, record in pool.map(one, todo):
                records[qid] = record
        eval_lakes._save(path, records)
        failed = [q for q in records if q.startswith(lake_name) and "error" in records[q]]
        log.info("%s: %d questions, failed: %s", lake_name, len(todo), failed or "none")

    lines = eval_lakes._lines(log_path)
    totals = serve.usage_totals(lines) if lines else {"calls": 0, "dollars": 0.0}
    lanes = dict(collections.Counter("cached" if l.get("cached") else l.get("service_tier") for l in lines))
    print(f"{tag}: {len(records)} records; LLM calls {totals['calls']} new, {len(lines)} logged"
          f" {lanes}; cost ${totals['dollars']:.3f}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    main()
