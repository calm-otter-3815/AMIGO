"""Extra tables for the paper, scored by stage 1 of docs/eval_protocol.md with the protocol's
own functions (experiments/protocol.py), on outputs that already exist. No method is run
again and no LLM call is made.

  .venv/bin/python experiments/results/paper_extra_2026-10-25/rescore.py

Writes extra.md and extra.json next to this file:
  1. ablations: the join-choice run's rows (runs/joinchoice_2026-10-24) and the ablations of
     the 2026-10-20 paper run (runs/paper_2026-10-20), with AMIGO minus each row (paired
     bootstrap, Holm), the protocol's way;
  2. every baseline at every k of the 2026-10-20 run;
  3. the multi-valid label on its ambiguous questions only (two or more retrieval targets);
  4. pooled P on the gold label (a lower bound: the gold label is incomplete);
  5. the run-to-run check: the 150 BIRD questions run again with an empty cache (N1);
  6. time per question on an idle GPU (30 timed questions per lake) and LLM calls per question;
  7. stage 1 on the questions that stage 2 keeps (the protocol's exclusions), against all questions;
  8. the cost of building each lake's layer, summed over the steps of eval_2026-10-20/build.csv.
"""

import json
import pickle
import statistics
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402
import sqleval  # noqa: E402

NIGHT, JOINS = P.NIGHT, R.JOINCHOICE
NEW = JOINS  # every AMIGO run of 2026-11-08; baselines and labels stay on NIGHT
NAMES = {"bird_dev": "BIRD", "spider_dev": "Spider", "mmqa": "MMQA"}
LABEL = {"gold": "gold label", "multi": "multi-valid label"}

ABLATIONS = {
    "AMIGO (place judge + join choice)": (JOINS, "joinchoice/records_inf.json", False),
    "place judge only (no join choice)": (NEW, "abl_nojudge2/records_inf.json", False),
    "place judge + whole judge (AMIGO-WJ)": (NEW, "amigo/records_inf.json", False),
    "no judge at all": (NEW, "abl_nojudge/records_inf.json", False),
}
OLDER = {
    "AMIGO-WJ (place judge + whole judge)": (NEW, "amigo/records_inf.json", False),
    "  without the relaxed fallback": (NEW, "abl_norelaxed/records_inf.json", False),
    "  without LLM-judged links": (NEW, "abl_nojudgedlinks/records_inf.json", False),
    "  without the place judge (BIRD only)": (NEW, "abl_nojudge1/records_inf.json", False),
}
BASELINES = {f"{name} k{k}": (NIGHT, f"bl_{tag}_k{k}/records.json", False)
             for name, tag in (("Dense", "dense"), ("BM25", "bm25"), ("Hybrid", "hybrid"), ("JAR", "jar"),
                               ("Greedy JAR", "greedy_jar"), ("MURRE", "murre")) for k in (1, 3, 5)}
BASELINES |= {f"CRUSH4SQL {k} tables": (NIGHT, f"bl_crush4sql_t{k}/records.json", False) for k in (1, 3, 5)}
BASELINES |= {"CORE-T": (NIGHT, "bl_core_t/records.json", False),
              "Route+SQL": (NIGHT, "bl_route_sql/records.json", False),
              "Full schema": (NIGHT, "bl_full_schema/records.json", False)}


def scored(methods: dict, lake: str) -> dict:
    """R.score with another set of rows: {label: {method: {question: R.question()}}}."""
    saved = R.METHODS
    R.METHODS = methods
    try:
        return R.score(lake)
    finally:
        R.METHODS = saved


def row(per_q: dict, ids=None) -> dict:
    """Mean of every score of R.question (all targets), sets, tables, empty and n over the
    questions `ids` (all)."""
    one = [s for q, s in per_q.items() if ids is None or q in ids]
    out = {k: 100 * statistics.fmean(s["all"][k] for s in one) for k in one[0]["all"]}
    sized = [s["size"] for s in one if s["size"] is not None]
    out |= {"sets": statistics.fmean(s["sets"] for s in one), "tables": statistics.fmean(s["tables"] for s in one),
            "size": statistics.fmean(sized) if sized else 0.0,
            "empty": sum(s["sets"] == 0 for s in one), "n": len(one)}
    return out


