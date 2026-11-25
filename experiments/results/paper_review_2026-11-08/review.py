"""Answers to the first review round of the paper draft, scored by stage 1 of
docs/eval_protocol.md with the protocol's own functions (experiments/protocol.py), on outputs
that already exist. No method is run again and no LLM call is made; the search alone is run
again, from the stored places and grades, to count how often its caps are reached.

  .venv/bin/python experiments/results/paper_review_2026-10-25/review.py

Writes review.md and review.json next to this file:
  1. AMIGO cut to its first m table sets (m = 1, 2, 3, 5, 10, all), in its own order;
  2. the judges at equal size: each variant cut, per question, to the number of table sets
     AMIGO returns there, against AMIGO (paired bootstrap, Holm);
  3. relaxed candidates in the default AMIGO, and its scores without them;
  4. what the join choice call did, and how often the caps were reached;
  5. the share of candidates that hold a labeled table set, by their cost above the best;
  6. the multi-valid label by kind of alternative, and the share of questions with two or
     more valid queries without copies and without tables that share a name with a table of
     the original query;
  7. the MMQA database as released: declared foreign keys, and tables that share a base name;
  8. output tokens per question of the place judge and of the join choice;
  9. the 18 EX differences between AMIGO with hints and AMIGO, from the three writers' files;
 10. the main writer's failed queries and the questions result P is computed over.
Added for the second review round:
 11. each labeled table set that AMIGO's output does not hold, by the first step that lost it,
     and the share of the labeled tables that are among the places listed for some part;
 12. AMIGO's sets on questions with one and with several table-set targets, the sets left when
     tables that share a base name are taken as one, and AMIGO against each method on the
     ambiguous questions (paired bootstrap, Holm);
 13. the place-judge-only search run again with a cap of 25 and of 100 candidates;
 14. how often the labeler's judge and AMIGO's place judge agree on the columns and tables
     that both saw for the same question;
 15. the main methods against the multi-valid label without copies and same-name alternatives;
 16. a one-to-one score: each returned table set stands for at most one labeled table set;
 17. the scores of the first hint prompt, replaced during development, copied from git history.
Added for the third review round:
 18. AMIGO without relaxed candidates, without the candidates the join choice judged no, and
     without either;
 19. the joins of the reference queries that the link graph holds, and the links that the
     declared-foreign-key rule drops;
 20. how well "AMIGO returns two or more table sets" finds the questions whose multi-valid
     label has two or more table sets;
 21. how many of the labeler's options were rejected after one vote;
 22. the alternative queries whose aggregates, grouping, order and limit keywords are those of
     the original query;
 23. the label of the worked example of the benchmark section;
 24. output tokens and GPU-hour shares of the scored runs, and AMIGO's logged place judge and
     join choice replies;
 25. Spider's questions with a labeled table set in another database, by development or
     training database;
 26. every method on the alternatives only: the multi-valid table-set targets other than the
     original query's table set;
 27. stage 2 with AMIGO cut to its first m table sets, from the queries already written, and
     each cut against CORE-T;
 28. the links of the "by few values" rule, recomputed without an LLM call, and how many of
     them weigh enough to be an edge of the link graph;
 29. AMIGO's table sets in its cost order against the same sets in random order and fewest tables
     first, cut to the first 1, 2 and 3 sets, with tests;
 30. the candidates of each cost gap whose table set is exactly a labeled table set;
 31. the parts that relaxed candidates leave out: whether the place judge said yes to any place
     of them, and whether they carry a value;
 32. AMIGO's precision per target when the matched set is the first set in its order with the
     highest recall, instead of the one with the highest precision among them;
 33. result precision of every method of the main writer against the single-valid label too;
 34. Dense top-k tables grouped by database, one table set per database (a baseline that
     returns several table sets, built without an LLM call);
 35. execution accuracy of the main writer when the column order of a result is ignored: every
     saved query that returned rows, and one query of each labeled result, run again in SQLite;
 36. the means over the three benchmarks tested: AMIGO and AMIGO top-1 minus CORE-T, resampling
     the questions of each benchmark apart (stratified paired bootstrap, Holm per label);
 37. result precision with each failed query counted as a wrong result;
 38. EX of the found targets by how many extra tables the smallest returned set that holds them has;
 39. the place-judge-only search run again from the stored places and grades with the edge threshold
     at 1/3 and 2/3, and with 20 columns and 5 tables listed per part;
 40. the results out of the Oracle's reach when a labeled table set serves a result only when it
     equals the tables of one of its reference queries (the written protocol's counts), and when it
     contains them (the scoring rule, as in stats.md);
 41. the multi-valid table-set targets that only alternatives found by the labeler's value signal alone
     give (no gold query and no other alternative reads the same tables);
 42. input and output tokens per question of the place judge, the join choice, CORE-T, Route+SQL and
     Full schema, from the logs of the scored runs (reused replies log no tokens);
 43. stage 2 on the questions whose candidates are all relaxed: execution accuracy of AMIGO and of CORE-T
     on them (main writer, queries already written, no LLM call; not tested);
Added for the seventh review round:
 44. output size as sets, distinct tables and tables with repetition, and AMIGO cut per question to
     CORE-T's tables, and the place-judge-only run, each against CORE-T (R, CR, P, set F1);
 45. MMQA with the tables that share a base name taken as one in outputs and labels;
 46. the link rules run again on BIRD and Spider with the declared keys hidden, against those keys;
 47. the place-judge and join-choice prompts cut in two, counted from the run logs;
 48. 95% intervals of the per-version means of R, CR and P;
 49. the place judge replaced by a cut-off on the place cost, as many places per part as it kept, in the
     place-judge-only search run again from the stored places (no LLM call);
 50. the same search with the value term removed from every place cost, grades kept (no LLM call);
 51. the inferred links of each built layer by the kind of their column, and those that are edges;
 the value_only step also gives the complete recall of AMIGO and CORE-T on the value-only targets;
 the judges step also gives Cohen's kappa and the agreement on yes answers, and the kinds
 step the share of questions with two or more valid queries when the alternatives that
 return the same rows as the original query are left out.
"""

import csv
import json
import logging
import pickle
import re
import statistics
import subprocess
import sys
from collections import Counter
from contextlib import closing
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT))
import eval_lakes  # noqa: E402
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402
from amigo import candidates, config, index, judge, layer, links, solve  # noqa: E402
from amigo.probe import Probe  # noqa: E402

NIGHT, JOINS = P.NIGHT, R.JOINCHOICE
NEW = JOINS  # every AMIGO run of 2026-11-08; baselines and labels stay on NIGHT
NAMES = {"bird_dev": "BIRD", "spider_dev": "Spider", "mmqa": "MMQA"}
LABEL = {"gold": "gold label", "multi": "multi-valid label"}
AMIGO = JOINS / "{lake}" / "joinchoice"
CUTS = (1, 2, 3, 5, 10, None)


def records(path: Path) -> dict:
    return json.loads(path.read_text())


def pickles(folder: Path, ids) -> dict:
    return {q: pickle.loads((folder / f"{q}.amigo.pkl").read_bytes()) for q in ids
            if (folder / f"{q}.amigo.pkl").exists()}


def mean_row(per_q: list[dict]) -> dict:
    out = {k: 100 * statistics.fmean(s["all"][k] for s in per_q) for k in per_q[0]["all"]}
    sized = [s["size"] for s in per_q if s["size"] is not None]  # mean set size, questions with a set
    out |= {"sets": statistics.fmean(s["sets"] for s in per_q), "tables": statistics.fmean(s["tables"] for s in per_q),
            "size": statistics.fmean(sized) if sized else 0.0, "n": len(per_q)}
    return out


def scored(labels: dict, sets_of) -> dict:
    """{question: R.question()} with pooled P on both labels."""
    return {q: R.question(R.targets_of(queries), sets_of(q), True) for q, queries in labels.items()}


def table(title: str, head: list[str], rows: list[list]) -> list[str]:
    """Scores with one decimal; counts of sets and tables per question with two."""
    def cell(x, name):
        if not isinstance(x, float):
            return str(x)
        return f"{x:.2f}" if "sets" in name or "tables" in name or name == "size" else f"{x:.1f}"
    return [f"## {title}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head),
            *("| " + " | ".join(cell(x, h) for x, h in zip(r, head)) + " |" for r in rows), ""]


def mean_worst(rows: list[list], first: int, keys: int, by: int = 1, worst_low: tuple = ()) -> list[list]:
    """Mean and worst rows over the lakes (column 0) per method (column `by`): the worst is
    the lowest value for scores, the highest for the columns in `worst_low` (counts)."""
    out = []
    methods = list(dict.fromkeys(tuple(r[1:first]) for r in rows))
    for kind in ("mean", "worst"):
        for m in methods:
            mine = [r for r in rows if tuple(r[1:first]) == m]
            vals = []
            for i in range(first, first + keys):
                xs = [r[i] for r in mine]
                vals.append(statistics.fmean(xs) if kind == "mean" else (max(xs) if i in worst_low else min(xs)))
            out.append([kind, *m, *vals])
    return out


def top_m(out: dict, lines: list[str]) -> None:
    for label in LABEL:
        rows = []
        for lake in P.THREE:
            labels = P.labels(NIGHT, lake)[label]
            got = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
            for m in CUTS:
                per_q = scored(labels, lambda q: R.returned(got.get(q), False)[:m] if m else R.returned(got.get(q), False))
                r = mean_row(list(per_q.values()))
                name = f"first {m}" if m else "all (AMIGO)"
                out.setdefault("top_m", []).append({"label": label, "lake": lake, "cut": m, **r})
                rows.append([NAMES[lake], name, *(r[k] for k in R.MAIN[label]), r["sets"], r["size"]])
        n = len(R.MAIN[label])
        lines += table(f"AMIGO cut to its first m table sets, {LABEL[label]}",
                       ["lake", "cut", *R.MAIN[label], "sets", "size"],
                       rows + mean_worst(rows, 2, n + 2, worst_low=(n + 2, n + 3)))


VARIANTS = {
    "no judge at all": NEW / "{lake}" / "abl_nojudge",
    "place judge only (no join choice)": NEW / "{lake}" / "abl_nojudge2",
}


def equal_size(out: dict, lines: list[str]) -> None:
    """Tests every main score but the first (R or IR, not tested), Holm over the variants x
    scores of one lake and label."""
    rng = np.random.default_rng(R.SEED)
    rows = {label: [] for label in LABEL}
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        size = {q: len(R.returned(r, False)) for q, r in mine.items()}
        for label in LABEL:
            keys = R.MAIN[label]
            labels = P.labels(NIGHT, lake)[label]
            base = scored(labels, lambda q: R.returned(mine.get(q), False))
            tests, kept = [], []
            for name, folder in VARIANTS.items():
                theirs = records(Path(str(folder).format(lake=lake)) / "records_inf.json")
                cut = scored(labels, lambda q: R.returned(theirs.get(q), False)[:size.get(q, 0)])
                full = scored(labels, lambda q: R.returned(theirs.get(q), False))
                for key in keys[1:]:
                    a = np.array([base[q]["all"][key] for q in labels])
                    b = np.array([cut[q]["all"][key] for q in labels])
                    tests.append(R.paired(a, b, rng))
                kept.append((name, mean_row(list(cut.values())), mean_row(list(full.values()))))
            ps = R.holm([t[3] for t in tests])
            amigo = mean_row(list(base.values()))
            n = len(keys) - 1
            for i, (name, cut_r, full_r) in enumerate(kept):
                one = {"lake": lake, "label": label, "variant": name, "AMIGO": amigo, "cut": cut_r, "full": full_r}
                cells = []
                for j, key in enumerate(keys[1:]):
                    t, pv = tests[n * i + j], ps[n * i + j]
                    one[f"AMIGO - cut, {key}"], one[f"Holm p, {key}"] = t[:3], pv
                    cells += [100 * t[0], f"{pv:.4f}"]
                out.setdefault("equal_size", []).append(one)
                rows[label].append([NAMES[lake], name, *(full_r[k] for k in keys), full_r["sets"],
                                    *(cut_r[k] for k in keys), cut_r["sets"], *(amigo[k] for k in keys), amigo["sets"],
                                    *cells])
    for label in LABEL:
        keys = R.MAIN[label]
        lines += table(f"Judges at equal size: each variant cut per question to AMIGO's number of table sets, {LABEL[label]}",
                       ["lake", "variant", *(f"{k} full" for k in keys), "sets full", *(f"{k} cut" for k in keys),
                        "sets cut", *(f"{k} AMIGO" for k in keys), "sets AMIGO",
                        *(x for k in keys[1:] for x in (f"AMIGO - cut {k}", f"Holm p {k}"))], rows[label])
    for label in LABEL:
        summary = []
        for name in ["AMIGO", *VARIANTS]:
            got = [one for one in out["equal_size"] if one["label"] == label and one["variant"] == (name if name != "AMIGO" else next(iter(VARIANTS)))]
            scores = [one["AMIGO"] if name == "AMIGO" else one["cut"] for one in got]
            for kind in ("mean", "worst"):
                pick = statistics.fmean if kind == "mean" else min
                summary.append([kind, name if name == "AMIGO" else name + ", cut", *(pick(x[k] for x in scores) for k in R.MAIN[label])])
        lines += table(f"Judges at equal size, mean and worst over the three benchmarks, {LABEL[label]} "
                       f"({R.MAIN[label][0]} not tested)", ["over", "variant", *R.MAIN[label]], summary)


def relaxed(out: dict, lines: list[str]) -> None:
    rows = {label: [] for label in LABEL}
    for lake in P.THREE:
        folder = Path(str(AMIGO).format(lake=lake))
        mine = records(folder / "records_inf.json")
        saved = pickles(folder, mine)
        some = {q for q, s in saved.items() if any(c.left_out for c in s["found"])}
        only = {q for q, s in saved.items() if s["found"] and all(c.left_out for c in s["found"])}
        mismatch = sum(len(s["found"]) != len(mine[q]["interpretations"]) for q, s in saved.items())

        def without(q):
            s = saved.get(q)
            if s is None:
                return R.returned(mine.get(q), False)
            keep = [o for o, c in zip(mine[q]["interpretations"], s["found"]) if not c.left_out]
            return R.returned({"interpretations": keep}, False)

        for label in LABEL:
            labels = P.labels(NIGHT, lake)[label]
            a = mean_row(list(scored(labels, lambda q: R.returned(mine.get(q), False)).values()))
            b = mean_row(list(scored(labels, without).values()))
            hit = sum(1 for q in labels if q in only
                      and R.question(R.targets_of(labels[q]), R.returned(mine.get(q), False), False)["all"]["CR"] > 0)
            one = {"lake": lake, "label": label, "questions": len(labels), "with relaxed candidates": len(some & set(labels)),
                   "only relaxed candidates": len(only & set(labels)), "only relaxed, some target found": hit,
                   "AMIGO": a, "without relaxed": b, "records and pickles of different length": mismatch}
            out.setdefault("relaxed", []).append(one)
            rows[label].append([NAMES[lake], len(labels), len(some & set(labels)), len(only & set(labels)), hit,
                                *(x for k in R.MAIN[label] for x in (a[k], b[k])), mismatch])
    for label in LABEL:
        lines += table(f"Relaxed candidates in AMIGO (place judge + join choice), {LABEL[label]}",
                       ["lake", "questions", "with relaxed", "only relaxed", "only relaxed, a target found",
                        *(x for k in R.MAIN[label] for x in (k, f"{k} without")), "length mismatch"], rows[label])


class _Count(logging.Handler):
    def __init__(self):
        super().__init__()
        self.hits = 0

    def emit(self, record):
        if "search cap reached" in record.getMessage():
            self.hits += 1


