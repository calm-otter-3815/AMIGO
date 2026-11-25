"""Every compared method on Spider 2.0-Lite (both labels), printed as LaTeX rows. No LLM call.

  .venv/bin/python experiments/results/table4_2026-11-18/s2.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments')); sys.path.insert(0, str(ROOT))
from amigo import config
import paper_results as P
config.LAKES_DIR = P.NIGHT / "lakes"
import protocol as R
M = {}
for name, f in [("Dense", "dense"), ("BM25", "bm25"), ("Hybrid", "hybrid"), ("JAR", "jar"), ("Greedy JAR", "greedy_jar"), ("MURRE", "murre"), ("CRUSH4SQL", "crush4sql")]:
    for k in (1, 3, 5):
        M[f"{name}@{k}"] = (P.NIGHT, f"bl_{f}_{'t' if f == 'crush4sql' else 'k'}{k}/records.json", False)
M |= {"CORE-T": (P.NIGHT, "bl_core_t/records.json", False), "Route+SQL": (P.NIGHT, "bl_route_sql/records.json", False),
      "Full schema": (P.NIGHT, "bl_full_schema/records.json", False)}
R.METHODS = M
sc = R.score("spider2_lite")
K = {"gold": ("R", "CR", "P", "CR="), "multi": ("IR", "ICR", "IP", "IR=", "ICR=", "IP=")}
for n in M:
    g, m = sc["gold"][n], sc["multi"][n]
    cells = [100 * R.means(g, "all", k).mean() for k in K["gold"]] + [100 * R.means(m, "all", k).mean() for k in K["multi"]]
    sz = [s["size"] for s in g.values() if s["size"] is not None]
    empty = sum(s["sets"] == 0 for s in g.values())
    print(f"    {n} & " + " & ".join(f"{c:.1f}" for c in cells) + f" & {sum(sz)/len(sz):.2f} \\\\" + f"  % empty {empty}")
