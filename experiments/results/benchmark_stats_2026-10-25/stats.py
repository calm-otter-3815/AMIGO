"""Statistics of the benchmark versions used in the paper (gold label and multi-valid label of
BIRD, Spider and MMQA), read from the lakes of the paper run and the labeler's label files,
with the same readers the scoring code uses (paper_results.labels, sqleval.targets). No LLM call.

  .venv/bin/python experiments/results/benchmark_stats_2026-10-25/stats.py

Writes stats.md and stats.json next to this file.
"""

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT))
import eval_lakes  # noqa: E402
import paper_results as P  # noqa: E402
import sqleval  # noqa: E402

NAMES = {"bird_dev": "BIRD", "spider_dev": "Spider", "mmqa": "MMQA"}


def lake_size(lake: str) -> dict:
    conn = sqlite3.connect(ROOT / "lakes" / lake / "layer.sqlite")
    one = lambda q: conn.execute(q).fetchone()[0]  # noqa: E731
    return {"databases": one("SELECT count(*) FROM databases"), "tables": one("SELECT count(*) FROM tables"),
            "columns": one("SELECT count(*) FROM columns")}


def spread(values: list[float]) -> dict:
    return {"mean": mean(values), "median": median(values), "max": max(values), "min": min(values)}


def reachable(answers: list[tuple[str, list[frozenset]]], fits=frozenset.issubset) -> int:
    """The most results of one question that the oracle (one SQL per label table set) can return:
    a maximum matching between results and label table sets (augmenting paths). A label set can
    serve a result when it holds the tables of one of the result's valid queries, as in scoring
    (`fits`: frozenset.__eq__ asks for those tables exactly)."""
    labeled = list(dict.fromkeys(s for _, own in answers for s in own))
    serves = [[s for s in labeled if any(fits(t, s) for t in own)] for _, own in answers]
    owner: dict[frozenset, int] = {}

    def take(i: int, seen: set) -> bool:
        for s in serves[i]:
            if s not in seen:
                seen.add(s)
                if s not in owner or take(owner[s], seen):
                    owner[s] = i
                    return True
        return False

    return sum(take(i, set()) for i in range(len(answers)))