def caps(out: dict, lines: list[str]) -> None:
    """The join choice's own counts (judge.chosen), and the search run again from the stored
    places and grades of the place-judge run, with the 3000-solve cap counted."""
    counter = _Count()
    logging.getLogger("amigo.candidates").addHandler(counter)
    logging.getLogger("amigo.candidates").setLevel(logging.INFO)
    for lake in P.THREE:
        folder = Path(str(AMIGO).format(lake=lake))
        mine = records(folder / "records_inf.json")
        saved = pickles(folder, mine)
        infos = [s["joins"] for s in saved.values() if s.get("joins")]
        asked = sum(i["joins"] > 0 for i in infos)
        source = pickles(NEW / lake / "abl_nojudge2", mine)
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        capped_q, same, parts_over = 0, 0, 0
        for q, s in source.items():
            if s.get("error") or not s.get("shown"):
                continue
            parts_over += len(s["entities"]) > 10
            before = counter.hits
            places = judge.graded(s["shown"], s["grades"])
            found = candidates.candidates(probe, graph, s["stage"], judge.MOST, graded=places)
            if not found:
                found = judge.relaxed(probe, graph, s["stage"], places, judge.MOST, None)
            placed = judge.split(found, places)
            capped_q += counter.hits > before
            same += [(c.tables, c.holders, c.edges) for c in placed] == [(c.tables, c.holders, c.edges) for c in s["placed"]]
        searched = [s for s in source.values() if not s.get("error") and s.get("shown")]
        one = {"lake": lake, "questions": len(mine),
               "join choice: questions asked": asked,
               "join choice: joins asked": sum(i["joins"] for i in infos),
               "join choice: lists said no to entirely": sum(i["refused"] for i in infos),
               "join choice: questions with ways past the cap of 50": sum(i["capped"] > 0 for i in infos),
               "join choice: ways past the cap": sum(i["capped"] for i in infos),
               "output: questions with 50 or more candidates": sum(len(r.get("interpretations") or []) >= judge.MOST
                                                                   for r in mine.values()),
               "search: questions run again": len(searched),
               "search: same candidates as stored": same,
               "search: questions with 50 or more candidates (cap of 50)": sum(len(s["placed"]) >= judge.MOST for s in searched),
               "search: questions where the 3000-solve cap was reached": capped_q,
               "questions with more than 10 parts": parts_over}
        out.setdefault("caps", []).append(one)
    lines += _caps_lines(out)


def odds(out: dict, lines: list[str]) -> None:
    bins = [(0.0, 0.0, "best (cost above best 0)"), (0.0, 1.0, "above best by (0, 1] bit"),
            (1.0, 2.0, "by (1, 2] bits"), (2.0, 4.0, "by (2, 4] bits"), (4.0, float("inf"), "by more than 4 bits")]
    rows = []
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        for label in LABEL:
            labels = P.labels(NIGHT, lake)[label]
            count, hold = Counter(), Counter()
            for q, queries in labels.items():
                found = (mine.get(q) or {}).get("interpretations") or []
                if not found or (mine.get(q) or {}).get("error"):
                    continue
                targets = R.targets_of(queries)
                best = min(o["cost"] for o in found)
                for o in found:
                    gap = o["cost"] - best
                    name = next(n for lo, hi, n in bins if (gap <= 1e-9 if hi == 0.0 else lo + 1e-9 < gap <= hi + 1e-9))
                    count[name] += 1
                    hold[name] += any(t <= frozenset(o["tables"]) for t in targets)
            for _, _, name in bins:
                share = 100 * hold[name] / count[name] if count[name] else float("nan")
                out.setdefault("odds", []).append({"lake": lake, "label": label, "bin": name, "candidates": count[name],
                                                   "holding a labeled table set": hold[name], "share": share})
                rows.append([NAMES[lake], LABEL[label], name, count[name], share])
    lines += table("Candidates that hold all tables of a labeled table set, by cost above the best candidate",
                   ["lake", "label", "cost above best", "candidates", "share holding a labeled table set (%)"], rows)


def _base(table: str) -> str:
    """A table's name without its database and without a trailing number (department_3 -> department)."""
    return re.sub(r"_\d+$", "", table.split(".", 1)[1]).lower()


def _kinded(lake: str) -> dict:
    """{question: [(reference query as (tables, columns), kind, named, same)]} for the
    multi-valid label, the original query first: kind is the kind of its replacement, named
    whether its new tables all share a base name with a table of the original query, same
    whether it returns the same rows as the original query."""
    rows_q = eval_lakes._lines(P._questions(NIGHT, lake))
    folder = ROOT / "runs" / "labeler" / lake
    ids = {q["question_id"]: q["id"] for q in eval_lakes._lines(folder / "questions.jsonl")}
    stored = {one["id"]: one for one in eval_lakes._lines(folder / "labels.jsonl")}
    read = eval_lakes.Gold(lake)
    multi = P.labels(NIGHT, lake)["multi"]
    out = {}
    for row in rows_q:
        if row["id"] not in multi:
            continue
        one = stored.get(row["id"]) or stored.get(ids.get(row["question_id"]))
        gold = read(row["db_id"], row["gold_sql"])
        gold_names = {_base(t) for t in gold[0]}
        kind_of = {a["name"]: a["kind"] for a in one["accepted"]}
        queries = [(gold, "original", False, False)]
        for group in one.get("interpretations") or []:
            for q in group:
                if q["name"] != "gold" and q.get("sql"):
                    try:
                        pair = read(q["db"], q["sql"])
                    except Exception:  # noqa: BLE001 (the label's own reader skips these too)
                        continue
                    if all(pair != p for p, *_ in queries):
                        new = set(pair[0]) - set(gold[0])
                        named = bool(new) and all(_base(t) in gold_names for t in new)
                        queries.append((pair, kind_of.get(q["name"], "unknown"), named, q.get("answer") == "same rows"))
        assert len(queries) == len(multi[row["id"]]), row["id"]
        out[row["id"]] = queries
    return out


def kinds(out: dict, lines: list[str]) -> None:
    rows = []
    for lake in P.THREE:
        by_kind, two, two_nocopy, two_noname, two_neither, two_nosame, total = Counter(), 0, 0, 0, 0, 0, 0
        for queries in _kinded(lake).values():
            total += 1
            for _, kind, named, _ in queries[1:]:
                by_kind[kind] += 1
                by_kind["new tables all share a name with an original table"] += named
            two += len(queries) > 1
            two_nocopy += len([x for x in queries if x[1] != "copy"]) > 1
            two_noname += len([x for x in queries if not x[2]]) > 1
            two_neither += len([x for x in queries if x[1] != "copy" and not x[2]]) > 1
            two_nosame += len([x for x in queries if not x[3]]) > 1
        alternatives = sum(v for k, v in by_kind.items() if k != "new tables all share a name with an original table")
        one = {"lake": lake, "questions": total, "alternative queries": alternatives, "alternative queries by kind": dict(by_kind),
               "share with 2+ valid queries": 100 * two / total,
               "share with 2+ valid queries, copies left out": 100 * two_nocopy / total,
               "share with 2+ valid queries, same-name tables left out": 100 * two_noname / total,
               "share with 2+ valid queries, both left out": 100 * two_neither / total,
               "share with 2+ valid queries, same-row alternatives left out": 100 * two_nosame / total}
        out.setdefault("kinds", []).append(one)
        rows.append([NAMES[lake], total, alternatives, ", ".join(f"{k} {v}" for k, v in by_kind.items()),
                     *(f"{one[k]:.2f}" for k in ("share with 2+ valid queries", "share with 2+ valid queries, copies left out",
                                                 "share with 2+ valid queries, same-name tables left out",
                                                 "share with 2+ valid queries, both left out",
                                                 "share with 2+ valid queries, same-row alternatives left out"))])
    lines += table("Multi-valid label: alternative queries by kind, and questions with two or more valid queries",
                   ["lake", "questions", "alternative queries", "by kind", "2+ (%)", "2+ without copies (%)",
                    "2+ without same-name tables (%)", "2+ without either (%)", "2+ without same-row alternatives (%)"], rows)


def mmqa_file(out: dict, lines: list[str]) -> None:
    """The MMQA database as released: its tables, declared foreign keys, and the tables whose
    name is another table's name with a numeric suffix (customers, customers_2, ...)."""
    import sqlite3
    path = ROOT / "benchmarks" / "MMQA" / "databases" / "mmqa" / "mmqa.sqlite"
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    fks = sum(len(conn.execute(f'PRAGMA foreign_key_list("{t}")').fetchall()) for t in tables)
    groups: dict[str, list[str]] = {}
    for t in tables:
        groups.setdefault(re.sub(r"_\d+$", "", t).lower(), []).append(t)
    shared = {k: v for k, v in groups.items() if len(v) > 1}
    biggest = sorted(shared.items(), key=lambda kv: -len(kv[1]))[:5]
    one = {"tables": len(tables), "declared foreign keys": fks, "groups of tables sharing a base name": len(shared),
           "tables in those groups": sum(len(v) for v in shared.values()),
           "largest groups": {k: len(v) for k, v in biggest}}
    out["mmqa_file"] = one
    lines += [f"## MMQA database as released ({path.relative_to(ROOT)})", "",
              *(f"- {k}: {v}" for k, v in one.items()), ""]


def tokens(out: dict, lines: list[str]) -> None:
    """Output tokens per question of the place judge and of the join choice, over all questions,
    from the cost table of paper_extra_2026-11-08 (the join choice was not timed alone)."""
    cost = json.loads((ROOT / "experiments" / "results" / "paper_extra_2026-11-08" / "extra.json").read_text())["cost"]
    rows = []
    for one in cost:
        r = {"lake": one["lake"], "place judge output tokens per question": round(one["place judge output tokens per question"]),
             "join choice output tokens per question": round(one["join choice output tokens per question"])}
        out.setdefault("tokens", []).append(r)
        rows.append([NAMES[one["lake"]], *list(r.values())[1:]])
    lines += table("Output tokens per question over all questions (a measure of the size of each LLM step)",
                   ["lake", "place judge output tokens", "join choice output tokens"], rows)


SQL = ROOT / "experiments" / "results" / "sqleval_2026-11-08"
WRITERS = {"qwen": "Qwen3.8-27B", "granite": "Granite 4.2 8B", "gemma": "Gemma 4 E4B"}


def hints(out: dict, lines: list[str]) -> None:
    """The 18 EX differences of AMIGO with hints minus AMIGO (three writers, three lakes, two
    labels), as each writer's result file prints them; a positive value means hints are higher."""
    rows, higher, starred = [], 0, 0
    for w, writer in WRITERS.items():
        if not (SQL / f"sql_{w}.md").exists():  # a writer not scored yet
            continue
        for line in (SQL / f"sql_{w}.md").read_text().splitlines():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 4 and cells[2] == "AMIGO" and "[" in cells[3]:
                rows.append([writer, cells[0], cells[1], cells[3]])
                higher += cells[3].startswith("+")
                starred += cells[3].startswith("+") and cells[3].endswith("*")
    out["hints"] = {"rows": rows, "hints higher": higher, "hints higher, significant": starred}
    out["hints_minus_plain"] = rows
    lines += table("AMIGO with hints minus AMIGO, EX (from sql_<writer>.md)", ["writer", "label", "lake", "difference"], rows)
    lines += [f"Hints higher in {higher} of {len(rows)}; significant (*) in {starred}.", ""]


def failed(out: dict, lines: list[str]) -> None:
    """Main writer: share of queries that fail, and the questions result P is computed over
    (those where some query of the method gives a result), from sql_qwen.json."""
    rows = []
    got = json.loads((SQL / "sql_qwen.json").read_text())
    for r in got:
        rows.append([NAMES[r["lake"]], LABEL[r["label"]], r["method"], f"{r['failed %']:.1f}%",
                     r.get("result P n", "--"), r["n"]])
    out["failed"] = rows
    lines += table("Main writer: failed queries and questions in result P", ["lake", "label", "method", "failed",
                   "questions in result P", "questions"], rows)


CAUSES = ("found", "empty output", "a table not among the places listed for any part, nor reached by a join",
          "the place judge said no to every place in a table", "only relaxed candidates",
          "no candidate holds all its tables", "dropped by the join choice")


def misses(out: dict, lines: list[str]) -> None:
    """Each labeled table set, by the first step that lost it: AMIGO's output holds it; the
    output is empty; one of its tables is neither a listed place of any part nor a table of
    a candidate before the join choice; the place judge said no to every place of one of its
    tables; the question has only relaxed candidates; no candidate holds all its tables; or a
    candidate before the join choice held it and the join choice dropped it."""
    rows = []
    for lake in P.THREE:
        folder = Path(str(AMIGO).format(lake=lake))
        mine = records(folder / "records_inf.json")
        saved = pickles(folder, mine)
        before = records(NEW / lake / "abl_nojudge2" / "records_inf.json")
        probe = Probe(lake)
        for label in LABEL:
            count, tables, listed = Counter(), 0, 0
            for q, queries in P.labels(NIGHT, lake)[label].items():
                final, pre = R.returned(mine.get(q), False), R.returned(before.get(q), False)
                s = saved.get(q) or {}
                shown = {probe.path("table", h.table) for part in s.get("shown") or [] for h in part}
                kept = ({probe.path("table", h.table) for part in judge.graded(s["shown"], s["grades"]) for h in part}
                        if s.get("shown") else set())
                reached = set().union(*pre)
                relaxed_only = bool(s.get("found")) and all(c.left_out for c in s["found"])
                for t in R.targets_of(queries):
                    tables += len(t)
                    listed += len(t & shown)
                    if any(t <= x for x in final):
                        cause = CAUSES[0]
                    elif not final:
                        cause = CAUSES[1]
                    elif any(t <= x for x in pre):
                        cause = CAUSES[6]
                    elif not t <= shown | reached:
                        cause = CAUSES[2]
                    elif not t <= kept | reached:
                        cause = CAUSES[3]
                    elif relaxed_only:
                        cause = CAUSES[4]
                    else:
                        cause = CAUSES[5]
                    count[cause] += 1
            n = sum(count.values())
            one = {"lake": lake, "label": label, "targets": n, **{c: count[c] for c in CAUSES},
                   "labeled tables": tables, "labeled tables among the listed places": listed}
            out.setdefault("misses", []).append(one)
            rows.append([NAMES[lake], LABEL[label], n, *(f"{count[c]} ({100 * count[c] / n:.1f})" for c in CAUSES),
                         tables, f"{listed} ({100 * listed / tables:.1f})"])
    lines += table("Labeled table sets by the first step that lost them (count, and % of the targets of all questions)",
                   ["lake", "label", "targets", *CAUSES, "labeled tables", "labeled tables among the listed places"], rows)


def _based(t: str) -> str:
    return t.split(".", 1)[0] + "." + _base(t)


def ambiguity(out: dict, lines: list[str]) -> None:
    rows, diffs = [], []
    rng = np.random.default_rng(R.SEED)
    for lake in P.THREE:
        labels = P.labels(NIGHT, lake)["multi"]
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        for group, pick in (("one table-set target", lambda n: n == 1), ("two or more", lambda n: n > 1)):
            ids = [q for q, v in labels.items() if pick(len(R.targets_of(v)))]
            sets = [R.returned(mine.get(q), False) for q in ids]
            merged = [len({frozenset(_based(t) for t in s) for s in x}) for x in sets]
            one = {"lake": lake, "questions": group, "n": len(ids),
                   "AMIGO returns two or more sets (%)": 100 * sum(len(x) >= 2 for x in sets) / len(ids),
                   "sets": statistics.fmean(len(x) for x in sets),
                   "sets, tables sharing a base name taken as one": statistics.fmean(merged)}
            out.setdefault("ambiguity", []).append(one)
            rows.append([NAMES[lake], group, len(ids), one["AMIGO returns two or more sets (%)"], one["sets"],
                         one["sets, tables sharing a base name taken as one"]])
        amb = [q for q, v in labels.items() if len(R.targets_of(v)) > 1]
        got = R.score(lake)["multi"]
        tests = [(m, k, R.paired(np.array([got["AMIGO"][q]["all"][k] for q in amb]),
                                 np.array([got[m][q]["all"][k] for q in amb]), rng))
                 for m in got if m != "AMIGO" for k in R.MAIN["multi"]]
        ps = R.holm([x[2][3] for x in tests])
        cells = {(m, k): f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if a < 0.05 else ''}"
                 for (m, k, (d, lo, hi, _)), a in zip(tests, ps)}
        for m in dict.fromkeys(m for m, _, _ in tests):
            out.setdefault("ambiguous_tests", []).append({"lake": lake, "method": m, **{k: cells[m, k] for k in R.MAIN["multi"]}})
            diffs.append([NAMES[lake], m, *(cells[m, k] for k in R.MAIN["multi"])])
    lines += table("AMIGO's table sets on questions with one and with several table-set targets (multi-valid label)",
                   ["lake", "questions", "n", "AMIGO returns two or more sets (%)", "sets",
                    "sets, tables sharing a base name taken as one"], rows)
    lines += table("Ambiguous questions (multi-valid label, two or more targets): AMIGO minus each method, points, "
                   "95% interval, Holm over the comparisons of one lake; * when below 0.05",
                   ["lake", "method", *R.MAIN["multi"]], diffs)


