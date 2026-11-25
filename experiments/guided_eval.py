"""The guided search (amigo/guide.py) on saved AMIGO runs, walked by three simulated people.
No LLM call: the tree's candidates come from the saved run of the paper's AMIGO.

  .venv/bin/python experiments/guided_eval.py [LAKE...] [--limit N] [--workers N] [--idle S] [--out DIR] [--report]

Per question, the tree is built once from the saved candidates (runs/rerun_2026-11-08/LAKE/
joinchoice). Then:

- lazy: "any of these" at every fork. They keep every candidate, so their table sets must be
  exactly those of the automatic answer (records_inf.json). A check of the tree, not a score.
- conservative: the heaviest option at every fork. They must end with exactly the table set
  of AMIGO top-1. A check too.
- informed: reads the label, and wants every labeled table set of the question (each label,
  the gold one and the multi-valid one, walked on its own). At each fork, for each wanted
  table set, they tick the options under which a candidate reads exactly its tables, else
  those under which one holds them all (`informed`); with no such option, they say none of
  these. They see every candidate under each option, so these scores are a best case. Their
  table sets are scored as protocol.py scores every method, against the whole label.

A run also reports the tree's size per question (candidates, forks asked, and the most forks
on one path from the top) and what the informed person went through: how each case ended
(`outcome`), how many questions they answered, how many options a question showed and how
many they ticked, how often they said none of these, and which kinds of question were asked.

A lake stops once no question has finished for --idle seconds: the questions still going
are named and left out, like those whose saved run failed. --report prints the scores of a
run already saved in --out.
"""

import argparse
import json
import pickle
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocol as R  # noqa: E402

from amigo import candidates, config, guide  # noqa: E402
from amigo.probe import Probe  # noqa: E402

P = R.P
# the saved runs were made on the paper's lakes, not on the ones of this checkout
config.LAKES_DIR = P.NIGHT / "lakes"
OUT = P.ROOT / "runs" / "guided_2026-11-13"
# every answer goes down the tree or rules options out, so a walk ends; this only stops a bug
GUARD = 500
PROBE = GRAPH = None

OUTCOMES = {"exact": "exactly their tables", "larger": "theirs inside a larger set",
            "missed": "table sets left, none holds theirs", "nothing": "nothing left"}


def outcome(target: frozenset, sets: list[frozenset]) -> str:
    """How a case ended for the person, one of OUTCOMES: a table set left is exactly theirs,
    else one holds all their tables with others, else none does, else nothing is left."""
    if target in sets:
        return "exact"
    if any(target <= s for s in sets):
        return "larger"
    return "missed" if sets else "nothing"


def lazy(fork: guide.Fork, leads) -> guide.Answer:
    return guide.Answer("any")


def conservative(fork: guide.Fork, leads) -> guide.Answer:
    return guide.Answer("pick", frozenset({fork.options[0].n}))


def informed(fork: guide.Fork, leads) -> guide.Answer:
    """What the label reader answers. They want every labeled table set of the question;
    `leads(option)` gives, per wanted table set, 2 when a candidate under the option reads
    exactly its tables, 1 when one holds them all, else 0. For each wanted table set they tick
    the options that lead closest to it; when no option leads to any, they say none of these."""
    fits = [leads(o) for o in fork.options]
    picked = set()
    for j in range(len(fits[0])):
        best = max(f[j] for f in fits)
        if best:
            picked |= {o.n for o, f in zip(fork.options, fits) if f[j] == best}
    return guide.Answer("pick", frozenset(picked)) if picked else guide.Answer("none")


def walk(tree: guide.Tree, policy, wanted: tuple = ()) -> tuple[list, list[dict]]:
    """The candidates kept once the person is done, and each fork asked on the way: its kind,
    the options it showed, how many more sat behind none of these, how many the person
    ticked, and whether they said none of these. `wanted`: the table sets the person wants."""
    answers, asked = [], []

    def leads(option: guide.Option) -> tuple[int, ...]:
        return tuple(max(2 if tables == tree.found[i].tables else int(tables <= tree.found[i].tables)
                         for i in option.leaves) for tables in wanted)

    while True:
        step = guide.step(tree, answers)
        fork = step.fork
        if fork is None:
            return step.leaves, asked
        if len(answers) >= GUARD:
            raise RuntimeError(f"still asking after {GUARD} answers")
        said = policy(fork, leads)
        asked.append({"kind": fork.kind, "options": len(fork.options), "more": fork.more,
                      "ticked": len(said.picked), "none": said.kind == "none"})
        answers.append(said)


def _start(lake: str) -> None:
    global PROBE, GRAPH
    PROBE = Probe(lake)
    GRAPH = candidates.Graph(PROBE)


def _sets(leaves: list) -> list[list[str]]:
    """The distinct non-empty table sets of the candidates kept, in order, as protocol.returned."""
    sets = dict.fromkeys(tuple(sorted(PROBE.path("table", t) for t in leaf.tables)) for leaf in leaves)
    return [list(s) for s in sets if s]


