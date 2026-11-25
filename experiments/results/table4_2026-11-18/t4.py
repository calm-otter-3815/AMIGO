"""Table 4 values and AMIGO-lazy-minus-method tests (Holm per lake and label), with the
methods of Table 4. No LLM call.

  .venv/bin/python experiments/results/table4_2026-11-18/t4.py extra experiments/results/table4_2026-11-18/extra.json
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments')); sys.path.insert(0, str(ROOT))
from amigo import config
import paper_results as P
config.LAKES_DIR = P.NIGHT / "lakes"
import protocol as R
base = dict(R.METHODS)
extra = sys.argv[1] == 'extra'
M = {"Dense@3": base["Dense k3"], "MURRE@3": base["MURRE k3"], "CORE-T": base["CORE-T"], "Route+SQL": base["Route+SQL"],
     "AMIGO conservative": base["AMIGO top-1"], "AMIGO": base["AMIGO"]}
if extra:
    N = P.NIGHT
    for name, f in [("Dense@5", "bl_dense_k5"), ("MURRE@5", "bl_murre_k5"), ("BM25@3", "bl_bm25_k3"), ("BM25@5", "bl_bm25_k5"),
                    ("JAR@3", "bl_jar_k3"), ("JAR@5", "bl_jar_k5"), ("Greedy JAR@3", "bl_greedy_jar_k3"), ("Greedy JAR@5", "bl_greedy_jar_k5"),
                    ("CRUSH4SQL@3", "bl_crush4sql_t3"), ("CRUSH4SQL@5", "bl_crush4sql_t5"), ("Full schema", "bl_full_schema")]:
        M[name] = (N, f + "/records.json", False)
R.METHODS = M
rng = np.random.default_rng(R.SEED)
out = {}
for lake in (*P.THREE, "spider2_lite"):
    sc = R.score(lake)
    for label in ("gold", "multi"):
        per = sc[label]
        if not per: continue
        if lake == "mmqa" or True:
            pass
        keys = R.MAIN[label]
        vals = {}
        for n, pq in per.items():
            v = {k: 100 * R.means(pq, "all", k).mean() for k in keys}
            v["sets"] = float(np.mean([s["sets"] for s in pq.values()]))
            sz = [s["size"] for s in pq.values() if s["size"] is not None]
            v["size"] = float(np.mean(sz)) if sz else None
            v["empty"] = sum(s["sets"] == 0 for s in pq.values()); v["n"] = len(pq)
            vals[n] = v
        others = [n for n in per if n != "AMIGO"]
        tests = [(n, k, R.paired(R.means(per["AMIGO"], "all", k), R.means(per[n], "all", k), rng)) for n in others for k in keys]
        adj = R.holm([t[2][3] for t in tests])
        for (n, k, (d, lo, hi, _)), a in zip(tests, adj):
            vals[n][k + " test"] = (round(100 * d, 2), a)
        out[f"{lake}/{label}"] = vals
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print('ok')