def table(title: str, head: list[str], rows: list[list]) -> list[str]:
    """Scores and seconds with one decimal; counts of sets and tables per question with two."""
    def cell(x, name):
        if not isinstance(x, float):
            return str(x)
        return f"{x:.2f}" if name in ("sets", "tables") else f"{x:.1f}"
    return [f"## {title}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head),
            *("| " + " | ".join(cell(x, h) for x, h in zip(r, head)) + " |" for r in rows), ""]


def mean_worst(rows: list[list], first: int, count: int = 3) -> list[list]:
    """Mean and worst rows over the lakes of `rows` ([lake, method, numbers...]) per method, over
    the `count` numbers from position `first`."""
    out = []
    methods = list(dict.fromkeys(r[1] for r in rows))
    for kind in ("mean", "worst"):
        for m in methods:
            mine = [r for r in rows if r[1] == m]
            if len(mine) < 3:
                out.append([kind, m, f"ran on {len(mine)} of 3 lakes"])
                continue
            nums = [[r[i] for r in mine] for i in range(first, first + count)]
            out.append([kind, m] + [statistics.fmean(v) if kind == "mean" else min(v) for v in nums])
    return out


def ablations(out: dict, lines: list[str]) -> None:
    rng = np.random.default_rng(R.SEED)
    for block, methods in (("Ablations of AMIGO (join-choice run)", ABLATIONS),
                           ("Ablations of the AMIGO-WJ (with the whole judge)", OLDER)):
        got = {lake: scored(methods, lake) for lake in P.THREE}
        for label in LABEL:
            rows, diffs = [], []
            for lake in P.THREE:
                base = next(iter(methods))
                for m in methods:
                    if m not in got[lake][label]:
                        continue
                    r = row(got[lake][label][m])
                    out.setdefault("ablations", []).append({"block": block, "label": label, "lake": lake, "method": m, **r})
                    rows.append([NAMES[lake], m, *(r[k] for k in R.MAIN[label]), r["sets"], r["tables"], r["empty"], r["n"]])
                ps, found = [], []
                for m in methods:
                    if m == base or m not in got[lake][label]:
                        continue
                    for key in R.MAIN[label]:
                        a = R.means(got[lake][label][base], "all", key)
                        b = R.means(got[lake][label][m], "all", key)
                        d, lo, hi, p = R.paired(100 * a, 100 * b, rng)
                        found.append((m, key, d, lo, hi))
                        ps.append(p)
                for (m, key, d, lo, hi), p in zip(found, R.holm(ps)):
                    diffs.append([NAMES[lake], m, key, f"{d:+.1f} [{lo:+.1f}, {hi:+.1f}]" + ("*" if p < 0.05 else "")])
                    out.setdefault("ablation_diffs", []).append({"block": block, "label": label, "lake": lake, "method": m,
                                                                 "metric": key, "diff": d, "low": lo, "high": hi, "p_holm": p})
            head = ["lake", "method", *R.MAIN[label]]
            lines += table(f"{block}, {LABEL[label]}", head + ["sets", "tables", "empty", "n"],
                           rows + mean_worst(rows, 2, len(head) - 2))
            lines += table(f"{block}, {LABEL[label]}: first row minus each other row (points, 95% interval, Holm)",
                           ["lake", "method", "metric", "difference"], diffs)


def every_k(out: dict, lines: list[str]) -> None:
    got = {lake: scored(BASELINES, lake) for lake in P.THREE}
    for label in LABEL:
        rows = []
        for lake in P.THREE:
            for m in BASELINES:
                if m in got[lake][label]:
                    r = row(got[lake][label][m])
                    out.setdefault("every_k", []).append({"label": label, "lake": lake, "method": m, **r})
                    rows.append([NAMES[lake], m, *(r[k] for k in R.MAIN[label]), r["tables"], r["empty"], r["n"]])
        lines += table(f"Every baseline at every k, {LABEL[label]}",
                       ["lake", "method", *R.MAIN[label], "tables", "empty", "n"], rows + mean_worst(rows, 2, len(R.MAIN[label])))


