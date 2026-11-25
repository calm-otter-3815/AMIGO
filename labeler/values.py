"""Check the accepted rewrites that dropped a value the gold SQL filters on.

  LABEL_RUN=export .venv/bin/python -m labeler.values bird_dev spider_dev mmqa

The rewrite step (labeler.swap) sees only three stored values of the new column. When the
question's value is not among them, the model sometimes picks one it was shown ("Canada"
becomes 'United States'). A rewrite can also drop a value for a good reason: the new
column stores it in another form ("Prague" becomes 'Hl.m. Praha'). Code cannot tell the two
apart, so the judge reads each such rewrite: one vote, best of three on "different".
Writes runs/labeler/<run>/values.jsonl, one record per checked rewrite.
"""

import json
import re
import sys

from labeler import OUT, run
from labeler.llm import ask_json

QUOTED = re.compile(r"""'([^']*)'|"([^"]*)\"""")
SCHEMA = {"type": "object", "required": ["values"], "additionalProperties": False,
          "properties": {"values": {"enum": ["same", "different"]}}}

PROMPT = """You check one rewritten SQL query.

A question was asked to a database. The reference SQL answers it. The rewritten query reads some words of the question another way (another column or table), and that change is allowed. Check only the values the question names.

The rewritten query no longer contains some values of the reference SQL. Answer "same" when each of them is still asked for, written the way the new column stores it (a code, an abbreviation, another spelling, another format). Answer "different" when any of them now names something else (another place, person, category, date), was dropped, or was replaced by a list of ids or values taken from the data instead of what the question names.

Example 1
Question: "How many parcels were shipped to Lyon?"
Reference SQL: SELECT COUNT(*) FROM parcels WHERE dest_city = 'Lyon'
Rewritten query: SELECT COUNT(*) FROM parcels p JOIN depots d ON p.depot_id = d.id WHERE d.city_code = 'LYS'
Values no longer in the rewritten query: 'Lyon'
Output Format:
{{"values": "same"}}

Example 2
Question: "List the pumps installed in Oslo."
Reference SQL: SELECT name FROM pumps WHERE city = 'Oslo'
Rewritten query: SELECT p.name FROM pumps p JOIN sites s ON p.site_id = s.id WHERE s.region = 'Bergen'
Values no longer in the rewritten query: 'Oslo'
Output Format:
{{"values": "different"}}

Example 3
Question: "What did the chess club spend on snacks at the Spring Fair?"
Reference SQL: SELECT b.spent FROM budget b JOIN events e ON b.event_id = e.id WHERE e.title = 'Spring Fair' AND b.category = 'Snacks'
Rewritten query: SELECT spent FROM budget WHERE category = 'Snacks' AND event_id IN ('ev17', 'ev42')
Values no longer in the rewritten query: 'Spring Fair'
Output Format:
{{"values": "different"}}

Now this one.
Question: "{question}"
Reference SQL: {gold_sql}
Rewritten query: {sql}
Values no longer in the rewritten query: {missing}

Output Format: a JSON object with exactly the key "values", whose value is "same" or "different". No other text.
Return an answer only in this exact Output Format."""


def missing(gold_sql: str, sql: str) -> list[str]:
    """The quoted values of `gold_sql` that `sql` does not contain (ignoring case and % signs)."""
    values = dict.fromkeys(a or b for a, b in QUOTED.findall(gold_sql))
    return [v for v in values if v.strip("%") and v.strip("%").lower() not in sql.lower()]


def todo(lakes: list[str]) -> list[dict]:
    items = []
    for lake in lakes:
        for r in map(json.loads, (OUT / lake / "labels.jsonl").open()):
            for a in r["accepted"]:
                if a["sql"] and (gone := missing(r["gold_sql"], a["sql"])):
                    items.append({"id": f"{r['id']}|{a['item']}|{a['name']}", "question": r["question"],
                                  "gold_sql": r["gold_sql"], "sql": a["sql"], "missing": gone})
    return items


def check(item: dict) -> dict:
    prompt = PROMPT.format(**{**item, "missing": ", ".join(f"'{v}'" for v in item["missing"])})
    votes = [ask_json(prompt, 0, SCHEMA, f"values {item['id']}")["values"]]
    if votes[0] == "different":
        votes += [ask_json(prompt, seed, SCHEMA, f"values {item['id']}")["values"] for seed in (1, 2)]
    return {"id": item["id"], "missing": item["missing"], "votes": votes,
            "verdict": "different" if votes.count("different") >= 2 else "same"}


if __name__ == "__main__":
    run("values", todo(sys.argv[1:]), check)
