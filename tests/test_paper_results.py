import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import paper_results as pr  # noqa: E402

# the label: two valid table sets; AMIGO returns one of them whole and one wrong set
LABEL = [({"db.a", "db.b"}, set()), ({"db.c"}, set())]
AMIGO = {"picked": [], "interpretations": [{"tables": ["db.a", "db.b"], "bound": [], "joins": []},
                                           {"tables": ["db.d"], "bound": [], "joins": []}]}


def test_one_question_and_an_error_scored_empty(tmp_path):
    (tmp_path / "amigo").mkdir()
    (tmp_path / "amigo" / "records_inf.json").write_text(json.dumps({"q1": AMIGO}))
    (tmp_path / "bl_x").mkdir()
    (tmp_path / "bl_x" / "records.json").write_text(json.dumps({"q1": {"error": "TimeoutError"}}))

    record, failed = pr.answer(pr.records(tmp_path, "amigo@inf"), "q1", "amigo@inf")
    got = pr.metrics(LABEL, record)
    assert not failed
    # pooled {a, b, d} against {a, b, c}; sets: {a, b} found exactly, {c} not; {d} holds none
    assert {k: round(got[k], 4) for k in ("R", "CR", "P", "F1", "sR", "sCR", "sP", "eR", "eCR", "eP")} == {
        "R": 0.6667, "CR": 0.0, "P": 0.6667, "F1": 0.6667, "sR": 0.5, "sCR": 0.0, "sP": 0.5,
        "eR": 0.5, "eCR": 0.0, "eP": 0.5}

    record, failed = pr.answer(pr.records(tmp_path, "bl_x"), "q1", "bl_x")
    assert failed and record == pr.EMPTY
    assert all(pr.metrics(LABEL, record)[k] == 0 for k in ("R", "CR", "P", "F1", "sR", "sCR", "sP", "eR", "eCR", "eP"))

    # a missing question fails too, and the lake mean counts it
    pq = {("bird_dev", "amigo", "var"): {"multi": ({"q1": got, "q2": pr.metrics(LABEL, pr.EMPTY)}, ["q2"])}}
    rows = {(r[4], r[5], r[1]): (r[6], r[7], r[8]) for r in pr.summarize(pq)}
    assert rows[("table", "R", "bird_dev")] == (round(2 / 3 / 2, 6), 2, 1)
