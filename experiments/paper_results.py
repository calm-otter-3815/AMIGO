"""Every table and figure of the night evaluation (docs/night-eval-2026-10-20.md, sections 6.7,
8, 9, 10.2 and 12). Reads the night folder, writes only the results folder. No LLM call.

  .venv/bin/python experiments/paper_results.py COMMAND [--night DIR] [--out DIR]

COMMAND is sets, scores, latency, build, runs, tables, figures, readme or all (every one, in
that order). A command whose inputs are missing writes "not run yet" rows and goes on.

Scoring (changed from section 8 on 2026-10-21): only tables. Table level: R, CR, P, F1 of every
returned table pooled against every table of the label. Footprint level: each table set of the
label against each returned set (a top-k list is one set, an AMIGO interpretation one set),
soft (the returned set holds it) and exact (equal). Column scores: AMIGO only. A failed question
(a baseline record with an error, a missing record, an unreadable file) is scored as an empty
answer and counted in `failed`; an AMIGO answer saved with a judge error is scored as returned
and counted too. Every method of a lake is scored on the same ids (sets.json).
"""

import argparse
import csv
import json
import os
import pickle
import random
import re
import sqlite3
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_lakes  # noqa: E402
import latency  # noqa: E402

ROOT = eval_lakes.ROOT
NIGHT = ROOT / "runs" / "paper_2026-10-20"
OUT = ROOT / "experiments" / "results" / "eval_2026-10-20"
LABELER = ROOT / "runs" / "labeler"
LAKES = {"bird_dev": "BIRD", "spider_dev": "Spider", "mmqa": "MMQA", "spider2_lite": "Spider 2.0-Lite",
         "taco_us": "TACO-US"}
THREE = ("bird_dev", "spider_dev", "mmqa")
VARIANTS = ("gold", "multi", "multi_amb")
EMPTY = {"picked": [], "interpretations": [], "levels": ["tables"]}
NOT_RUN = "not run yet"
WARM = 2  # latency: the first questions of each block are warm-up, not timed
AMIGO_COLOR = "#2a78d6"


def _fixed(name: str, prefix: str, color: str, marker: str) -> dict:
    return {"name": name, "kind": "fixed", "tags": {f"k{n}": f"{prefix}{n}" for n in (1, 3, 5)},
            "color": color, "marker": marker}


def _variable(name: str, tag: str, color: str, marker: str) -> dict:
    return {"name": name, "kind": "variable", "tags": {"var": tag}, "color": color, "marker": marker}


# every method: display name, kind, tag of each setting, legend colour and marker
METHODS = {
    "dense": _fixed("dense", "bl_dense_k", "#eb6834", "o"),
    "bm25": _fixed("BM25", "bl_bm25_k", "#1baf7a", "s"),
    "hybrid": _fixed("hybrid", "bl_hybrid_k", "#eda100", "D"),
    "jar": _fixed("JAR", "bl_jar_k", "#e87ba4", "^"),
    "greedy_jar": _fixed("Greedy JAR", "bl_greedy_jar_k", "#008300", "v"),
    "crush4sql": _fixed("CRUSH4SQL", "bl_crush4sql_t", "#6250d6", "P"),
    "murre": _fixed("MURRE", "bl_murre_k", "#e34948", "X"),
    "core_t": _variable("CORE-T", "bl_core_t", "#52514e", "h"),
    "route_sql": _variable("Route+SQL", "bl_route_sql", "#8a8987", "p"),
    "full_schema": _variable("full schema", "bl_full_schema", "#b5b4b0", "*"),
    "amigo": {"name": "AMIGO", "kind": "variable", "color": AMIGO_COLOR, "marker": "o",
              "tags": {"var": "amigo@inf", **{f"k{n}": f"amigo@inf:cover{n}" for n in (1, 3, 5)},
                       **{f"w{w}": f"amigo@{w}" for w in range(7)}}},
}
# AMIGO with one part removed (5.4); N1 is AMIGO run again on 150 BIRD questions
ABLATIONS = {
    "abl_nojudge2": ("A1", "judge call 2"),
    "abl_norelaxed": ("A2", "relaxed fallback"),
    "abl_nojudge": ("A3", "both judge calls"),
    "abl_nojudge1": ("A4", "judge call 1"),
    "abl_nojudgedlinks": ("A5", "LLM-judged join links"),
    "abl_novalues": ("A6", "value lookup"),
}
COLUMN_LEVEL = ("amigo", "route_sql")
# latency: the run timed for each method; one run gives every k of a cut method
TIMED = [("dense", "any k", "bl_dense_k5"), ("bm25", "any k", "bl_bm25_k5"), ("hybrid", "any k", "bl_hybrid_k5"),
         ("jar", "k1", "bl_jar_k1"), ("jar", "k3", "bl_jar_k3"), ("jar", "k5", "bl_jar_k5"),
         ("greedy_jar", "any k", "bl_greedy_jar_k5"), ("crush4sql", "any k", "bl_crush4sql_b100"),
         ("murre", "any k", "bl_murre_k5"), ("core_t", "-", "bl_core_t"), ("route_sql", "-", "bl_route_sql"),
         ("full_schema", "-", "bl_full_schema"), ("amigo", "default", "amigo")]
BUILD_STEPS = ("schema", "profile", "describe", "names", "index", "words", "links", "more_links",
               "judged_links", "roles", "embed")
LLM_STEPS = ("describe", "judged_links")
CUT_TAG = re.compile(r"bl_(dense|murre|greedy_jar|bm25|hybrid)_k[13]|bl_crush4sql_t\d+")


# ---- small helpers

def _lines(path: Path) -> list[dict]:
    out = []
    if path.exists():
        for line in filter(None, path.read_text().split("\n")):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:  # a line cut at kill time
                pass
    return out


