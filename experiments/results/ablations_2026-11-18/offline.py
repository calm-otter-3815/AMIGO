"""Two offline ablations of AMIGO for Table 8 of the paper: the lake built without the table and
column descriptions (nodesc), and without the declared foreign keys (nofk, BIRD and Spider; MMQA
declares none). Each starts from a copy of the paper's lake and runs the paper's AMIGO lazy again
on it, from the paper's saved splits:

  build VARIANT LAKE   copy runs/paper_2026-10-20/lakes/LAKE to runs/ablations_2026-11-18/lakes_VARIANT/LAKE
                       and build again the steps that depend on what is removed:
                       nodesc: every description emptied (the benchmark's value descriptions kept);
                               judged links, roles and embeddings built again;
                       nofk:   declared foreign keys hidden from the link rules (primary keys kept);
                               links, more links, judged links, roles and embeddings built again.
  eval ARGS...         experiments/eval_lakes.py on the copied lakes (ABL_LAKES), with the whole
                       judge left out, so the 'amigo' command saves the place-judge-only answers
                       that the 'joins' command takes, as in runs/rerun_2026-11-08/run.sh.
  score                stage 1 of the protocol, both labels, against the stored AMIGO lazy run.

run.sh next to this file chains them.
"""
import json
import os
import runpy
import shutil
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT), str(HERE.parent / "paper_review_2026-11-08")]
from amigo import config, judge, layer, links  # noqa: E402

OUT = ROOT / "runs" / "ablations_2026-11-18"
NIGHT_LAKES = ROOT / "runs" / "paper_2026-10-20" / "lakes"
STEPS = {"nodesc": ("judged_links", "roles", "embed"),
         "nofk": ("links", "more_links", "judged_links", "roles", "embed")}


def build(variant: str, lake: str) -> None:
    lakes = OUT / f"lakes_{variant}"
    prepared = lakes / lake / ".prepared"  # the copy is made and edited; a stopped build resumes from it
    if (lakes / lake).exists() and not prepared.exists():
        shutil.rmtree(lakes / lake)  # stopped while copying or editing: start the copy again
    if not prepared.exists():
        lakes.mkdir(parents=True, exist_ok=True)
        shutil.copytree(NIGHT_LAKES / lake, lakes / lake)
        with sqlite3.connect(lakes / lake / "layer.sqlite") as conn:
            if variant == "nodesc":
                conn.execute("UPDATE tables SET description = ''")
                conn.execute("UPDATE columns SET description = ''")
            for step in STEPS[variant]:
                conn.execute("DELETE FROM meta WHERE key = ?", (f"step_{step}",))
        prepared.touch()
    if variant == "nofk":
        links.declared = lambda *_: []  # the schema's foreign keys, as if none were declared
    config.LAKES_DIR = lakes
    layer.build(lake)


def evaluate(args: list[str]) -> None:
    config.LAKES_DIR = Path(os.environ["ABL_LAKES"])
    judge.whole_grades = lambda *_, **__: []  # place judge only: every candidate kept
    sys.argv = [str(ROOT / "experiments" / "eval_lakes.py"), *args]
    runpy.run_path(sys.argv[0], run_name="__main__")


def score() -> None:
    import paper_results as P
    import protocol as R
    import review as V
    out = []
    for variant in STEPS:
        for lake in P.THREE:
            path = OUT / variant / lake / "joinchoice" / "records_inf.json"
            if not path.exists():
                continue
            mine = V.records(path)
            for label in V.LABEL:
                labels = P.labels(P.NIGHT, lake)[label]
                row = V.mean_row(list(V.scored(labels, lambda q: R.returned(mine.get(q), False)).values()))
                out.append({"variant": variant, "lake": lake, "label": label, **row})
    (HERE / "offline.json").write_text(json.dumps(out, indent=1))
    for r in out:
        print(r["variant"], r["lake"], r["label"], *(f"{k} {r[k]:.1f}" for k in ("CR", "P", "IR", "IP") if k in r),
              f"sets {r['sets']:.2f}")


if __name__ == "__main__":
    command, rest = sys.argv[1], sys.argv[2:]
    if command == "build":
        build(*rest)
    elif command == "eval":
        evaluate(rest)
    elif command == "score":
        score()
    else:
        sys.exit(f"unknown command {command}")
