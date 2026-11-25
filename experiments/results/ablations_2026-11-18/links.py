"""AMIGO without the join links chosen by an LLM call (Section 3.1), for Table 8 of the paper.

The place-judge-only configuration (no join judge) is searched again from its stored places and
place judge answers, no LLM call: first with every link, which must give the stored table sets
back (a check that the code still reproduces the paper run), then with the links of kind
'judged' left out of the link graph. Scored by stage 1 of the protocol, both labels.

  .venv/bin/python experiments/results/ablations_2026-11-18/links.py
Writes links.json next to this file.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT), str(HERE.parent / "paper_review_2026-11-08")]
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402
import review as V  # noqa: E402
from amigo import candidates, config, judge  # noqa: E402
from amigo.probe import Probe  # noqa: E402

config.LAKES_DIR = P.NIGHT / "lakes"
RULES = frozenset({"declared", "inferred", "values", "name"})  # every kind but 'judged'


def search(probe, graph, saved):
    places = judge.graded(saved["shown"], saved["grades"])
    found = candidates.candidates(probe, graph, saved["stage"], judge.MOST, graded=places)
    if not found:
        found = judge.relaxed(probe, graph, saved["stage"], places, judge.MOST, None)
    return list(dict.fromkeys(frozenset(probe.path("table", t) for t in c.tables) for c in judge.split(found, places)))


def main():
    out = []
    for lake in P.THREE:
        folder = V.NEW / lake / "abl_nojudge2"
        stored = V.records(folder / "records_inf.json")
        source = V.pickles(folder, stored)
        probe = Probe(lake)
        for name, kinds in (("all links", None), ("no LLM-chosen links", RULES)):
            graph = candidates.Graph(probe, kinds)
            sets = {q: search(probe, graph, s) for q, s in source.items() if not s.get("error") and s.get("shown")}
            if kinds is None:
                same = sum(set(sets[q]) == set(R.returned(stored.get(q), False)) for q in sets)
                print(f"{lake}: all links give the stored table sets back on {same} of {len(sets)} questions")
            for label in V.LABEL:
                labels = P.labels(P.NIGHT, lake)[label]
                row = V.mean_row(list(V.scored(labels, lambda q: sets[q] if q in sets else R.returned(stored.get(q), False)).values()))
                out.append({"lake": lake, "label": label, "setting": name, **row})
    (HERE / "links.json").write_text(json.dumps(out, indent=1))
    for r in out:
        print(r["lake"], r["label"], r["setting"], *(f"{k} {r[k]:.1f}" for k in ("CR", "P", "IR", "IP") if k in r), f"sets {r['sets']:.2f}")


if __name__ == "__main__":
    main()
