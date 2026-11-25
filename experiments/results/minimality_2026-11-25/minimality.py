"""Are the gold table sets the smallest ones? From the labels and the saved SQL results. No LLM call.

T: the single-valid gold table set of a question (the tables of its original query), on the
questions whose original query returns rows.

1. Labels only: the questions whose multi-valid label holds a gold table set strictly inside T
   (fewer tables, all among T's), and those where such a set belongs to a reference query that
   returns the same result as the original query.
2. Per method that returns one table set S: the questions where S holds T, where S is strictly
   inside T, and the others; in each group, the share whose saved query (main writer, written from
   S) returns the gold result, and for S strictly inside T, how many S are gold table sets of the
   multi-valid label. Then, over the questions where S does not hold T, how many S are gold table
   sets of the multi-valid label, and how many are that or return the gold result.

  .venv/bin/python experiments/results/minimality_2026-11-25/minimality.py   -> minimality.txt next to it
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT)]
import paper_results as P  # noqa: E402
import protocol as R  # noqa: E402
import sqleval as S  # noqa: E402

CONS = ROOT / "runs/refplaces_2026-11-19/{lake}/conservative/records_inf.json"


def ok(r: dict) -> bool:
    return r.get("status") in ("ok", "empty")


def main() -> None:
    lines = []
    for lake in P.THREE:
        got, goal = S.results("qwen", lake), S.targets(lake)
        gold = {q: (a[0][0], a[0][1][0]) for q, a in goal["gold"].items()}  # question -> (result hash, T)
        joins = [q for q, (_, t) in gold.items() if len(t) >= 2]
        inside = {q: [(h, s) for h, sets in goal["multi"].get(q, []) for s in sets if s < gold[q][1]] for q in gold}
        any_ = [q for q in gold if inside[q]]
        same = [q for q in gold if any(h == gold[q][0] for h, _ in inside[q])]
        lines.append(f"{lake}: {len(gold)} questions, {len(joins)} whose original query reads 2+ tables; "
                     f"multi-valid label holds a gold table set strictly inside T: {len(any_)} "
                     f"({100 * len(any_) / len(gold):.1f}% of all, {100 * len(any_) / len(joins):.1f}% of 2+); "
                     f"with the same result as the original query: {len(same)} "
                     f"({100 * len(same) / len(gold):.1f}% of all, {100 * len(same) / len(joins):.1f}% of 2+)")
        name, file, first = R.METHODS["CORE-T"]
        recs = {"CORE-T": (json.loads((name / lake / file).read_text()), first),
                "AMIGO conservative": (json.loads(Path(str(CONS).format(lake=lake)).read_text()), True)}
        for method, (rec, first) in recs.items():
            groups = {"holds T": [], "strictly inside T": [], "other": [], "no set": []}
            in_mv = miss = miss_mv = miss_either = inside_either = 0
            for q, (h, t) in gold.items():
                sets = R.returned(rec.get(q), first)
                if not sets:  # an empty output misses T
                    groups["no set"].append(0.0)
                    miss += 1
                    continue
                s = sets[0]
                right = float(ok(got.get((q, s), {})) and got[(q, s)]["hash"] == h)
                kind = "holds T" if t <= s else "strictly inside T" if s < t else "other"
                groups[kind].append(right)
                labeled = any(s in sets_ for _, sets_ in goal["multi"].get(q, []))
                in_mv += kind == "strictly inside T" and labeled
                inside_either += kind == "strictly inside T" and (labeled or bool(right))
                miss += kind != "holds T"
                miss_mv += kind != "holds T" and labeled
                miss_either += kind != "holds T" and (labeled or bool(right))
            lines.append(f"  {method}: " + "; ".join(
                f"{k} {len(v)} questions, gold result on {int(sum(v))} ({100 * sum(v) / len(v):.1f}%)" if v else f"{k} 0"
                for k, v in groups.items()) + f"; strictly inside T and in the multi-valid label: {in_mv}, in it or gold result: {inside_either}"
                         f"; S does not hold T: {miss}, of them S is a gold table set of the multi-valid label: {miss_mv} "
                         f"({100 * miss_mv / miss:.1f}%), that or gold result: {miss_either} ({100 * miss_either / miss:.1f}%)")
    (HERE / "minimality.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
