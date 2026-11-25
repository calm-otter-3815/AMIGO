"""How often a one-set method's set holds the tables of two or more interpretations of the
multi-valid label, on its questions with two or more labeled table sets: any two, and two that
are not nested (neither set inside the other). CORE-T and AMIGO conservative. No LLM call.

  .venv/bin/python experiments/results/behavior_2026-11-24/merged_sets.py
"""
import json, sys
from itertools import combinations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments')); sys.path.insert(0, str(ROOT))
from amigo import config
import paper_results as P
config.LAKES_DIR = P.NIGHT / "lakes"
import protocol as R
RUNS = {"CORE-T": P.NIGHT / "{lake}/bl_core_t/records.json",
        "AMIGO conservative": ROOT / "runs/refplaces_2026-11-19/{lake}/conservative/records_inf.json"}
for lake in P.THREE:
    labels = P.labels(P.NIGHT, lake)["multi"]
    amb = [q for q, qs in labels.items() if len(R.targets_of(qs)) >= 2]
    for name, path in RUNS.items():
        rec = json.loads(Path(str(path).format(lake=lake)).read_text())
        any2 = apart = 0
        for q in amb:
            s = R.returned(rec.get(q), False)
            held = [t for t in R.targets_of(labels[q]) if s and t <= s[0]]
            if len(held) >= 2:
                any2 += 1
                apart += any(not (a <= b or b <= a) for a, b in combinations(held, 2))
        print(f"{lake} {name}: {len(amb)} ambiguous questions; holds two or more {100*any2/len(amb):.1f}%, two not nested {100*apart/len(amb):.1f}%")
