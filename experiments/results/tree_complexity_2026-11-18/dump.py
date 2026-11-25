"""Per question: AMIGO's tree size (forks, leaves, depth) and the question's complexity
(tables of its original query, parts that AMIGO placed, labeled table sets of the
multi-valid label). No LLM call. Writes questions.json next to this file.

  .venv/bin/python experiments/results/tree_complexity_2026-11-18/dump.py

Tree sizes: runs/guided_2026-11-13 (experiments/guided_eval.py). Parts: the largest number
of placed columns ('bound') over AMIGO's candidates in runs/rerun_2026-11-08 (the saved run
the tree is built from); a relaxed candidate places fewer.
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments")); sys.path.insert(0, str(ROOT))
from amigo import config
import paper_results as P
config.LAKES_DIR = P.NIGHT / "lakes"
import protocol as R

out = {}
for lake in P.THREE:
    tree = json.loads((ROOT / f"runs/guided_2026-11-13/{lake}.json").read_text())
    recs = json.loads((ROOT / f"runs/rerun_2026-11-08/{lake}/joinchoice/records_inf.json").read_text())
    labels = P.labels(P.NIGHT, lake)
    for q, queries in labels["multi"].items():
        t = tree.get(q, {}).get("tree")
        gold = labels["gold"].get(q)
        if t is None or not gold:
            continue
        interps = (recs.get(q) or {}).get("interpretations") or []
        out[q] = {"lake": lake, "forks": t["forks"], "leaves": t["leaves"], "depth": t["depth"],
                  "tables": len(R.targets_of(gold)[0]), "labeled_sets": len(R.targets_of(queries)),
                  "parts": max((len(i.get("bound") or []) for i in interps), default=0)}
(HERE / "questions.json").write_text(json.dumps(out, indent=1))
print(len(out), "questions")