def cap_sizes(out: dict, lines: list[str]) -> None:
    """The place-judge-only configuration (no join choice), its search run again from the
    stored places and grades with a cap of 25, 50 and 100 candidates. The cap of 50 gives the
    stored candidates back (step caps)."""
    rows = []
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        stored = records(NEW / lake / "abl_nojudge2" / "records_inf.json")
        source = pickles(NEW / lake / "abl_nojudge2", mine)
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        for cap in (25, 50, 100):
            judge.MOST, sets = cap, {}
            try:
                for q, s in source.items():
                    if s.get("error") or not s.get("shown"):
                        continue
                    places = judge.graded(s["shown"], s["grades"])
                    found = candidates.candidates(probe, graph, s["stage"], cap, graded=places)
                    if not found:
                        found = judge.relaxed(probe, graph, s["stage"], places, cap, None)
                    sets[q] = list(dict.fromkeys(frozenset(probe.path("table", t) for t in c.tables)
                                                 for c in judge.split(found, places)))
            finally:
                judge.MOST = 50
            for label in LABEL:
                labels = P.labels(NIGHT, lake)[label]
                r = mean_row(list(scored(labels, lambda q: sets[q] if q in sets else R.returned(stored.get(q), False)).values()))
                out.setdefault("cap_sizes", []).append({"lake": lake, "label": label, "cap": cap, **r})
    lines += _cap_lines(out)


def _cap_lines(out: dict) -> list[str]:
    lines = []
    for label in LABEL:
        keys = R.MAIN[label]
        rows = [[NAMES[o["lake"]], o["cap"], *(o[k] for k in keys), o["sets"], o["size"]]
                for o in out["cap_sizes"] if o["label"] == label]
        lines += table(f"Place judge only (no join choice), search run again with a cap of 25, 50 and 100 candidates, "
                       f"{LABEL[label]}", ["lake", "cap", *keys, "sets", "size"], rows + mean_worst(rows, 2, len(keys)))
    return lines


def judges(out: dict, lines: list[str]) -> None:
    """The labeler's yes or no per option against the place judge's yes or no per place, on
    the columns and tables that both saw for one question. Decoys are left out. The two judge
    different words (an item of the original query, a part of the split), so a column counts
    as yes for a judge when any of its items or parts got a yes."""
    rows = []
    for lake in P.THREE:
        folder = Path(str(AMIGO).format(lake=lake))
        multi = P.labels(NIGHT, lake)["multi"]
        saved = pickles(folder, multi)
        probe = Probe(lake)
        lab = ROOT / "runs" / "labeler" / lake
        ids = {q["question_id"]: q["id"] for q in eval_lakes._lines(lab / "questions.jsonl")}
        stored = {one["id"]: one for one in eval_lakes._lines(lab / "labels.jsonl")}
        pairs, questions = Counter(), 0
        for row in eval_lakes._lines(P._questions(NIGHT, lake)):
            s = saved.get(row["id"])
            one = stored.get(row["id"]) or stored.get(ids.get(row["question_id"]))
            if row["id"] not in multi or not s or not s.get("shown") or not one:
                continue
            theirs = {}
            for item in one.get("judged") or []:
                for o in item.get("options") or []:
                    if not o.get("decoy"):
                        theirs[o["name"]] = theirs.get(o["name"], False) or o.get("verdict") == "yes"
            ours = {}
            for part, grades in zip(s["shown"], s["grades"]):
                for h in part:
                    name = probe.path("column", h.column) if h.column is not None else probe.path("table", h.table)
                    ours[name] = ours.get(name, False) or bool(grades.get((h.table, h.column)))
            both = theirs.keys() & ours.keys()
            questions += bool(both)
            pairs.update((theirs[n], ours[n]) for n in both)
        n = sum(pairs.values())
        a, b, c, d = pairs[True, True], pairs[True, False], pairs[False, True], pairs[False, False]
        chance = ((a + b) * (a + c) + (c + d) * (b + d)) / n ** 2
        kappa = ((a + d) / n - chance) / (1 - chance)
        one = {"lake": lake, "questions with a shared option": questions, "shared options": n,
               "both yes": a, "both no": d, "labeler yes, place judge no": b, "labeler no, place judge yes": c,
               "Cohen's kappa": kappa, "agreement on yes (2a / (2a + b + c))": 2 * a / (2 * a + b + c)}
        out.setdefault("judges", []).append(one)
        rows.append([NAMES[lake], questions, n, pairs[True, True], pairs[False, False], pairs[True, False],
                     pairs[False, True], 100 * (pairs[True, True] + pairs[False, False]) / n,
                     100 * pairs[True, True] / (pairs[True, True] + pairs[True, False]),
                     100 * pairs[True, True] / (pairs[True, True] + pairs[False, True]), f"{kappa:.2f}",
                     100 * one["agreement on yes (2a / (2a + b + c))"]])
    lines += table("The labeler's judge and AMIGO's place judge on the columns and tables both saw for one question",
                   ["lake", "questions with a shared option", "shared options", "both yes", "both no",
                    "labeler yes, place judge no", "labeler no, place judge yes", "agree (%)",
                    "place judge yes among labeler yes (%)", "labeler yes among place judge yes (%)", "Cohen's kappa",
                    "agreement on yes (%)"], rows)


def no_copies(out: dict, lines: list[str]) -> None:
    """The main methods against the multi-valid label without its copies and without the
    alternatives whose new tables all share a base name with a table of the original query."""
    rows = []
    for lake in P.THREE:
        multi = P.labels(NIGHT, lake)["multi"]
        kept = {}
        for q, queries in _kinded(lake).items():
            drop = [pair for pair, kind, named, _ in queries[1:] if kind == "copy" or named]
            assert all(pair in multi[q] for pair in drop), q
            kept[q] = [m for m in multi[q] if m not in drop]
        for name, (night, file, first) in R.METHODS.items():
            path = night / lake / file
            if not path.exists():
                continue
            got = records(path)
            r = mean_row(list(scored(kept, lambda q: R.returned(got.get(q), first)).values()))
            out.setdefault("no_copies", []).append({"lake": lake, "method": name, **r})
            rows.append([NAMES[lake], name, *(r[k] for k in R.MAIN["multi"]), r["sets"], r["size"]])
    full = [r for r in rows if r[1] != "Route+SQL"]
    lines += table("Multi-valid label without copies and without same-name alternatives (stage 1)",
                   ["lake", "method", *R.MAIN["multi"], "sets", "size"],
                   rows + mean_worst(full, 2, len(R.MAIN["multi"])))


def one_to_one(out: dict, lines: list[str]) -> None:
    """Set recall: the share of a question's targets that get a returned set of their own;
    set precision: the share of its returned sets so used (0 with no set); F1 of the two per
    question; each averaged over questions. Then AMIGO minus each method in set F1 (paired
    bootstrap, Holm over the methods of one lake and label)."""
    rng = np.random.default_rng(R.SEED)
    for label in LABEL:
        rows, diffs = [], []
        for lake in P.THREE:
            labels = P.labels(NIGHT, lake)[label]
            per_q = {}
            for name, (night, file, first) in R.METHODS.items():
                path = night / lake / file
                if not path.exists():
                    continue
                got = records(path)
                rec, prec, f1 = [], [], []
                for q, queries in labels.items():
                    targets, sets = R.targets_of(queries), R.returned(got.get(q), first)
                    k = len(R.paired_up(targets, sets))
                    r, p = k / len(targets), (k / len(sets) if sets else 0.0)
                    rec.append(r)
                    prec.append(p)
                    f1.append(2 * r * p / (r + p) if k else 0.0)
                per_q[name] = np.array(f1)
                one = {"set recall": 100 * statistics.fmean(rec), "set precision": 100 * statistics.fmean(prec),
                       "set F1": 100 * statistics.fmean(f1)}
                out.setdefault("one_to_one", []).append({"label": label, "lake": lake, "method": name, **one})
                rows.append([NAMES[lake], name, *one.values()])
            others = [m for m in per_q if m != "AMIGO"]
            tests = [R.paired(per_q["AMIGO"], per_q[m], rng) for m in others]
            for m, (d, lo, hi, _), a in zip(others, tests, R.holm([t[3] for t in tests])):
                cell = f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if a < 0.05 else ''}"
                out.setdefault("one_to_one_tests", []).append({"label": label, "lake": lake, "method": m,
                                                               "AMIGO - method, set F1": cell})
                diffs.append([NAMES[lake], m, cell])
        full = [r for r in rows if r[1] != "Route+SQL"]
        lines += table(f"One returned table set per labeled table set, {LABEL[label]} (stage 1)",
                       ["lake", "method", "set recall", "set precision", "set F1"], rows + mean_worst(full, 2, 3))
        lines += table(f"Set F1, AMIGO minus each method, {LABEL[label]}: points, 95% interval, Holm over the methods "
                       "of one lake; * when below 0.05", ["lake", "method", "AMIGO - method"], diffs)


FIRST_HINTS = "009dcb6"  # the last commit whose sql_qwen.md holds the first hint prompt's scores


def first_hints(out: dict, lines: list[str]) -> None:
    """The first hint prompt (one SQL per interpretation, with its bindings and join links),
    replaced in commit 76f6587: the header and AMIGO with hints rows of sql_qwen.md as of
    commit FIRST_HINTS, copied as they are."""
    text = subprocess.run(["git", "-C", str(ROOT), "show", f"{FIRST_HINTS}:experiments/results/sqleval_2026-10-24/sql_qwen.md"],
                          capture_output=True, text=True, check=True).stdout
    lines += [f"## First hint prompt, main writer (sql_qwen.md at commit {FIRST_HINTS}, AMIGO with hints rows)", ""]
    header = False
    for line in text.splitlines():
        if line.startswith("## "):
            lines.append("### " + line[3:])
            header = True
        elif line.startswith("|") and (header or line.startswith("|---")):
            lines.append(line)
            header = False
        elif "| AMIGO with hints |" in line:
            lines.append(line)
            out.setdefault("first_hints", []).append(line)
    lines.append("")


def fallbacks(out: dict, lines: list[str]) -> None:
    """AMIGO's scores with every candidate it returns, without its relaxed candidates, without
    the candidates the join choice judged no (kept when it said no to every option), and
    without either. A question left with no candidate scores 0. Without either is tested against
    CORE-T per lake and on the mean over the three benchmarks."""
    def judged_no(c) -> bool:  # marked by the join choice (judge.joins) or by the whole judge (judge.kept)
        return c.extra.get("joins_no", False) or c.extra.get("judged_no", False)
    drops = {"all": lambda c: False, "without relaxed": lambda c: c.left_out, "without judged no": judged_no,
             "without either": lambda c: c.left_out or judged_no(c)}
    rng, diffs = np.random.default_rng(R.SEED), []
    rng_mean = np.random.default_rng(R.SEED)  # apart, so the tests per lake stay as before
    for label in LABEL:
        rows, means, keys = [], {}, R.MAIN[label]
        for lake in P.THREE:
            folder = Path(str(AMIGO).format(lake=lake))
            mine = records(folder / "records_inf.json")
            saved = pickles(folder, mine)
            labels = P.labels(NIGHT, lake)[label]
            for name, drop in drops.items():
                def sets_of(q, drop=drop):
                    s = saved.get(q)
                    if s is None:
                        return R.returned(mine.get(q), False)
                    keep = [o for o, c in zip(mine[q]["interpretations"], s["found"]) if not drop(c)]
                    return R.returned({"interpretations": keep}, False)
                touched = sum(1 for q in labels if q in saved and any(drop(c) for c in saved[q]["found"]))
                per_q = scored(labels, sets_of)
                r = mean_row(list(per_q.values()))
                if name == "without either":
                    night, file, first = R.METHODS["CORE-T"]
                    core = records(night / lake / file)
                    base = scored(labels, lambda q: R.returned(core.get(q), first))
                    tests = [(k, R.paired(np.array([per_q[q]["all"][k] for q in labels]),
                                          np.array([base[q]["all"][k] for q in labels]), rng)) for k in keys]
                    for k in keys:
                        means.setdefault(k, ({}, {}))[0][lake] = np.array([per_q[q]["all"][k] for q in labels])
                        means[k][1][lake] = np.array([base[q]["all"][k] for q in labels])
                    ps = R.holm([t[1][3] for t in tests])
                    diffs.append([NAMES[lake], *(f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]"
                                                               f"{'*' if pv < 0.05 else ''}"
                                                               for (_, (d, lo, hi, _)), pv in zip(tests, ps))])
                out.setdefault("fallbacks", []).append({"label": label, "lake": lake, "kept": name,
                                                        "questions with such candidates": touched, **r})
                rows.append([NAMES[lake], name, *(r[k] for k in keys), r["sets"], touched])
        tests = [_strata(a, b, rng_mean) for a, b in means.values()]
        diffs.append(["mean (stratified)", *(f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]"
                                                          f"{'*' if pv < 0.05 else ''}"
                                                          for (d, lo, hi, _), pv in zip(tests, R.holm([t[3] for t in tests])))])
        lines += table(f"AMIGO without its fallback candidates, {LABEL[label]} (stage 1)",
                       ["lake", "candidates kept", *keys, "sets", "questions with such candidates"],
                       rows + [r[:-1] for r in mean_worst([r[:-1] for r in rows], 2, len(keys) + 1,
                                                          worst_low=(len(keys) + 2,))])
        lines += table(f"AMIGO without either kind of fallback candidate, minus CORE-T, {LABEL[label]}: points, 95% "
                       f"interval, Holm over the {len(keys)} scores of one lake (mean row: stratified paired bootstrap "
                       "over the three benchmarks); * when below 0.05", ["lake", *keys], diffs)
        diffs = []


def _dropped(probe: Probe) -> list[tuple[int, int, frozenset]]:
    """The inferred links that solve.joins leaves out because the schema declares a foreign
    key between the same two tables, and that would otherwise join: (table, table, columns)."""
    table = {c: column["table_id"] for c, column in probe.columns.items()}
    declared, groups = set(), {}
    for number, link in enumerate(probe.links):
        a, b = table[link["from_column"]], table[link["to_column"]]
        if a == b:
            continue
        if link["kind"] == "declared":
            declared.add(frozenset((a, b)))
        grp = link.get("grp")
        groups.setdefault(("grp", grp) if grp is not None else ("link", number), []).append(link)
    out = []
    for group in groups.values():
        a, b = table[group[0]["from_column"]], table[group[0]["to_column"]]
        if (group[0]["kind"] != "declared" and frozenset((a, b)) in declared
                and min(solve.link_quality(probe, link) for link in group) >= config.MIN_EDGE_QUALITY):
            out.append((a, b, frozenset(c for link in group for c in (link["from_column"], link["to_column"]))))
    return out


def _connected(nodes: set, edges: set) -> bool:
    nodes = set(nodes)
    seen, todo = set(), [next(iter(nodes))]
    while todo:
        n = todo.pop()
        if n not in seen:
            seen.add(n)
            todo += [m for e in edges if n in e for m in e if m != n and m in nodes]
    return seen == nodes