def ambiguous_and_pooled(out: dict, lines: list[str]) -> None:
    rows, pooled = [], []
    for lake in P.THREE:
        labels = P.labels(NIGHT, lake)
        amb = {q for q, v in labels["multi"].items() if len(R.targets_of(v)) > 1}
        got = R.score(lake)
        for m, per_q in got["multi"].items():
            r = row(per_q, amb)
            out.setdefault("ambiguous", []).append({"lake": lake, "method": m, **r})
            rows.append([NAMES[lake], m, *(r[k] for k in R.MAIN["multi"]), r["sets"], r["tables"], r["n"]])
        for name, (night, file, first) in R.METHODS.items():
            path = night / lake / file
            if not path.exists():
                continue
            records = json.loads(path.read_text())
            values = [R.question(R.targets_of(qs), R.returned(records.get(q), first), True)["all"]["pooled P"]
                      for q, qs in labels["gold"].items()]
            p = 100 * statistics.fmean(values)
            out.setdefault("pooled_gold", []).append({"lake": lake, "method": name, "pooled P": p, "n": len(values)})
            pooled.append([NAMES[lake], name, p, len(values)])
    lines += table("Multi-valid label, ambiguous questions only (two or more retrieval targets)",
                   ["lake", "method", *R.MAIN["multi"], "sets", "tables", "n"], rows + mean_worst(rows, 2, len(R.MAIN["multi"])))
    lines += table("Pooled P on the gold label (a lower bound)", ["lake", "method", "pooled P", "n"], pooled)


def noise(out: dict, lines: list[str]) -> None:
    lake = "bird_dev"
    labels = P.labels(NIGHT, lake)
    ids = list(json.loads((NEW / lake / "noise" / "amigo" / "records_inf.json").read_text()))
    methods = {"AMIGO-WJ, first run": (NEW, "amigo/records_inf.json", False),
               "AMIGO-WJ, second run (empty cache)": (NEW, "noise/amigo/records_inf.json", False)}
    got = scored(methods, lake)
    rows = []
    for label in LABEL:
        for m in methods:
            r = row(got[label][m], set(ids))
            out.setdefault("noise", []).append({"label": label, "method": m, **r})
            rows.append([LABEL[label], m, *(r[k] for k in R.MAIN[label]), r["sets"], r["tables"], r["n"]])
    first = json.loads((NEW / lake / "amigo" / "records_inf.json").read_text())
    second = json.loads((NEW / lake / "noise" / "amigo" / "records_inf.json").read_text())
    same = sum(R.returned(first.get(q), False) == R.returned(second.get(q), False) for q in ids)
    same_sets = sum(set(R.returned(first.get(q), False)) == set(R.returned(second.get(q), False)) for q in ids)
    out["noise_same"] = {"questions": len(ids), "same table sets in the same order": same, "same table sets": same_sets}
    lines += table("Run-to-run check, 150 BIRD questions (gold: R, CR, P, CR=; multi-valid: IR, ICR, IP, IR=, ICR=, IP=)",
                   ["label", "run", "scores", "sets", "tables", "n"],
                   [[r[0], r[1], " / ".join(f"{x:.1f}" for x in r[2:-3]), *r[-3:]] for r in rows])
    lines += [f"Same table sets in the same order: {same} of {len(ids)}; same table sets in any order: {same_sets} of {len(ids)}.", ""]
    del labels


def cost(out: dict, lines: list[str]) -> None:
    rows = []
    for lake in P.THREE:
        # timed chain of 2026-11-11 (timing.sh): split, then AMIGO with the join choice, one at a time
        folder = JOINS / "timing" / lake
        ids = [r["id"] for r in P._lines(folder / "questions.jsonl")][P.WARM:]
        split = json.loads((folder / "split_medium.json").read_text())
        secs = {}
        for q in ids:
            path = folder / "joinchoice_medium" / f"{q}.amigo.pkl"
            # our own run outputs
            got = pickle.loads(path.read_bytes()) if path.exists() else {"error": "missing"}
            if not got.get("error") and "seconds" in split.get(q, {}):
                secs[q] = {"llm split": split[q]["seconds"], **got["seconds"],
                           "total": got["seconds"]["total"] + split[q]["seconds"]}
        through = [s["total"] - s.get("llm judge wholes", 0.0) for s in secs.values()]
        steps = {k: statistics.fmean(s.get(k, 0.0) for s in secs.values())
                 for k in ("llm split", "lookups", "places", "llm judge places", "search", "llm judge joins",
                           "llm judge wholes")}
        # LLM calls per question of the default AMIGO over the whole run: one split, the place judge
        # calls of the 2026-11-08 run (re-asks included), the join choice calls of the join-choice run
        places = [one for one in P._lines(NEW / lake / "amigo" / "judge.jsonl") if one.get("label", "").startswith("judge places")]
        joins = P._lines(JOINS / lake / "joinchoice" / "judge.jsonl")
        n = len(json.loads((JOINS / lake / "joinchoice" / "records_inf.json").read_text()))
        asked = len({one["question"] for one in joins})
        r = {"lake": lake, "timed": len(secs), "total mean": statistics.fmean(through),
             "total median": statistics.median(through), **{f"{k} mean": v for k, v in steps.items()},
             "questions": n, "place judge calls": len(places), "join choice calls": len(joins),
             "questions with a join choice call": asked,
             "LLM calls per question": 1 + (len(places) + len(joins)) / n,
             "place judge output tokens per question": sum(o["usage"]["output_tokens"] for o in places if o.get("usage")) / n,
             "join choice output tokens per question": sum(o["usage"]["output_tokens"] for o in joins if o.get("usage")) / n}
        out.setdefault("cost", []).append(r)
        rows.append([NAMES[lake], r["timed"], steps["llm split"], steps["lookups"], steps["llm judge places"], steps["search"],
                     steps["llm judge joins"],
                     r["total mean"], r["total median"], n, asked, r["LLM calls per question"]])
    lines += table("Time per question (idle GPU) and LLM calls per question",
                   ["lake", "timed", "split s", "lookups s", "place judge s", "search s", "join choice s", "total mean s",
                    "total median s", "questions", "with a join choice call", "LLM calls per question"], rows)


