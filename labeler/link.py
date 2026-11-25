"""Step 2: tie each gold table and column to the words of the question that ask for it.

  .venv/bin/python -m labeler.link

One LLM call per question (the question, the benchmark's note when it has one, the gold
SQL and the list of gold items). Per item it gives a role (table, answer, filter, join,
group_or_sort) and the exact words, or none: the question is then underspecified there,
or explained only by the note (BIRD's "evidence"). It also lists the computation choices
the SQL makes that the question does not ask for. Code checks that every item is covered
and every span is in the question; a bad reply, or one with a span not in the question,
is retried with the next seed (3 tries). When all tries have such a span, the last is kept.
Writes runs/labeler/link.jsonl.
"""

from labeler import llm, read, run

TRIES = 3
ROLES = ["table", "answer", "filter", "join", "group_or_sort"]

SCHEMA = {
    "type": "object", "required": ["items", "computation_gaps"], "additionalProperties": False,
    "properties": {
        "items": {"type": "array", "items": {
            "type": "object", "required": ["item", "role", "words", "note_only"], "additionalProperties": False,
            "properties": {
                "item": {"type": "string"}, "role": {"enum": ROLES},
                "words": {"type": ["string", "null"]}, "note_only": {"type": "boolean"},
            }}},
        "computation_gaps": {"type": "array", "items": {"type": "string"}},
    },
}

PROMPT = """You compare a question asked to a database with the SQL query a person wrote to answer it. For each table and column the SQL uses, find the words of the question that ask for it.

For each item give:
- "role": "table" for a table. For a column: "answer" when its values are returned or computed into the answer; "filter" when it restricts which rows count (WHERE, HAVING, a condition in a join); "join" when it only links two tables, even if it is also grouped on; "group_or_sort" when it is only used in GROUP BY or ORDER BY.
- "words": the words of the question that ask for this item, copied exactly, character for character, as one continuous piece of the question. Use null when no words of the question ask for it. Join columns usually have null.
- "note_only": true when the question has no words for the item but the note does explain it. Otherwise false.

Then give "computation_gaps": the choices the SQL makes that the question does not ask for, a few words each (for example: keeps one row when several tie, removes duplicates, rounds the result, counts rows instead of distinct names). Use an empty list when there are none.

The note, when there is one, was written by the benchmark authors. It is not part of the question.

Example
Question: Which harbor received the most ferries in 2019?
Note: (none)
SQL: SELECT h.name FROM harbor h JOIN arrival a ON a.harbor_id = h.id WHERE strftime('%Y', a.day) = '2019' GROUP BY h.id ORDER BY COUNT(*) DESC LIMIT 1
Items: harbor, arrival, harbor.name, harbor.id, arrival.harbor_id, arrival.day
Output Format:
{{"items": [
  {{"item": "harbor", "role": "table", "words": "harbor", "note_only": false}},
  {{"item": "arrival", "role": "table", "words": "received the most ferries", "note_only": false}},
  {{"item": "harbor.name", "role": "answer", "words": "Which harbor", "note_only": false}},
  {{"item": "harbor.id", "role": "join", "words": null, "note_only": false}},
  {{"item": "arrival.harbor_id", "role": "join", "words": null, "note_only": false}},
  {{"item": "arrival.day", "role": "filter", "words": "in 2019", "note_only": false}}],
 "computation_gaps": ["keeps one harbor when several tie for the most"]}}

Now this one.
Question: {question}
Note: {note}
SQL: {sql}
Items: {items}

Output Format: a JSON object with exactly the keys "items" (one object per item above, each with exactly the keys "item", "role", "words", "note_only") and "computation_gaps" (a list of strings). No other text.
Return an answer only in this exact Output Format."""


def check(reply: dict, items: list[str], question: str) -> list[dict] | None:
    """The items in input order when the reply covers each exactly once; spans not found
    in the question become null and are marked."""
    by_name = {i["item"]: i for i in reply["items"]}
    if sorted(by_name) != sorted(items) or len(reply["items"]) != len(items):
        return None
    out = []
    for name in items:
        one = dict(by_name[name])
        if one["words"] is not None and one["words"].lower() not in question.lower():
            one["words"], one["bad_words"] = None, by_name[name]["words"]
        out.append(one)
    return out


def link(row: dict) -> dict:
    items = row["tables"] + row["columns"]
    prompt = PROMPT.format(question=row["question"], note=row["evidence"] or "(none)",
                           sql=row["gold_sql"], items=", ".join(items))
    kept = {"id": row["id"], "items": [], "computation_gaps": [], "tries": TRIES, "failed": True}
    for seed in range(TRIES):
        try:
            reply = llm.ask_json(prompt, seed, SCHEMA, tag=f"link {row['id']}")
            linked = check(reply, items, row["question"])
        except (ValueError, KeyError, TypeError):
            continue
        if linked is not None:
            kept = {"id": row["id"], "items": linked, "computation_gaps": reply["computation_gaps"], "tries": seed + 1}
            if not any("bad_words" in i for i in linked):
                return kept
    return kept


def note() -> str:
    u = llm.used
    return (f"\033[2mrunning {u['open']}  done {u['calls']}  cached {u['cached']}  "
            f"{u['tokens'] / 1e6:.2f}M tok  too long {u['cut']}\033[0m")


def main() -> None:
    rows = [r for r in read("questions") if r["tables"]]
    run("link", rows, link, colour="magenta", note=note)


if __name__ == "__main__":
    main()