def links_held(out: dict, lines: list[str]) -> None:
    """For each reference query of two or more tables: whether the link graph that AMIGO
    searches joins its tables using only those tables (some link between each joined pair),
    and whether it does so with links whose columns the query itself reads; then the same
    with the links dropped by the declared-foreign-key rule put back."""
    rows = []
    for lake in P.THREE:
        probe = Probe(lake)
        ways = solve.joins(probe)
        dropped = _dropped(probe)
        table_id = {probe.path("table", t): t for t in probe.tables}
        column_id = {probe.path("column", c): c for c in probe.columns}
        labels = P.labels(NIGHT, lake)
        distinct = {label: {(frozenset(t), frozenset(c)) for v in labels[label].values() for t, c in v} for label in LABEL}
        groups = {**{LABEL[k]: v for k, v in distinct.items()},
                  "multi-valid label, alternatives only": distinct["multi"] - distinct["gold"]}
        for label, queries in groups.items():
            counts = Counter()
            for tables, columns in queries:
                if len(tables) < 2:
                    continue
                counts["queries of 2+ tables"] += 1
                if any(t not in table_id for t in tables):
                    counts["tables not found in the layer"] += 1
                    continue
                ids = {table_id[t] for t in tables}
                read = {column_id[c] for c in columns if c in column_id}
                any_link = {frozenset(p) for p in ways if set(p) <= ids}
                own = {frozenset(p) for p, js in ways.items() if set(p) <= ids
                       and any({x for pair in j.links for x in pair} <= read for j in js)}
                back = {frozenset((a, b)) for a, b, cols in dropped if {a, b} <= ids and cols <= read}
                counts["joined by some link"] += _connected(ids, any_link)
                counts["joined by links on columns it reads"] += _connected(ids, own)
                counts["the same, dropped links put back"] += _connected(ids, own | back)
            n = counts["queries of 2+ tables"]
            one = {"lake": lake, "label": label, **counts, "dropped links in the lake": len(dropped)}
            out.setdefault("links_held", []).append(one)
            rows.append([NAMES[lake], label, n, counts["tables not found in the layer"],
                         100 * counts["joined by some link"] / n, 100 * counts["joined by links on columns it reads"] / n,
                         100 * counts["the same, dropped links put back"] / n, len(dropped)])
    lines += table("Reference queries of two or more tables whose joins the link graph holds (distinct queries)",
                   ["lake", "label", "queries", "tables not in the layer", "joined by some link (%)",
                    "joined by links on columns the query reads (%)", "the same with dropped links put back (%)",
                    "links dropped by the declared-key rule"], rows)


def detection(out: dict, lines: list[str]) -> None:
    """Whether a method returns two or more table sets, as a test for the multi-valid label
    having two or more table sets: precision and recall of that test over the questions."""
    rows = []
    for lake in P.THREE:
        labels = P.labels(NIGHT, lake)["multi"]
        amb = {q for q, v in labels.items() if len(R.targets_of(v)) > 1}
        for name, folder in {"AMIGO": Path(str(AMIGO).format(lake=lake)),
                             "place judge only (no join choice)": Path(str(VARIANTS["place judge only (no join choice)"]).format(lake=lake))}.items():
            got = records(folder / "records_inf.json")
            many = {q for q in labels if len(R.returned(got.get(q), False)) >= 2}
            hit = len(many & amb)
            one = {"lake": lake, "method": name, "questions": len(labels), "label 2+": len(amb), "returns 2+": len(many),
                   "both": hit, "precision": 100 * hit / len(many), "recall": 100 * hit / len(amb)}
            out.setdefault("detection", []).append(one)
            rows.append([NAMES[lake], name, len(labels), len(amb), len(many), hit, one["precision"], one["recall"]])
    lines += table("Returning two or more table sets as a test for a multi-valid label of two or more table sets",
                   ["lake", "method", "questions", "label has 2+ table sets", "returns 2+ sets", "both", "precision (%)",
                    "recall (%)"], rows)


def votes(out: dict, lines: list[str]) -> None:
    """The labeler's options (decoys left out) by the votes they got: one vote, three votes,
    or none (an option copied from an identical one, clone_of)."""
    rows = []
    for lake in P.THREE:
        count = Counter()
        for one in eval_lakes._lines(ROOT / "runs" / "labeler" / lake / "labels.jsonl"):
            for item in one.get("judged") or []:
                for o in item.get("options") or []:
                    if o.get("decoy"):
                        continue
                    n = len(o.get("votes") or [])
                    count["options"] += 1
                    count[f"{n} votes, {o.get('verdict')}"] += 1
        out.setdefault("votes", []).append({"lake": lake, **count})
        rows.append([NAMES[lake], count["options"], count["1 votes, no"], count["3 votes, no"], count["3 votes, yes"],
                     sum(v for k, v in count.items() if k not in ("options", "1 votes, no", "3 votes, no", "3 votes, yes"))])
    lines += table("The labeler's options (decoys left out) by votes",
                   ["lake", "options", "no after one vote", "no after three votes", "yes after three votes", "other"], rows)


SHAPE = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT|DISTINCT|ASC|DESC)\b", re.I)


def _shape(sql: str) -> Counter:
    """The aggregates, grouping, order, limit and DISTINCT keywords of a query, string literals removed."""
    bare = re.sub(r"'(?:[^']|'')*'", "''", sql)
    return Counter(re.sub(r"\s+", " ", m).upper() for m in SHAPE.findall(bare))


def shape(out: dict, lines: list[str]) -> None:
    """The alternative queries of the multi-valid labels that return rows, by who wrote them:
    the share whose aggregates, grouping, order, limit and DISTINCT keywords are those of the
    original query (a check of the rewrite that needs no parser and no LLM call)."""
    rows = []
    for lake in P.THREE:
        count = Counter()
        for one in eval_lakes._lines(ROOT / "runs" / "labeler" / lake / "labels.jsonl"):
            gold = _shape(one["gold_sql"])
            for group in one.get("interpretations") or []:
                for q in group:
                    if q["name"] != "gold" and q.get("sql") and q.get("answer") in ("same rows", "different rows"):
                        count[q["by"], "queries"] += 1
                        count[q["by"], "same keywords"] += _shape(q["sql"]) == gold
        one = {"lake": lake, **{f"{by}: {k}": v for (by, k), v in count.items()}}
        out.setdefault("shape", []).append(one)
        for by in ("llm", "code"):
            n = count[by, "queries"]
            rows.append([NAMES[lake], "with an LLM call" if by == "llm" else "without an LLM call", n,
                         count[by, "same keywords"], 100 * count[by, "same keywords"] / n if n else float("nan")])
    lines += table("Alternative queries that return rows: same aggregates, grouping, order, limit and DISTINCT "
                   "keywords as the original query",
                   ["lake", "rewritten", "queries", "same keywords", "share (%)"], rows)


EXAMPLE = "bird_dev-q78"  # the question of the worked example of the benchmark section


def example(out: dict, lines: list[str]) -> None:
    """The label of the worked example: options per item, decoys, accepted options and groups."""
    one = next(r for r in eval_lakes._lines(ROOT / "runs" / "labeler" / "bird_dev" / "labels.jsonl") if r["id"] == EXAMPLE)
    got = {"question": one["question"],
           "items": [{"item": i["item"], "words": i.get("words"),
                      "options": sum(not o.get("decoy") for o in i.get("options") or []),
                      "decoys": [(o["name"], o["verdict"]) for o in i.get("options") or [] if o.get("decoy")]}
                     for i in one["judged"]],
           "accepted": [(a["item"], a["name"], a["by"], a.get("answer")) for a in one["accepted"]],
           "groups": [[q["name"] for q in g] for g in one["interpretations"]]}
    out["example"] = got
    lines += [f"## Worked example of the benchmark section ({EXAMPLE})", "", *(f"- {k}: {v}" for k, v in got.items()), ""]


def _caps_lines(out: dict) -> list[str]:
    head = ["lake", *list(out["caps"][0])[1:]]
    rows = [[NAMES[one["lake"]], *list(one.values())[1:]] for one in out["caps"]]
    return table("Join choice outcomes and caps", head, rows)


RUN_NAMES = {"murre": "MURRE (k=5)", "core_t": "CORE-T", "route_sql": "Route+SQL", "full_schema": "Full schema",
             "amigo": "AMIGO-WJ (split, place judge, whole judge)"}


def costs(out: dict, lines: list[str]) -> None:
    """Output tokens per question and GPU-hour shares of the scored runs of 2026-10-20
    (eval_2026-10-20/runs.csv, which allots the GPU's busy time to the runs by output tokens), and
    the logged place judge and join choice replies of AMIGO (paper_extra_2026-11-08/extra.json)."""
    rows = []
    with open(HERE.parent / "eval_2026-10-20" / "runs.csv") as f:
        for r in csv.DictReader(f):
            if r["method"] not in RUN_NAMES:
                continue
            n, failed, tokens = int(r["questions"]), int(r["failed"]), int(r["output_tokens"])
            note = "every question failed" if failed == n else "replies taken from saved replies" if not tokens else ""
            rows.append([NAMES[r["lake"]], RUN_NAMES[r["method"]], n, int(r["llm_calls"]), tokens,
                         round(tokens / n) if tokens else "", r["gpu_hours"] if tokens else "", note])
    out["costs"] = rows
    lines += table("Output tokens and GPU-hour shares of the scored runs (eval_2026-10-20/runs.csv)",
                   ["lake", "method", "questions", "LLM calls", "output tokens", "output tokens per question",
                    "GPU hours (share of busy time, by output tokens)", "note"], rows)
    rows = [[NAMES[c["lake"]], c["questions"], c["place judge calls"], c["questions with a join choice call"],
             c["join choice calls"]] for c in json.loads((HERE.parent / "paper_extra_2026-11-08" / "extra.json").read_text())["cost"]]
    lines += table("AMIGO's logged place judge and join choice replies (cut prompts and repeated calls included)",
                   ["lake", "questions", "place judge replies", "questions with a join choice call", "join choice replies"], rows)
    rows = []
    for lake in P.THREE:
        places = [o for o in eval_lakes._lines(NEW / lake / "amigo" / "judge.jsonl")
                  if o.get("label", "").startswith("judge places")]
        joins = eval_lakes._lines(JOINS / lake / "joinchoice" / "judge.jsonl")
        n = len(records(JOINS / lake / "joinchoice" / "records_inf.json"))
        saved = sum(o.get("status") != "completed" for o in places + joins)
        rows.append([NAMES[lake], n, len(places) + len(joins), saved, f"{1 + (len(places) + len(joins)) / n:.2f}",
                     f"{1 + (len(places) + len(joins) - saved) / n:.2f}"])
    out["saved_replies"] = rows
    lines += table("Saved replies among AMIGO's logged judging replies (no status: given back from the saved replies, "
                   "not a new call); LLM calls per question with one split call, with and without them",
                   ["lake", "questions", "judging replies", "saved replies", "calls per question",
                    "calls per question without saved replies"], rows)


def cross_db(out: dict, lines: list[str]) -> None:
    """Spider multi-valid label: questions with a labeled table set in another database than the
    original query's, by whether that database is one of the development databases (those of
    some original query) or a training database that the lake pools."""
    labels = P.labels(NIGHT, "spider_dev")
    gold, multi = labels["gold"], labels["multi"]
    db = lambda tables: {t.split(".", 1)[0] for t in tables}  # noqa: E731
    dev = {d for v in gold.values() for d in db(v[0][0])}
    count = Counter()
    for q, v in multi.items():
        others = {d for t, _ in v for d in db(t)} - db(gold[q][0][0])
        if others:
            count["questions with a table set in another database"] += 1
            count["of them, in a development database"] += bool(others & dev)
            count["of them, in a training database"] += bool(others - dev)
            count["of them, in training databases only"] += not (others & dev)
    out["cross_db"] = {"development databases": len(dev), **count}
    lines += table("Spider multi-valid label: questions with a table set in another database",
                   ["questions", "development databases", *count], [[len(multi), len(dev), *count.values()]])


def alternatives_only(out: dict, lines: list[str]) -> None:
    """Multi-valid label, alternatives only: on each question, the table-set targets other than
    the original query's table set, on the questions that have one. R, CR, P of every method on
    them, then AMIGO minus each method (paired bootstrap, Holm over the comparisons of one lake)."""
    rows, diffs = [], []
    rng = np.random.default_rng(R.SEED)
    for lake in P.THREE:
        labels = P.labels(NIGHT, lake)
        gold, kept = labels["gold"], {}
        for q, queries in labels["multi"].items():
            if q in gold:
                own = {frozenset(t) for t, _ in gold[q]}
                alt = [m for m in queries if frozenset(m[0]) not in own]
                if alt:
                    kept[q] = alt
        per = {}
        for name, (night, file, first) in R.METHODS.items():
            path = night / lake / file
            if not path.exists():
                continue
            got = records(path)
            per[name] = scored(kept, lambda q: R.returned(got.get(q), first))
            r = mean_row(list(per[name].values()))
            out.setdefault("alternatives_only", []).append({"lake": lake, "method": name, **r})
            rows.append([NAMES[lake], name, *(r[k] for k in R.MAIN["multi"]), r["sets"], r["size"], len(kept)])
        tests = [(m, k, R.paired(np.array([per["AMIGO"][q]["all"][k] for q in kept]),
                                 np.array([per[m][q]["all"][k] for q in kept]), rng))
                 for m in per if m != "AMIGO" for k in R.MAIN["multi"]]
        ps = R.holm([x[2][3] for x in tests])
        cells = {(m, k): f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if a < 0.05 else ''}"
                 for (m, k, (d, lo, hi, _)), a in zip(tests, ps)}
        for m in dict.fromkeys(m for m, _, _ in tests):
            diffs.append([NAMES[lake], m, *(cells[m, k] for k in R.MAIN["multi"])])
    full = [r for r in rows if r[1] != "Route+SQL"]
    lines += table("Multi-valid label, alternatives only: table-set targets other than the original query's "
                   "table set, on the questions that have one (stage 1)",
                   ["lake", "method", *R.MAIN["multi"], "sets", "size", "questions"], rows + mean_worst(full, 2, len(R.MAIN["multi"])))
    lines += table("Alternatives only: AMIGO minus each method, points, 95% interval, Holm over the comparisons "
                   "of one lake; * when below 0.05", ["lake", "method", *R.MAIN["multi"]], diffs)


