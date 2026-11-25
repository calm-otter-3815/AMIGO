"""Stage 1 of the evaluation protocol (docs/eval_protocol.md): retrieval scores per target,
averaged per question, then over questions, with bootstrap intervals. No LLM call.

  .venv/bin/python experiments/protocol.py retrieval [--out DIR]

A target is one distinct table set among a question's valid queries. The method's
returned sets are its distinct non-empty table sets. Per target, the matched set has the
highest recall, then the highest precision. A failed or missing answer is an empty one,
counted in `empty`.
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_results as P  # noqa: E402

ROOT = P.ROOT
JOINCHOICE = ROOT / "runs" / "rerun_2026-11-08"  # AMIGO with the 2026-11-08 prompts
OUT = ROOT / "experiments" / "results" / "protocol_2026-11-08"
# display name -> records file under a lake folder, and whether to keep only the first
METHODS = {
    "Dense k3": (P.NIGHT, "bl_dense_k3/records.json", False),
    "MURRE k3": (P.NIGHT, "bl_murre_k3/records.json", False),
    "CORE-T": (P.NIGHT, "bl_core_t/records.json", False),
    "Route+SQL": (P.NIGHT, "bl_route_sql/records.json", False),
    "AMIGO top-1": (JOINCHOICE, "joinchoice/records_inf.json", True),
    "AMIGO": (JOINCHOICE, "joinchoice/records_inf.json", False),
}
LABEL_NAMES = {"gold": "gold label", "multi": "multi-valid label"}
SIZES = ("all", "single", "multi")
LAKES = (*P.THREE, "spider2_lite")  # Spider 2.0-Lite has the gold label only
# the scores of each label in the paper's main table, tested AMIGO against each method
MAIN = {"gold": ("R", "CR", "P", "CR="), "multi": ("IR", "ICR", "IP", "IR=", "ICR=", "IP=")}
RESAMPLES = 10_000
SEED = 0


def returned(record: dict | None, first: bool) -> list[frozenset]:
    """The distinct non-empty table sets of an answer, in order; none for a failed one."""
    if not record or record.get("error"):
        return []
    found = record.get("interpretations") or []
    sets = list(dict.fromkeys(frozenset(o["tables"]) for o in (found[:1] if first else found)))
    return [s for s in sets if s]


def matched(target: frozenset, sets: list[frozenset]) -> tuple[float, float, float]:
    """(R, CR, P) of one target against the set of highest recall, then highest precision."""
    if not target:  # a query that reads no table: found (0 such queries on these lakes)
        return 1.0, 1.0, 0.0
    best = (0.0, 0.0)
    for s in sets:
        best = max(best, (len(target & s) / len(target), len(target & s) / len(s)))
    return best[0], float(best[0] == 1.0), best[1]


def paired_up(targets: list[frozenset], sets: list[frozenset]) -> dict[int, int]:
    """The largest one-to-one pairing of targets with returned sets that hold all their
    tables, each set used once: {target index: set index} (augmenting paths)."""
    owner: dict[int, int] = {}

    def take(i: int, seen: set) -> bool:
        for j, s in enumerate(sets):
            if j not in seen and targets[i] <= s:
                seen.add(j)
                if j not in owner or take(owner[j], seen):
                    owner[j] = i
                    return True
        return False
    for i in range(len(targets)):
        take(i, set())
    return {i: j for j, i in owner.items()}


def question(targets: list[frozenset], sets: list[frozenset], pooled: bool) -> dict:
    """Per size (all, single-table targets, multi-table targets) the question's mean R, CR,
    P, F1 and strict CR (CR=) over its targets of that size, and the share IR (IR=) of them
    paired one to one with a returned set that holds (equals) them; None when it has none.
    On all targets, also ICR (ICR=): every target paired, and IP (IP=): the share of returned
    sets paired. Pooled P over every returned table when `pooled`; and the counts shown next
    to the scores."""
    out = {}
    hold = paired_up(targets, sets)
    for size in SIZES:
        mine = [i for i, t in enumerate(targets) if size == "all" or (len(t) == 1) == (size == "single")]
        got = [matched(targets[i], sets) for i in mine]
        out[size] = {k: mean(g[i] for g in got) for i, k in enumerate(("R", "CR", "P"))} if got else None
        if got:  # F1: the harmonic mean of R and P per target, 0 when R is 0
            out[size]["F1"] = mean(2 * r * p / (r + p) if r else 0.0 for r, _, p in got)
            out[size]["CR="] = out[size]["IR="] = mean(float(targets[i] in sets) for i in mine)
            out[size]["IR"] = mean(float(i in hold) for i in mine)
    if out["all"] is not None:
        same = sum(t in sets for t in targets)
        out["all"] |= {"ICR": float(len(hold) == len(targets)), "IP": len(hold) / len(sets) if sets else 0.0,
                       "ICR=": float(same == len(targets)), "IP=": same / len(sets) if sets else 0.0}
    every = frozenset().union(*sets) if sets else frozenset()
    if pooled:
        out["all"]["pooled P"] = len(every & frozenset().union(*targets)) / len(every) if every else 0.0
    out["sets"], out["tables"] = len(sets), len(every)
    out["size"] = mean(len(s) for s in sets) if sets else None  # mean set size; None with no set
    return out


def targets_of(queries: list) -> list[frozenset]:
    return list(dict.fromkeys(frozenset(tables) for tables, _ in queries))


def score(lake: str) -> dict:
    """{label: {method: {question id: question()}}} on the label's questions; methods that
    did not run on the lake are left out. A question with no answer has sets == 0."""
    labels = P.labels(P.NIGHT, lake)
    out = {}
    for label in LABEL_NAMES:
        out[label] = {}
        for name, (night, file, first) in METHODS.items() if labels[label] else ():
            path = night / lake / file
            if not path.exists():
                continue
            records = json.loads(path.read_text())
            out[label][name] = {q: question(targets_of(queries), returned(records.get(q), first), label == "multi")
                                for q, queries in labels[label].items()}
    return out


def means(per_q: dict, size: str, key: str) -> np.ndarray:
    return np.array([s[size][key] for s in per_q.values() if s[size] is not None])


def interval(values: np.ndarray, rng) -> tuple[float, float]:
    picks = rng.integers(0, len(values), (RESAMPLES, len(values)))
    boot = values[picks].mean(axis=1)
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def paired(a: np.ndarray, b: np.ndarray, rng) -> tuple[float, float, float, float]:
    """The mean of a - b over questions, its 95% percentile interval and a two-sided
    bootstrap p value, resampling questions."""
    diff = a - b
    picks = rng.integers(0, len(diff), (RESAMPLES, len(diff)))
    boot = diff[picks].mean(axis=1)
    p = min(1.0, 2 * min((boot <= 0).mean(), (boot >= 0).mean()))
    return float(diff.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), float(p)


def holm(ps: list[float]) -> list[float]:
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, running = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        out[i] = running
    return out


def retrieval(out: Path) -> None:
    rng = np.random.default_rng(SEED)
    scored = {lake: score(lake) for lake in LAKES}
    lines = ["# Retrieval (stage 1 of docs/eval_protocol.md)", "",
             "Per target R, CR, P from the returned set with the highest recall (then precision), and F1, their "
             "harmonic mean (0 when R is 0); mean over the "
             "question's targets, then over questions. Pooled P: every returned table against every table of a "
             "valid query (multi-valid label only). sets: distinct table sets returned per question; tables: "
             "distinct tables returned per question; size: mean tables per returned set, per question, then over the "
             "questions with a set. empty: questions with no table returned (a failed run "
             "counts here, scored as returning nothing). "
             "AMIGO is the join-choice version; AMIGO top-1 keeps its first interpretation.", ""]
    rows = []
    for label, title in LABEL_NAMES.items():
        for size in SIZES:
            keys = ["R", "CR", "P", "F1", "CR="] + (["IR", "IR="] if label == "multi" else [])
            if size == "all" and label == "multi":
                keys += ["pooled P", "ICR", "IP", "ICR=", "IP="]
            head = keys + (["sets", "tables", "size", "empty", "n"] if size == "all" else ["n"])
            lines += [f"## {title}, {'every target' if size == 'all' else size + '-table targets'}", "",
                      "| lake | method | " + " | ".join(head) + " |", "|" + "---|" * (len(head) + 2)]
            table: dict[str, dict[str, list]] = {}
            lakes = [lake for lake in LAKES if scored[lake][label]]
            for lake in lakes:
                for name, per_q in scored[lake][label].items():
                    vals = {k: means(per_q, size, k) for k in keys}
                    n = len(vals["R"])
                    cells = [100 * v.mean() for v in vals.values()]
                    extra = ([float(mean(s["sets"] for s in per_q.values())), float(mean(s["tables"] for s in per_q.values())),
                              float(mean(s["size"] for s in per_q.values() if s["size"] is not None)),
                              sum(s["sets"] == 0 for s in per_q.values())] if size == "all" else [])
                    spans = {f"{k} 95%": [100 * x for x in interval(v, rng)] for k, v in vals.items()}
                    table.setdefault(name, {})[lake] = cells
                    rows.append({"label": label, "size": size, "lake": lake, "method": name, "n": n,
                                 **dict(zip(keys, cells)), **spans,
                                 **dict(zip(("sets", "tables", "set size", "empty"), extra))})
                    lines.append(f"| {P.LAKES[lake]} | {name} | " + " | ".join(f"{c:.1f}" for c in cells)
                                 + "".join(f" | {e:.2f}" if isinstance(e, float) else f" | {e}" for e in extra)
                                 + f" | {n} |")
            for agg in ("mean", "worst"):
                for name, per_lake in table.items():
                    if len(per_lake) < len(lakes):
                        lines.append(f"| {agg} | {name} | ran on {len(per_lake)} of {len(lakes)} lakes |")
                        continue
                    cols = list(zip(*per_lake.values()))
                    cells = [mean(c) if agg == "mean" else min(c) for c in cols]
                    lines.append(f"| {agg} | {name} | " + " | ".join(f"{c:.1f}" for c in cells) + " |")
            lines.append("")
    # paired differences, AMIGO minus each other method, on the main-table scores of each label
    lines += ["## AMIGO minus each method", "",
              "Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of "
              "questions), Holm-corrected p over the comparisons of one lake and label (every method and "
              "score); * when below 0.05.", ""]
    for label in LABEL_NAMES:
        keys = MAIN[label]
        lines += [f"| label | lake | method | {' | '.join(keys)} |", "|---|---|---|" + "---|" * len(keys)]
        for lake in [lake for lake in LAKES if scored[lake][label]]:
            mine = scored[lake][label]
            others = [n for n in mine if n != "AMIGO"]
            tests = [(n, k, paired(means(mine["AMIGO"], "all", k), means(mine[n], "all", k), rng))
                     for n in others for k in keys]
            adjusted = holm([t[2][3] for t in tests])
            cells = {(n, k): f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if a < 0.05 else ''}"
                     for (n, k, (d, lo, hi, _)), a in zip(tests, adjusted)}
            for (n, k, (d, lo, hi, _)), a in zip(tests, adjusted):
                rows.append({"test": True, "label": label, "lake": lake, "method": n, "score": k,
                             "diff": 100 * d, "lo": 100 * lo, "hi": 100 * hi, "p": a})
            for n in others:
                lines.append(f"| {LABEL_NAMES[label]} | {P.LAKES[lake]} | {n} | "
                             + " | ".join(cells[n, k] for k in keys) + " |")
        lines.append("")
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval.md").write_text("\n".join(lines) + "\n")
    (out / "retrieval.json").write_text(json.dumps(rows, indent=1))
    print(f"wrote {out / 'retrieval.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["retrieval"])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    retrieval(args.out)
