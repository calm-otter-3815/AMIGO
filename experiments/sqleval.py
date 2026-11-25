"""Stage 2 of the evaluation protocol (docs/eval_protocol.md): one SQL per distinct
returned table set, written from the question and the schema of that set only, run, and
compared with the label's results.

  .venv/bin/python experiments/sqleval.py write WRITER [--hints] [--url URL] [--sample N] [--threads T] [--shard I/N]
  .venv/bin/python experiments/sqleval.py score WRITER [--out DIR]

`write` asks the writer (an OpenAI-style server, vLLM) for every (question, table set) of
every method and of the oracle, runs each SQL and stores it in runs/sqleval/WRITER/. A
reply is cached by its prompt, so a set two methods return costs one call, and a rerun
costs none. `--sample N` takes N random prompts, to time the server first. `--shard I/N`
only asks the I-th of N parts, for N servers at once; a last run with no shard then
finds every reply cached and runs the SQL.

The writer sees no gold and no evidence. A set over one database names its tables bare;
a set over several names them database.table, and runs with each database attached. A
SQL that reads a table outside its set is an error ("outside"): the writer must answer
from what the method returned.

`--hints` writes the row "AMIGO with hints": AMIGO's plain prompt for each table set it
returned, plus, when several of its interpretations share one set, a few lines saying
only where those interpretations differ (`hints`); one SQL per distinct prompt, so a set
with one interpretation costs no call beyond the plain row's.
"""

import argparse
import hashlib
import json
import pickle
import random
import sqlite3
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from statistics import mean

import numpy as np
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eval_lakes  # noqa: E402
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402

from amigo import answer, bundle, candidates, interpret  # noqa: E402
from amigo.probe import Probe  # noqa: E402
from baselines.lake import Lake  # noqa: E402
from baselines.sql import PROMPT  # noqa: E402
from labeler.gold import connect, result  # noqa: E402

OUT = R.JOINCHOICE / "sqleval"
SCORES = R.ROOT / "experiments" / "results" / "sqleval_2026-11-08"
# name -> (served model name, checkpoint for the cache key, extra request fields to turn thinking off)
WRITERS = {
    "qwen": ("qwen", "Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a",
             {"chat_template_kwargs": {"enable_thinking": False}}),
    "granite": ("granite", "ibm-granite/granite-4.2-8b@a7042144125ce5ae64f89610e8289647fc000b9a",
                {"chat_template_kwargs": {"enable_thinking": False}}),
    "gemma": ("gemma", "google/gemma-4-E4B-it@ee0ef6023621cff504d758262d4e04895a5af4a2",
              {"chat_template_kwargs": {"enable_thinking": False}}),
}
SETTINGS = {"temperature": 0.0, "max_tokens": 1024}
SCHEMA = {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"],
          "additionalProperties": False}
ORACLE = "Gold-table oracle"
SINGLE_DB = "- Never write the database name in the SQL."
MANY_DB = "- The tables sit in several databases: write each table as database.table, as named above."
HINTS = "AMIGO with hints"


def prompt(lake: Lake, tables: frozenset, question: str) -> str:
    many = len({lake.table[t].database for t in tables}) > 1
    text = PROMPT.substitute(schema=lake.schema_text([lake.table[t] for t in sorted(tables)], qualified=many),
                             question=question)
    return text.replace(SINGLE_DB, MANY_DB) if many else text


def jobs(lake: str) -> tuple[dict[str, str], dict[str, list[frozenset]]]:
    """The questions' text and, per question, every table set some method or the oracle
    needs a SQL for (the multi-valid label's sets hold the gold label's)."""
    labels = P.labels(P.NIGHT, lake)
    rows = eval_lakes._lines(P._questions(P.NIGHT, lake))
    text = {r["id"]: r["question"] for r in rows}
    sets: dict[str, list] = {q: [] for q in labels["gold"] | labels["multi"]}
    for name, (night, file, first) in R.METHODS.items():
        records = json.loads((night / lake / file).read_text()) if (night / lake / file).exists() else {}
        for q in sets:
            sets[q] += R.returned(records.get(q), first)
    for q, queries in labels["multi"].items():
        sets[q] += R.targets_of(queries)
    return text, {q: list(dict.fromkeys(s)) for q, s in sets.items()}