def sql_top_m(out: dict, lines: list[str]) -> None:
    """Stage 2, main writer: AMIGO cut to its first m table sets, scored from the queries
    already written for those sets (one per table set, no LLM call); then each cut minus CORE-T
    in EX (paired bootstrap, Holm over the cuts of one lake and label)."""
    import sqleval
    rng = np.random.default_rng(R.SEED)
    rows, diffs = [], []
    for label in LABEL:
        for lake in P.THREE:
            got, goal = sqleval.results("qwen", lake), sqleval.targets(lake)[label]

            def per_q(file_of, cut):
                night, file, first = R.METHODS[file_of]
                saved = records(night / lake / file)
                return {q: sqleval.question(a, R.returned(saved.get(q), first)[:cut],
                                            [got.get((q, s), {"status": "no sql"})
                                             for s in R.returned(saved.get(q), first)[:cut]], label == "multi")
                        for q, a in goal.items()}
            base = per_q("CORE-T", None)
            tests = []
            for cut in (1, 2, 3, None):
                mine = per_q("AMIGO", cut)
                name = f"AMIGO, first {cut}" if cut else "AMIGO, all sets"
                ex = 100 * statistics.fmean(s["all"] for s in mine.values())
                queries = statistics.fmean(s["sqls"] for s in mine.values())
                out.setdefault("sql_top_m", []).append({"label": label, "lake": lake, "method": name, "EX": ex,
                                                         "queries per question": queries})
                rows.append([LABEL[label], NAMES[lake], name, ex, f"{queries:.2f}"])
                tests.append((name, R.paired(np.array([mine[q]["all"] for q in goal]),
                                             np.array([base[q]["all"] for q in goal]), rng)))
            rows.append([LABEL[label], NAMES[lake], "CORE-T", 100 * statistics.fmean(s["all"] for s in base.values()),
                         f"{statistics.fmean(s['sqls'] for s in base.values()):.2f}"])
            for (name, (d, lo, hi, _)), p in zip(tests, R.holm([t[1][3] for t in tests])):
                diffs.append([LABEL[label], NAMES[lake], name,
                              f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if p < 0.05 else ''}"])
    lines += table("Stage 2, main writer: AMIGO cut to its first m table sets (queries already written, no LLM call)",
                   ["label", "lake", "method", "EX", "queries per question"], rows)
    lines += table("Stage 2: AMIGO cut minus CORE-T, EX points, 95% interval, Holm over the cuts of one lake and "
                   "label; * when below 0.05", ["label", "lake", "cut", "EX"], diffs)


def few_values(out: dict, lines: list[str]) -> None:
    """The links of the "by few values" rule (links.small_links), recomputed from each database
    of the layer as the build makes them, with their weight, the column's distinct values over
    the near-key's: a link is an edge of the link graph only at MIN_EDGE_QUALITY or more."""
    rows = []
    for lake in P.THREE:
        with closing(layer.open_layer(lake)) as conn:
            found = []
            for database in conn.execute("SELECT id, path FROM databases ORDER BY id").fetchall():
                cards = layer._database_cards(conn, database["id"])
                linked = layer._database_links(conn, database["id"], ("declared", "inferred"))
                declared = {pair for pair, link in linked.items() if link["kind"] == "declared"}
                with closing(index.open_source(database["path"])) as source:
                    found += links.small_links(source, cards, declared, set(linked))
            stored = {(r["from_column"], r["to_column"])
                      for r in conn.execute("SELECT from_column, to_column FROM links WHERE kind = 'values'")}
        edges = sum(score >= config.MIN_EDGE_QUALITY for *_, score in found)
        held = sum((a, b) in stored for a, b, _ in found)
        out.setdefault("few_values", []).append({"lake": lake, "links": len(found), "in the layer": held, "edges": edges})
        rows.append([NAMES[lake], len(found), held, edges])
    lines += table('Links of the "by few values" rule (recomputed, no LLM call) and those whose weight reaches the '
                   "edge threshold of 1/2", ["lake", "links", "of them in the layer", "weight 1/2 or more"], rows)


ORDERS = ("cost order (AMIGO)", "random order (mean of 20)", "fewest tables first")
PERMUTATIONS = 20


def order(out: dict, lines: list[str]) -> None:
    """Whether AMIGO's cost order puts the table sets that hold targets first: the same distinct
    table sets of each question in cost order, in random order (scores averaged over PERMUTATIONS
    shuffles) and fewest tables first (ties in cost order), cut to the first m; cost order minus
    each other order, paired over questions, Holm over the comparisons of one lake and label."""
    rows, diffs = {label: [] for label in LABEL}, {label: [] for label in LABEL}
    for lake in P.THREE:
        got = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        for label in LABEL:
            keys = R.MAIN[label]
            labels = P.labels(NIGHT, lake)[label]
            shuffle = np.random.default_rng(R.SEED)
            mine = {q: R.returned(got.get(q), False) for q in labels}
            shuffled = {q: [list(shuffle.permutation(len(s))) for _ in range(PERMUTATIONS)] for q, s in mine.items()}
            per = {}
            for m in (1, 2, 3):
                def scores(sets_of):
                    return {q: R.question(R.targets_of(queries), sets_of(q), False)["all"] for q, queries in labels.items()}
                cost = scores(lambda q: mine[q][:m])
                small = scores(lambda q: sorted(mine[q], key=len)[:m])
                runs = [scores(lambda q, k=k: [mine[q][i] for i in shuffled[q][k]][:m]) for k in range(PERMUTATIONS)]
                rand = {q: {key: statistics.fmean(r[q][key] for r in runs) for key in keys} for q in labels}
                per[m] = dict(zip(ORDERS, (cost, rand, small)))
            rng = np.random.default_rng(R.SEED)
            tests = []
            for m, by in per.items():
                for name in ORDERS:
                    vals = [100 * statistics.fmean(by[name][q][key] for q in labels) for key in keys]
                    out.setdefault("order", []).append({"lake": lake, "label": label, "m": m, "order": name,
                                                        **dict(zip(keys, vals))})
                    rows[label].append([NAMES[lake], m, name, *vals])
                for name in ORDERS[1:]:
                    for key in keys:
                        a = np.array([by[ORDERS[0]][q][key] for q in labels])
                        b = np.array([by[name][q][key] for q in labels])
                        tests.append((m, name, key, R.paired(a, b, rng)))
            ps = R.holm([t[3][3] for t in tests])
            for (m, name, key, t), pv in zip(tests, ps):
                diffs[label].append([NAMES[lake], m, name, key,
                              f"{100 * t[0]:+.1f} [{100 * t[1]:+.1f}, {100 * t[2]:+.1f}]" + ("*" if pv < 0.05 else "")])
    for label in LABEL:
        keys = R.MAIN[label]
        lines += table(f"AMIGO's table sets in three orders, cut to the first m sets (stage 1), {LABEL[label]}",
                       ["lake", "m", "order", *keys], rows[label])
        summary = []
        for m in (1, 2, 3):
            for name in ORDERS:
                got = [o for o in out["order"] if o["label"] == label and o["m"] == m and o["order"] == name]
                for kind, pick in (("mean", statistics.fmean), ("worst", min)):
                    summary.append([kind, m, name, *(pick(o[k] for o in got) for k in keys)])
        lines += table(f"AMIGO's table sets in three orders, mean and worst over the three benchmarks, {LABEL[label]}",
                       ["over", "m", "order", *keys], summary)
        lines += table(f"Cost order minus each other order, {LABEL[label]}: points, 95% interval, Holm over the "
                       "comparisons of one lake; * when below 0.05", ["lake", "m", "order", "score", "difference"],
                       diffs[label])


def odds_exact(out: dict, lines: list[str]) -> None:
    """By cost gap, the candidates whose table set is exactly a labeled table set (a measure that
    a larger candidate cannot meet more easily, unlike holding every table of one)."""
    bins = [(0.0, 0.0, "best (cost above best 0)"), (0.0, 1.0, "above best by (0, 1] bit"),
            (1.0, 2.0, "by (1, 2] bits"), (2.0, 4.0, "by (2, 4] bits"), (4.0, float("inf"), "by more than 4 bits")]
    rows = []
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        for label in LABEL:
            labels = P.labels(NIGHT, lake)[label]
            count, exact = Counter(), Counter()
            for q, queries in labels.items():
                found = (mine.get(q) or {}).get("interpretations") or []
                if not found or (mine.get(q) or {}).get("error"):
                    continue
                targets = set(R.targets_of(queries))
                best = min(o["cost"] for o in found)
                for o in found:
                    gap = o["cost"] - best
                    name = next(n for lo, hi, n in bins if (gap <= 1e-9 if hi == 0.0 else lo + 1e-9 < gap <= hi + 1e-9))
                    count[name] += 1
                    exact[name] += frozenset(o["tables"]) in targets
            for _, _, name in bins:
                share = 100 * exact[name] / count[name] if count[name] else float("nan")
                out.setdefault("odds_exact", []).append({"lake": lake, "label": label, "bin": name,
                                                         "candidates": count[name], "exact": exact[name], "share": share})
                rows.append([NAMES[lake], LABEL[label], name, count[name], share])
    lines += table("Candidates whose table set is exactly a labeled table set, by cost above the best candidate",
                   ["lake", "label", "cost above best", "candidates", "share equal to a labeled table set (%)"], rows)


def left_out(out: dict, lines: list[str]) -> None:
    """The parts that AMIGO's relaxed candidates leave out, once per scored question and part
    (relaxed candidates come only when no candidate places every part): those with no place that
    the place judge said yes to (and of them, those with no place listed at all, and those with a
    rejected place in a table that the original query reads, the gold used for scoring only), and
    those that carry a value."""
    rows, more = [], []
    for lake in P.THREE:
        folder = Path(str(AMIGO).format(lake=lake))
        gold = P.labels(NIGHT, lake)["gold"]
        saved = pickles(folder, gold)
        with closing(layer.open_layer(lake)) as conn:
            name = {r["id"]: f'{r["db"]}.{r["name"]}' for r in conn.execute(
                "SELECT t.id, d.name AS db, t.name FROM tables t JOIN databases d ON d.id = t.database_id")}
        parts, unkept, valued, questions, mixed, unlisted, near = 0, 0, 0, 0, 0, 0, 0
        for q, s in saved.items():
            found = s["found"]
            if not any(c.left_out for c in found):
                continue
            questions += 1
            mixed += not all(c.left_out for c in found)
            tables = set().union(*R.targets_of(gold[q]))
            for j in sorted({j for c in found for j in c.left_out}):
                parts += 1
                graded = s["grades"][j] or {}
                if not any(graded.values()):
                    unkept += 1
                    unlisted += not graded
                    near += any(name.get(t) in tables for t, _ in graded)
                valued += s["entities"][j].literal is not None
        out.setdefault("left_out", []).append({"lake": lake, "questions": questions, "also full candidates": mixed,
                                               "parts": parts, "no kept place": unkept, "with a value": valued,
                                               "no place listed": unlisted, "rejected place in an original table": near})
        rows.append([NAMES[lake], questions, mixed, parts, unkept, 100 * unkept / parts, valued, 100 * valued / parts])
        more.append([NAMES[lake], unkept, unlisted, near, 100 * near / unkept if unkept else float("nan")])
    lines += table("Parts left out by AMIGO's relaxed candidates, once per question and part",
                   ["lake", "questions with a relaxed candidate", "of them with a full candidate too",
                    "parts left out", "no place judged yes", "% of them", "with a value", "% with a value"], rows)
    lines += table("Of the left-out parts with no place judged yes: no place listed at all, and a rejected place in a "
                   "table that the original query reads (gold used for scoring only)",
                   ["lake", "no place judged yes", "no place listed", "a rejected place in an original table", "%"],
                   more)


def first_match(out: dict, lines: list[str]) -> None:
    """Precision per target, order-aware: the matched set is the first set in AMIGO's cost order
    among those of highest recall (R and CR do not change), against the protocol's matched set."""
    def first(target, sets):
        if not target or not sets:
            return 0.0
        top = max(len(target & s) / len(target) for s in sets)
        s = next(s for s in sets if len(target & s) / len(target) == top)
        return len(target & s) / len(s)
    rows = []
    for lake in P.THREE:
        got = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        for label in LABEL:
            labels = P.labels(NIGHT, lake)[label]
            mine = {q: R.returned(got.get(q), False) for q in labels}
            a = np.array([R.question(R.targets_of(queries), mine[q], False)["all"]["P"] for q, queries in labels.items()])
            b = np.array([statistics.fmean(first(t, mine[q]) for t in R.targets_of(queries)) for q, queries in labels.items()])
            out.setdefault("first_match", []).append({"lake": lake, "label": label, "P": 100 * a.mean(),
                                                      "P first": 100 * b.mean()})
            rows.append([NAMES[lake], LABEL[label], 100 * a.mean(), 100 * b.mean()])
    for label in LABEL:
        got = [o for o in out["first_match"] if o["label"] == label]
        for kind, pick in (("mean", statistics.fmean), ("worst", min)):
            rows.append([kind, LABEL[label], pick(o["P"] for o in got), pick(o["P first"] for o in got)])
    lines += table("AMIGO's precision per target: matched set as in the protocol, and the first set in cost order "
                   "among those of highest recall", ["lake", "label", "P (protocol)", "P (first in order)"], rows)


def _sql_inputs(lake: str, label: str, match) -> dict:
    """{method: {question: (targets, returned sets, results)}} of the main writer, as
    sqleval.score() builds them; `match` may replace the hashes of the results."""
    import sqleval as Q
    got, goal, hinted = Q.results("qwen", lake), Q.targets(lake), Q.hint_results("qwen", lake)
    goal, got, hinted = match(goal, got, hinted) if match else (goal, got, hinted)

    def one(a, sets, q):
        return a, sets, [got.get((q, s), {"status": "no sql"}) for s in sets]
    out = {"Oracle": {q: one(a, list(dict.fromkeys(t for _, ts in a for t in ts)), q) for q, a in goal[label].items()}}
    for method, (night, file, first) in R.METHODS.items():
        if (night / lake / file).exists():
            records = json.loads((night / lake / file).read_text())
            out[method] = {q: one(a, R.returned(records.get(q), first), q) for q, a in goal[label].items()}
    out["AMIGO with hints"] = {q: (a, list(dict.fromkeys(s for s, _ in hinted.get(q, []))),
                                   [r for _, r in hinted.get(q, [])]) for q, a in goal[label].items()}
    return out


def _sql_scores(lake: str, label: str, match) -> dict:
    """{method: {question: sqleval.question()}}, with result P on both labels."""
    import sqleval as Q
    return {method: {q: Q.question(a, sets, res, True) for q, (a, sets, res) in by_q.items()}
            for method, by_q in _sql_inputs(lake, label, match).items()}


def result_p_sv(out: dict, lines: list[str]) -> None:
    """Result precision of the main writer's queries against both labels: the share of a
    question's distinct results that are a target, failed queries left out, averaged over the
    questions with a result. Against the single-valid label it is a lower bound, since a result
    of another valid interpretation counts as wrong."""
    rows, per = [], {}
    for lake in P.THREE:
        for label in LABEL:
            for method, by_q in _sql_scores(lake, label, None).items():
                vals = [s["result P"] for s in by_q.values() if s["result P"] is not None]
                per.setdefault((label, method), []).append(100 * statistics.fmean(vals))
                out.setdefault("result_p_sv", []).append({"lake": lake, "label": label, "method": method,
                                                          "result P": 100 * statistics.fmean(vals), "n": len(vals)})
                rows.append([NAMES[lake], LABEL[label], method, 100 * statistics.fmean(vals), len(vals)])
    for (label, method), vals in per.items():
        rows.append(["mean", LABEL[label], method, statistics.fmean(vals), ""])
        rows.append(["worst", LABEL[label], method, min(vals), ""])
    lines += table("Result precision of the main writer's queries against each label (the multi-valid rows repeat "
                   "sql_qwen.md)", ["lake", "label", "method", "result P", "questions with a result"], rows)


def dense_by_db(out: dict, lines: list[str]) -> None:
    """Dense retrieval's k tables split by database: one returned table set per database, in
    the order of each database's best-ranked table, against Dense as scored (one set)."""
    rows, per = [], {}
    for lake in P.THREE:
        for k in (3, 5):
            got = records(NIGHT / lake / f"bl_dense_k{k}" / "records.json")
            for label in LABEL:
                labels = P.labels(NIGHT, lake)[label]
                for name, split in ((f"Dense k{k}", False), (f"Dense k{k} by database", True)):
                    def sets(q):
                        one = R.returned(got.get(q), False)
                        if not split or not one:
                            return one
                        order = (got[q].get("order") or sorted(one[0]))
                        groups = {}
                        for t in order:
                            if t in one[0]:
                                groups.setdefault(t.split(".")[0], set()).add(t)
                        return [frozenset(g) for g in groups.values()]
                    row = mean_row(list(scored(labels, sets).values()))
                    per.setdefault((label, name), []).append(row)
                    out.setdefault("dense_by_db", []).append({"lake": lake, "label": label, "method": name, **row})
                    rows.append([label, NAMES[lake], name, *(row[k] for k in R.MAIN[label]), row["sets"], row["size"]])
    for (label, name), got in per.items():
        for kind, pick in (("mean", statistics.fmean), ("worst", min)):
            rows.append([label, kind, name, *(pick(r[key] for r in got) for key in R.MAIN[label]), "", ""])
    for label in LABEL:
        lines += table(f"Dense retrieval split by database (stage 1, no LLM call), {LABEL[label]}; not tested",
                       ["lake", "method", *R.MAIN[label], "sets", "size"], [r[1:] for r in rows if r[0] == label])


def _loose(job):
    """The result of one query as labeler.gold.result hashes it, but with the cells of each row
    sorted, so two results that differ only in column order get the same hash; None on failure."""
    import hashlib
    import sqlite3
    from labeler.gold import STEPS as LIMIT, _cell, connect
    path, sql = job
    steps = 0

    def tick():
        nonlocal steps
        steps += 1000
        return steps > LIMIT
    try:
        with closing(connect(dict(path) if isinstance(path, tuple) else path)) as conn:
            conn.set_progress_handler(tick, 1000)
            rows = conn.execute(sql).fetchall()
    except sqlite3.Error:
        return None
    norm = sorted(json.dumps(sorted(json.dumps(_cell(v)) for v in row)) for row in rows)
    return hashlib.sha256("\n".join(norm).encode()).hexdigest()[:16]


def column_order(out: dict, lines: list[str]) -> None:
    """Execution accuracy of the main writer when the column order of a result is ignored, next to
    the protocol's row rule. Every saved query that returned rows is run again, and one query of
    each labeled result (the original query, or the first alternative of its group); a result
    then counts as a target's when their rows match with the cells of each row in any order."""
    from concurrent.futures import ProcessPoolExecutor
    from baselines.lake import Lake
    import sqleval as Q
    rows = []
    for lake_name in P.THREE:
        lake = Lake(lake_name)

        def where(s):
            dbs = sorted({lake.table[t].database for t in s})
            return tuple((d, lake.paths[d]) for d in dbs) if len(dbs) > 1 else lake.paths[dbs[0]]
        mine = [json.loads(x) for x in (Q.OUT / "qwen" / f"{lake_name}.jsonl").read_text().splitlines()]
        hints = [json.loads(x) for x in (Q.OUT / "qwen" / f"{lake_name}.hints.jsonl").read_text().splitlines()]
        stored = [json.loads(x) for x in (ROOT / "runs" / "labeler" / lake_name / "labels.jsonl").read_text().splitlines()]
        jobs = {}
        for x in mine + hints:
            if x["result"]["status"] == "ok":
                jobs[(where(x["set"]), x["sql"])] = None
        group_job = {}  # result hash -> one query that returns it: equal rows give equal loose hashes
        for one in stored:
            for group, digest in zip(one.get("interpretations") or [], one.get("hashes") or []):
                member = group[0]
                sql = one["gold_sql"] if member["name"] == "gold" else member.get("sql")
                if sql and digest not in group_job:
                    group_job[digest] = (lake.paths[member["db"]], sql)
                    jobs[group_job[digest]] = None
        work = list(jobs)
        with ProcessPoolExecutor(8) as pool:
            for job, h in zip(work, pool.map(_loose, work, chunksize=16)):
                jobs[job] = h
        loose_of = {}
        for x in mine:
            loose_of[(x["q"], frozenset(x["set"]))] = jobs.get((where(x["set"]), x["sql"]))
        hint_loose = {}
        for x in sorted(hints, key=lambda x: (x["q"], x["i"])):
            hint_loose.setdefault(x["q"], []).append(jobs.get((where(x["set"]), x["sql"])))

        def relabel(goal, got, hinted):
            """Replace each hash by its loose hash where one exists, so sqleval.question() matches
            results with column order ignored."""
            def target(h):
                return jobs.get(group_job.get(h)) or h
            goal = {label: {q: [(target(h), ts) for h, ts in a] for q, a in per.items()} for label, per in goal.items()}
            got = {key: ({**r, "hash": loose_of.get(key) or r.get("hash")} if r["status"] == "ok" else r)
                   for key, r in got.items()}
            hinted = {q: [(s, {**r, "hash": h or r.get("hash")} if r["status"] == "ok" else r)
                          for (s, r), h in zip(pairs, hint_loose.get(q, [None] * len(pairs)))]
                      for q, pairs in hinted.items()}
            return goal, got, hinted
        for label in LABEL:
            strict = _sql_scores(lake_name, label, None)
            loose = _sql_scores(lake_name, label, relabel)
            for method in strict:
                a = [s["all"] for s in strict[method].values() if s["all"] is not None]
                b = [s["all"] for s in loose[method].values() if s["all"] is not None]
                gained = sum(y > x for x, y in zip(a, b))
                one = {"lake": lake_name, "label": label, "method": method, "EX": 100 * statistics.fmean(a),
                       "EX column order ignored": 100 * statistics.fmean(b), "questions gaining": gained,
                       "queries run": len(work), "failed reruns": sum(h is None for h in jobs.values())}
                out.setdefault("column_order", []).append(one)
    lines += _column_lines(out)


def _column_lines(out: dict) -> list[str]:
    rows = [[NAMES[o["lake"]], LABEL[o["label"]], o["method"], o["EX"], o["EX column order ignored"],
             o["questions gaining"]] for o in out["column_order"]]
    for label in LABEL:
        methods = dict.fromkeys(o["method"] for o in out["column_order"] if o["label"] == label)
        for method in methods:
            got = [o for o in out["column_order"] if o["label"] == label and o["method"] == method]
            for kind, pick in (("mean", statistics.fmean), ("worst", min)):
                rows.append([kind, LABEL[label], method, pick(o["EX"] for o in got),
                             pick(o["EX column order ignored"] for o in got), ""])
    runs = {o["lake"]: (o["queries run"], o["failed reruns"]) for o in out["column_order"]}
    return table("Main writer: EX by the row rule and with the column order of results ignored (queries run again "
                 "in SQLite, no LLM call; " + "; ".join(f"{NAMES[k]}: {n} queries, {f} failed" for k, (n, f) in runs.items())
                 + ")", ["lake", "label", "method", "EX", "EX, column order ignored", "questions that gain"], rows)


def _strata(a: dict, b: dict, rng) -> tuple[float, float, float, float]:
    """Mean over the benchmarks of the per-benchmark mean of a - b ({lake: array per question}),
    its 95% interval and two-sided p, resampling the questions of each benchmark apart."""
    boot = np.zeros(R.RESAMPLES)
    for lake in a:
        diff = a[lake] - b[lake]
        boot += diff[rng.integers(0, len(diff), (R.RESAMPLES, len(diff)))].mean(axis=1) / len(a)
    mean = statistics.fmean(float((a[lake] - b[lake]).mean()) for lake in a)
    p = min(1.0, 2 * min((boot <= 0).mean(), (boot >= 0).mean()))
    return mean, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), float(p)