def subset(out: dict, lines: list[str]) -> None:
    """Stage 1 R, CR, P of every protocol row on all questions and on the questions stage 2
    scores (sqleval.targets), per lake and label, and the largest change of CR."""
    rows, moved = [], 0.0
    for lake in P.THREE:
        kept = sqleval.targets(lake)
        got = R.score(lake)
        for label in LABEL:
            for m, per_q in got[label].items():
                a, b = row(per_q), row(per_q, set(kept[label]))
                moved = max(moved, abs(a["CR"] - b["CR"]))
                out.setdefault("subset", []).append({"lake": lake, "label": label, "method": m, "all": a, "stage 2": b})
                rows.append([NAMES[lake], LABEL[label], m, a["R"], b["R"], a["CR"], b["CR"], a["P"], b["P"], a["n"], b["n"]])
    out["subset_largest_CR_change"] = moved
    lines += table("Stage 1 on all questions and on the questions stage 2 keeps",
                   ["lake", "label", "method", "R all", "R kept", "CR all", "CR kept", "P all", "P kept", "n all", "n kept"], rows)
    lines += [f"Largest change of CR: {moved:.2f} points.", ""]


def build(out: dict, lines: list[str]) -> None:
    """Seconds, LLM calls and tokens of AMIGO's layer per lake (the baselines' own preparation
    steps, named "prep ...", left out), and per step."""
    import csv
    rows = list(csv.DictReader(open(ROOT / "experiments" / "results" / "eval_2026-10-20" / "build.csv")))
    table_rows = []
    for lake in P.THREE:
        mine = [r for r in rows if r["lake"] == lake and not r["step"].startswith("prep ")]
        total = {k: sum(float(r[k]) for r in mine) for k in ("seconds", "llm_calls", "input_tokens", "output_tokens")}
        llm = {r["step"]: int(r["llm_calls"]) for r in mine if int(r["llm_calls"])}
        out.setdefault("build", []).append({"lake": lake, **total, "llm calls by step": llm})
        table_rows.append([NAMES[lake], total["seconds"], total["seconds"] / 60, int(total["llm_calls"]),
                           int(total["input_tokens"]), int(total["output_tokens"]), ", ".join(f"{k} {v}" for k, v in llm.items())])
    lines += table("Building AMIGO's layer (baselines' preparation left out)",
                   ["lake", "seconds", "minutes", "LLM calls", "input tokens", "output tokens", "LLM calls by step"], table_rows)


def main() -> None:
    out, lines = {}, ["# Extra tables for the paper (stage 1 of docs/eval_protocol.md, no LLM call)", "",
                      "Scored with experiments/protocol.py on existing outputs. R, CR, P: per target from the returned set "
                      "with the best recall (then precision), averaged per question, then over questions.", ""]
    ablations(out, lines)
    every_k(out, lines)
    ambiguous_and_pooled(out, lines)
    noise(out, lines)
    cost(out, lines)
    subset(out, lines)
    build(out, lines)
    (HERE / "extra.json").write_text(json.dumps(out, indent=1))
    (HERE / "extra.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