def _interpretations(probe: Probe, lake: str):
    """(question, position, saved run, card) per AMIGO interpretation of the join-choice run,
    in the order of its records (every interpretation: records_inf)."""
    graph = candidates.Graph(probe)
    labels = P.labels(P.NIGHT, lake)
    for q in labels["gold"] | labels["multi"]:
        path = R.JOINCHOICE / lake / "joinchoice" / f"{q}.amigo.pkl"
        got = pickle.loads(path.read_bytes()) if path.exists() else {"found": []}
        for n, one in enumerate(got["found"] or []):
            yield q, n, got, interpret._card(probe, graph, got["stage"], one, n + 1, got["found"][0].cost)


HINT = "\n\nThis question has several readings over these tables. Write the SQL for this reading:\n"


def _place(probe: Probe, binding) -> str:
    """Where one part of the question sits, in plain words."""
    if probe.find(binding.column)[0] == "table":
        return f"the table {answer._sql_name(probe, binding.column)}, each of its rows being one"
    pairs = [(binding.column, binding.value), *binding.also]
    names = [answer._sql_name(probe, c) + ("" if v is None else f" is {answer._sql_text(v)}") for c, v in pairs]
    if all(v is None for _, v in pairs):
        return f"the column {names[0]}" if len(names) == 1 else f"the columns {' and '.join(names)} together"
    return "the rows where " + " and ".join(names)


def hints(interpretations: list[dict[str, tuple[str, str]]]) -> list[list[str]]:
    """Per interpretation of one table set ({part: (its words, its place)}), one line per part
    whose place differs between the interpretations; a part every interpretation puts in the
    same place gets none, so the writer picks it as in the plain prompt."""
    parts = sorted(set().union(*interpretations), key=lambda e: int(e[1:]))
    differ = [e for e in parts if len({r[e][1] if e in r else None for r in interpretations}) > 1]
    out = []
    for mine in interpretations:
        lines = []
        for e in differ:
            words = next(r[e][0] for r in interpretations if e in r)
            others = list(dict.fromkeys(r[e][1] for r in interpretations if e in r and r[e] != mine.get(e)))
            also = (f" Other readings take it as: {'; '.join(others)}." if len(others) > 1
                    else f" Another reading takes it as {others[0]}." if others else "")
            lines.append(f'- "{words}" is {mine[e][1]}.{also}' if e in mine else f'- "{words}" is left out of this reading.')
        out.append(lines)
    return out


def hint_jobs(lake: str) -> list[tuple[str, int, frozenset, str]]:
    """(question, position, tables, prompt) per distinct prompt of AMIGO's interpretations: the
    plain prompt of the table set, plus, when several interpretations share that set, the
    lines of `hints`. Interpretations that differ only in their joins share one prompt."""
    probe, lake_ = Probe(lake), Lake(lake)
    text = {r["id"]: r["question"] for r in eval_lakes._lines(P._questions(P.NIGHT, lake))}
    groups: dict[tuple[str, frozenset], list] = {}
    for q, n, got, card in _interpretations(probe, lake):
        places = {}
        for b in card.bindings:
            entity = answer._entity(got["entities"], b)
            words = entity.attribute + ("" if entity.literal is None else f" = {bundle._as_written(entity.literal)}")
            places[b.entity] = (words, _place(probe, b))
        groups.setdefault((q, frozenset(card.tables)), []).append((n, places))
    out, seen = [], set()
    for (q, s), group in groups.items():
        base = prompt(lake_, s, text[q])
        for (n, _), lines in zip(group, hints([r for _, r in group])):
            body = base.replace("\n\nOutput Format:", HINT + "\n".join(lines) + "\n\nOutput Format:") if lines else base
            if (q, body) not in seen:
                seen.add((q, body))
                out.append((q, n, s, body))
    return out


