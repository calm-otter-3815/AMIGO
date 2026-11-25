"""Re-run every query of a finished label with the current row rule (gold.result) and
group its answers again (label.answers), with no LLM call. Each lake's labels.jsonl is
rewritten; the old one is kept as labels.jsonl.bak-<date>.

  .venv/bin/python -m labeler.regroup bird_dev spider_dev mmqa
"""

import datetime
import json
import shutil
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from labeler import OUT, databases
from labeler.gold import result
from labeler.label import answers


def again(x: dict, q: dict, paths: dict) -> dict:
    gold = result(paths[q["db_id"]], q["gold_sql"])
    results = [result(paths[a["name"].split(".", 1)[0]], a["sql"]) if a["sql"] else None for a in x["accepted"]]
    accepted = [a if res is None else {**a, "answer": "failed" if res["status"] in ("error", "slow") else
                                       "empty" if res["status"] == "empty" else
                                       "same rows" if res["hash"] == gold.get("hash") else "different rows"}
                for a, res in zip(x["accepted"], results)]
    return {**x, "gold": {"status": gold["status"], "rows": gold["rows"], "hash": gold.get("hash")},
            "accepted": accepted, **answers(q, gold, accepted, results)}


def main(lakes: list[str]) -> None:
    for lake in lakes:
        folder = OUT / lake
        questions = {q["id"]: q for q in map(json.loads, open(folder / "questions.jsonl"))}
        old = [json.loads(line) for line in open(folder / "labels.jsonl")]
        paths = databases(lake)
        with ThreadPoolExecutor(max_workers=32) as pool:
            new = list(pool.map(lambda x: again(x, questions[x["id"]], paths), old))
        changed = Counter()
        for a, b in zip(old, new):
            changed["gold status"] += a["gold"]["status"] != b["gold"]["status"]
            changed["answers"] += len(a["interpretations"]) != len(b["interpretations"])
            changed["questions"] += a["interpretations"] != b["interpretations"]
        shutil.copy(folder / "labels.jsonl", folder / f"labels.jsonl.bak-{datetime.date.today()}")
        with open(folder / "labels.jsonl", "w") as out:
            out.writelines(json.dumps(b) + "\n" for b in new)
        print(f"{lake}: {len(new)} labels; changed: {dict(changed)}; answers {sum(len(a['interpretations']) for a in old)}"
              f" -> {sum(len(b['interpretations']) for b in new)}; gold {dict(Counter(b['gold']['status'] for b in new))}")


if __name__ == "__main__":
    main(sys.argv[1:])
