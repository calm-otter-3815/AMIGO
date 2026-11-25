"""Share of the scored questions on which MURRE stops after its first round, and on which
CORE-T's LLM forms more than one group (runs/multiset_2026-11-19). No LLM call.

  .venv/bin/python experiments/results/behavior_2026-11-24/rounds_and_groups.py
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT)]
import paper_results as P
for lake in ("bird_dev", "spider_dev", "mmqa"):
    qs = set(P.labels(P.NIGHT, lake)["gold"])
    m = json.loads((ROOT / f"runs/multiset_2026-11-19/{lake}/bl_murre_paths1/records.json").read_text())
    c = json.loads((ROOT / f"runs/multiset_2026-11-19/{lake}/bl_core_t_groups/records.json").read_text())
    stop = sum(m[q].get("hops") == 1 for q in qs if q in m)
    groups = sum((c[q].get("groups_formed") or 0) > 1 for q in qs if q in c)
    print(f"{lake} {len(qs)} questions: MURRE stops after round 1 on {100*stop/len(qs):.1f}%; "
          f"CORE-T forms more than one group on {100*groups/len(qs):.1f}%")