def one(task: tuple[str, str, list]) -> dict:
    """One question: the tree's size, the table sets the lazy and the conservative person
    keep, and per label the informed person's walk, who wants every labeled table set."""
    path, qid, targets = task
    try:
        # our own saved run, as eval_lakes.py reads it: a failed place judge still keeps its
        # candidates (saved["error"]), and the automatic answer is built from them, so the tree is too
        saved = pickle.loads(Path(path).read_bytes())
        tree = guide.build(saved["found"])
        out = {"id": qid, "tree": guide.size(tree), "sorted": tree.found == saved["found"]}
        for name, policy in (("lazy", lazy), ("conservative", conservative)):
            leaves, asked = walk(tree, policy)
            out[name] = {"sets": _sets(leaves), "asked": len(asked)}
        walks = {}
        for label, sets in targets.items():
            leaves, asked = walk(tree, informed, tuple(frozenset(PROBE.find(t)[1] for t in tables) for tables in sets))
            walks[label] = {"asked": asked, "sets": _sets(leaves)}
        return out | {"walks": walks}
    except Exception as err:  # a failed question is reported, not hidden
        return {"id": qid, "error": repr(err)}


def _targets(labels: dict, qid: str) -> dict[str, list[tuple]]:
    """Per label of the question, its labeled table sets, each as sorted table names."""
    return {label: [tuple(sorted(t)) for t in R.targets_of(labels[label][qid])]
            for label in R.LABEL_NAMES if qid in labels[label]}


def run(lake: str, limit: int | None, workers: int, idle: int, out: Path) -> dict:
    labels = P.labels(P.NIGHT, lake)
    folder = R.JOINCHOICE / lake / "joinchoice"
    # every question with a label: Spider 2.0-Lite has the gold label only
    ids = [q for q in {**labels["gold"], **labels["multi"]} if (folder / f"{q}.amigo.pkl").exists()][:limit]
    tasks = {q: (str(folder / f"{q}.amigo.pkl"), q, _targets(labels, q)) for q in ids}
    got = {}
    with Pool(workers, _start, (lake,)) as pool:  # leaving the block stops the questions still going
        waiting = {q: pool.apply_async(one, (task,)) for q, task in tasks.items()}
        last = time.monotonic()
        while waiting and time.monotonic() - last < idle:
            time.sleep(1)
            for q in [q for q, r in waiting.items() if r.ready()]:
                got[q] = waiting.pop(q).get()
                last = time.monotonic()
    for q in waiting:
        got[q] = {"id": q, "error": "did not end"}
    got = {q: got[q] | {"targets": task[2]} for q, task in tasks.items()}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{lake}.json").write_text(json.dumps(got))
    return got


def _spread(values: list[float]) -> str:
    return f"mean {mean(values):.2f}, median {median(values):g}, most {max(values)}"


def checks(lake: str, got: dict, records: dict) -> None:
    """The tree's size, and every question where the lazy or the conservative person does not
    keep exactly the automatic answer's table sets, or AMIGO top-1's."""
    done = {q: r for q, r in got.items() if "error" not in r}
    failed = Counter("did not end" if r["error"] == "did not end" else "saved run failed"
                     for r in got.values() if "error" in r)
    print(f"{lake}: {len(done)} questions, left out: "
          + (", ".join(f"{n} {why}" for why, n in failed.items()) or "none"))
    sizes = [r["tree"] for r in done.values()]
    print("  tree      " + " | ".join(f"{k} {_spread([s[k] for s in sizes])}" for k in ("leaves", "forks", "depth"))
          + f" | questions with no fork to ask {mean(s['forks'] == 0 for s in sizes):.1%}")
    unsorted = [q for q, r in done.items() if not r["sorted"]]
    if unsorted:
        print(f"  saved candidates not cheapest first: {unsorted}")
    for name, first in (("lazy", False), ("conservative", True)):
        wrong = [q for q, r in done.items()
                 if [frozenset(s) for s in r[name]["sets"]] != R.returned(records.get(q), first)]
        asked = [r[name]["asked"] for r in done.values()]
        print(f"  {name:12} questions answered: {_spread(asked)} | table sets not exactly "
              f"{'AMIGO top-1' if first else 'the automatic answer'}: {len(wrong)}" + (f" {wrong}" if wrong else ""))


WHO = ("lazy", "conservative", "informed")


