"""AMIGO at each reasoning effort (2026-11-08 prompts), stage-1 scores of the main table.

  .venv/bin/python experiments/results/effort_2026-11-08/effort.py   (cwd: worktree campaign-1108)

Medium is the main AMIGO run (protocol.METHODS["AMIGO"]); none, low and xhigh are the effort
runs. Each level is tested against medium, paired bootstrap, Holm over the levels and scores of
one version. Seconds: the 30 timed questions (first 2 of 32 warm-up), one at a time, split plus
every AMIGO step, the join choice included. Out: output tokens per question of the place judge
and the join choice, over the full run. Writes effort.json next to this file.
"""
import json
import pickle
import sys
from pathlib import Path
from statistics import mean

import numpy as np

sys.path.insert(0, str(Path.cwd() / "experiments"))
sys.path.insert(0, str(Path.cwd()))
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402

HERE = Path(__file__).resolve().parent
RUN = R.JOINCHOICE
LEVELS = ("none", "low", "medium", "xhigh")
LAKES = ("bird_dev", "spider_dev")
WARM = 2


def folder(lake, level, step):  # step: amigo or joinchoice
    return RUN / lake / step if level == "medium" else RUN / "effort" / lake / f"{step}_{level}"


def lines(path):
    return [json.loads(x) for x in path.read_text().split("\n") if x] if path.exists() else []


def seconds(lake, level):
    timing = RUN / "timing" / lake
    split = json.loads((timing / f"split_{level}.json").read_text()) if (timing / f"split_{level}.json").exists() else {}
    if not (timing / "questions.jsonl").exists():
        return []
    out = []
    for q in [r["id"] for r in lines(timing / "questions.jsonl")][WARM:]:
        path = timing / f"joinchoice_{level}" / f"{q}.amigo.pkl"
        if q not in split or "seconds" not in split[q] or not path.exists():
            continue
        got = pickle.loads(path.read_bytes())
        if not failed(got):
            out.append(split[q]["seconds"] + got["seconds"]["total"] - got["seconds"].get("llm judge wholes", 0.0))
    return out


def failed(record):
    error = str(record.get("error") or record.get("judge_error") or "")
    return bool(error) and not error.startswith("judge wholes")


def main():
    rng = np.random.default_rng(R.SEED)
    out = []
    for lake in LAKES:
        labels = P.labels(P.NIGHT, lake)
        recs = {lv: json.loads((folder(lake, lv, "joinchoice") / "records_inf.json").read_text()) for lv in LEVELS}
        tok = {lv: sum((one.get("usage") or {}).get("output_tokens", 0)
                       for step, tag in (("amigo", "places"), ("joinchoice", "joins"))
                       for one in lines(folder(lake, lv, step) / "judge.jsonl")
                       if "response_id" in one and tag in str(one.get("label", ""))) for lv in LEVELS}
        for label, keys in R.MAIN.items():
            per = {lv: {q: R.question(R.targets_of(v), R.returned(recs[lv].get(q), False), True)
                        for q, v in labels[label].items()} for lv in LEVELS}
            others = [lv for lv in LEVELS if lv != "medium"]
            tests = [(lv, k, R.paired(R.means(per[lv], "all", k), R.means(per["medium"], "all", k), rng))
                     for lv in others for k in keys]
            sig = {(lv, k): q < 0.05 for (lv, k, _), q in zip(tests, R.holm([t[2][3] for t in tests]))}
            for lv in LEVELS:
                sizes = [s["size"] for s in per[lv].values() if s.get("size") is not None]
                secs = seconds(lake, lv)
                out.append({"lake": lake, "label": label, "level": lv,
                            **{k: 100 * R.means(per[lv], "all", k).mean() for k in keys},
                            "sig": [k for k in keys if sig.get((lv, k))],
                            "diff": {k: 100 * d for (l2, k, (d, *_)) in tests if l2 == lv},
                            "sets": mean(s["sets"] for s in per[lv].values()),
                            "set size": mean(sizes) if sizes else None,
                            "seconds": mean(secs) if secs else None, "timed": len(secs),
                            "out k": tok[lv] / len(labels["gold"]) / 1000,
                            # the whole judge is not part of AMIGO (the join choice replaces it): not a failure
                            "failed": sum(failed(r) for r in recs[lv].values())})
    (HERE / "effort.json").write_text(json.dumps(out, indent=1))
    for r in out:
        print(r["lake"], r["label"], r["level"], " ".join(f"{k}={r[k]:.1f}" for k in R.MAIN[r["label"]]),
              "sig", r["sig"], f"sets={r['sets']:.2f} size={r['set size']:.2f} out={r['out k']:.1f}k failed={r['failed']}",
              f"sec={r['seconds']}" if r["seconds"] else "")


if __name__ == "__main__":
    main()