def mean_tests(out: dict, lines: list[str]) -> None:
    """The means over the three benchmarks that the paper leads with, tested: AMIGO and AMIGO
    top-1 minus CORE-T in the main scores of the label (stage 1) and in EX (stage 2, main writer), stratified paired
    bootstrap over the questions of each benchmark, Holm over the tests of one label."""
    import sqleval
    rng = np.random.default_rng(R.SEED)
    stage1 = {lake: R.score(lake) for lake in P.THREE}
    rows = []
    for label in LABEL:
        tests = []
        for mine in ("AMIGO", "AMIGO top-1"):
            for key in R.MAIN[label]:
                a = {lake: np.array([s["all"][key] for s in stage1[lake][label][mine].values()]) for lake in P.THREE}
                b = {lake: np.array([s["all"][key] for s in stage1[lake][label]["CORE-T"].values()]) for lake in P.THREE}
                tests.append((mine, key, _strata(a, b, rng)))
            a, b = {}, {}
            for lake in P.THREE:
                got, goal = sqleval.results("qwen", lake), sqleval.targets(lake)[label]
                hinted = sqleval.hint_results("qwen", lake)
                for name, side in ((mine, a), ("CORE-T", b)):
                    if name == "AMIGO":  # one query per candidate, as in the paper
                        side[lake] = np.array([sqleval.question(x, list(dict.fromkeys(s for s, _ in hinted.get(q, []))),
                                                                [r for _, r in hinted.get(q, [])], False)["all"]
                                               for q, x in goal.items()])
                        continue
                    night, file, first = R.METHODS[name]
                    saved = records(night / lake / file)
                    side[lake] = np.array([sqleval.question(x, R.returned(saved.get(q), first),
                                                            [got.get((q, t), {"status": "no sql"})
                                                             for t in R.returned(saved.get(q), first)], False)["all"]
                                           for q, x in goal.items()])
            tests.append((mine, "EX", _strata(a, b, rng)))
        for (mine, key, (d, lo, hi, _)), pv in zip(tests, R.holm([t[2][3] for t in tests])):
            out.setdefault("mean_tests", []).append({"label": label, "method": mine, "score": key, "difference": 100 * d,
                                                     "low": 100 * lo, "high": 100 * hi, "p Holm": pv})
            rows.append([LABEL[label], mine, key, f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]"
                         + ("*" if pv < 0.05 else "")])
    lines += table("Mean over the three benchmarks, minus CORE-T: points, 95% interval (stratified paired bootstrap), "
                   "Holm over the tests of one label; * when below 0.05", ["label", "method", "score", "difference"], rows)


def result_p_failed(out: dict, lines: list[str]) -> None:
    """Result precision with each failed query (error, a table outside the set, too slow, no
    query) counted as one wrong result: the distinct results that are a target, over the
    distinct results plus the failed queries; questions with at least one query."""
    rows, per = [], {}
    for lake in P.THREE:
        for label in LABEL:
            for method, by_q in _sql_inputs(lake, label, None).items():
                vals = []
                for a, _, res in by_q.values():
                    if not res:
                        continue
                    hashes = {r["hash"] for r in res if r["status"] in ("ok", "empty")}
                    failed = sum(r["status"] not in ("ok", "empty") for r in res)
                    vals.append(len(hashes & {h for h, _ in a}) / (len(hashes) + failed))
                v = 100 * statistics.fmean(vals)
                per.setdefault((label, method), []).append(v)
                out.setdefault("result_p_failed", []).append({"lake": lake, "label": label, "method": method,
                                                              "result P, failures wrong": v, "n": len(vals)})
                rows.append([NAMES[lake], LABEL[label], method, v, len(vals)])
    for (label, method), vals in per.items():
        if len(vals) == len(P.THREE):
            rows += [["mean", LABEL[label], method, statistics.fmean(vals), ""],
                     ["worst", LABEL[label], method, min(vals), ""]]
    lines += table("Result precision with each failed query counted as a wrong result (main writer)",
                   ["lake", "label", "method", "result P", "questions with a query"], rows)


def extra_tables(out: dict, lines: list[str]) -> None:
    """EX of the found targets (main writer) by how many tables the smallest returned set that
    holds a reference query's tables has beyond them: 0, 1, 2 or more. Not a controlled measure:
    the targets in each group differ in other ways too."""
    rows = []
    for lake in P.THREE:
        for label in LABEL:
            for method, by_q in _sql_inputs(lake, label, None).items():
                if method not in ("CORE-T", "AMIGO", "AMIGO top-1"):
                    continue
                hit, count = Counter(), Counter()
                for a, sets, res in by_q.values():
                    hashes = {r["hash"] for r in res if r["status"] in ("ok", "empty")}
                    for h, ts in a:
                        extra = [len(s) - len(t) for t in ts for s in sets if t <= s]
                        if not extra:
                            continue
                        group = min(min(extra), 2)
                        count[group] += 1
                        hit[group] += h in hashes
                for group in (0, 1, 2):
                    v = 100 * hit[group] / count[group] if count[group] else float("nan")
                    out.setdefault("extra_tables", []).append({"lake": lake, "label": label, "method": method,
                                                               "extra": group, "targets": count[group], "EX": v})
                    rows.append([NAMES[lake], LABEL[label], method, ("0", "1", "2 or more")[group], count[group], v])
    lines += table("EX of found targets by the extra tables of the smallest returned set that holds them (main writer; "
                   "pooled over targets; not controlled)", ["lake", "label", "method", "extra tables", "targets", "EX"],
                   rows)


SENSITIVITY = (("edge threshold 1/3", 1 / 3, 30), ("edge threshold 2/3", 2 / 3, 30),
               ("20 columns per part", 0.5, 20))


def sensitivity(out: dict, lines: list[str]) -> None:
    """The place-judge-only configuration (no join choice), its search run again from the stored
    places and grades: with the edge threshold at 1/3 and 2/3 at search time (the layer, built at
    1/2, unchanged), and with 20 columns listed per part in place of 30. The
    shorter lists are recomputed (embeddings, no LLM call) and keep the stored grades, given when
    the place judge saw the longer lists; "same lists" counts the questions whose lists recomputed
    at 30 hold the stored places."""
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        stored = records(NEW / lake / "abl_nojudge2" / "records_inf.json")
        source = {q: s for q, s in pickles(NEW / lake / "abl_nojudge2", mine).items()
                  if not s.get("error") and s.get("shown")}
        probe = Probe(lake)
        same = sum([{(h.table, h.column) for h in part} for part in s["shown"]]
                   == [{(h.table, h.column) for h in candidates.holders(probe, s["stage"], j)}
                       for j in range(len(s["shown"]))] for s in source.values())
        for name, threshold, columns in SENSITIVITY:
            config.MIN_EDGE_QUALITY, candidates.COLUMNS_PER_PART = threshold, columns
            sets, unjudged = {}, 0
            try:
                graph = candidates.Graph(probe)
                pairs = len(graph.ways) // 2
                for q, s in source.items():
                    shown = s["shown"] if columns == config.COLUMNS_PER_PART else [
                        candidates.holders(probe, s["stage"], j) for j in range(len(s["shown"]))]
                    unjudged += sum((h.table, h.column) not in s["grades"][j] for j, part in enumerate(shown) for h in part)
                    places = judge.graded(shown, [{(h.table, h.column): s["grades"][j].get((h.table, h.column), False)
                                                   for h in part} for j, part in enumerate(shown)])
                    found = candidates.candidates(probe, graph, s["stage"], judge.MOST, graded=places)
                    if not found:
                        found = judge.relaxed(probe, graph, s["stage"], places, judge.MOST, None)
                    sets[q] = list(dict.fromkeys(frozenset(probe.path("table", t) for t in c.tables)
                                                 for c in judge.split(found, places)))
            finally:
                config.MIN_EDGE_QUALITY = 0.5
                candidates.COLUMNS_PER_PART = config.COLUMNS_PER_PART
            for label in LABEL:
                labels = P.labels(NIGHT, lake)[label]
                r = mean_row(list(scored(labels, lambda q: sets[q] if q in sets else R.returned(stored.get(q), False)).values()))
                out.setdefault("sensitivity", []).append({"lake": lake, "label": label, "variant": name, **r,
                                                          "places not graded": unjudged, "questions run again": len(source),
                                                          "same lists": same, "table pairs joined": pairs})
    lines += _sens_lines(out)


def _sens_lines(out: dict) -> list[str]:
    lines = []
    for label in LABEL:
        keys = R.MAIN[label]
        rows = [[NAMES[o["lake"]], o["variant"], *(o[k] for k in keys), o["sets"], o["size"], o["table pairs joined"],
                 o["places not graded"], o["questions run again"], o["same lists"]]
                for o in out["sensitivity"] if o["label"] == label]
        lines += table("Place judge only (no join choice), search run again with the edge threshold at 1/3 and 2/3 "
                       f"(layer unchanged) and with 20 columns per part (stored grades), {LABEL[label]}",
                       ["lake", "variant", *keys, "sets", "size", "table pairs joined", "places not graded",
                        "questions run again", "same lists at 30"], rows + mean_worst(rows, 2, len(keys)))
    return lines


def reach_rule(out: dict, lines: list[str]) -> None:
    """Results out of the Oracle's reach (one query per labeled table set) under the two rules for
    when a labeled table set serves a result: it equals, or it contains, the tables of one of the
    result's reference queries (benchmark_stats_2026-10-25/stats.py, reachable)."""
    import sqleval
    sys.path.insert(0, str(HERE.parent / "benchmark_stats_2026-10-25"))
    import stats as S
    rows = []
    for lake in P.THREE:
        targets = sqleval.targets(lake)["multi"]
        total = sum(len(v) for v in targets.values())
        equal = sum(len(v) - S.reachable(v, frozenset.__eq__) for v in targets.values())
        held = sum(len(v) - S.reachable(v) for v in targets.values())
        out.setdefault("reach_rule", []).append({"lake": lake, "results": total, "out of reach, equals": equal,
                                                 "out of reach, contains": held})
        rows.append([NAMES[lake], total, equal, held])
    lines += table("Multi-valid results out of the Oracle's reach, by the rule for when a labeled table set serves a "
                   "result", ["lake", "results", "equals its tables", "contains its tables"], rows)


