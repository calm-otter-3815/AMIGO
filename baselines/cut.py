"""Write a smaller setting's records by cutting a larger setting's, where the smaller answer
is always the start of the larger one: dense and MURRE rank tables and k only cuts the
ranking; CRUSH4SQL picks columns one at a time and b only stops the picking. JAR picks its
best set of k tables as a whole (its best 3 need not be inside its best 5), so JAR is run at
each k, never cut. A cut record keeps the larger run's seconds: one run gives both answers.

  .venv/bin/python -m baselines.cut bl_murre_k5 3      # writes bl_murre_k3

`tables` cuts CRUSH4SQL to its first n tables in pick order instead, scored at the table
level like a top-n table retriever:
  .venv/bin/python -m baselines.cut bl_crush4sql_b100 10 tables   # writes bl_crush4sql_t10
"""

import re
import sys

from .lake import Lake, record
from .run import eval_lakes

CUTTABLE = ("bl_dense_k", "bl_murre_k", "bl_crush4sql_b", "bl_greedy_jar_k", "bl_bm25_k", "bl_hybrid_k")


def cut(one: dict, n: int, lake: Lake | None = None) -> dict:
    """The record with only its first n tables, or, given the lake (CRUSH4SQL), its first n
    picked columns and their tables in pick order."""
    if "error" in one:
        return one
    if lake is None:
        return {**one, **record(one["order"][:n], levels=one["levels"])}
    columns = one["pick_order"][:n]
    tables = list(dict.fromkeys(lake.column[c].table for c in columns))
    return {**one, **record(tables, columns, levels=one["levels"]), "pick_order": columns}


def main() -> None:
    source, n = sys.argv[1], int(sys.argv[2])
    tables = sys.argv[3:] == ["tables"]
    prefix, larger = re.fullmatch(r"(.*\D)(\d+)", source).groups()
    if prefix not in CUTTABLE or not 0 < n < int(larger) or (tables and prefix != "bl_crush4sql_b"):
        sys.exit(f"cannot cut {source} to {n}: only {', '.join(CUTTABLE)} cut, to a smaller number,"
                 " and only CRUSH4SQL to tables")
    name = f"bl_crush4sql_t{n}" if tables else f"{prefix}{n}"
    target = eval_lakes.RUNS / name / "records.json"
    if target.exists():
        sys.exit(f"{target} exists; delete it to cut again")
    lake_of = {row["id"]: row["lake"] for row in eval_lakes._lines(eval_lakes.QUESTIONS)}
    lakes: dict[str, Lake] = {}
    records = {}
    for qid, one in eval_lakes._load(eval_lakes.RUNS / source / "records.json").items():
        if tables:
            records[qid] = cut(one, n) | ({} if "error" in one else {"levels": ["tables"]})
            continue
        lake = None
        if prefix == "bl_crush4sql_b":
            if lake_of[qid] not in lakes:
                lakes[lake_of[qid]] = Lake(lake_of[qid])
            lake = lakes[lake_of[qid]]
        records[qid] = cut(one, n, lake)
    eval_lakes._save(target, records)
    failed = sum("error" in one for one in records.values())
    print(f"{name}: {len(records)} records cut from {source}; failed: {failed}")


if __name__ == "__main__":
    main()
