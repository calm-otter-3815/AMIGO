"""AMIGO lazy without each lake input, for Table 8 of the paper and its appendix table: no value
lookup (runs/novalues_2026-11-18), no descriptions and no declared foreign keys
(runs/ablations_2026-11-18, see offline.py), on BIRD and Spider, against the stored AMIGO lazy run.
Stage 1 of the protocol, both labels; paired bootstrap against AMIGO lazy, Holm over the three
configurations and the scores of one benchmark and label.

  .venv/bin/python experiments/results/ablations_2026-11-18/table8.py
Writes table8.json next to this file and prints the LaTeX rows.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT), str(HERE.parent / "paper_review_2026-11-08")]
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402
import review as V  # noqa: E402

RUNS = ROOT / "runs"
CONFIGS = {
    "AMIGO lazy": RUNS / "rerun_2026-11-08" / "{lake}" / "joinchoice",
    "No value lookup": RUNS / "novalues_2026-11-18" / "{lake}" / "joinchoice",
    "No descriptions": RUNS / "ablations_2026-11-18" / "nodesc" / "{lake}" / "joinchoice",
    "No foreign keys": RUNS / "ablations_2026-11-18" / "nofk" / "{lake}" / "joinchoice",
}
LAKES = ("bird_dev", "spider_dev")
COLUMNS = [("gold", "R"), ("gold", "CR"), ("gold", "P"), ("gold", "CR="),
           ("multi", "IR"), ("multi", "ICR"), ("multi", "IP"), ("multi", "IR="), ("multi", "ICR="), ("multi", "IP=")]


def main() -> None:
    rng = np.random.default_rng(R.SEED)
    out = []
    for lake in LAKES:
        per_q, rows = {}, {}
        for name, folder in CONFIGS.items():
            mine = V.records(Path(str(folder).format(lake=lake)) / "records_inf.json")
            for label in V.LABEL:
                labels = P.labels(P.NIGHT, lake)[label]
                per_q[name, label] = V.scored(labels, lambda q: R.returned(mine.get(q), False))
                rows[name, label] = V.mean_row(list(per_q[name, label].values()))
        stars = {}
        for label in V.LABEL:  # one family per benchmark and label
            keys = [k for lab, k in COLUMNS if lab == label]
            qs = list(per_q["AMIGO lazy", label])
            tests = [(name, k, R.paired(np.array([per_q[name, label][q]["all"][k] for q in qs]),
                                        np.array([per_q["AMIGO lazy", label][q]["all"][k] for q in qs]), rng))
                     for name in list(CONFIGS)[1:] for k in keys]
            for (name, k, t), p in zip(tests, R.holm([t[3] for _, _, t in tests])):
                stars[name, label, k] = p < 0.05
        for name in CONFIGS:
            out.append({"lake": lake, "configuration": name,
                        **{f"{label} {k}": rows[name, label][k] for label, k in COLUMNS},
                        **{f"significant {label} {k}": stars.get((name, label, k), False) for label, k in COLUMNS},
                        "sets": rows[name, "gold"]["sets"], "size": rows[name, "gold"]["size"]})
    (HERE / "table8.json").write_text(json.dumps(out, indent=1))
    for r in out:
        cells = [f"{r[f'{lab} {k}']:.1f}" + ("$^*$" if r[f"significant {lab} {k}"] else "") for lab, k in COLUMNS]
        print(V.NAMES[r["lake"]], "&", r["configuration"], "&", " & ".join(cells),
              f"& {r['sets']:.2f} & {r['size']:.2f} \\\\")
    for agg, f in (("Mean", np.mean), ("Worst", np.min)):
        for name in CONFIGS:
            rs = [r for r in out if r["configuration"] == name]
            print(agg, "&", name, "&", " & ".join(f"{f([r[f'{lab} {k}'] for r in rs]):.1f}" for lab, k in COLUMNS),
                  f"& {(np.mean if agg == 'Mean' else np.max)([r['sets'] for r in rs]):.2f}"
                  f" & {(np.mean if agg == 'Mean' else np.max)([r['size'] for r in rs]):.2f} \\\\")


if __name__ == "__main__":
    main()