def value_only(out: dict, lines: list[str]) -> None:
    """Multi-valid table-set targets that come only from alternatives whose option the labeler's
    value signal alone found (its sources are ["value"]): the gold query and every other
    alternative read other tables. The label is read as eval_lakes._label reads it. Also the share of
    these targets, and of the other table-set targets, whose tables some returned set of AMIGO and of
    CORE-T contains (complete recall pooled over targets; not tested)."""
    import sqlite3
    rows, held_rows = [], []
    for lake in P.THREE:
        night, file, first = R.METHODS["CORE-T"]
        outputs = {"AMIGO": (records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json"), False),
                   "CORE-T": (records(night / lake / file), first)}
        held = Counter()
        multi = P.labels(NIGHT, lake)["multi"]
        folder = ROOT / "runs" / "labeler" / lake
        stored = {one["id"]: one for one in eval_lakes._lines(folder / "labels.jsonl")}
        ids = {q["question_id"]: q["id"] for q in eval_lakes._lines(folder / "questions.jsonl")}
        qrows = {r["id"]: r for r in eval_lakes._lines(P._questions(NIGHT, lake))}
        read = eval_lakes.Gold(lake)
        targets = only = questions = alternatives = by_value = 0
        for q in multi:
            row = qrows[q]
            one = stored.get(q) or stored.get(ids.get(row["question_id"]))
            sources = {(i["item"], o["name"]): o.get("sources", [])
                       for i in one.get("judged") or [] for o in i.get("options", [])}
            origin = {frozenset(read(row["db_id"], row["gold_sql"])[0]): {"other"}}
            for group in one.get("interpretations") or []:
                for alt in group:
                    if alt["name"] == "gold" or not alt.get("sql"):
                        continue
                    try:
                        tables = frozenset(read(alt["db"], alt["sql"])[0])
                    except sqlite3.Error:
                        continue
                    value = set(sources.get((alt["item"], alt["name"]), [])) == {"value"}
                    alternatives += 1
                    by_value += value
                    origin.setdefault(tables, set()).add("value" if value else "other")
            for name, (got, first_only) in outputs.items():
                sets = R.returned(got.get(q), first_only)
                for tables, kinds in origin.items():
                    side = "value only" if kinds == {"value"} else "other"
                    held[name, side] += any(tables <= s for s in sets)
                    held[name, side, "n"] += 1
            mine = sum(kinds == {"value"} for kinds in origin.values())
            targets += len(origin)
            only += mine
            questions += mine > 0
        out.setdefault("value_only", []).append({"lake": lake, "questions": len(multi), "table-set targets": targets,
                                                 "targets only from value-only alternatives": only,
                                                 "questions with such a target": questions,
                                                 "alternatives that ran": alternatives,
                                                 "of them found by the value signal alone": by_value})
        rows.append([NAMES[lake], len(multi), targets, only, questions, alternatives, by_value])
        for name in outputs:
            one = {"lake": lake, "method": name,
                   **{f"CR on {side} targets": 100 * held[name, side] / held[name, side, "n"]
                      for side in ("value only", "other") if held[name, side, "n"]}}
            out.setdefault("value_only_held", []).append(one)
            held_rows.append([NAMES[lake], name, held[name, "value only", "n"], one.get("CR on value only targets", "n/a"),
                              held[name, "other", "n"], one.get("CR on other targets", "n/a")])
    lines += table("Complete recall pooled over the targets only from value-only alternatives and over the other "
                   "table-set targets of the multi-valid label (no LLM call, not tested)",
                   ["lake", "method", "value-only targets", "CR on them", "other targets", "CR on them"], held_rows)
    lines += table("Multi-valid table-set targets that only alternatives found by the labeler's value signal alone give",
                   ["lake", "questions", "table-set targets", "targets only from value-only alternatives",
                    "questions with such a target", "alternatives that ran", "of them found by the value signal alone"],
                   rows)



def input_tokens(out: dict, lines: list[str]) -> None:
    """Input and output tokens per question over all questions, summed from the logs of the scored
    runs: AMIGO's place judge (the 2026-10-20 run) and join choice, CORE-T, Route+SQL and Full schema.
    The split of AMIGO and MURRE took their replies from saved replies, which log no tokens."""
    def summed(logs, n):
        got = [sum(o.get("usage", {}).get(k, 0) for o in logs) for k in ("input_tokens", "output_tokens")]
        return [round(x / n) for x in got] if n and any(got) else ["", ""]
    rows = []
    for lake in P.THREE:
        n = len(records(JOINS / lake / "joinchoice" / "records_inf.json"))
        places = [o for o in eval_lakes._lines(NEW / lake / "amigo" / "judge.jsonl")
                  if o.get("label", "").startswith("judge places")]
        rows.append([NAMES[lake], "AMIGO place judge", n, *summed(places, n)])
        rows.append([NAMES[lake], "AMIGO join choice", n,
                     *summed(eval_lakes._lines(JOINS / lake / "joinchoice" / "judge.jsonl"), n)])
        for tag, name in (("bl_core_t", "CORE-T"), ("bl_route_sql", "Route+SQL"), ("bl_full_schema", "Full schema")):
            q = len(P.records(NIGHT / lake, tag) or {})
            if q:
                rows.append([NAMES[lake], name, q, *summed(eval_lakes._lines(NIGHT / lake / tag / "llm.jsonl"), q)])
    out["input_tokens"] = rows
    lines += table("Input and output tokens per question over all questions, from the logs of the scored runs "
                   "(empty: no call made, every question failed)",
                   ["lake", "LLM step", "questions", "input tokens per question", "output tokens per question"], rows)


def relaxed_sql(out: dict, lines: list[str]) -> None:
    """Stage 2, main writer, on the questions whose candidates are all relaxed: execution accuracy of
    AMIGO and of CORE-T on these questions, from the queries already written (no LLM call)."""
    import sqleval
    rows = []
    for label in LABEL:
        for lake in P.THREE:
            folder = Path(str(AMIGO).format(lake=lake))
            mine = records(folder / "records_inf.json")
            saved = pickles(folder, mine)
            only = {q for q, s in saved.items() if s["found"] and all(c.left_out for c in s["found"])}
            got, goal = sqleval.results("qwen", lake), sqleval.targets(lake)[label]
            kept = [q for q in goal if q in only]
            row = [LABEL[label], NAMES[lake], len(only), len(kept)]
            for method in ("AMIGO", "CORE-T"):
                night, file, first = R.METHODS[method]
                rec = records(night / lake / file)
                scores = [sqleval.question(goal[q], R.returned(rec.get(q), first),
                                           [got.get((q, s), {"status": "no sql"}) for s in R.returned(rec.get(q), first)],
                                           label == "multi")["all"] for q in kept]
                row.append(100 * statistics.fmean(scores) if scores else "")
            out.setdefault("relaxed_sql", []).append(dict(zip(["label", "lake", "only relaxed", "kept by stage 2",
                                                                 "AMIGO EX", "CORE-T EX"], row)))
            rows.append(row)
    lines += table("Stage 2, main writer, on the questions whose candidates are all relaxed (queries already written, "
                   "no LLM call; not tested)",
                   ["label", "lake", "questions with only relaxed candidates", "of them kept by stage 2", "AMIGO EX",
                    "CORE-T EX"], rows)


def _set_f1(targets: list[frozenset], sets: list[frozenset]) -> float:
    k = len(R.paired_up(targets, sets))
    r, p = k / len(targets), (k / len(sets) if sets else 0.0)
    return 2 * r * p / (r + p) if k else 0.0


def budget(out: dict, lines: list[str]) -> None:
    """Output size counted three ways per question: table sets (one writer prompt each), distinct
    tables, and tables with repetition (the sum of the sizes of the sets). AMIGO "within CORE-T's
    tables" keeps, per question, its first sets while their tables with repetition stay within the
    tables of CORE-T's set on that question (always its first set); not in the paper since 2026-11-09,
    so not tested. The place-judge-only run is tested against CORE-T in R, CR, P and set F1, Holm
    over the tests of one lake and label."""
    rng = np.random.default_rng(R.SEED)
    judge_only = (NEW, "abl_nojudge2/records_inf.json", False)
    for label in LABEL:
        rows, diffs, keys = [], [], R.MAIN[label]
        for lake in P.THREE:
            labels = P.labels(NIGHT, lake)[label]
            night, file, first = R.METHODS["CORE-T"]
            core = records(night / lake / file)
            room = {q: len(frozenset().union(*R.returned(core.get(q), first))) if R.returned(core.get(q), first) else 0
                    for q in labels}
            mine = records(JOINS / lake / "joinchoice" / "records_inf.json")

            def within(q):
                kept, used = [], 0
                for s in R.returned(mine.get(q), False):
                    if kept and used + len(s) > room[q]:
                        break
                    kept.append(s)
                    used += len(s)
                return kept
            methods = {name: (lambda q, got=records(n / lake / f), first=fi: R.returned(got.get(q), first))
                       for name, (n, f, fi) in R.METHODS.items() if (n / lake / f).exists()}
            methods["place judge only (no join choice)"] = (
                lambda q, got=records(judge_only[0] / lake / judge_only[1]): R.returned(got.get(q), False))
            methods["AMIGO within CORE-T's tables"] = within
            per = {}
            for name, sets_of in methods.items():
                got = {q: sets_of(q) for q in labels}
                s = scored(labels, lambda q: got[q])
                f1 = {q: _set_f1(R.targets_of(labels[q]), got[q]) for q in labels}
                per[name] = (s, f1)
                r = mean_row(list(s.values()))
                rep = statistics.fmean(sum(len(x) for x in got[q]) for q in labels)
                one = {"label": label, "lake": lake, "method": name, **r, "tables with repetition": rep,
                       "set F1": 100 * statistics.fmean(f1.values())}
                out.setdefault("budget", []).append(one)
                rows.append([NAMES[lake], name, r["sets"], r["tables"], rep, *(r[k] for k in keys), one["set F1"]])
            tests = []
            for name in ("place judge only (no join choice)",):
                for key in (*keys, "set F1"):
                    def column(m, key=key):
                        s, f1 = per[m]
                        return np.array([f1[q] if key == "set F1" else s[q]["all"][key] for q in labels])
                    tests.append((name, key, R.paired(column(name), column("CORE-T"), rng)))
            for (name, key, (d, lo, hi, _)), pv in zip(tests, R.holm([t[2][3] for t in tests])):
                cell = f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if pv < 0.05 else ''}"
                out.setdefault("budget_tests", []).append({"label": label, "lake": lake, "method": name, "score": key,
                                                           "minus CORE-T": cell, "p Holm": pv})
                diffs.append([NAMES[lake], name, key, cell])
        full = [r for r in rows if r[1] != "Route+SQL"]
        lines += table(f"Output size three ways (sets, distinct tables, tables with repetition), {LABEL[label]} (stage 1)",
                       ["lake", "method", "sets", "size", "tables with repetition", *keys, "set F1"],
                       rows + mean_worst(full, 2, len(keys) + 4, worst_low=(2, 3, 4)))
        lines += table(f"Minus CORE-T, {LABEL[label]}: points, 95% interval, Holm over the {len(keys) + 1} tests of one lake; "
                       "* when below 0.05", ["lake", "method", "score", "minus CORE-T"], diffs)


def mmqa_merged(out: dict, lines: list[str]) -> None:
    """MMQA with the tables that share a base name (customers, customers_2) taken as one table,
    in every output and in both labels; then AMIGO minus CORE-T in the main scores of the label
    (Holm over the scores of one label)."""
    rng = np.random.default_rng(R.SEED)
    methods = dict(R.METHODS)
    methods["place judge only (no join choice)"] = (NEW, "abl_nojudge2/records_inf.json", False)
    for label in LABEL:
        rows, keys = [], R.MAIN[label]
        labels = {q: [(frozenset(_based(t) for t in tables), cols) for tables, cols in queries]
                  for q, queries in P.labels(NIGHT, "mmqa")[label].items()}
        per = {}
        for name, (night, file, first) in methods.items():
            if not (night / "mmqa" / file).exists():
                continue
            got = records(night / "mmqa" / file)
            per[name] = scored(labels, lambda q: list(dict.fromkeys(
                frozenset(_based(t) for t in s) for s in R.returned(got.get(q), first))))
            r = mean_row(list(per[name].values()))
            out.setdefault("mmqa_merged", []).append({"label": label, "method": name, **r})
            rows.append([name, *(r[k] for k in keys), r["sets"], r["size"]])
        tests = [(k, R.paired(np.array([per["AMIGO"][q]["all"][k] for q in labels]),
                              np.array([per["CORE-T"][q]["all"][k] for q in labels]), rng)) for k in keys]
        diffs = [[f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if pv < 0.05 else ''}"
                  for (_, (d, lo, hi, _)), pv in zip(tests, R.holm([t[1][3] for t in tests]))]]
        lines += table(f"MMQA with tables sharing a base name taken as one, in outputs and labels, {LABEL[label]} (stage 1)",
                       ["method", *keys, "sets", "size"], rows)
        lines += table(f"MMQA with base names merged, AMIGO minus CORE-T, {LABEL[label]}: points, 95% interval, Holm over "
                       "the scores; * when below 0.05", list(keys), diffs)


def links_hidden(out: dict, lines: list[str]) -> None:
    """The link rules run again on BIRD and Spider with the declared foreign keys hidden, then with
    the declared primary keys hidden too: the pairs of tables joined by a rule link of weight 1/2 or
    more, against the pairs of tables of a declared foreign key, per rule. Judged links (an LLM call)
    are left out. Declared keys are incomplete, so a rule pair that no key declares is not always wrong."""
    edge = config.MIN_EDGE_QUALITY
    for lake in ("bird_dev", "spider_dev"):
        for hidden in ("foreign keys", "foreign and primary keys"):
            gold, by_rule = set(), {}
            with closing(layer.open_layer(lake)) as conn:
                for database in conn.execute("SELECT id, path FROM databases ORDER BY id").fetchall():
                    cards = layer._database_cards(conn, database["id"])
                    if hidden != "foreign keys":
                        cards = [{**c, "is_pk": False} for c in cards]
                    card_of = {c["id"]: c for c in cards}

                    def pair(a, b):
                        ta, tb = card_of[a]["table"], card_of[b]["table"]
                        return (database["id"], frozenset((ta, tb))) if ta != tb else None
                    gold |= {pair(a, b) for a, b in layer._database_links(conn, database["id"], ("declared",))} - {None}
                    with closing(index.open_source(database["path"])) as source:
                        inferred = links.inferred(source, cards, set())
                        linked = {(a, b): {"kind": "inferred", "score": s} for a, b, s in inferred}
                        found = links.contained(source, cards, set())
                        found += links.small_links(source, cards, set(), set(linked))
                        sure = {p for p, link in linked.items() if links.quality(link, card_of[p[0]], card_of[p[1]]) >= edge}
                        sure |= {(a, b) for a, b, s in found if s >= edge}
                        seen = {(a, b) for a, b, _ in found}
                        agreed = [x for x in links.agreeing(source, cards, set(), sure) if x[:2] not in seen]
                    edges = [p for p, link in linked.items() if links.quality(link, card_of[p[0]], card_of[p[1]]) >= edge]
                    kinds = {"inferred, text columns (containment)": [p for p in edges if card_of[p[0]]["kind"] == "text"],
                             "inferred, number columns (name rule)": [p for p in edges if card_of[p[0]]["kind"] != "text"],
                             "near-key rules (by values, by names and values, by few values)":
                                 [(a, b) for a, b, s in found + agreed if s >= edge],
                             "by name onto or out of an empty table": links.named(cards, set())}
                    for kind, pairs in kinds.items():
                        by_rule.setdefault(kind, set()).update({pair(a, b) for a, b in pairs} - {None})
            by_rule["any rule"] = set().union(*by_rule.values())
            for kind, pairs in by_rule.items():
                hit = len(pairs & gold)
                one = {"lake": lake, "hidden": hidden, "rule": kind, "rule table pairs": len(pairs),
                       "declared table pairs": len(gold), "both": hit,
                       "precision": 100 * hit / len(pairs) if pairs else None, "recall": 100 * hit / len(gold)}
                out.setdefault("links_hidden", []).append(one)
    lines += _links_lines(out)


