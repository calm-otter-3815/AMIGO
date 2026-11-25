"""Step 6: put each question's label together (code only), and the taxonomy per lake.

  .venv/bin/python -m labeler.label     prints the per-lake summary of runs/labeler/labels.jsonl

Per question (written by labeler.go into runs/labeler/labels.jsonl):
  gold            health of the gold SQL: ok, empty, error or slow, with its row count;
  underspecified  gold items no words of the question ask for (join columns, and tables
                  that have gold columns, aside), the ones only the benchmark's note
                  explains, filter values the question does not spell as stored, and the
                  computation choices it does not ask for;
  accepted        every accepted alternative, its kind (copy, same table, other table,
                  other database), who rewrote its SQL (code or LLM) and what it returned;
  interpretations the gold, then every alternative whose query ran, grouped by result
                  rows: one group per distinct answer;
  ambiguity       number of distinct answers inside the gold's database and in the lake;
  checks          decoys accepted, unsure votes, re-votes, LLM calls, gold items the
                  candidate search would have found.
"""

import re
from collections import Counter, defaultdict

from labeler import LAKES, dbs, read, split_item


def kind(row: dict, item: str, option: dict) -> str:
    db, rest = option["name"].split(".", 1)
    if "copy" in option["sources"]:
        return "copy"
    if db not in dbs(row):
        return "other database"
    cross = "db_ids" in row  # the item is then named db.table.column, like the option
    table, column = split_item(item, cross)
    return "same table" if column is not None and split_item(option["name"] if cross else rest, cross)[0] == table else "other table"


def spelled(value: str, question: str) -> bool:
    """`value` (its % signs removed) appears in `question` as a whole word or phrase, a plural s
    or es allowed, ignoring case."""
    value = value.strip("%").lower()
    return not value or bool(re.search(rf"(?<![a-z0-9]){re.escape(value)}(?:e?s)?(?![a-z0-9])", question.lower()))


def answers(row: dict, gold: dict, accepted: list[dict], results: list[dict | None]) -> dict:
    """The gold, then every accepted alternative whose query ran (`results`, one per
    alternative), grouped by result rows: one interpretation per distinct answer, with its
    row hash, and how many answers lie in the gold's database and in the lake."""
    groups: dict[str, list[dict]] = defaultdict(list)
    if gold.get("hash") and gold["status"] == "ok":
        groups[gold["hash"]].append({"name": "gold", "db": "+".join(dbs(row))})
    for one, res in zip(accepted, results):
        if (res or {}).get("status") == "ok":
            groups[res["hash"]].append({**one, "db": one["name"].split(".", 1)[0]})
    own = [g for g in groups.values() if any(m["name"] == "gold" or m["db"] in dbs(row) for m in g)]
    return {"interpretations": list(groups.values()), "hashes": list(groups),
            "ambiguity": {"own_database": len(own), "lake": len(groups)}}


def label(row: dict, link: dict, judged: dict, swaps: dict) -> dict:
    items = link.get("items", [])
    cross = "db_ids" in row
    with_columns = {split_item(i["item"], cross)[0] for i in items if split_item(i["item"], cross)[1] is not None}  # named by its columns, or only joined
    named = [i for i in items if i["role"] != "join" and i["item"] not in with_columns]
    hidden_values = list(dict.fromkeys(x["text"] for x in row["literals"] if not spelled(x["text"], row["question"])))
    gold = row["gold"]
    options = {(i["item"], o["name"]): o for i in judged.get("items", []) for o in i.get("options", [])}
    accepted = [{"item": s["item"], "name": s["name"], "kind": kind(row, s["item"], options[(s["item"], s["name"])]),
                 "by": s.get("by"), "answer": s["answer"], "sql": s["sql"]} for s in swaps.get("swaps", [])]
    judged_items = [i for i in judged.get("items", []) if "options" in i]
    asked = [o for o in options.values() if "votes" in o]
    return {
        "id": row["id"], "lake": row["lake"], "question": row["question"], "gold_sql": row["gold_sql"],
        "gold": {"status": gold["status"], "rows": gold["rows"], "hash": gold.get("hash")},
        "underspecified": {"not_asked": [i["item"] for i in named if not i["words"] and not i["note_only"]],
                           "note_only": [i["item"] for i in named if not i["words"] and i["note_only"]],
                           "hidden_value_form": hidden_values,
                           "computation": link.get("computation_gaps", [])},
        "accepted": accepted,
        **answers(row, gold, accepted, [s.get("result") for s in swaps.get("swaps", [])]),
        "checks": {
            "decoys_accepted": sum(o["decoy"] and o["verdict"] == "yes" for o in options.values()),
            "decoys": sum(o["decoy"] for o in options.values()),
            "unsure": sum(o.get("verdict") in ("unsure", "failed") for o in asked),
            "no_vote": sum(None in o["votes"] for o in asked),
            "revoted": sum(len(o["votes"]) == 3 for o in asked),
            "asked": len(asked),
            "calls": sum(i.get("calls", 0) for i in judged_items) + sum(s.get("by") == "llm" for s in swaps.get("swaps", [])),
            "gold_items_found": sum(bool(i.get("gold_found_by")) for i in judged_items),
            "gold_items": len(judged_items),
        },
    }


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "  -"


def summary(labels: list[dict]) -> list[str]:
    """One line per lake: gold health, how vague and how ambiguous the questions are, and
    the quality checks."""
    head = (f"{'lake':11} {'done':>4}  {'gold ok/empty/broken':>20}  {'underspec':>9}  {'ambiguous own/lake':>18}  "
            f"{'answers own/lake':>16}  {'decoys in':>9}  {'unsure':>6}  {'revoted':>7}  {'search found gold':>17}")
    lines = [head]
    for lake in LAKES + sorted({x["lake"] for x in labels} - set(LAKES)) + ["all"]:
        mine = [x for x in labels if lake in (x["lake"], "all")]
        if not mine:
            continue
        health = Counter(x["gold"]["status"] for x in mine)
        under = sum(any(x["underspecified"][k] for k in ("not_asked", "hidden_value_form")) for x in mine)
        amb_own = sum(x["ambiguity"]["own_database"] >= 2 for x in mine)
        amb_lake = sum(x["ambiguity"]["lake"] >= 2 for x in mine)
        mean_own = sum(x["ambiguity"]["own_database"] for x in mine) / len(mine)
        mean_lake = sum(x["ambiguity"]["lake"] for x in mine) / len(mine)
        c = Counter()
        for x in mine:
            c.update(x["checks"])
        lines.append(
            f"{lake:11} {len(mine):>4}  {health['ok']:>12}/{health['empty']}/{health['error'] + health['slow']:<5}  "
            f"{pct(under, len(mine)):>9}  {amb_own:>10}/{amb_lake:<7}  {mean_own:>9.1f}/{mean_lake:<6.1f}  "
            f"{c['decoys_accepted']:>4}/{c['decoys']:<4}  {pct(c['unsure'], c['asked']):>6}  {pct(c['revoted'], c['asked']):>7}  "
            f"{c['gold_items_found']:>10}/{c['gold_items']:<6}")
    return lines


def main() -> None:
    print("\n".join(summary(read("labels"))))


if __name__ == "__main__":
    main()
