import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import eval_lakes  # noqa: E402


def test_label_by_row_id(tmp_path, monkeypatch):
    # a single and a cross question share question_id 7; each keeps its own label
    folder = tmp_path / "runs" / "labeler" / "taco"
    folder.mkdir(parents=True)
    rows = [{"id": "taco-q7", "question_id": 7, "lake": "taco", "db_id": "d", "gold_sql": "g"},
            {"id": "taco-x7", "question_id": 7, "lake": "taco", "db_id": "d", "gold_sql": "g"}]
    (folder / "questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    labels = [{"id": r["id"], "interpretations": [[{"name": "other", "db": "d", "sql": r["id"]}]]} for r in rows]
    (folder / "labels.jsonl").write_text("".join(json.dumps(one) + "\n" for one in labels))
    monkeypatch.setattr(eval_lakes, "ROOT", tmp_path)
    monkeypatch.setattr(eval_lakes, "Gold", lambda lake: lambda db, sql: ({sql}, set()))
    gold, missing = eval_lakes._label(rows)
    assert not missing
    assert gold["taco-q7"][1] == ({"taco-q7"}, set())
    assert gold["taco-x7"][1] == ({"taco-x7"}, set())


def test_paired():
    def one(complete):
        return {"tables": {"complete": complete, "f1": complete, "precision": 1.0}}
    sa = {q: one(c) for q, c in zip("abcd", (1.0, 1.0, 1.0, 0.0))}
    sb = {q: one(c) for q, c in zip("abcd", (1.0, 0.0, 0.0, 0.0))}
    got = eval_lakes._paired(sa, sb, list("abcd"), random.Random(0))
    assert (got["cr_won"], got["cr_lost"], got["sign_p"], got["cr_lead"]) == (2, 0, 0.5, 0.5)
    assert got["p_lead"] == 0.0


def test_lines_keep_a_next_line_character_inside_a_string(tmp_path):
    path = tmp_path / "llm.jsonl"
    path.write_text(json.dumps({"reply": "a\x85b"}, ensure_ascii=False) + "\n" + json.dumps({"n": 2}) + "\n")
    assert eval_lakes._lines(path) == [{"reply": "a\x85b"}, {"n": 2}]