def report(lake: str, got: dict) -> dict:
    """{label: {"<who> <score>": value}}: per person (WHO), the R, CR and P of each target
    against the table sets kept, the sets kept and the questions answered; printed as a table
    per label, after the tree's size and the checks, with what the informed person went
    through."""
    labels = P.labels(P.NIGHT, lake)
    records = json.loads((R.JOINCHOICE / lake / "joinchoice" / "records_inf.json").read_text())
    checks(lake, got, records)
    out = {}
    for label in R.LABEL_NAMES:
        rows, forks, counts = [], [], []
        for q, result in got.items():
            if q not in labels[label] or "error" in result:
                continue
            w = result["walks"][label]
            kept = {name: [frozenset(s) for s in result[name]["sets"]] for name in ("lazy", "conservative")}
            kept["informed"] = [frozenset(s) for s in w["sets"]]
            forks += w["asked"]
            counts.append(len(w["asked"]))
            mine = []
            for target in R.targets_of(labels[label][q]):
                asked = {"lazy": result["lazy"]["asked"], "conservative": result["conservative"]["asked"],
                         "informed": len(w["asked"])}
                one = {}
                for name in WHO:
                    r, cr, p = R.matched(target, kept[name])
                    one |= {f"{name} R": r, f"{name} CR": cr, f"{name} P": p, f"{name} sets": len(kept[name]),
                            f"{name} asked": asked[name]}
                how = outcome(target, kept["informed"])
                mine.append(one | {"no question": not w["asked"], "said none": any(f["none"] for f in w["asked"]),
                                   **{o: how == o for o in OUTCOMES}})
            rows.append({k: mean(m[k] for m in mine) for k in mine[0]})
        if not rows:  # no question has this label on the lake
            continue
        s = out[label] = {k: mean(r[k] for r in rows) for k in rows[0]}
        kinds = Counter(f["kind"] for f in forks)
        print(f"  {R.LABEL_NAMES[label]}: {len(rows)} questions")
        print(f"    {'':13} {'R':>6} {'CR':>6} {'P':>6} {'sets':>5} {'questions':>9}")
        for name in WHO:
            print(f"    {name:13} " + " ".join(f"{s[f'{name} {k}']:6.1%}" for k in ("R", "CR", "P"))
                  + f" {s[f'{name} sets']:5.2f} {s[f'{name} asked']:9.2f}")
        print("    informed, outcome: " + " | ".join(f"{name} {s[o]:.1%}" for o, name in OUTCOMES.items()))
        print(f"    informed, questions: median {median(counts):g}, most {max(counts)}, none asked in "
              f"{s['no question']:.1%} of questions | none of these said at least once in {s['said none']:.1%} of cases")
        if forks:
            print(f"    informed, per question asked ({len(forks)}): options shown {mean(f['options'] for f in forks):.2f}, "
                  f"ticked {mean(f['ticked'] for f in forks):.2f}, none of these {mean(f['none'] for f in forks):.1%}, "
                  f"more options behind none of these {mean(f['more'] > 0 for f in forks):.1%} | kinds: "
                  + ", ".join(f"{k} {n / len(forks):.1%}" for k, n in kinds.most_common()))
        sys.stdout.flush()
    return out


def main_table(lake: str, got: dict) -> dict:
    """{label: {score: value}}: the informed person in the columns of the paper's main table,
    scored by protocol.question as every method is (Size: over the questions with a set). IF1
    is the harmonic mean of IR and IP, 0 when either is 0, as in the paper's appendix."""
    labels = P.labels(P.NIGHT, lake)
    out = {}
    for label in R.LABEL_NAMES:
        per_q, sizes = [], []
        for q, result in got.items():
            if q not in labels[label] or "error" in result:
                continue
            sets = [frozenset(s) for s in result["walks"][label]["sets"]]
            one = R.question(R.targets_of(labels[label][q]), sets, True)
            ir, ip = one["all"]["IR"], one["all"]["IP"]
            per_q.append(one["all"] | {"Sets": one["sets"], "IF1": 2 * ir * ip / (ir + ip) if ir and ip else 0.0})
            if one["size"] is not None:
                sizes.append(one["size"])
        if per_q:
            out[label] = {k: mean(r[k] for r in per_q) for k in per_q[0]} | {"Size": mean(sizes)}
            print(f"  informed, main table, {R.LABEL_NAMES[label]}: " + " ".join(
                f"{k} {out[label][k] * (1 if k in ('Sets', 'Size') else 100):.2f}"
                for k in ("R", "CR", "P", "F1", "CR=", "IR", "ICR", "IP", "IR=", "ICR=", "IP=", "pooled P", "IF1",
                          "Sets", "Size")))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("lakes", nargs="*", default=list(P.THREE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--idle", type=int, default=1800)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    summary = {}
    for lake in args.lakes:
        got = (json.loads((args.out / f"{lake}.json").read_text()) if args.report
               else run(lake, args.limit, args.workers, args.idle, args.out))
        summary[lake] = report(lake, got)
        main_table(lake, got)
    for label in R.LABEL_NAMES:
        print(f"{R.LABEL_NAMES[label]}, over {len(summary)} lakes: mean (worst)")
        for name in WHO:
            values = {k: [summary[lake][label][f"{name} {k}"] for lake in summary if label in summary[lake]] for k in ("R", "CR", "P", "asked")}
            print(f"  {name:13} " + " ".join(f"{k} {mean(v):.1%} ({min(v):.1%})" for k, v in values.items() if k != "asked")
                  + f" questions {mean(values['asked']):.2f} ({max(values['asked']):.2f})")
