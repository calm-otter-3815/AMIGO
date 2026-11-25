"""Two checks behind Section 5.1, no LLM call.
1. Route+SQL: share of single-valid questions routed to the database of the labeled query, and its
   CR when the routing is right and when it is wrong.
2. On the questions where CORE-T's set holds the single-valid labeled set and AMIGO conservative's
   does not: how often AMIGO conservative's set is another table set of the multi-valid label.

  .venv/bin/python experiments/results/behavior_2026-11-24/route_and_alternatives.py
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments')); sys.path.insert(0, str(ROOT))
from amigo import config
import paper_results as P
config.LAKES_DIR = P.NIGHT / "lakes"
import protocol as R
CONS = ROOT / "runs/refplaces_2026-11-19/{lake}/conservative/records_inf.json"
for lake in ("bird_dev", "spider_dev"):
    gold = P.labels(P.NIGHT, lake)["gold"]
    rs = json.loads((P.NIGHT / lake / "bl_route_sql/records.json").read_text())
    right = wrong = 0; cr_r = cr_w = 0
    for q, qs in gold.items():
        t = R.targets_of(qs)[0]
        dbs = {x.split(".")[0] for x in t}
        rec = rs.get(q) or {}
        s = R.returned(rec, False)
        hit = bool(s) and t <= s[0]
        if rec.get("database") in dbs:
            right += 1; cr_r += hit
        else:
            wrong += 1; cr_w += hit
    n = right + wrong
    print(f"{lake} Route+SQL: routed to the labeled database on {100*right/n:.1f}% of {n} questions; "
          f"CR {100*cr_r/max(1,right):.1f} when right, {100*cr_w/max(1,wrong):.1f} when wrong")
for lake in P.THREE:
    labels = P.labels(P.NIGHT, lake)
    ct = json.loads((P.NIGHT / lake / "bl_core_t/records.json").read_text())
    cs = json.loads(Path(str(CONS).format(lake=lake)).read_text())
    only = other = 0
    for q, qs in labels["gold"].items():
        t = R.targets_of(qs)[0]
        a, b = R.returned(ct.get(q), False), R.returned(cs.get(q), False)
        if a and t <= a[0] and not (b and t <= b[0]):
            only += 1
            mv = R.targets_of(labels["multi"].get(q, []))
            other += bool(b) and b[0] in mv and b[0] != t
    print(f"{lake}: CORE-T holds the labeled set and AMIGO conservative does not on {only} questions; "
          f"AMIGO conservative's set is another valid table set on {other} of them ({100*other/max(1,only):.1f}%)")