def _links_lines(out: dict) -> list[str]:
    rows = [[NAMES[o["lake"]], o["hidden"], o["rule"], o["rule table pairs"], o["declared table pairs"], o["both"],
             o["precision"] if o["rule table pairs"] else "n/a", o["recall"]] for o in out["links_hidden"]]
    return table("Link rules with declared keys hidden: pairs of tables joined by a rule link of weight 1/2 or more, "
                 "against pairs of tables of a declared foreign key (judged links left out)",
                 ["lake", "hidden", "rule", "rule table pairs", "declared table pairs", "both", "precision", "recall"], rows)


def cut_prompts(out: dict, lines: list[str]) -> None:
    """How many place-judge prompts and join-choice prompts were cut in two because they passed
    config.PROMPT_TOKENS, counted from the "items split over" lines of the logs of the scored runs
    (the place judge from the 2026-11-08 run; MMQA's question run again after its failure counted once)."""
    rows = []
    split = re.compile(r"^(\S+ \S+) amigo\.judge judge: (\d+) items split over (\d+) calls")
    for lake in P.THREE:
        text = (NEW / lake / "logs" / "amigo.log").read_text(errors="replace").splitlines()
        runs, current = [], None
        for line in text:
            if line.startswith("==== "):
                current = []
                runs.append(current)
            elif (m := split.match(line)) and current is not None:
                current.append((int(m[2]), int(m[3])))
        main = max(runs, key=len) if runs else []
        n = len(records(JOINS / lake / "joinchoice" / "records_inf.json"))
        rows.append([NAMES[lake], n, sum(len(r) for r in runs), len(main), max((c for _, c in main), default=0),
                     min((i for r in runs for i, _ in r), default=0)])
        out.setdefault("cut_prompts", []).append(dict(zip(["lake", "questions", "place-judge prompts cut, every run",
                                                           "in the run with the most", "most calls", "fewest items"],
                                                          rows[-1])))
    cut = Counter()
    for lake in P.THREE:
        for line in (NEW / lake / "logs" / "joinchoice.log").read_text(errors="replace").splitlines():
            if split.match(line):
                cut[lake] += 1
    out["cut_join_prompts"] = dict(cut)
    lines += table("Place-judge prompts cut in two (amigo.log of the 2026-11-08 run; all are cut into the number of calls "
                   f"given). The same log line is written for AMIGO-WJ's whole judge, whose prompt holds at most "
                   f"{judge.MOST} candidates, so a cut prompt of more items is a place-judge prompt",
                   ["lake", "questions", "cut prompts, every run of the log", "cut prompts, the run with the most",
                    "most calls per prompt", "fewest items in a cut prompt"], rows)
    lines += [f"Join-choice prompts cut (joinchoice.log of each lake): "
              + ", ".join(f"{NAMES.get(k, k)} {v}" for k, v in cut.items()) + "; none on the others.", ""]


def cutoff(out: dict, lines: list[str]) -> None:
    """The place judge replaced by a cut-off without an LLM call: on each part, the places of lowest
    cost (Definition 3.3; ties by cosine) are kept, as many as the place judge kept on that part. The
    place-judge-only search (no join choice) is run again from the stored places, once with the stored
    grades and once with the cut-off, and the two are tested in R, CR and P (Holm over the three of one
    lake and label)."""
    rng = np.random.default_rng(R.SEED)
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        stored = records(NEW / lake / "abl_nojudge2" / "records_inf.json")
        source = {q: s for q, s in pickles(NEW / lake / "abl_nojudge2", mine).items()
                  if not s.get("error") and s.get("shown")}
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        runs = {"stored grades": {}, "cut-off": {}}
        for q, s in source.items():
            cut = []
            for j, part in enumerate(s["shown"]):
                n = sum(s["grades"][j].get((h.table, h.column), False) for h in part)
                keep = {(h.table, h.column) for h in sorted(part, key=lambda h: (h.cost, -h.score))[:n]}
                cut.append({(h.table, h.column): (h.table, h.column) in keep for h in part})
            stored_grades = [{(h.table, h.column): s["grades"][j].get((h.table, h.column), False) for h in part}
                             for j, part in enumerate(s["shown"])]
            for name, grades in (("stored grades", stored_grades), ("cut-off", cut)):
                places = judge.graded(s["shown"], grades)
                found = candidates.candidates(probe, graph, s["stage"], judge.MOST, graded=places)
                if not found:
                    found = judge.relaxed(probe, graph, s["stage"], places, judge.MOST, None)
                runs[name][q] = list(dict.fromkeys(frozenset(probe.path("table", t) for t in c.tables)
                                                   for c in judge.split(found, places)))
        for label in LABEL:
            labels = P.labels(NIGHT, lake)[label]
            per = {name: scored(labels, lambda q, got=got: got[q] if q in got else R.returned(stored.get(q), False))
                   for name, got in runs.items()}
            tests = [R.paired(np.array([per["cut-off"][q]["all"][k] for q in labels]),
                              np.array([per["stored grades"][q]["all"][k] for q in labels]), rng) for k in R.MAIN[label]]
            diff = {k: f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if pv < 0.05 else ''}"
                    for k, (d, lo, hi, _), pv in zip(R.MAIN[label], tests, R.holm([t[3] for t in tests]))}
            for name in runs:
                r = mean_row(list(per[name].values()))
                out.setdefault("cutoff", []).append({"lake": lake, "label": label, "places kept": name, **r,
                                                     "questions run again": len(source),
                                                     "cut-off minus stored grades": diff if name == "cut-off" else ""})
    lines += _cutoff_lines(out)


def no_value_term(out: dict, lines: list[str]) -> None:
    """The place cost without its value term: every stored place keeps its rank cost and loses the cost
    added for not storing the part's value (Holder.miss), with the place judge's stored grades unchanged.
    The place-judge-only search (no join choice, relaxed step as in AMIGO) is run again from the stored
    places, no LLM call, and tested against the saved place-judge-only output (which the search gives
    back unchanged, step caps) in the main scores of the label (Holm over the scores of one lake and label). The value
    still adds its places to the lists; only its cost is removed."""
    import dataclasses
    rng = np.random.default_rng(R.SEED)
    for lake in P.THREE:
        mine = records(Path(str(AMIGO).format(lake=lake)) / "records_inf.json")
        stored = records(NEW / lake / "abl_nojudge2" / "records_inf.json")
        source = {q: s for q, s in pickles(NEW / lake / "abl_nojudge2", mine).items()
                  if not s.get("error") and s.get("shown")}
        probe = Probe(lake)
        graph = candidates.Graph(probe)
        got, changed = {}, 0
        for q, s in source.items():
            shown = [[dataclasses.replace(h, cost=h.cost - h.miss, miss=0.0) for h in part] for part in s["shown"]]
            changed += any(h.miss for part in s["shown"] for h in part)
            grades = [{(h.table, h.column): s["grades"][j].get((h.table, h.column), False) for h in part}
                      for j, part in enumerate(shown)]
            places = judge.graded(shown, grades)
            found = candidates.candidates(probe, graph, s["stage"], judge.MOST, graded=places)
            if not found:
                found = judge.relaxed(probe, graph, s["stage"], places, judge.MOST, None)
            got[q] = list(dict.fromkeys(frozenset(probe.path("table", t) for t in c.tables)
                                        for c in judge.split(found, places)))
        for label in LABEL:
            labels = P.labels(NIGHT, lake)[label]
            per = {"stored costs": scored(labels, lambda q: R.returned(stored.get(q), False)),
                   "without the value term": scored(labels, lambda q: got[q] if q in got else R.returned(stored.get(q), False))}
            tests = [R.paired(np.array([per["without the value term"][q]["all"][k] for q in labels]),
                              np.array([per["stored costs"][q]["all"][k] for q in labels]), rng) for k in R.MAIN[label]]
            diff = {k: f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if pv < 0.05 else ''}"
                    for k, (d, lo, hi, _), pv in zip(R.MAIN[label], tests, R.holm([t[3] for t in tests]))}
            for name in per:
                r = mean_row(list(per[name].values()))
                out.setdefault("no_value_term", []).append({
                    "lake": lake, "label": label, "costs": name, **r, "questions run again": len(source),
                    "questions with a value term": changed,
                    "minus stored costs": diff if name != "stored costs" else ""})
    lines += _no_value_lines(out)


def _no_value_lines(out: dict) -> list[str]:
    lines = []
    for label in LABEL:
        keys, mine = R.MAIN[label], [o for o in out["no_value_term"] if o["label"] == label]
        rows = [[NAMES[o["lake"]], o["costs"], *(o[k] for k in keys), o["sets"], o["size"], o["questions run again"],
                 o["questions with a value term"]] for o in mine]
        diffs = [[NAMES[o["lake"]], *(o["minus stored costs"][k] for k in keys)] for o in mine if o["minus stored costs"]]
        n = len(keys)
        lines += (table("Place judge only (no join choice), search run again from the stored places with the stored "
                        "grades and the place cost without its value term (no LLM call), against the saved output, "
                        f"{LABEL[label]}", ["lake", "costs", *keys, "sets", "size", "questions run again",
                                            "questions with a value term"],
                        rows + mean_worst(rows, 2, n + 2, worst_low=(n + 2, n + 3)))
                  + table(f"Without the value term minus stored costs, {LABEL[label]}: points, 95% interval, Holm over "
                          "the scores of one lake; * when below 0.05", ["lake", *keys], diffs))
    return lines


def link_kinds(out: dict, lines: list[str]) -> None:
    """The inferred links of each built layer, split by the kind of their column (text: containment of
    1/2 alone; number: the name rule), and those whose weight reaches the edge threshold; no LLM call."""
    edge = config.MIN_EDGE_QUALITY
    rows = []
    for lake in P.THREE:
        count = Counter()
        with closing(layer.open_layer(lake)) as conn:
            for database in conn.execute("SELECT id FROM databases ORDER BY id").fetchall():
                card_of = {c["id"]: c for c in layer._database_cards(conn, database["id"])}
                for (a, b), link in layer._database_links(conn, database["id"], ("inferred",)).items():
                    kind = "text" if card_of[a]["kind"] == "text" else "number"
                    count[kind] += 1
                    count[kind + " edges"] += links.quality(link, card_of[a], card_of[b]) >= edge
        one = {"lake": lake, **{k: count[k] for k in ("text", "text edges", "number", "number edges")}}
        out.setdefault("link_kinds", []).append(one)
        rows.append([NAMES[lake], one["text"], one["text edges"], one["number"], one["number edges"]])
    lines += table("Inferred links of the built layers by the kind of their column, and those whose weight reaches the "
                   "edge threshold of 1/2", ["lake", "text column links", "of them edges", "number column links",
                                             "of them edges"], rows)


def _cutoff_lines(out: dict) -> list[str]:
    lines = []
    for label in LABEL:
        keys, mine = R.MAIN[label], [o for o in out["cutoff"] if o["label"] == label]
        rows = [[NAMES[o["lake"]], o["places kept"], *(o[k] for k in keys), o["sets"], o["size"],
                 o["questions run again"]] for o in mine]
        diffs = [[NAMES[o["lake"]], *(o["cut-off minus stored grades"][k] for k in keys)]
                 for o in mine if o["cut-off minus stored grades"]]
        n = len(keys)
        lines += (table("Place judge only (no join choice), search run again from the stored places: with the place "
                        "judge's grades, and with a cut-off that keeps on each part the places of lowest cost, as many "
                        f"as the judge kept (no LLM call), {LABEL[label]}",
                        ["lake", "places kept", *keys, "sets", "size", "questions run again"],
                        rows + mean_worst(rows, 2, n + 2, worst_low=(n + 2, n + 3)))
                  + table(f"Cut-off minus the place judge's grades, {LABEL[label]}: points, 95% interval, Holm over the "
                          "scores of one lake; * when below 0.05", ["lake", *keys], diffs))
    return lines


def mean_ci(out: dict, lines: list[str]) -> None:
    """95% percentile intervals of the per-version means of the label's main scores, resampling questions."""
    rng = np.random.default_rng(R.SEED)
    rows = {label: [] for label in LABEL}
    for label in LABEL:
        for lake in P.THREE:
            got = R.score(lake)[label]
            for name, per_q in got.items():
                cells = []
                for key in R.MAIN[label]:
                    x = np.array([s["all"][key] for s in per_q.values()])
                    boot = x[rng.integers(0, len(x), (R.RESAMPLES, len(x)))].mean(axis=1)
                    lo, hi = np.percentile(boot, [2.5, 97.5])
                    cells.append(f"{100 * x.mean():.1f} [{100 * lo:.1f}, {100 * hi:.1f}]")
                    out.setdefault("mean_ci", []).append({"label": label, "lake": lake, "method": name, "score": key,
                                                          "mean": 100 * x.mean(), "low": 100 * lo, "high": 100 * hi})
                rows[label].append([NAMES[lake], name, *cells])
    widest = max(o["high"] - o["low"] for o in out["mean_ci"])
    for label in LABEL:
        lines += table(f"Per-version means with 95% intervals (bootstrap over questions), {LABEL[label]}; widest interval "
                       f"over both labels {widest:.1f} points", ["lake", "method", *R.MAIN[label]], rows[label])


STEPS = {"top_m": top_m, "equal_size": equal_size, "relaxed": relaxed, "odds": odds, "kinds": kinds,
         "mmqa_file": mmqa_file, "tokens": tokens, "hints": hints, "failed": failed, "caps": caps,
         "misses": misses, "ambiguity": ambiguity, "cap_sizes": cap_sizes, "judges": judges, "no_copies": no_copies,
         "one_to_one": one_to_one, "first_hints": first_hints, "fallbacks": fallbacks, "links_held": links_held,
         "detection": detection, "votes": votes, "shape": shape, "example": example, "costs": costs,
         "cross_db": cross_db, "alternatives_only": alternatives_only,
         "sql_top_m": sql_top_m, "few_values": few_values,
         "order": order, "odds_exact": odds_exact, "left_out": left_out,
         "first_match": first_match, "result_p_sv": result_p_sv, "dense_by_db": dense_by_db,
         "column_order": column_order, "mean_tests": mean_tests, "result_p_failed": result_p_failed,
         "extra_tables": extra_tables, "sensitivity": sensitivity, "reach_rule": reach_rule,
         "value_only": value_only, "input_tokens": input_tokens, "relaxed_sql": relaxed_sql,
         "budget": budget, "mmqa_merged": mmqa_merged, "links_hidden": links_hidden, "cut_prompts": cut_prompts,
         "mean_ci": mean_ci, "cutoff": cutoff, "no_value_term": no_value_term, "link_kinds": link_kinds}
SLOW = {"caps": _caps_lines, "cap_sizes": _cap_lines, "column_order": _column_lines, "sensitivity": _sens_lines,
        "links_hidden": _links_lines, "cutoff": _cutoff_lines, "no_value_term": _no_value_lines}


def main() -> None:
    """Every step. The caps and cap_sizes steps run the search again and take long: when step
    names are given and one of them is not among them, its stored result is kept."""
    chosen = sys.argv[1:] or list(STEPS)
    old = json.loads((HERE / "review.json").read_text()) if (HERE / "review.json").exists() else {}
    out, lines = {}, ["# Answers to review rounds 1 to 3 (stage 1 of docs/eval_protocol.md, no LLM call)", "",
                      "Scored with experiments/protocol.py on existing outputs. Gold label: R, CR, P, CR= per target "
                      "against its matched set; multi-valid label: IR, ICR, IP and their strict forms IR=, ICR=, IP= from "
                      "a one-to-one pairing (paper Section 4.1). Averaged per question, then over questions. size: mean "
                      "tables per returned set, per question, then over the questions with a set.", ""]
    for name, step in STEPS.items():
        if name in chosen:
            step(out, lines)
        elif name in SLOW and name in old:
            out[name] = old[name]
            lines += SLOW[name](out)
        else:
            step(out, lines)
        (HERE / "review.json").write_text(json.dumps(out, indent=1, default=str))
        (HERE / "review.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
