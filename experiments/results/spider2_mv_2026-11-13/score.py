"""Spider 2.0-Lite multi-valid label on the 24 questions with a public gold SQL: label
statistics and retrieval scores, with the paper's own code. No LLM call.

  .venv/bin/python experiments/results/spider2_mv_2026-11-13/score.py

Labels: runs/labeler/spider2_lite/labels.jsonl (LABEL_RUN=spider2_lite labeler.sample, then
labeler.go, labeler.values, labeler.regroup, labeler.export). Retrieval outputs: the saved
records of protocol.METHODS (no retrieval rerun). The lake is the paper run's
(runs/paper_2026-10-20/lakes/spider2_lite), the one these records were made on; lakes/ on
main has no spider2_lite. Scores: protocol.question per question, means, 95% bootstrap
intervals, and AMIGO minus each method with Holm-corrected bootstrap p values, as
protocol.retrieval does per lake and label. The single-valid label is scored on all 135
questions (it must equal the paper's row) and on the same 24 as the multi-valid label.
Writes scores.md and scores.json next to this file.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "results" / "benchmark_stats_2026-10-25"))
sys.path.insert(0, str(ROOT / "experiments" / "results" / "paper_review_2026-11-08"))
sys.path.insert(0, str(ROOT))
from amigo import config  # noqa: E402
import paper_results as P  # noqa: E402

config.LAKES_DIR = P.NIGHT / "lakes"  # the lake the saved records were made on
import protocol as R  # noqa: E402
import review  # noqa: E402
import stats as S  # noqa: E402

LAKE = "spider2_lite"
S.NAMES[LAKE] = "Spider 2.0-Lite"
S.lake_size = lambda lake: {k: v for k, v in zip(("databases", "tables", "columns"), (
    __import__("sqlite3").connect(P.NIGHT / "lakes" / lake / "layer.sqlite").execute(
        "SELECT (SELECT count(*) FROM databases), (SELECT count(*) FROM tables), (SELECT count(*) FROM columns)").fetchone()))}


def kinds() -> dict:
    """review.kinds for this lake: alternative queries of the final label by kind."""
    by_kind, two, two_neither, total = Counter(), 0, 0, 0
    for queries in review._kinded(LAKE).values():
        total += 1
        for _, kind, named, _ in queries[1:]:
            by_kind[kind] += 1
            by_kind["new tables all share a name with an original table"] += named
        two += len(queries) > 1
        two_neither += len([x for x in queries if x[1] != "copy" and not x[2]]) > 1
    return {"questions": total, "alternative queries by kind": dict(by_kind), "share with 2+ valid queries": 100 * two / total,
            "share with 2+ valid queries, both left out": 100 * two_neither / total}


# the points of the paper's figure of output size, as review.top_m and rescore.every_k make them for the other lakes
CURVES = {f"{name} k{k}": f"bl_{name.lower()}_k{k}" for name in ("MURRE", "Dense") for k in (1, 3, 5)}
CURVES |= {"CORE-T": "bl_core_t", "Route+SQL": "bl_route_sql"}


def figure() -> list[dict]:
    labels = P.labels(P.NIGHT, LAKE)
    amigo = review.records(review.AMIGO.parent.parent / LAKE / "joinchoice" / "records_inf.json")
    points = []
    for label in ("gold", "multi"):
        for m in review.CUTS:
            sets = lambda q: R.returned(amigo.get(q), False)[:m] if m else R.returned(amigo.get(q), False)
            points.append({"label": label, "method": "AMIGO", "cut": m,
                           **review.mean_row(list(review.scored(labels[label], sets).values()))})
        for name, folder in CURVES.items():
            got = review.records(P.NIGHT / LAKE / folder / "records.json")
            sets = lambda q: R.returned(got.get(q), False)
            points.append({"label": label, "method": name, **review.mean_row(list(review.scored(labels[label], sets).values()))})
    return points


def table(scored: dict, keys: tuple, rng) -> tuple[list[str], list[dict]]:
    lines = ["| method | " + " | ".join(keys) + " | sets | n |", "|---|" + "---|" * (len(keys) + 2)]
    rows = []
    for name, per_q in scored.items():
        vals = {k: R.means(per_q, "all", k) for k in keys}
        cells = {k: 100 * v.mean() for k, v in vals.items()}
        spans = {f"{k} 95%": [100 * x for x in R.interval(v, rng)] for k, v in vals.items()}
        sets = float(np.mean([s["sets"] for s in per_q.values()]))
        rows.append({"method": name, "n": len(per_q), **cells, **spans, "sets": sets})
        lines.append(f"| {name} | " + " | ".join(f"{cells[k]:.1f}" for k in keys) + f" | {sets:.2f} | {len(per_q)} |")
    return lines, rows


def tests(scored: dict, keys: tuple, rng) -> tuple[list[str], list[dict]]:
    others = [n for n in scored if n != "AMIGO"]
    got = [(n, k, R.paired(R.means(scored["AMIGO"], "all", k), R.means(scored[n], "all", k), rng)) for n in others for k in keys]
    adjusted = R.holm([t[2][3] for t in got])
    lines = ["| method | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
    cells = {(n, k): f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if a < 0.05 else ''}"
             for (n, k, (d, lo, hi, _)), a in zip(got, adjusted)}
    lines += [f"| {n} | " + " | ".join(cells[n, k] for k in keys) + " |" for n in others]
    rows = [{"method": n, "score": k, "diff": 100 * d, "lo": 100 * lo, "hi": 100 * hi, "p": a}
            for (n, k, (d, lo, hi, _)), a in zip(got, adjusted)]
    return lines, rows


def main() -> None:
    rng = np.random.default_rng(R.SEED)
    scored = R.score(LAKE)
    ids = list(P.labels(P.NIGHT, LAKE)["multi"])
    views = {
        "single-valid label, all 135 questions": (scored["gold"], R.MAIN["gold"]),
        f"single-valid label, the {len(ids)} questions of the multi-valid label": (
            {n: {q: per_q[q] for q in ids} for n, per_q in scored["gold"].items()}, R.MAIN["gold"]),
        f"multi-valid label, {len(ids)} questions": (scored["multi"], R.MAIN["multi"]),
    }
    out = {"stats": S.stats(LAKE), "kinds": kinds(), "figure": figure(), "scores": {}, "tests": {}}
    lines = ["# Spider 2.0-Lite multi-valid label (24 questions with a public gold SQL)", "",
             "Made by score.py from runs/labeler/spider2_lite and the saved retrieval records. No LLM call.", "",
             "## Label statistics", ""]
    for key, value in out["stats"].items():
        if isinstance(value, dict) and key in ("gold", "multi", "labeler"):
            lines.append(f"### {key}" + (" (all 135 questions)" if key == "gold" else ""))
            lines += [f"- {k}: {S.fmt(v)}" for k, v in value.items()]
        elif key != "lake":
            lines.append(f"- {key}: {S.fmt(value)}")
    lines += ["", "### alternative queries of the final label by kind", ""]
    lines += [f"- {k}: {S.fmt(v)}" for k, v in out["kinds"].items()]
    for title, (per_method, keys) in views.items():
        got, rows = table(per_method, keys, rng)
        lines += ["", f"## Retrieval, {title}", ""] + got
        out["scores"][title] = rows
    lines += ["", "## AMIGO minus each method", "",
              "Mean difference in points, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over "
              "the comparisons of one label (every method and score); * when below 0.05."]
    for title, (per_method, keys) in views.items():
        got, rows = tests(per_method, keys, rng)
        lines += ["", f"### {title}", ""] + got
        out["tests"][title] = rows
    (HERE / "scores.md").write_text("\n".join(lines) + "\n")
    (HERE / "scores.json").write_text(json.dumps(out, indent=1, default=str))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
