"""Every step for one question at a time: link, candidates, judge, swap and run, label.

  LABEL_RUN=bird_dev .venv/bin/python -m labeler.go

Reads runs/labeler/<run>/questions.jsonl (labeler.sample) and appends each finished
question to labels.jsonl, so labels arrive steadily from the start. THREADS questions run
at once. A stopped run resumes where it was; LLM replies come from the shared cache, so a
question labeled before (in the pilot) costs nothing. Watch it with labeler.watch and
labeler.feed.
"""

import os
import threading
import time
from itertools import zip_longest

from labeler import LAKES, read, run, split_item
from labeler.judge import judge
from labeler.label import label
from labeler.link import link, note
from labeler.pool import BATCH, Lake, candidates, grouped
from labeler.swap import swap_all

THREADS = int(os.environ.get("LABEL_THREADS", 40))  # fewer when the judge server is shared


def pooled(lake: Lake, row: dict, linked: dict, lock: threading.Lock) -> dict:
    """Step 3 for one question (the embedding model is shared, hence the lock)."""
    cross = "db_ids" in row
    items = grouped(linked["items"], cross)
    covered = {i["item"] if "columns" in i else split_item(i["item"], cross)[0]
               for i in items if i["words"] and i["role"] not in ("join", "table")}
    out = []
    for i in items:
        skip = i["role"] == "table" and i["item"] in covered
        if i["words"] and i["role"] != "join" and not skip:
            with lock:
                out.append(candidates(lake, row, i))
        else:
            out.append({**i, "candidates": [], **({"covered": True} if skip else {})})
    return {"id": row["id"], "items": out}


def main() -> None:
    rows = {r["id"]: r for r in read("questions")}
    order = LAKES + sorted({r["lake"] for r in rows.values()} - set(LAKES))
    lakes = {name: Lake(name) for name in order if any(r["lake"] == name for r in rows.values())}
    by_lake = [[{"id": i} for i, r in rows.items() if r["lake"] == lake] for lake in order]
    for name, lake in lakes.items():
        if len(lake.flat) > BATCH:  # every gold value of the run in one pass, not one pass each under the lock
            lake.hold([x["text"] for r in rows.values() if r["lake"] == name for x in r["literals"]])
    todo = [x for group in zip_longest(*by_lake) for x in group if x]
    lock = threading.Lock()

    def one(item: dict) -> dict:
        row = rows[item["id"]]
        lake = lakes[row["lake"]]
        linked = link(row) if row["tables"] else {"id": row["id"], "items": [], "computation_gaps": []}
        record = pooled(lake, row, linked, lock)
        judged = judge(row, record, lake)
        swaps = swap_all(lake, row, judged)
        return {**label(row, linked, judged, swaps), "finished": time.time(),
                "judged": judged["items"], "swaps": swaps["swaps"]}

    run("labels", todo, one, colour="green", threads=THREADS, note=note)


if __name__ == "__main__":
    main()
