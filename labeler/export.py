"""Write the multi-valid benchmarks for Hugging Face: one JSON Lines file per benchmark.

  LABEL_RUN=export .venv/bin/python -m labeler.export bird_dev spider_dev mmqa spider2_lite

Reads runs/labeler/<lake>/labels.jsonl and questions.jsonl, and the value check
(labeler.values, runs/labeler/<run>/values.jsonl). A rewrite the judge found to change a
value of the question leaves the interpretations; it stays listed under alternatives with
value_check "changed". Each SQL lists the tables and columns SQLite reports it reads.
Writes runs/labeler/<run>/data/<name>/dev.jsonl.
"""

import ast
import json
import sys
from contextlib import closing

from labeler import OUT, RUN, databases, read
from labeler.gold import connect, reads
from labeler.values import missing

NAMES = {"bird_dev": "bird", "spider_dev": "spider", "mmqa": "mmqa", "spider2_lite": "spider2_lite"}


def export(lake: str, verdicts: dict[str, str]) -> list[dict]:
    paths = databases(lake)
    questions = {q["id"]: q for q in map(json.loads, (OUT / lake / "questions.jsonl").open())}

    def used(db: str, sql: str) -> tuple[list[str], list[str]] | tuple[None, None]:
        try:
            with closing(connect(paths[db])) as conn:
                tables, columns = reads(conn, sql)
            return sorted(tables), sorted(f"{t}.{c}" for t, c in columns)
        except Exception:  # a gold SQL that does not run
            return None, None

    def check(r: dict, a: dict) -> str | None:
        if not a["sql"]:
            return None
        if not missing(r["gold_sql"], a["sql"]):
            return "kept"
        verdict = verdicts.get(f"{r['id']}|{a['item']}|{a['name']}")  # None when the judge gave no reply
        return {None: "unchecked", "same": "re-expressed", "different": "changed"}[verdict]

    rows = []
    for r in map(json.loads, (OUT / lake / "labels.jsonl").open()):
        q = questions[r["id"]]
        found = {(s["item"], s["name"]): (s.get("result") or {}).get("rows") for s in r["swaps"]}
        answers = []
        for group in r["interpretations"]:
            ways = []
            for m in group:
                if m["name"] == "gold":
                    tables, columns = used(m["db"], r["gold_sql"])
                    ways.append({"is_gold_sql": True, "database": m["db"], "sql": r["gold_sql"], "tables": tables,
                                 "columns": columns, "change": None, "result_rows": r["gold"]["rows"]})
                elif check(r, m) != "changed":
                    tables, columns = used(m["db"], m["sql"])
                    ways.append({"is_gold_sql": False, "database": m["db"], "sql": m["sql"], "tables": tables,
                                 "columns": columns, "change": {"gold_item": m["item"], "replaced_by": m["name"],
                                                                "found_in": m["kind"], "sql_written_by": m["by"]},
                                 "result_rows": found[m["item"], m["name"]]})
            if ways:
                answers.append({"answer": len(answers), "is_gold_answer": ways[0]["is_gold_sql"],
                                "result_rows": ways[0]["result_rows"], "ways": ways})
        u, c = r["underspecified"], r["checks"]
        rows.append({
            "id": r["id"], "source": NAMES[lake], "db_id": q["db_id"], "question": r["question"],
            "evidence": q.get("evidence") or None, "gold_sql": r["gold_sql"],
            "gold_status": r["gold"]["status"], "gold_result_rows": r["gold"]["rows"],
            "gold_tables": ast.literal_eval(q["tables"]) if isinstance(q["tables"], str) else q["tables"],
            "gold_columns": ast.literal_eval(q["columns"]) if isinstance(q["columns"], str) else q["columns"],
            "num_answers": len(answers),
            "num_answers_same_db": sum(any(w["database"] == q["db_id"] for w in a["ways"]) for a in answers),
            "is_ambiguous": len(answers) > 1,
            "interpretations": answers,
            "alternatives": [{"gold_item": a["item"], "replaced_by": a["name"], "found_in": a["kind"],
                              "sql_written_by": a["by"], "outcome": a["answer"], "value_check": check(r, a),
                              "sql": a["sql"]} for a in r["accepted"]],
            "underspecified": {"parts_not_in_question": u["not_asked"], "parts_only_in_evidence": u["note_only"],
                               "values_spelled_differently": u["hidden_value_form"],
                               "computation_not_asked": u["computation"]},
            "label_checks": {"decoys": c["decoys"], "decoys_accepted": c["decoys_accepted"], "unsure_votes": c["unsure"],
                             "revoted": c["revoted"], "options_judged": c["asked"], "judge_calls": c["calls"],
                             "gold_items_found": c["gold_items_found"], "gold_items": c["gold_items"]},
        })
    return rows


if __name__ == "__main__":
    verdicts = {v["id"]: v["verdict"] for v in read("values")}
    for lake in sys.argv[1:]:
        rows = export(lake, verdicts)
        path = RUN / "data" / NAMES[lake] / "dev.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        print(f"{lake}: {len(rows)} questions, {sum(r['is_ambiguous'] for r in rows)} with more than one answer -> {path}")
