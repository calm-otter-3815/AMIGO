"""Stage 2 (main writer), two checks for Section 5.2, from the saved SQL results.

1. Top-R EX (multi-valid label): AMIGO lazy, which writes one query per candidate
   (sqleval --hints, the paper's row), keeps only the queries of its first R candidates, R being
   the number of labeled results of the question (as R-precision cuts at the number of
   relevant items). The label sets R only for scoring; no method sees it.
2. Same tables found: over the labeled results whose tables both AMIGO conservative and
   CORE-T found, the EX of each and the extra tables of the set that holds them.
Paired bootstrap over questions, Holm over the compared methods of one lake and label.

  .venv/bin/python experiments/results/sql_budget_2026-11-18/budget.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT)]
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402
import sqleval as S  # noqa: E402

OTHERS = ["Dense k3", "MURRE k3", "CORE-T", "Route+SQL", "AMIGO top-1"]


def hits(got, q, sets):
    return {got[(q, s)]["hash"] for s in sets if got.get((q, s), {}).get("status") in ("ok", "empty")}


def main():
    rng = np.random.default_rng(R.SEED)
    out = {"top_r": [], "same_found": []}
    for lake in P.THREE:
        got, goal = S.results("qwen", lake), S.targets(lake)
        hinted = {}
        for x in sorted(S.eval_lakes._lines(S.OUT / "qwen" / f"{lake}.hints.jsonl"), key=lambda x: (x["q"], x["i"])):
            hinted.setdefault(x["q"], []).append((x["i"], x["result"]))
        rec = {m: json.loads((n / lake / f).read_text()) for m, (n, f, _) in R.METHODS.items() if (n / lake / f).exists()}
        sets = {m: {q: R.returned(rec[m].get(q), R.METHODS[m][2]) for q in goal["multi"]} for m in rec}
        # 1. top-R EX, multi-valid label
        ans = goal["multi"]
        qs = list(ans)
        ex = {m: np.array([np.mean([h in hits(got, q, sets[m][q]) for h, _ in ans[q]]) for q in qs]) for m in rec}
        lazy = {q: [(i, r) for i, r in hinted.get(q, [])] for q in qs}

        def lazy_ex(q, cut):
            got_q = {r["hash"] for i, r in lazy[q] if i < cut and r["status"] in ("ok", "empty")}
            return np.mean([h in got_q for h, _ in ans[q]])
        ex["AMIGO"] = np.array([lazy_ex(q, 10 ** 9) for q in qs])
        top = np.array([lazy_ex(q, len(ans[q])) for q in qs])
        queries = np.mean([sum(i < len(ans[q]) for i, _ in lazy[q]) for q in qs])
        others = [m for m in OTHERS if m in rec]
        tests = [R.paired(top, ex[m], rng) for m in others]
        for m, t, p in zip(others, tests, R.holm([t[3] for t in tests])):
            out["top_r"].append({"lake": lake, "method": m, "EX": 100 * ex[m].mean(), "top-R EX": 100 * top.mean(),
                                 "diff": [100 * x for x in t[:3]], "p holm": p})
        out["top_r"].append({"lake": lake, "method": "AMIGO", "EX": 100 * ex["AMIGO"].mean(), "top-R EX": 100 * top.mean(),
                             "top-R queries": queries, "R": float(np.mean([len(ans[q]) for q in qs]))})
        # 2. same tables found: AMIGO conservative against CORE-T, both labels
        for label in ("gold", "multi"):
            a, c, xa, xc = [], [], [], []
            for q, targets in goal[label].items():
                sa, sc = (R.returned(rec[m].get(q), R.METHODS[m][2]) for m in ("AMIGO top-1", "CORE-T"))
                ha, hc = hits(got, q, sa), hits(got, q, sc)
                both = [(h, ts) for h, ts in targets if any(t <= s for t in ts for s in sa) and any(t <= s for t in ts for s in sc)]
                if not both:
                    continue
                a.append(np.mean([h in ha for h, _ in both]))
                c.append(np.mean([h in hc for h, _ in both]))
                extra = lambda s, ts: len(s) - max(len(t) for t in ts if t <= s)  # noqa: E731
                xa.append(np.mean([min(extra(s, ts) for s in sa if any(t <= s for t in ts)) for _, ts in both]))
                xc.append(np.mean([min(extra(s, ts) for s in sc if any(t <= s for t in ts)) for _, ts in both]))
            d, lo, hi, p = R.paired(np.array(a), np.array(c), rng)
            out["same_found"].append({"lake": lake, "label": label, "questions": len(a), "AMIGO conservative EX": 100 * np.mean(a),
                                      "CORE-T EX": 100 * np.mean(c), "diff": [100 * d, 100 * lo, 100 * hi], "p": p,
                                      "extra tables AMIGO conservative": float(np.mean(xa)), "extra tables CORE-T": float(np.mean(xc))})
    path = Path(__file__).with_name("budget.json")
    path.write_text(json.dumps(out, indent=1))
    for k, rows in out.items():
        print(k)
        for r in rows:
            print(" ", {a: (round(b, 2) if isinstance(b, float) else [round(x, 1) for x in b] if isinstance(b, list) else b)
                        for a, b in r.items()})


if __name__ == "__main__":
    main()