class Writer:
    def __init__(self, name: str, url: str, threads: int, shard: str | None = None):
        self.model, checkpoint, self.extra = WRITERS[name]
        self.base = [checkpoint, SETTINGS, self.extra, SCHEMA]
        self.client = OpenAI(base_url=url, api_key="local", timeout=1800, max_retries=3)
        # one cache file per shard: two processes appending to one file on shared storage can mix lines
        self.path = OUT / name / (f"cache-{shard.replace('/', 'of')}.jsonl" if shard else "cache.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        for path in sorted(self.path.parent.glob("cache*.jsonl")):
            for line in path.read_text().split("\n"):
                try:
                    one = json.loads(line)
                except json.JSONDecodeError:  # empty, or cut short when a run was killed mid-write
                    continue
                self.cache[one["key"]] = one
        self.lock = threading.Lock()
        self.used = Counter()
        self.threads = threads

    def key(self, text: str) -> str:
        return hashlib.sha256(json.dumps(self.base + [text]).encode()).hexdigest()

    def __call__(self, text: str) -> dict:
        """{"sql": ..., or None with "why"}; one sample, cached by the prompt."""
        key = self.key(text)
        if key in self.cache:
            self.used["cached"] += 1
            return self.cache[key]
        start = time.time()
        try:
            out = self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": text}], **SETTINGS,
                extra_body=self.extra | {"response_format": {
                    "type": "json_schema", "json_schema": {"name": "answer", "schema": SCHEMA}}})
        except Exception as error:  # noqa: BLE001 - a call the client gave up on after its retries is counted, not cached
            self.used["failed"] += 1
            return {"sql": None, "why": f"call failed: {str(error)[:200]}"}
        choice = out.choices[0]
        one = {"key": key, "sql": None, "seconds": round(time.time() - start, 2),
               "prompt_tokens": out.usage.prompt_tokens, "tokens": out.usage.completion_tokens}
        try:
            one["sql"] = json.loads(choice.message.content)["sql"].strip() if choice.finish_reason == "stop" else None
            one["why"] = None if one["sql"] else f"no answer ({choice.finish_reason})"
        except (json.JSONDecodeError, KeyError, TypeError):
            one["why"] = "reply is not the JSON asked for"
        with self.lock:
            self.used["calls"] += 1
            self.cache[key] = one
            with self.path.open("a") as f:
                f.write(json.dumps(one) + "\n")
        return one


def run(paths: dict[str, str], tables: frozenset, sql: str) -> dict:
    """The result of `sql` on the databases of `tables` (labeler.gold.result), or status
    "outside" when it reads a table that is not in the set."""
    if not sql:
        return {"status": "no sql", "rows": 0}
    many = len(paths) > 1
    target = paths if many else next(iter(paths.values()))
    seen = set()

    def authorize(action, table, _column, database, *_):
        if action == sqlite3.SQLITE_READ and table and not table.startswith("sqlite_"):
            seen.add(f"{database}.{table}".lower() if many else f"{next(iter(paths))}.{table}".lower())
        return sqlite3.SQLITE_OK

    try:
        with closing(connect(target)) as conn:
            conn.set_authorizer(authorize)
            conn.execute("EXPLAIN " + sql)
    except sqlite3.Error as error:
        return {"status": "error", "error": str(error)[:200], "rows": 0}
    if seen - {t.lower() for t in tables}:
        return {"status": "outside", "error": "reads " + ", ".join(sorted(seen - {t.lower() for t in tables})), "rows": 0}
    return result(target, sql)


def _run(args):
    return run(*args)


