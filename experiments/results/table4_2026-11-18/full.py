"""Every method of Appendix D.2 plus AMIGO lazy and conservative: values and tests, Holm over all
the tests of one lake and label. No LLM call.

  .venv/bin/python experiments/results/table4_2026-11-18/full.py experiments/results/table4_2026-11-18/full.json
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
M = {}
for name, f in [("Dense", "dense"), ("BM25", "bm25"), ("Hybrid", "hybrid"), ("JAR", "jar"), ("Greedy JAR", "greedy_jar"), ("MURRE", "murre"), ("CRUSH4SQL", "crush4sql")]:
    for k in (1, 3, 5):
        M[f"{name}@{k}"] = (P.NIGHT, f"bl_{f}_{'t' if f == 'crush4sql' else 'k'}{k}/records.json", False)
M |= {"CORE-T": base["CORE-T"], "Route+SQL": base["Route+SQL"], "Full schema": (P.NIGHT, "bl_full_schema/records.json", False),
      "AMIGO conservative": base["AMIGO top-1"], "AMIGO": base["AMIGO"]}
rng = np.random.default_rng(R.SEED)
out = {}
for lake in (*P.THREE, "spider2_lite"):
    R.METHODS = {n: v for n, v in M.items() if not (n == "Full schema" and lake in ("spider_dev", "mmqa"))}
    sc = R.score(lake)
    for label in ("gold", "multi"):
        per = sc[label]; keys = R.MAIN[label]; vals = {}
        for n, pq in per.items():
            v = {k: 100 * R.means(pq, "all", k).mean() for k in keys}
            sz = [s["size"] for s in pq.values() if s["size"] is not None]
            v["size"] = float(np.mean(sz)) if sz else None
            vals[n] = v
        others = [n for n in per if n != "AMIGO"]
        tests = [(n, k, R.paired(R.means(per["AMIGO"], "all", k), R.means(per[n], "all", k), rng)) for n in others for k in keys]
        adj = R.holm([t[2][3] for t in tests])
        for (n, k, (d, lo, hi, _)), a in zip(tests, adj):
            vals[n][k + " test"] = (100 * d, a)
        out[f"{lake}/{label}"] = vals
json.dump(out, open(sys.argv[1], 'w'), indent=1); print('ok')