def stats(lake: str) -> dict:
    labels = P.labels(P.NIGHT, lake)
    gold, multi = labels["gold"], labels["multi"]
    rows = {r["id"]: r for r in eval_lakes._lines(P._questions(P.NIGHT, lake))}
    folder = ROOT / "runs" / "labeler" / lake
    stored = {one["id"]: one for one in eval_lakes._lines(folder / "labels.jsonl")}
    # the labeler's own ids differ from the question file's on spider2_lite: match on question_id too
    ids = {q["question_id"]: q["id"] for q in eval_lakes._lines(folder / "questions.jsonl")}
    stored |= {q: stored[ids[r["question_id"]]] for q, r in rows.items() if q not in stored and ids.get(r["question_id"]) in stored}
    targets = sqleval.targets(lake)
    out = {"lake": NAMES[lake], **lake_size(lake), "questions in labeler": len(rows)}
    # gold label: one query per question; questions whose gold SQL SQLite cannot prepare are out
    out["gold"] = {
        "questions (retrieval)": len(gold),
        "questions (SQL)": len(targets["gold"]),
        "tables per query": spread([len(q[0][0]) for q in gold.values()]),
        "share single-table": 100 * sum(len(q[0][0]) == 1 for q in gold.values()) / len(gold),
        "databases per query": spread([len({t.split(".", 1)[0] for t in q[0][0]}) for q in gold.values()]),
    }
    queries = {q: v for q, v in multi.items()}
    sets = {q: list(dict.fromkeys(frozenset(t) for t, _ in v)) for q, v in queries.items()}
    results = {q: len(v) for q, v in targets["multi"].items()}
    gold_db = {q: {t.split(".", 1)[0] for t in gold[q][0][0]} for q in queries if q in gold}
    other_db = sum(any({t.split(".", 1)[0] for t in s} - gold_db.get(q, set()) for s in sets[q]) for q in queries)
    out["multi"] = {
        "questions (retrieval)": len(queries),
        "questions (SQL)": len(targets["multi"]),
        "valid queries per question": spread([len(v) for v in queries.values()]),
        "share with 2+ valid queries": 100 * sum(len(v) > 1 for v in queries.values()) / len(queries),
        "table sets per question": spread([len(s) for s in sets.values()]),
        "share with 2+ table sets": 100 * sum(len(s) > 1 for s in sets.values()) / len(sets),
        "tables per valid query": spread([len(t) for v in queries.values() for t, _ in v]),
        "tables per table set": spread([len(t) for s in sets.values() for t in s]),
        "results per question (SQL questions)": spread(list(results.values())),
        "share with 2+ results (SQL questions)": 100 * sum(n > 1 for n in results.values()) / len(results),
        "results, total (SQL questions)": sum(results.values()),
        "share with a table set in another database": 100 * other_db / len(queries),
        "results out of reach of the oracle (one SQL per label table set)": sum(len(v) - reachable(v) for v in targets["multi"].values()),
    }
    out["multi"]["share of results out of reach of the oracle"] = (
        100 * out["multi"]["results out of reach of the oracle (one SQL per label table set)"] / sum(results.values()))
    # the labeler's own record of each question: alternatives judged, kinds, outcomes, checks
    mine = [stored[q] for q in rows if q in stored]
    accepted = [a for x in mine for a in x["accepted"]]
    checks = Counter()
    for x in mine:
        checks.update(x["checks"])
    out["labeler"] = {
        "labels": len(mine),
        "gold status": dict(Counter(x["gold"]["status"] for x in mine)),
        "accepted alternatives": len(accepted),
        "accepted per question": len(accepted) / len(mine),
        "kind": dict(Counter(a["kind"] for a in accepted)),
        "rewritten by": dict(Counter(a["by"] for a in accepted)),
        "outcome": dict(Counter(a["answer"] for a in accepted)),
        "checks": dict(checks),
        "distinct results in the gold database (2+)": 100 * sum(x["ambiguity"]["own_database"] >= 2 for x in mine) / len(mine),
        "distinct results in the lake (2+)": 100 * sum(x["ambiguity"]["lake"] >= 2 for x in mine) / len(mine),
        "underspecified: items not asked": 100 * sum(bool(x["underspecified"]["not_asked"]) for x in mine) / len(mine),
        "underspecified: note only": 100 * sum(bool(x["underspecified"]["note_only"]) for x in mine) / len(mine),
        "underspecified: value form": 100 * sum(bool(x["underspecified"]["hidden_value_form"]) for x in mine) / len(mine),
        "underspecified: computation": 100 * sum(bool(x["underspecified"]["computation"]) for x in mine) / len(mine),
    }
    return out


def fmt(x) -> str:
    if isinstance(x, float):
        return f"{x:.2f}"
    if isinstance(x, dict):
        return ", ".join(f"{k} {fmt(v)}" for k, v in x.items())
    return str(x)


def main() -> None:
    got = [stats(lake) for lake in P.THREE]
    (HERE / "stats.json").write_text(json.dumps(got, indent=1))
    lines = ["# Benchmark statistics (gold label and multi-valid label)", "",
             "From runs/paper_2026-10-20/lakes/<lake>/layer.sqlite and runs/labeler/<lake>/labels.jsonl, read with "
             "paper_results.labels (stage 1 view: every valid query, queries with the same tables and columns once) "
             "and sqleval.targets (stage 2 view: distinct non-empty results). No LLM call.", ""]
    for one in got:
        lines.append(f"## {one['lake']}")
        lines.append("")
        for key, value in one.items():
            if isinstance(value, dict) and key in ("gold", "multi", "labeler"):
                lines.append(f"### {key}")
                lines += [f"- {k}: {fmt(v)}" for k, v in value.items()]
            elif key != "lake":
                lines.append(f"- {key}: {fmt(value)}")
        lines.append("")
    (HERE / "stats.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
