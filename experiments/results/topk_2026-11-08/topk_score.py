"""Scores of the top-k sweep (topk_<lake>.jsonl): per lake, label and setting, every score of
protocol.question and table sets per question, scored as the paper's stage 1 (protocol.question); each setting
tested against the place judge under the same cap (paired bootstrap, Holm over the settings and
scores of one lake and label), at full size and cut per question to the place judge's number of
table sets. Run from the worktree root (campaign-1108). Writes topk_scores.json here."""
import collections, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "experiments"); sys.path.insert(0, ".")
import paper_results as P
import protocol as R

HERE = Path(__file__).parent
KS = ["1", "2", "3", "5", "10", "15", "20"]
rng = np.random.default_rng(R.SEED)
out = []
for lake in P.THREE:
    path = HERE / f"topk_{lake}.jsonl"
    if not path.exists():
        continue
    got = collections.defaultdict(dict)
    capped = collections.Counter()
    for line in path.open():
        r = json.loads(line)
        sets = [] if r.get("error") else list(dict.fromkeys(frozenset(s) for s in r["sets"] if s))
        got[r["setting"]][r["q"]] = sets
        capped[r["setting"]] += bool(r.get("capped"))
    done = set(got["judge"])
    for label in ("gold", "multi"):
        labels = {q: v for q, v in P.labels(P.NIGHT, lake)[label].items() if q in done}
        size = {q: len(got["judge"][q]) for q in labels}
        per = {}
        for setting in ["judge", *KS]:
            for cut in (False, True):
                if cut and setting == "judge":
                    continue
                per[(setting, cut)] = {q: R.question(R.targets_of(v), got[setting].get(q, [])[:size[q]] if cut
                                                     else got[setting].get(q, []), True) for q, v in labels.items()}
        tests = {}
        for key in per:
            if key[0] == "judge":
                continue
            for score in R.MAIN[label]:
                a = np.array([per[key][q]["all"][score] for q in labels])
                b = np.array([per[("judge", False)][q]["all"][score] for q in labels])
                tests[(key, score)] = R.paired(a, b, rng)
        holm = dict(zip(tests, R.holm([t[3] for t in tests.values()])))
        for (setting, cut), scores in per.items():
            row = {"lake": lake, "label": label, "setting": setting, "cut": cut, "n": len(labels),
                   "capped": capped[setting] if not cut else None}
            for score in next(iter(scores.values()))["all"]:
                row[score] = 100 * float(np.mean([s["all"][score] for s in scores.values()]))
                if (setting, cut) != ("judge", False) and score in R.MAIN[label]:
                    row[f"{score} diff"] = 100 * tests[((setting, cut), score)][0]
                    row[f"{score} p"] = holm[((setting, cut), score)]
            row["sets"] = float(np.mean([s["sets"] for s in scores.values()]))
            row["tables"] = float(np.mean([s["tables"] for s in scores.values()]))
            row["size"] = float(np.mean([s["size"] for s in scores.values() if s["size"] is not None]))
            out.append(row)
(HERE / "topk_scores.json").write_text(json.dumps(out, indent=1))
for r in out:
    star = lambda k: "*" if r.get(f"{k} p", 1) < 0.05 else " "
    print(f"{r['lake']:10} {r['label']:5} {r['setting']:>5}{' cut' if r['cut'] else '    '} n={r['n']:4} "
          + " ".join(f"{k} {r[k]:5.1f}{star(k)}" for k in R.MAIN[r["label"]])
          + f" sets {r['sets']:7.2f} capped {r['capped']}")