def write(name: str, url: str, sample: int | None, threads: int, shard: str | None, hinted: bool) -> None:
    writer = Writer(name, url, threads, shard)
    work = []
    for lake_name in P.THREE:
        lake = Lake(lake_name)

        def paths(s):
            return {d: lake.paths[d] for d in sorted({lake.table[t].database for t in s})}

        if hinted:
            work += [(lake_name, q, s, text, paths(s), n) for q, n, s, text in hint_jobs(lake_name)]
        else:
            text, sets = jobs(lake_name)
            work += [(lake_name, q, s, prompt(lake, s, text[q]), paths(s), None) for q in sets for s in sets[q]]
    if sample:
        work = random.Random(0).sample(work, sample)
    # one schema after another, so the server reuses the shared start of the prompts
    work.sort(key=lambda w: (w[0], sorted(w[2])))
    if shard:
        i, n = map(int, shard.split("/"))
        work = work[i * len(work) // n:(i + 1) * len(work) // n]
    print(f"{name}: {len(work)} prompts, {sum(writer.key(w[3]) not in writer.cache for w in work)} not cached", flush=True)
    start = time.time()
    done = 0

    def one(w):
        nonlocal done
        got = writer(w[3])
        done += 1
        if done % 500 == 0:
            print(f"  {done}/{len(work)} in {time.time() - start:.0f} s, {dict(writer.used)}", flush=True)
        return got

    with ThreadPoolExecutor(threads) as pool:
        replies = list(pool.map(one, work))
    seconds = time.time() - start
    if shard:
        print(f"{name} shard {shard}: {len(work)} prompts in {seconds:.0f} s; calls {dict(writer.used)}", flush=True)
        return
    with ProcessPoolExecutor(8) as pool:
        results = list(pool.map(_run, [(w[4], w[2], r["sql"]) if r["sql"] else ({}, w[2], "") for w, r in zip(work, replies)],
                                chunksize=16))
    by_lake: dict[str, list] = {}
    for w, r, res in zip(work, replies, results):
        res = res if r["sql"] else {"status": "no sql", "error": r["why"], "rows": 0}
        by_lake.setdefault(w[0], []).append({"q": w[1], "set": sorted(w[2]), "sql": r["sql"], "result": res}
                                            | ({} if w[5] is None else {"i": w[5]}))
    suffix = (".hints" if hinted else "") +(f".sample{sample}" if sample else "")
    for lake_name, rows in by_lake.items():
        (OUT / name / f"{lake_name}{suffix}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    tokens = replies
    status = Counter(x["result"]["status"] for rows in by_lake.values() for x in rows)
    print(f"{name}: {len(work)} prompts in {seconds:.0f} s; calls {dict(writer.used)}; results {dict(status)}; "
          f"mean prompt tokens {np.mean([t['prompt_tokens'] for t in tokens]):.0f}, "
          f"mean reply tokens {np.mean([t['tokens'] for t in tokens]):.0f}", flush=True)


# ---- scores


def targets(lake: str) -> dict[str, dict[str, list[tuple[str, list[frozenset]]]]]:
    """{label: {question: [(result hash, table sets of the valid queries that return it)]}}.
    Gold label: the gold result, when it has rows. Multi-valid label: every answer group
    of runs/labeler/LAKE/labels.jsonl (the labeler keeps only results with rows)."""
    labels = P.labels(P.NIGHT, lake)
    folder = R.ROOT / "runs" / "labeler" / lake
    ids = {q["question_id"]: q["id"] for q in eval_lakes._lines(folder / "questions.jsonl")}
    stored = {one["id"]: one for one in eval_lakes._lines(folder / "labels.jsonl")}
    read = eval_lakes.Gold(lake)
    out = {"gold": {}, "multi": {}}
    for row in eval_lakes._lines(P._questions(P.NIGHT, lake)):
        q = row["id"]
        one = stored.get(q) or stored.get(ids.get(row.get("question_id")))
        if q not in labels["gold"] or one is None:
            continue
        gold_tables = frozenset(labels["gold"][q][0][0])
        if one["gold"]["status"] == "ok":
            out["gold"][q] = [(one["gold"]["hash"], [gold_tables])]
        answers = []
        for group, digest in zip(one.get("interpretations") or [], one.get("hashes") or []):
            sets = []
            for member in group:
                if member["name"] == "gold":
                    sets.append(gold_tables)
                elif member.get("sql"):
                    try:
                        sets.append(frozenset(read(member["db"], member["sql"])[0]))
                    except sqlite3.Error:
                        continue
            if sets:
                answers.append((digest, list(dict.fromkeys(sets))))
        if answers and q in labels["multi"]:
            out["multi"][q] = answers
    return out


def results(name: str, lake: str) -> dict[tuple[str, frozenset], dict]:
    path = OUT / name / f"{lake}.jsonl"
    return {(x["q"], frozenset(x["set"])): x["result"] for x in eval_lakes._lines(path)}


def hint_results(name: str, lake: str) -> dict[str, list[tuple[frozenset, dict]]] | None:
    """Per question, (tables, result) of each SQL written from AMIGO's interpretations
    (--hints); None before that run."""
    path = OUT / name / f"{lake}.hints.jsonl"
    if not path.exists():
        return None
    out: dict[str, list] = {}
    for x in sorted(eval_lakes._lines(path), key=lambda x: (x["q"], x["i"])):
        out.setdefault(x["q"], []).append((frozenset(x["set"]), x["result"]))
    return out


def question(answers: list, sets: list[frozenset], res: list[dict], pooled: bool) -> dict:
    """Per size (all, single, multi) the mean EX over the question's targets of that size,
    and the same over targets whose tables some returned set holds ("found") or not
    ("missed"); result P on the multi-valid label; SQLs and how many failed to give rows
    or an empty answer (error, outside, slow, no sql). `res` holds the results of the
    question's SQLs, one per returned set (or per interpretation, with hints)."""
    hashes = {r["hash"] for r in res if r["status"] in ("ok", "empty")}
    out = {}
    for size in R.SIZES:
        mine = [(h, ts) for h, ts in answers if size == "all" or (min(map(len, ts)) == 1) == (size == "single")]
        for split in ("", " found", " missed"):
            keep = [h for h, ts in mine if not split or any(t <= s for t in ts for s in sets) == (split == " found")]
            out[f"{size}{split}"] = mean(float(h in hashes) for h in keep) if keep else None
    target = {h for h, _ in answers}
    out["result P"] = len(hashes & target) / len(hashes) if pooled and hashes else None
    out["sqls"] = len(res)
    out["failed"] = sum(r["status"] not in ("ok", "empty") for r in res)
    return out


def score(name: str, out: Path) -> None:
    rng = np.random.default_rng(R.SEED)
    scored = {}
    for lake in P.THREE:
        got, goal = results(name, lake), targets(lake)
        hinted = hint_results(name, lake)

        def scored_q(a, sets, q, multi):
            return question(a, sets, [got.get((q, s), {"status": "no sql"}) for s in sets], multi)

        scored[lake] = {}
        for label in R.LABEL_NAMES:
            multi = label == "multi"
            scored[lake][label] = {ORACLE: {q: scored_q(a, list(dict.fromkeys(t for _, ts in a for t in ts)), q, multi)
                                            for q, a in goal[label].items()}}
            for method, (night, file, first) in R.METHODS.items():
                if (night / lake / file).exists():
                    records = json.loads((night / lake / file).read_text())
                    scored[lake][label][method] = {q: scored_q(a, R.returned(records.get(q), first), q, multi)
                                                   for q, a in goal[label].items()}
            if hinted is not None:
                scored[lake][label][HINTS] = {
                    q: question(a, list(dict.fromkeys(s for s, _ in hinted.get(q, []))), [r for _, r in hinted.get(q, [])],
                                multi)
                    for q, a in goal[label].items()}
    lines = [f"# SQL (stage 2 of docs/eval_protocol.md), writer {name}", "",
             "EX: a target (one distinct result of the label) counts when some SQL of the method returns its rows; mean "
             "over the question's targets, then over questions. Single / multi: targets whose smallest valid query reads "
             "one table / two or more. found / missed: targets whose tables some returned set holds / none does. "
             "result P (multi-valid label): distinct results that are a target, over distinct results (empty ones "
             "included, failed SQLs left out). SQLs: one per distinct returned set. failed: share of SQLs with no "
             "result (error, a table outside the set, too slow, no SQL). The oracle writes from the label's own "
             "table sets. AMIGO with hints writes AMIGO's plain prompt per table set, plus, when several interpretations share the set, "
             "one line per part whose place differs between them (one SQL per distinct prompt).", ""]
    rows = []
    keys = ["all", "single", "multi", "all found", "all missed"]
    for label, title in R.LABEL_NAMES.items():
        cols = keys + (["result P"] if label == "multi" else [])
        lines += [f"## {title}", "", "| lake | method | EX | single EX | multi EX | EX found | EX missed | "
                  + ("result P | " if label == "multi" else "") + "SQLs | failed | n |", "|" + "---|" * (len(cols) + 5)]
        table: dict[str, dict[str, list]] = {}
        for lake in P.THREE:
            for method, per_q in scored[lake][label].items():
                vals = {k: np.array([s[k] for s in per_q.values() if s[k] is not None]) for k in cols}
                cells = [100 * v.mean() if len(v) else float("nan") for v in vals.values()]
                sqls = sum(s["sqls"] for s in per_q.values())
                failed = 100 * sum(s["failed"] for s in per_q.values()) / max(sqls, 1)
                table.setdefault(method, {})[lake] = cells
                rows.append({"label": label, "lake": lake, "method": method, "n": len(per_q),
                             **dict(zip(cols, cells)), **{f"{k} n": len(v) for k, v in vals.items()},
                             "EX 95%": [100 * x for x in R.interval(vals["all"], rng)],
                             "SQLs per question": sqls / len(per_q), "failed %": failed})
                lines.append(f"| {P.LAKES[lake]} | {method} | " + " | ".join(f"{c:.1f}" for c in cells)
                             + f" | {sqls / len(per_q):.2f} | {failed:.1f}% | {len(per_q)} |")
        for agg in ("mean", "worst"):
            for method, per_lake in table.items():
                if len(per_lake) < len(P.THREE):
                    lines.append(f"| {agg} | {method} | ran on {len(per_lake)} of {len(P.THREE)} lakes |")
                    continue
                cells = [np.mean(c) if agg == "mean" else np.min(c) for c in zip(*per_lake.values())]
                lines.append(f"| {agg} | {method} | " + " | ".join(f"{c:.1f}" for c in cells) + " |")
        lines.append("")
    me = HINTS if hinted is not None else "AMIGO"  # the paper's AMIGO writes one query per candidate
    lines += [f"## {me} minus each method, EX", "",
              "Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), "
              "Holm-corrected p over the comparisons of one lake and label; * when below 0.05.", "",
              "| label | lake | method | EX |", "|---|---|---|---|"]
    for label in R.LABEL_NAMES:
        for lake in P.THREE:
            mine = scored[lake][label]
            others = [m for m in mine if m not in (me, ORACLE)]
            tests = [R.paired(np.array([s["all"] for s in mine[me].values()]),
                              np.array([s["all"] for s in mine[m].values()]), rng) for m in others]
            for m, (d, lo, hi, _), p in zip(others, tests, R.holm([t[3] for t in tests])):
                lines.append(f"| {R.LABEL_NAMES[label]} | {P.LAKES[lake]} | {m} | "
                             f"{100 * d:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]{'*' if p < 0.05 else ''} |")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"sql_{name}.md").write_text("\n".join(lines) + "\n")
    (out / f"sql_{name}.json").write_text(json.dumps(rows, indent=1))
    print(f"wrote {out / f'sql_{name}.md'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["write", "score"])
    parser.add_argument("writer", choices=list(WRITERS))
    parser.add_argument("--url", default="http://localhost:8000/v1")
    parser.add_argument("--sample", type=int)
    parser.add_argument("--threads", type=int, default=64)
    parser.add_argument("--shard")
    parser.add_argument("--hints", action="store_true")
    parser.add_argument("--out", type=Path, default=SCORES)
    args = parser.parse_args()
    if args.command == "score":
        score(args.writer, args.out)
    else:
        write(args.writer, args.url, args.sample, args.threads, args.shard, args.hints)


if __name__ == "__main__":
    main()