def _write_csv(path: Path, head: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(head)
        out.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return [r for r in csv.DictReader(f) if NOT_RUN not in r.values()]


def _questions(night: Path, lake: str) -> Path:
    if lake == "spider2_lite":  # no multi-valid label: its gold SQL is mostly hidden
        return night / "questions" / "spider2_lite.jsonl"
    return night / "questions" / "taco_us_A.jsonl" if lake == "taco_us" else LABELER / lake / "questions.jsonl"


def _built(night: Path, lake: str) -> bool:
    return (night / "lakes" / lake / "layer.sqlite").exists()


# ---- sets: the question ids of each variant

_LABELS: dict = {}


def labels(night: Path, lake: str) -> dict[str, dict[str, list]]:
    """{variant: {id: the label's queries as (tables, columns)}}, ids in file order."""
    if lake not in _LABELS:
        rows = eval_lakes._lines(_questions(night, lake))
        gold = {q: [pair] for q, pair in eval_lakes._gold(rows).items()}
        for row in rows:
            if row.get("tables_alt"):  # Spider 2.0-Lite: a gold view, or the tables it reads
                names = eval_lakes.Gold(lake).names
                gold[row["id"]] = [({names[(row["db_id"], t.lower())] for t in ts}, set())
                                   for ts in (row["tables"], row["tables_alt"])]
        multi, _ = eval_lakes._label(rows)
        order = [r["id"] for r in rows]
        gold = {q: gold[q] for q in order if q in gold}
        multi = {q: multi[q] for q in order if q in multi}
        amb = {q: v for q, v in multi.items() if len({frozenset(t) for t, _ in v}) > 1}
        _LABELS[lake] = {"gold": gold, "multi": multi, "multi_amb": amb}
    return _LABELS[lake]


def _lakes(night: Path) -> list[str]:
    return [lake for lake in LAKES if _questions(night, lake).exists() and _built(night, lake)]


def sets(night: Path, out: Path) -> None:
    got = {lake: {v: list(ids) for v, ids in labels(night, lake).items()} for lake in _lakes(night)}
    path = night / "questions" / "sets.json"
    path.write_text(json.dumps(got))
    print("sets.json: " + ", ".join(f"{lake} " + "/".join(str(len(v)) for v in s.values()) for lake, s in got.items()))


# ---- scores

def records(folder: Path, tag: str) -> dict | None:
    """The records of `tag` (name, name@W, name@W:cut) in a lake folder: None when the
    method did not run there; {} for a file that cannot be read (cut at kill time)."""
    name = tag.partition(":")[0]
    name, _, within = name.partition("@")
    path = folder / name / (f"records_{float(within)}.json" if within else "records.json")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def answer(got: dict, qid: str, tag: str) -> tuple[dict, bool]:
    """(the record to score, failed) by the failure rule of 8.3."""
    one = got.get(qid)
    failed = one is None or "error" in one or bool(one.get("judge_error"))
    if one is None or "error" in one:
        one = EMPTY
    how = tag.partition(":")[2]
    return (eval_lakes.cut(one, how) if how else one), failed


def metrics(queries: list, record: dict, columns: bool = False) -> dict:
    """One question's metrics: R, CR, P, F1 at the table level; s* and e* at the footprint
    level, soft and exact; whether the label has no table or the answer none; the column and
    interpretation levels for a method that names columns."""
    own = eval_lakes.measure(queries, record)
    out = {k: own["tables"][key] for k, key in (("R", "recall"), ("CR", "complete"), ("P", "precision"), ("F1", "f1"))}
    for x, hit in (("s", "soft"), ("e", "exact")):
        out |= {x + k: own["footprint"][hit][key] for k, key in (("R", "recall"), ("CR", "complete"),
                                                                 ("P", "precision"), ("F1", "f1"))}
    out |= {"t" + k: own["interpretation_tables"][key] for k, key in (("R", "recall"), ("CR", "complete"),
                                                                      ("P", "precision"), ("F1", "f1"),
                                                                      ("SP", "set_precision"))}
    out |= {"size": float(own["size"]), "count": float(own["count"]),
            "no_gold": float(not any(t for t, _ in queries)), "no_answer": float(not own["size"])}
    if columns:
        full = eval_lakes.measure(queries, {**record, "levels": eval_lakes.LEVELS})
        for x, level in (("c", "columns"), ("i", "interpretation")):
            out |= {x + k: full[level][key] for k, key in (("R", "recall"), ("CR", "complete"),
                                                           ("P", "precision"), ("F1", "f1"))}
    return out


def _runs_of(night: Path) -> list[tuple[str, str, str, Path, str]]:
    """(method, setting, tag, folder, lake) of everything scored."""
    out = []
    for lake in _lakes(night):
        for method, spec in METHODS.items():
            out += [(method, s, tag, night / lake, lake) for s, tag in spec["tags"].items()]
        out += [(name, "var", f"{name}@inf", night / lake, lake) for name in ABLATIONS]
        if lake == "bird_dev":
            out.append(("noise", "var", "amigo@inf", night / lake / "noise", lake))
    return out


def per_question(night: Path) -> dict:
    """{(lake, method, setting): {variant: ({id: metrics}, failed ids)}} for every run on disk."""
    out = {}
    for method, setting, tag, folder, lake in _runs_of(night):
        got = records(folder, tag)
        if got is None:
            continue
        cols = method in COLUMN_LEVEL or method in ABLATIONS or method == "noise"
        row = {}
        for variant, label in labels(night, lake).items():
            ids = list(label)
            if method == "noise":  # N1 ran on its 150 questions only
                ids = [q for q in ids if q in got]
            scored, failed = {}, []
            for q in ids:
                rec, bad = answer(got, q, tag)
                scored[q] = metrics(label[q], rec, cols)
                if bad:
                    failed.append(q)
            row[variant] = (scored, failed)
        out[(lake, method, setting)] = row
    return out


SCORE_LEVEL = {"R": ("table", "R"), "CR": ("table", "CR"), "P": ("table", "P"), "F1": ("table", "F1"),
               "size": ("table", "size"), "count": ("table", "count"),
               "no_gold": ("table", "no_gold"), "no_answer": ("table", "no_answer"),
               **{x + k: (f"footprint_{hit}", k) for x, hit in (("s", "soft"), ("e", "exact")) for k in ("R", "CR", "P", "F1")},
               **{x + k: (level, k) for x, level in (("c", "column"), ("i", "interpretation"),
                                                     ("t", "interpretation_tables"))
                  for k in ("R", "CR", "P", "F1")}, "tSP": ("interpretation_tables", "SP")}


def summarize(pq: dict) -> list[list]:
    """scores.csv rows: per lake the mean over its questions, then mean and worst over 3 and 4 lakes."""
    rows, means = [], defaultdict(dict)
    for (lake, method, setting), variants in pq.items():
        for variant, (scored, failed) in variants.items():
            if not scored:
                continue
            keys = next(iter(scored.values())).keys()
            one = {k: statistics.fmean(s[k] for s in scored.values()) for k in keys}
            means[(variant, method, setting)][lake] = (one, len(scored), len(failed))
            rows += [[variant, lake, method, setting, *SCORE_LEVEL[k], round(v, 6), len(scored), len(failed)]
                     for k, v in one.items()]
    for (variant, method, setting), by_lake in means.items():
        if method == "noise":
            continue
        for pool in (THREE, tuple(LAKES)):
            if not all(lake in by_lake for lake in pool):
                continue
            n = sum(by_lake[lake][1] for lake in pool)
            failed = sum(by_lake[lake][2] for lake in pool)
            for k in by_lake[pool[0]][0]:
                values = [by_lake[lake][0][k] for lake in pool]
                worst = max(values) if k in ("size", "count", "no_gold", "no_answer") else min(values)  # the worst lake returns the most
                for name, value in ((f"mean{len(pool)}", statistics.fmean(values)), (f"worst{len(pool)}", worst)):
                    rows.append([variant, name, method, setting, *SCORE_LEVEL[k], round(value, 6), n, failed])
    return rows


def compare(pq: dict) -> list[list]:
    """paired.csv rows: AMIGO against each method setting and each ablation, per variant and lake.
    Every lead is AMIGO minus the other."""
    rows = []
    for (lake, method, setting), variants in pq.items():
        if method == "amigo" or (lake, "amigo", "var") not in pq:
            continue
        for variant, (scored, _) in variants.items():
            mine = pq[(lake, "amigo", "var")][variant][0]
            ids = [q for q in scored if q in mine]
            if not ids:
                continue
            wrap = lambda s: {q: {"tables": {"complete": s[q]["CR"], "f1": s[q]["F1"], "precision": s[q]["P"]}}  # noqa: E731
                              for q in ids}
            v = eval_lakes._paired(wrap(mine), wrap(scored), ids, random.Random(0))
            name = method if setting == "var" else f"{method}_{setting}"
            rows.append([variant, lake, name, v["cr_won"], v["cr_lost"], round(v["sign_p"], 6),
                         *(round(v[f"{m}_{x}"], 6) for m in ("f1", "cr", "p") for x in ("lead", "low", "high"))])
    return rows


SCORES_HEAD = ["variant", "lake", "method", "setting", "level", "metric", "value", "questions", "failed"]
PAIRED_HEAD = ["variant", "lake", "method", "cr_won", "cr_lost", "sign_p", "f1_lead", "f1_low", "f1_high",
               "cr_lead", "cr_low", "cr_high", "p_lead", "p_low", "p_high"]


def scores(night: Path, out: Path) -> None:
    pq = per_question(night)
    if not pq:
        _write_csv(out / "scores.csv", SCORES_HEAD, [[NOT_RUN] * len(SCORES_HEAD)])
        _write_csv(out / "paired.csv", PAIRED_HEAD, [[NOT_RUN] * len(PAIRED_HEAD)])
        return
    _write_csv(out / "scores.csv", SCORES_HEAD, summarize(pq))
    _write_csv(out / "paired.csv", PAIRED_HEAD, compare(pq) or [[NOT_RUN] * len(PAIRED_HEAD)])


# ---- latency (section 9)

def _real_calls(lines: list[dict], qid: str) -> int:
    return sum(one.get("question") == qid and "response_id" in one and not one.get("cached") for one in lines)


def _timed_seconds(folder: Path, tag: str, ids: list[str]) -> dict[str, dict]:
    """Each question's seconds, the total and its steps."""
    if tag == "amigo":
        split = eval_lakes._load(folder / "split_medium.json")
        out = {}
        for q in ids:
            path = folder / "amigo" / f"{q}.amigo.pkl"
            if path.exists() and "seconds" in split.get(q, {}):
                got = pickle.loads(path.read_bytes())
                if not got.get("error"):
                    s = dict(got["seconds"])
                    out[q] = {"llm split": split[q]["seconds"], **s, "total": s["total"] + split[q]["seconds"]}
        return out
    got = records(folder, tag) or {}
    return {q: got[q]["seconds"] for q in ids if q in got and "error" not in got[q]}


def latency_rows(night: Path) -> list[list]:
    rows = []
    for lake in LAKES:
        folder = night / "timing" / lake
        if not (folder / "questions.jsonl").exists():
            continue
        ids = [r["id"] for r in _lines(folder / "questions.jsonl")][WARM:]
        state = json.loads((folder / "block_state.json").read_text()) if (folder / "block_state.json").exists() else {}
        for method, setting, tag in TIMED:
            secs = _timed_seconds(folder, tag, ids)
            if not secs:
                continue
            monitor = _lines(folder / f"monitor_{tag}.jsonl")
            logs = [folder / "split_medium.jsonl", *(folder / "amigo").glob("*.jsonl")] if tag == "amigo" \
                else [folder / tag / "llm.jsonl"]
            lines = [one for p in logs for one in _lines(p)]
            windows = state.get("windows", {}).get(tag, {})
            flagged = sum(any(latency.flagged(tuple(w), monitor, _real_calls(lines, q)) for w in windows.get(q, []))
                          for q in ids)
            hits = [m for m in monitor if "prefix_queries" in m]
            asked = hits[-1]["prefix_queries"] - hits[0]["prefix_queries"] if len(hits) > 1 else 0
            share = round((hits[-1]["prefix_hits"] - hits[0]["prefix_hits"]) / asked, 4) if asked else ""
            calls = statistics.fmean(_real_calls(lines, q) for q in secs)
            steps = list(dict.fromkeys(k for s in secs.values() for k in s if k != "total")) + ["total"]
            for step in steps:
                values = [s.get(step, 0.0) for s in secs.values()]
                rows.append([lake, method, setting, step, len(values), round(statistics.fmean(values), 3),
                             round(statistics.median(values), 3), round(float(np.percentile(values, 90)), 3),
                             flagged, share])
            rows.append([lake, method, setting, "llm calls per question", len(secs), round(calls, 3), "", "", flagged, share])
    return rows


LATENCY_HEAD = ["lake", "method", "setting", "step", "n", "mean_s", "median_s", "p90_s", "flagged", "prefix_hit_share"]


def latency_cmd(night: Path, out: Path) -> None:
    _write_csv(out / "latency.csv", LATENCY_HEAD, latency_rows(night) or [[NOT_RUN] * len(LATENCY_HEAD)])


# ---- build (section 9.4)

def _local(stamp: str) -> datetime:
    """A log time (UTC, with its zone) as local wall time, the build meta's clock."""
    return datetime.fromisoformat(stamp).astimezone().replace(tzinfo=None)


def build_rows(night: Path) -> list[list]:
    rows = []
    for lake in LAKES:
        path = night / "lakes" / lake / "layer.sqlite"
        if not path.exists():
            continue
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        conn.close()
        lines = [one for one in _lines(ROOT / "runs" / f"build_{lake}.jsonl") if "time" in one]
        load = "shared" if lake == "taco_us" else "exclusive"
        for step in BUILD_STEPS:
            if f"seconds_{step}" not in meta:
                continue
            seconds = float(meta[f"seconds_{step}"])
            end = datetime.fromisoformat(meta[f"step_{step}"])
            start = end - timedelta(seconds=seconds)
            mine = [one for one in lines if start <= _local(one["time"]) <= end]
            rows.append([lake, step, seconds, sum("response_id" in one for one in mine),
                         sum(one["usage"]["input_tokens"] for one in mine),
                         sum(one["usage"]["output_tokens"] for one in mine), load])
        # baseline preparation: the setup lap of the first question
        for folder in sorted((night / "build" / lake / "prep").glob("bl_*")):
            got = records(night / "build" / lake / "prep", folder.name) or {}
            first = next((r for r in got.values() if "seconds" in r), None)
            if first:
                log = _lines(folder / "llm.jsonl")
                rows.append([lake, f"prep {folder.name}", first["seconds"].get("setup", 0.0),
                             sum("response_id" in one for one in log), sum(one["usage"]["input_tokens"] for one in log),
                             sum(one["usage"]["output_tokens"] for one in log), load])
    return rows


BUILD_HEAD = ["lake", "step", "seconds", "llm_calls", "input_tokens", "output_tokens", "load"]


def build_cmd(night: Path, out: Path) -> None:
    _write_csv(out / "build.csv", BUILD_HEAD, build_rows(night) or [[NOT_RUN] * len(BUILD_HEAD)])


# ---- runs (section 9.5)

def _gpu(night: Path) -> tuple[float, float]:
    """All output tokens of the night and the GPU busy hours (minutes with a running request)."""
    lines = _lines(night / "driver" / "gpu.jsonl")
    tokens = [one["generation_tokens_total"] for one in lines if "generation_tokens_total" in one]
    total = tokens[-1] - tokens[0] if len(tokens) > 1 else 0.0
    return total, sum(one.get("running", 0) > 0 for one in lines) / 60


def _releases(night: Path) -> dict[tuple[str, str], str]:
    """(lake, tag) -> the release of the job that ran it."""
    path = night / "driver" / "jobs.json"
    out = {}
    for job in json.loads(path.read_text()) if path.exists() else []:
        state_path = night / "driver" / "state" / f"{job['id']}.json"
        release = json.loads(state_path.read_text()).get("release", "") if state_path.exists() else ""
        for step in job["steps"]:
            try:
                parts = Path(step["log"]).relative_to(night).parts
            except ValueError:
                continue
            if step.get("tag") and len(parts) > 1:
                out[(parts[0], "noise" if parts[1] == "noise" else step["tag"])] = release
    return out


def runs_rows(night: Path) -> list[list]:
    total, busy = _gpu(night)
    releases = _releases(night)
    names = {tag.partition("@")[0]: (m, s) for m, spec in METHODS.items() for s, tag in spec["tags"].items()}
    names |= {f"bl_jar_k{n}": ("jar", f"k{n}") for n in (1, 3, 5)}
    names |= {"bl_dense_k5": ("dense", "k5"), "bl_murre_k5": ("murre", "k5"), "bl_crush4sql_b100": ("crush4sql", "b100"),
              "bl_greedy_jar_k5": ("greedy_jar", "k5"), "bl_bm25_k5": ("bm25", "k5"), "bl_hybrid_k5": ("hybrid", "k5"),
              "amigo": ("amigo", "var")}
    rows = []
    for lake in LAKES:
        for folder, tag in [(night / lake / t, t) for t in [*names, *ABLATIONS]] + [(night / lake / "noise" / "amigo", "noise")]:
            if not folder.is_dir() or CUT_TAG.fullmatch(tag):
                continue
            method, setting = names.get(tag, (tag, "var"))
            pkls = list(folder.glob("*.amigo.pkl"))
            if pkls:
                saved = []
                for p in pkls:
                    try:
                        saved.append(pickle.loads(p.read_bytes()))
                    except Exception:  # noqa: BLE001 - cut at kill time: failed
                        saved.append({"error": "unreadable"})
                questions, failed = len(saved), sum(bool(s.get("error")) for s in saved)
                logs = [folder / "judge.jsonl"]
                if tag in ("amigo", "noise"):
                    logs.append(folder.parent / "split_medium.jsonl")
            else:
                got = records(folder.parent, tag) or {}
                questions, failed = len(got), sum("error" in r for r in got.values())
                logs = [folder / "llm.jsonl"]
            lines = [one for p in logs for one in _lines(p)]
            calls = sum("response_id" in one or bool(one.get("cached")) for one in lines)
            out_tokens = sum(one.get("usage", {}).get("output_tokens", 0) for one in lines)
            retried = len({one.get("question") for one in lines if "error" in one or one.get("attempt", 1) > 1})
            gpu = round(out_tokens / total * busy, 3) if total else ""
            rows.append([lake, method, setting, questions, failed, retried, calls, out_tokens, gpu,
                         releases.get((lake, tag), "")])
    return rows


RUNS_HEAD = ["lake", "method", "setting", "questions", "failed", "retried", "llm_calls", "output_tokens",
             "gpu_hours", "release"]


def runs_cmd(night: Path, out: Path) -> None:
    _write_csv(out / "runs.csv", RUNS_HEAD, runs_rows(night) or [[NOT_RUN] * len(RUNS_HEAD)])


# ---- tables (section 12.1)

def _pct(x) -> str:
    return "-" if x is None else f"{100 * x:.1f}"


def _num(x) -> str:
    return "-" if x is None else f"{x:.1f}"


class Scores:
    def __init__(self, out: Path):
        self.v = {}
        self.n = {}
        for r in _read_csv(out / "scores.csv"):
            key = (r["variant"], r["lake"], r["method"], r["setting"])
            self.v[key + (r["level"], r["metric"])] = float(r["value"])
            self.n[key] = (int(r["questions"]), int(r["failed"]))

    def get(self, variant, lake, method, setting, level, metric):
        return self.v.get((variant, lake, method, setting, level, metric))

    def has(self, variant, lake, method, setting) -> bool:
        return (variant, lake, method, setting) in self.n

    def pool(self) -> str:
        """4 when every method planned for TACO-US finished stage A, else 3."""
        planned = [m for m in METHODS if m not in ("route_sql", "full_schema")]
        return "4" if all(self.has("multi", "taco_us", m, "var" if METHODS[m]["kind"] == "variable" else "k3")
                          for m in planned) else "3"


# AMIGO, then AMIGO with judge call 2, call 1 or both left out (A1, A4, A3)
JUDGE_ROWS = {"abl_nojudge2": "AMIGO, judge call 1 only", "abl_nojudge1": "AMIGO, judge call 2 only",
              "abl_nojudge": "AMIGO, no judge"}
ROWS = [(m, s) for m in METHODS if m != "amigo" for s in METHODS[m]["tags"]] + [("amigo", "var")] + \
    [(m, "var") for m in JUDGE_ROWS]
FOOT = "n = questions per lake; failures count as described in 8.3."


def _lake_name(lake: str, n: int | None = None) -> str:
    if lake.startswith("mean"):
        return "mean"
    if lake.startswith("worst"):
        return "worst lake"
    return f"{LAKES[lake]} (n={n})" if n is not None else LAKES[lake]


LABEL_NAME = {"gold": "gold label (the gold query alone)", "multi": "multi-valid label",
              "multi_amb": "multi-valid label, ambiguous questions only"}
# main scores first, on the table sets each interpretation holds (a list is one set): equal to a
# label's set (exact), or each label query against the closest set (interp.); then every table
# pooled, the one level a table retriever's list is scored on as it is
SCORE_KEYS = [(level, k) for level in ("footprint_exact", "interpretation_tables") for k in ("R", "CR", "P")] + \
    [("interpretation_tables", "SP")] + \
    [("table", k) for k in ("R", "CR", "P", "F1")] + [("footprint_soft", k) for k in ("R", "CR", "P")]
SCORE_HEAD = ["exact R", "exact CR", "exact P", "interp. R", "interp. CR", "interp. P", "interp. set P",
              "pooled R", "pooled CR", "pooled P", "pooled F1", "soft R", "soft CR", "soft P"]
# one gold set: footprint R equals CR and footprint P counts every other valid set as wrong. Soft R
# equals table CR for one returned set, not for several: AMIGO's sets can pool the gold tables
# without one set holding them all. Exact R: one set is the gold tables, nothing more.
GOLD_KEYS = [("footprint_exact", "R"), *SCORE_KEYS[3:11], ("footprint_soft", "R")]
GOLD_HEAD = ["exact match", *SCORE_HEAD[3:11], "soft match"]


def _score_table(sc: Scores, variant: str, lake: str, title: str) -> list[str]:
    """One lake (or mean / worst) under one label: every method, both levels."""
    rows = [(m, s) for m, s in ROWS if sc.has(variant, lake, m, s)]
    if not rows:
        return []
    n = sc.n[(variant, lake, *rows[0])][0]
    no_gold = sc.get(variant, lake, *rows[0], "table", "no_gold")
    keys, names = (GOLD_KEYS, GOLD_HEAD) if variant == "gold" else (SCORE_KEYS, SCORE_HEAD)
    head = ["method", "k", "tables / q", *names, "no answer", "failed"]
    out = [f"**{title}. {_lake_name(lake)}, {LABEL_NAME[variant]}** (n = {n}"
           + (f"; {round(no_gold * n)} with no gold table" if no_gold and lake in LAKES else "") + ")", "",
           "| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
    for m, s in rows:
        none = sc.get(variant, lake, m, s, "table", "no_answer")
        out.append("| " + " | ".join([JUDGE_ROWS.get(m) or METHODS[m]["name"], s[1:] if s.startswith("k") else "-",
                                      _num(sc.get(variant, lake, m, s, "table", "size")),
                                      *(_pct(sc.get(variant, lake, m, s, lv, k)) for lv, k in keys),
                                      str(round(none * n)) if none is not None and lake in LAKES else _pct(none),
                                      str(sc.n[(variant, lake, m, s)][1])]) + " |")
    return out + [""]


def _column_table(sc: Scores) -> list[str]:
    """AMIGO only: the baselines name no columns."""
    head = ["lake", "label", "n", "column R", "column CR", "column P", "column F1",
            "interp. R", "interp. CR", "interp. P", "interp. F1"]
    out = ["**Columns, AMIGO only.** column: the columns AMIGO binds against the columns of the label, "
           "pooled. interp.: as interp. on tables, on the columns of each interpretation's parts and joins.", "",
           "| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
    for lake in [*LAKES, f"mean{sc.pool()}", f"worst{sc.pool()}"]:
        for variant in ("gold", "multi"):
            if sc.has(variant, lake, "amigo", "var") and sc.get(variant, lake, "amigo", "var", "column", "R") is not None:
                out.append("| " + " | ".join([_lake_name(lake), LABEL_NAME[variant], str(sc.n[(variant, lake, "amigo", "var")][0]),
                                              *(_pct(sc.get(variant, lake, "amigo", "var", lv, k))
                                                for lv in ("column", "interpretation") for k in ("R", "CR", "P", "F1"))]) + " |")
    return out + [""]


def _latency_tables(out: Path) -> list[str]:
    rows = _read_csv(out / "latency.csv")
    if not rows:
        return ["T4. Latency: not run yet.", ""]
    by = {(r["lake"], r["method"], r["setting"], r["step"]): r for r in rows}
    head = ["method", "setting"] + [f"{LAKES[lake]} {x}" for lake in LAKES for x in ("median", "p90")] + \
           ["LLM calls / q", "flagged"]
    lines = ["**T4. Latency per question (seconds), one question at a time.**", "",
             "| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
    for method, setting, _ in TIMED:
        cells, calls, flagged = [], [], 0
        for lake in LAKES:
            r = by.get((lake, method, setting, "total"))
            cells += [r["median_s"], r["p90_s"]] if r else ["not run", "-"]
            c = by.get((lake, method, setting, "llm calls per question"))
            if c:
                calls.append(float(c["mean_s"]))
            flagged += int(r["flagged"]) if r else 0
        if any(c != "not run" and c != "-" for c in cells):
            lines.append("| " + " | ".join([METHODS[method]["name"], setting, *cells,
                                              f"{statistics.fmean(calls):.1f}" if calls else "-", str(flagged)]) + " |")
    lines += ["", "**T4b. Steps of each method (mean seconds per step, BIRD).**", ""]
    for method, setting, _ in TIMED:
        steps = [(r["step"], r["mean_s"]) for r in rows if (r["lake"], r["method"], r["setting"]) == ("bird_dev", method, setting)
                 and r["step"] not in ("total", "llm calls per question")]
        if steps:
            lines.append(f"- {METHODS[method]['name']} {setting}: " + ", ".join(f"{s} {float(v):.2f}" for s, v in steps))
    return lines + ["", FOOT, ""]


def _build_tables(out: Path) -> list[str]:
    rows = _read_csv(out / "build.csv")
    if not rows:
        return ["T5. Lake preparation: not run yet.", ""]
    head = ["lake", *BUILD_STEPS, "total", "LLM calls", "load"]
    lines = ["**T5. Lake preparation time (minutes).**", "", "| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
    for lake in LAKES:
        mine = {r["step"]: r for r in rows if r["lake"] == lake and not r["step"].startswith("prep ")}
        if not mine:
            continue
        mins = [f"{float(mine[s]['seconds']) / 60:.1f}" if s in mine else "-" for s in BUILD_STEPS]
        total = sum(float(r["seconds"]) for r in mine.values()) / 60
        calls = sum(int(r["llm_calls"]) for r in mine.values())
        lines.append("| " + " | ".join([LAKES[lake], *mins, f"{total:.1f}", str(calls), next(iter(mine.values()))["load"]]) + " |")
    lines += ["", "**T5b. Baseline preparation (seconds): the setup lap of the first question.**", "",
              "| lake | method | setup s | LLM calls |", "|---|---|---|---|"]
    lines += [f"| {LAKES[r['lake']]} | {r['step'][5:]} | {float(r['seconds']):.1f} | {r['llm_calls']} |"
              for r in rows if r["step"].startswith("prep ")]
    lines += ["", "Filled lazily, not in setup: JAR value hashes and CORE-T join pairs.", "",
              "Build steps each method reads: JAR, Greedy JAR, CRUSH4SQL, MURRE: schema only (names), plus their "
              "own vectors. CORE-T: schema, plus its own purposes (one LLM call per table, from the first 5 rows) "
              "and vectors. BM25 and full schema: schema + describe. dense and hybrid: schema + describe + embed. "
              "Route+SQL: schema + profile + describe + embed. AMIGO: all 11 steps.", ""]
    return lines


def _ablation_table(sc: Scores, out: Path) -> list[str]:
    paired = {(r["variant"], r["lake"], r["method"]): r for r in _read_csv(out / "paired.csv")}
    runs = {(r["lake"], r["method"]): r for r in _read_csv(out / "runs.csv")}
    keys = SCORE_KEYS
    head = ["variant", "removed", "tables / q", *SCORE_HEAD, "LLM calls / q", "output tokens / q",
            "CR change", "sign-test p"]
    lines = ["**T6. AMIGO ablations, multi label.** A change is the ablation minus AMIGO, in points.", ""]
    for lake in [lake for lake in LAKES if sc.has("multi", lake, "amigo", "var")]:
        lines += [f"{LAKES[lake]}", "", "| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
        for name, (aid, removed) in [("amigo", ("AMIGO", "nothing")), *ABLATIONS.items(),
                                     *([("noise", ("N1 noise band (BIRD, 150 q)", "nothing, run again"))]
                                       if lake == "bird_dev" else [])]:
            if not sc.has("multi", lake, name, "var"):
                continue
            r = runs.get((lake, name))
            per_q = (lambda k: f"{int(r[k]) / max(1, int(r['questions'])):.1f}") if r else (lambda k: "-")
            p = paired.get(("multi", lake, name))
            change = f"{-100 * float(p['cr_lead']):+.1f} [{-100 * float(p['cr_high']):+.1f}, {-100 * float(p['cr_low']):+.1f}]" \
                if p else ("0" if name == "amigo" else "-")
            lines.append("| " + " | ".join([aid, removed, _num(sc.get("multi", lake, name, "var", "table", "size")),
                                              *(_pct(sc.get("multi", lake, name, "var", lv, k)) for lv, k in keys),
                                              per_q("llm_calls"), per_q("output_tokens"), change,
                                              f"{float(p['sign_p']):.3f}" if p else "-"]) + " |")
        lines.append("")
    return lines + ["Ablations reuse AMIGO's saved answers; an AMIGO answer saved with an error is copied as it was.",
                    FOOT, ""]


def _runs_table(out: Path) -> list[str]:
    rows = _read_csv(out / "runs.csv")
    if not rows:
        return ["T7. Run report: not run yet.", ""]
    head = ["lake", "method", "setting", "questions", "failed", "retried", "LLM calls", "output tokens", "GPU hours"]
    lines = ["**T7. Run report.** LLM calls include replies from the cache; output tokens and GPU hours count only "
             "real calls.", "", "| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
    lines += ["| " + " | ".join([LAKES.get(r["lake"], r["lake"]), r["method"], r["setting"], r["questions"], r["failed"],
                                  r["retried"], r["llm_calls"], r["output_tokens"], r["gpu_hours"]]) + " |" for r in rows]
    return lines + [""]


def tables(night: Path, out: Path) -> None:
    sc = Scores(out)
    note = "Means and worst are over 4 lakes." if sc.pool() == "4" else \
        "Means and worst are over BIRD, Spider and MMQA: not every method finished TACO-US stage A."
    lines = ["# Tables of the night evaluation of 2026-10-20", ""]
    if not sc.v:
        lines += ["Scores: not run yet.", ""]
    else:
        lines += ["Main scores first. exact: each table set of the label against each returned set (a top-k list "
                  "is one set, each AMIGO interpretation one set), a hit only when equal: R the label's sets found, "
                  "P the returned sets that are one of them, CR every set found. interp.: each query of the label "
                  "against the returned set closest to it, on tables: R and P averaged over the queries, CR when "
                  "every query is held whole by one set; returned sets close to no query cost nothing there. interp. "
                  "set P is from the other side: each returned set, duplicates dropped, against the query it is "
                  "closest to (the share of its tables in that query), averaged over the returned sets. pooled: every returned table against every table of the label, both "
                  "pooled, so which tables go together is lost; it is the level a table retriever's list is scored "
                  "on as it is. soft: as exact, but a returned set holding a label set counts. Gold-label tables "
                  "show exact match (one returned set equals the gold tables) and soft match (one holds them all): "
                  "with one gold set CR repeats R and P counts every other valid set as wrong. No answer: questions with no returned table, scored 0 everywhere. No gold "
                  "table: the label reads none; table R and CR count it found, a footprint is held by any "
                  "returned set. Precision is a lower bound: the labels are incomplete.", note, FOOT, ""]
        pool = sc.pool()
        blocks = [lake for lake in LAKES if any(sc.has("gold", lake, m, s) for m, s in ROWS)] + [f"mean{pool}", f"worst{pool}"]
        order = [(lake, v) for lake in blocks for v in ("gold", "multi")] + [(lake, "multi_amb") for lake in blocks]
        for i, (lake, variant) in enumerate(order, 1):
            lines += _score_table(sc, variant, lake, f"T1.{i}")
        lines += _column_table(sc)
    lines += _latency_tables(out) + _build_tables(out)
    if sc.v:
        lines += _ablation_table(sc, out)
    lines += _runs_table(out)
    (out / "tables.md").write_text("\n".join(lines) + "\n")
    print("tables.md written")


# ---- figures (section 12.2)

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6})
    return plt


def _save(fig, out: Path, name: str) -> None:
    (out / "figures").mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out / "figures" / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    print(f"figures/{name} written")


def _panels(sc: Scores) -> list[str]:
    lakes = [lake for lake in LAKES if sc.has("multi", lake, "amigo", "var")]
    return lakes + ([f"mean{sc.pool()}"] if len(lakes) > 1 else [])


def _title(lake: str) -> str:
    return "mean" if lake.startswith("mean") else LAKES[lake]


def fig_at_k(plt, sc: Scores, out: Path, metric: str, name: str, question: str) -> None:
    panels = _panels(sc)
    fig, axes = plt.subplots(1, len(panels), figsize=(2.6 * len(panels), 2.8), sharey=True, squeeze=False)
    for ax, lake in zip(axes[0], panels):
        for m, spec in METHODS.items():
            if spec["kind"] != "fixed" and m != "amigo":
                continue
            pts = [(n, sc.get("multi", lake, m, f"k{n}", "table", metric)) for n in (1, 3, 5)]
            pts = [(n, 100 * v) for n, v in pts if v is not None]
            if pts:
                ax.plot(*zip(*pts), color=spec["color"], marker=spec["marker"], markersize=4, linewidth=2 if m == "amigo" else 1.2,
                        linestyle="--" if m == "amigo" else "-", label=f"{spec['name']} cut to k" if m == "amigo" else spec["name"])
        whole = sc.get("multi", lake, "amigo", "var", "table", metric)
        size = sc.get("multi", lake, "amigo", "var", "table", "size")
        if whole is not None:
            ax.axhline(100 * whole, color=AMIGO_COLOR, linewidth=2)
            ax.annotate(f"AMIGO, {size:.1f} tables on average", (1, 100 * whole), xytext=(0, 3),
                        textcoords="offset points", fontsize=7, color="#0b0b0b")
        ax.set_title(_title(lake))
        ax.set_xticks([1, 3, 5])
        ax.set_xlabel("tables returned")
    axes[0][0].set_ylabel(f"{'complete recall' if metric == 'CR' else 'precision'} (%)")
    handles, names = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.12))
    fig.suptitle(question, y=1.04)
    _save(fig, out, name)
    plt.close(fig)


def _points(sc: Scores, variant: str, lake: str):
    """(method, setting, label) of each mark of a scatter."""
    for m, spec in METHODS.items():
        for s in spec["tags"]:
            if s.startswith("w") or (m == "amigo" and s != "var"):
                continue
            if sc.has(variant, lake, m, s):
                yield m, s, s[1:] if s.startswith("k") else ""


def fig2(plt, sc: Scores, out: Path) -> None:
    lakes = [lake for lake in LAKES if sc.has("multi", lake, "amigo", "var")]
    fig, axes = plt.subplots(2, len(lakes), figsize=(2.8 * len(lakes), 5.4), squeeze=False)
    for row, variant in enumerate(("gold", "multi")):
        for ax, lake in zip(axes[row], lakes):
            for m, s, k in _points(sc, variant, lake):
                spec = METHODS[m]
                x = 100 * sc.get(variant, lake, m, s, "table", "P")
                y = 100 * sc.get(variant, lake, m, s, "table", "CR")
                ax.scatter(x, y, color=spec["color"], marker=spec["marker"], s=40 if m == "amigo" else 22,
                           edgecolors="white", linewidths=0.8, zorder=3, label=spec["name"] if k in ("", "3") else None)
                if k:
                    ax.annotate(k, (x, y), xytext=(3, 2), textcoords="offset points", fontsize=6, color="#52514e")
            ax.set_title(f"{LAKES[lake]}, {variant} label")
            ax.set_xlabel("precision (%)")
        axes[row][0].set_ylabel("complete recall (%)")
    handles, names = axes[1][0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Which methods find every valid table without returning extra ones?")
    fig.tight_layout()
    _save(fig, out, "fig2_recall_vs_precision")
    plt.close(fig)


def fig3_4(plt, sc: Scores, out: Path) -> None:
    rows = _read_csv(out / "latency.csv")
    if not rows:
        return
    by = {(r["lake"], r["method"], r["setting"], r["step"]): r for r in rows}
    lakes = [lake for lake in LAKES if any(r["lake"] == lake for r in rows)]
    fig, axes = plt.subplots(1, len(lakes), figsize=(2.8 * len(lakes), 3), squeeze=False)
    for ax, lake in zip(axes[0], lakes):
        for method, setting, _ in TIMED:
            r = by.get((lake, method, setting, "total"))
            s = "var" if METHODS[method]["kind"] == "variable" else (setting if setting.startswith("k") else "k3")
            cr = sc.get("multi", lake, method, s, "table", "CR")
            if r is None or cr is None:
                continue
            med, p90 = float(r["median_s"]), float(r["p90_s"])
            spec = METHODS[method]
            ax.plot([med, p90], [100 * cr] * 2, color=spec["color"], linewidth=1)
            ax.scatter(med, 100 * cr, color=spec["color"], marker=spec["marker"], s=40 if method == "amigo" else 22,
                       edgecolors="white", linewidths=0.8, zorder=3, label=spec["name"] if setting in ("any k", "k3", "-", "default") else None)
        ax.set_xscale("log")
        ax.set_title(LAKES[lake])
        ax.set_xlabel("seconds per question (median; bar to p90)")
    axes[0][0].set_ylabel("complete recall (%), multi label, k=3")
    handles, names = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, -0.14))
    fig.suptitle("What does complete recall cost in time?", y=1.04)
    _save(fig, out, "fig3_recall_vs_time")
    plt.close(fig)

    fig, axes = plt.subplots(1, len(lakes), figsize=(3.4 * len(lakes), 4), squeeze=False)
    shades = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
    for ax, lake in zip(axes[0], lakes):
        timed = [(m, s) for m, s, _ in TIMED if (lake, m, s, "total") in by]
        for y, (m, s) in enumerate(timed):
            left = 0.0
            steps = [r for r in rows if (r["lake"], r["method"], r["setting"]) == (lake, m, s)
                     and r["step"] not in ("total", "llm calls per question")]
            for i, r in enumerate(steps):
                w = float(r["mean_s"])
                ax.barh(y, w, left=left, color=shades[i % len(shades)], edgecolor="white", linewidth=1)
                if w > 0.08 * float(by[(lake, m, s, "total")]["mean_s"]):
                    ax.text(left + w / 2, y, r["step"], ha="center", va="center", fontsize=5, color="white")
                left += w
            ax.plot(float(by[(lake, m, s, "total")]["median_s"]), y, marker="|", color="black", markersize=10)
            ax.plot(float(by[(lake, m, s, "total")]["p90_s"]), y, marker="|", color="white", markersize=10,
                    markeredgecolor="black", markeredgewidth=0.4)
        ax.set_yticks(range(len(timed)), [f"{METHODS[m]['name']} {s}" for m, s in timed], fontsize=7)
        ax.set_title(LAKES[lake])
        ax.set_xlabel("mean seconds per step")
    fig.suptitle("Where does each method spend its time? (black tick: median total; white tick: p90)")
    fig.tight_layout()
    _save(fig, out, "fig4_time_per_step")
    plt.close(fig)


def fig5(plt, out: Path) -> None:
    rows = [r for r in _read_csv(out / "build.csv") if not r["step"].startswith("prep ")]
    if not rows:
        return
    lakes = [lake for lake in LAKES if any(r["lake"] == lake for r in rows)]
    fig, ax = plt.subplots(figsize=(1.4 * len(lakes) + 2, 3.4))
    bottom = np.zeros(len(lakes))
    llm_shades, plain_shades = ["#2a78d6", "#3987e5"], ["#c3c2b7", "#a3a29c", "#8a8987", "#d8d7d2"]
    for i, step in enumerate(BUILD_STEPS):
        mins = np.array([next((float(r["seconds"]) / 60 for r in rows if r["lake"] == lake and r["step"] == step), 0.0)
                         for lake in lakes])
        color = llm_shades[i % 2] if step in LLM_STEPS else plain_shades[i % 4]
        ax.bar(range(len(lakes)), mins, bottom=bottom, color=color, edgecolor="white", linewidth=1,
               label=("with an LLM call" if step == "describe" else None) if step in LLM_STEPS else
               ("without" if step == "schema" else None))
        bottom += mins
    if bottom.max() > 10 * max(min(bottom), 1e-9):
        ax.set_yscale("log")
        ax.set_ylabel("minutes (log scale)")
    else:
        ax.set_ylabel("minutes")
    ax.set_xticks(range(len(lakes)), [LAKES[lake] for lake in lakes])
    ax.legend(frameon=False)
    ax.set_title("How long does it take to prepare a lake?")
    _save(fig, out, "fig5_lake_preparation")
    plt.close(fig)


def fig6(plt, sc: Scores, out: Path) -> None:
    panels = _panels(sc)
    rows = [(m, "var") for m, s in METHODS.items() if s["kind"] == "variable"] + \
           [(m, "k3") for m, s in METHODS.items() if s["kind"] == "fixed"]
    fig, axes = plt.subplots(1, len(panels), figsize=(2.4 * len(panels), 3.6), sharey=True, squeeze=False)
    marks = (("R", "o", "#2a78d6"), ("CR", "s", "#eb6834"), ("P", "D", "#1baf7a"))
    for ax, lake in zip(axes[0], panels):
        for y, (m, s) in enumerate(rows):
            for hit in ("soft", "exact"):
                for key, marker, color in marks:
                    v = sc.get("multi", lake, m, s, f"footprint_{hit}", key)
                    if v is not None:
                        ax.scatter(100 * v, y, marker=marker, s=22, zorder=3, linewidths=1,
                                   color=color if hit == "soft" else "white", edgecolors="white" if hit == "soft" else color,
                                   label=f"{hit} {key}" if y == 0 else None)
        ax.set_yticks(range(len(rows)), [METHODS[m]["name"] + ("" if s == "var" else " k=3") for m, s in rows], fontsize=7)
        ax.set_title(_title(lake))
        ax.set_xlabel("share of questions (%)")
    axes[0][0].legend(frameon=False, fontsize=7)
    fig.suptitle("Does a returned table set match a valid footprint? (filled: soft, hollow: exact)", y=1.04)
    _save(fig, out, "fig6_interpretation_level")
    plt.close(fig)


def fig7(plt, sc: Scores, out: Path) -> None:
    paired = {(r["variant"], r["lake"], r["method"]): r for r in _read_csv(out / "paired.csv")}
    runs = {(r["lake"], r["method"]): r for r in _read_csv(out / "runs.csv")}
    names = [n for n in ABLATIONS if ("multi", "bird_dev", n) in paired]
    if not names:
        return
    fig, (ax, side) = plt.subplots(1, 2, figsize=(7, 0.45 * len(names) + 1.5), sharey=True,
                                   gridspec_kw={"width_ratios": [4, 1]})
    noise = paired.get(("multi", "bird_dev", "noise"))
    if noise:  # the band AMIGO moves by when run again
        ax.axvspan(-100 * float(noise["cr_high"]), -100 * float(noise["cr_low"]), color="#e4e3df", label="run again (N1)")
    ax.axvline(0, color="#52514e", linewidth=0.8)
    for y, n in enumerate(names):
        p = paired[("multi", "bird_dev", n)]
        for key, color, dy, label in (("cr", "#2a78d6", -0.12, "complete recall"), ("p", "#eb6834", 0.12, "precision")):
            lead, low, high = (-100 * float(p[f"{key}_{x}"]) for x in ("lead", "high", "low"))
            ax.errorbar(lead, y + dy, xerr=[[lead - low], [high - lead]], fmt="o", color=color, markersize=4,
                        capsize=2, label=label if y == 0 else None)
        r = runs.get(("bird_dev", n))
        if r:
            side.barh(y, int(r["llm_calls"]) / max(1, int(r["questions"])), color="#8a8987")
    ax.set_yticks(range(len(names)), [f"{ABLATIONS[n][0]} no {ABLATIONS[n][1]}" for n in names], fontsize=7)
    ax.set_xlabel("change against the full AMIGO, BIRD, multi label (points)")
    side.set_xlabel("LLM calls / question")
    ax.legend(frameon=False, fontsize=7)
    fig.suptitle("What does each part of AMIGO add?", y=1.04)
    _save(fig, out, "fig7_ablations")
    plt.close(fig)


def fig8(plt, sc: Scores, out: Path) -> None:
    panels = [p for p in _panels(sc) if p in LAKES or p.startswith("mean")]
    if not any(sc.has("multi", lake, "amigo", "w0") for lake in panels):
        return
    fig, axes = plt.subplots(1, len(panels), figsize=(2.6 * len(panels), 2.8), squeeze=False)
    for ax, lake in zip(axes[0], panels):
        ws = [w for w in range(7) if sc.has("multi", lake, "amigo", f"w{w}")]
        for metric, color in (("CR", "#2a78d6"), ("P", "#eb6834")):
            ax.plot(ws, [100 * sc.get("multi", lake, "amigo", f"w{w}", "table", metric) for w in ws], color=color,
                    marker="o", markersize=3, linewidth=1.5, label="complete recall (%)" if metric == "CR" else "precision (%)")
        twin = [sc.get("multi", lake, "amigo", f"w{w}", "table", "size") for w in ws]
        ax.plot(ws, twin, color="#52514e", linestyle=":", label="tables returned")
        ax.set_title(_title(lake))
        ax.set_xlabel("window W (bits)")
    axes[0][0].legend(frameon=False, fontsize=7)
    fig.suptitle("What does the window do to AMIGO? (no W is picked)", y=1.04)
    _save(fig, out, "fig8_window")
    plt.close(fig)


def figures(night: Path, out: Path) -> None:
    plt = _plt()
    sc = Scores(out)
    if sc.v:
        fig_at_k(plt, sc, out, "CR", "fig1_complete_recall_at_k",
                 "How many tables must a fixed-size method return to find every valid table?")
        fig_at_k(plt, sc, out, "P", "fig1b_precision_at_k", "What precision does each table count give?")
        fig2(plt, sc, out)
        fig6(plt, sc, out)
        fig7(plt, sc, out)
        fig8(plt, sc, out)
    fig3_4(plt, sc, out)
    fig5(plt, out)


# ---- readme

def readme(night: Path, out: Path) -> None:
    import subprocess
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    path = night / "questions" / "sets.json"
    counts = json.loads(path.read_text()) if path.exists() else {}
    runs = _read_csv(out / "runs.csv")
    jobs = []
    for state in sorted((night / "driver" / "state").glob("*.json")):
        s = json.loads(state.read_text())
        jobs.append(f"| {state.stem} | {s.get('state', '')} | {s.get('tries', '')} | {s.get('release', '')} |")
    plan = (ROOT / "docs" / "night-eval-2026-10-20.md")
    appendix = plan.read_text().split("## Appendix A.")[1].split("## Appendix B.")[0] if plan.exists() else ""
    sizes = []
    for name in ("lakes", "bl_cache", *(f"{lake}/cache" for lake in LAKES), *(f"{lake}/amigo" for lake in LAKES)):
        p = night / name
        if p.exists():
            total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            sizes.append(f"- `{name}`: {total / 1e9:.2f} GB")
    gpu = sum(float(r["gpu_hours"]) for r in runs if r["gpu_hours"])
    lines = [
        "# Night evaluation of 2026-10-20", "",
        f"- Run date: 2026-10-20 to 2026-10-22. Commit: {commit}. Model: qwen3.8-27b-fp8 at effort medium (local vLLM).",
        "- Embedder: granite-embedding-english-r2 on CPU.",
        "- Plan: docs/night-eval-2026-10-20.md. Failure rules: its section 8.3. Scoring: changed on 2026-10-21 to a "
        "table level and a footprint level (soft and exact), see `measure` in experiments/eval_lakes.py.", "",
        "## Questions per variant", "", "| lake | gold | multi | multi, ambiguous |", "|---|---|---|---|",
        *(f"| {LAKES[lake]} | {len(s['gold'])} | {len(s['multi'])} | {len(s['multi_amb'])} |" for lake, s in counts.items()),
        "", "TACO-US stage A (440 questions) is scored. " + ("" if "taco_us" in counts else "TACO-US was not scored."), "",
        "## Exclusions", "",
        "- TACO-US: the 430 cross-database questions and the other 2511 single-database questions are not in the sample.",
        "- MMQA: 56 gold SQLs do not run; those questions are left out of every variant.",
        "- TACO-US: 24 label time-outs are not in stage A.",
        "- Describe failures: see `$NIGHT/build/<lake>/<lake>_describe_failed.txt`.", "",
        "## Failures, retries and GPU hours", "",
        f"GPU hours in all: {gpu:.1f}. Per method: `runs.csv` and T7 in `tables.md`. A failed question is scored as an "
        "empty answer (an AMIGO answer saved with a judge error is scored as returned); see section 8.3 of the plan.", "",
        "## Jobs as run", "", "| job | state | tries | release |", "|---|---|---|---|", *jobs, "",
        "## Methods checked and left out", appendix.strip(), "",
        "## Sizes in the night folder (for you to decide what to delete)", "", *sizes, "",
        "## Files", "",
        "- `scores.csv`: per variant, lake (plus mean3/worst3/mean4/worst4), method, setting, level and metric, the mean "
        "over the questions (0 to 1), the questions and the failed ones.",
        "- `paired.csv`: AMIGO against each method setting and ablation; every lead is AMIGO minus the other, with "
        "its 95% paired bootstrap interval and the sign-test p on complete recall.",
        "- `latency.csv`: seconds per question, one question at a time, per step; `flagged` counts questions timed "
        "under load after the one retime; the row `llm calls per question` holds that count in `mean_s`.",
        "- `build.csv`: each build step's seconds, LLM calls and tokens; `prep <tag>` rows are baseline preparation.",
        "- `runs.csv`: per method run, questions, failed, retried (questions with a failed or repeated request), LLM "
        "calls (cached replies included), output tokens and GPU hours (real calls only).",
        "- `tables.md`, `figures/`: made from the CSVs by `experiments/paper_results.py`.", "",
    ]
    (out / "README.md").write_text("\n".join(lines))
    print("README.md written")


JOINS = ROOT / "runs" / "joinchoice_2026-10-24"


def joins_cmd(night: Path, out: Path) -> None:
    """joins.md: A1 (judge call 1 only) against A1 with the join choice of each saved answer
    (eval_lakes.py joins), and with its links chosen but every join path kept, per label and
    lake, then mean and worst: interpretations and tables per question, R, CR, P at the table
    level, at the interpretation level (the columns of the parts and of the joins, against each
    query's columns) and of the exact table sets."""
    keys = [lambda m: float(m["count"]), lambda m: float(m["size"])] + \
        [lambda m, lv=lv, k=k: m[lv][k] for lv in ("tables", "interpretation") for k in ("recall", "complete", "precision")] + \
        [lambda m, k=k: m["footprint"]["exact"][k] for k in ("recall", "complete", "precision")]
    runs = [("A1, judge call 1 only", lambda lake: night / lake / "abl_nojudge2"),
            ("A1 + join choice", lambda lake: JOINS / lake / "joinchoice"),
            ("A1 + links only", lambda lake: JOINS / lake / "linksonly")]
    means = defaultdict(dict)
    for lake in THREE:
        for name, folder in runs:
            got = records(folder(lake).parent, folder(lake).name + "@inf")
            if got is None:
                continue
            for variant in ("gold", "multi"):
                label = labels(night, lake)[variant]
                scored = []
                for q in label:
                    rec, _ = answer(got, q, "")
                    m = eval_lakes.measure(label[q], {**rec, "levels": eval_lakes.LEVELS})
                    scored.append([key(m) for key in keys])
                means[(variant, name)][lake] = ([statistics.fmean(c) for c in zip(*scored)], len(scored),
                                               sum(1 for q in label if q not in got or got[q].get("judge_error")))
    head = ["method", "interpretations / q", "tables / q", "table R", "table CR", "table P",
            "interpretation R", "interpretation CR", "interpretation P", "exact R", "exact CR", "exact P",
            "n", "failed"]
    lines = ["# A1 against A1 with the join choice", ""]
    for variant in ("gold", "multi"):
        lines += [f"**{LABEL_NAME[variant]}**", "", "| lake | " + " | ".join(head) + " |", "|---" * (len(head) + 1) + "|"]
        for lake in [*THREE, "mean", "worst"]:
            for name, _ in runs:
                by = means.get((variant, name), {})
                if not all(lake_ in by for lake_ in THREE) and lake in ("mean", "worst"):
                    continue
                if lake in THREE:
                    if lake not in by:
                        continue
                    values, n, failed = by[lake]
                else:
                    columns = list(zip(*(by[x][0] for x in THREE)))
                    pick = statistics.fmean if lake == "mean" else None
                    values = [pick(c) if pick else (max(c) if i < 2 else min(c)) for i, c in enumerate(columns)]
                    n, failed = sum(by[x][1] for x in THREE), sum(by[x][2] for x in THREE)
                cells = [_num(v) for v in values[:2]] + [_pct(v) for v in values[2:]]
                lines.append(f"| {LAKES.get(lake, lake)} | {name} | " + " | ".join(cells) + f" | {n} | {failed} |")
        lines.append("")
    (out / "joins.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


COMMANDS = {"sets": sets, "scores": scores, "latency": latency_cmd, "build": build_cmd, "runs": runs_cmd,
            "tables": tables, "figures": figures, "readme": readme, "joins": joins_cmd}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[*COMMANDS, "all"])
    parser.add_argument("--night", type=Path, default=Path(os.environ.get("NIGHT", NIGHT)))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name in [n for n in COMMANDS if n != "joins"] if args.command == "all" else [args.command]:
        COMMANDS[name](args.night, args.out)


if __name__ == "__main__":
    main()
