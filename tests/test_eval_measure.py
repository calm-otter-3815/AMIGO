import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import eval_lakes  # noqa: E402


def _record(*interpretations, levels=None):
    found = [{"tables": t, "bound": c, "joins": []} for t, c in interpretations]
    record = {"picked": sorted({x for _, c in interpretations for x in c}), "interpretations": found}
    return record | ({"levels": levels} if levels else {})


def test_several_valid_queries():
    # two valid queries: the gold reads a.x, the other reads b.y
    label = [({"d.a"}, {"d.a.x"}), ({"d.b"}, {"d.b.y"})]
    one = _record((["d.a"], ["d.a.x"]))
    got = eval_lakes.measure(label, one)
    assert got["tables"] == {"recall": 0.5, "complete": 0.0, "precision": 1.0, "f1": 2 / 3}
    assert got["footprint"]["soft"] == {"recall": 0.5, "complete": 0.0, "precision": 1.0, "f1": 2 / 3}
    assert got["interpretation"] == {"recall": 0.5, "complete": 0.0, "precision": 0.5, "f1": 0.5, "set_precision": 1.0}
    both = eval_lakes.measure(label, _record((["d.a"], ["d.a.x"]), (["d.b"], ["d.b.y"])))
    assert both["tables"]["complete"] == both["interpretation"]["complete"] == 1.0
    # against the gold query alone, the one-answer system is complete
    assert eval_lakes.measure(label[:1], one)["interpretation"]["complete"] == 1.0
    # a table retriever is scored at the table level only
    assert set(eval_lakes.measure(label, _record((["d.a"], []), levels=["tables"]))) == {"tables", "footprint", "interpretation_tables",
                                                                                        "count", "size", "effort"}



def test_table_and_footprint_levels():
    # three valid footprints, one returned set holding the first two
    label = [({"trip", "station"}, set()), ({"trip", "rider"}, set()), ({"survey"}, set())]
    got = eval_lakes.measure(label, _record((["trip", "station", "rider"], []), levels=["tables"]))
    assert (got["tables"]["recall"], got["tables"]["precision"], got["tables"]["complete"]) == (0.75, 1.0, 0.0)
    soft, exact = got["footprint"]["soft"], got["footprint"]["exact"]
    assert (soft["recall"], soft["precision"], soft["complete"]) == (2 / 3, 1.0, 0.0)
    assert (exact["recall"], exact["precision"], exact["complete"]) == (0.0, 0.0, 0.0)
    # each footprint against the one set: both trip sets held whole with one extra table, survey missed
    sets = got["interpretation_tables"]
    assert (sets["recall"], sets["precision"], sets["complete"]) == (2 / 3, 4 / 9, 0.0)
    # set side: the one set's best query holds 2 of its 3 tables; a second set {survey, x} adds 1 of 2
    assert sets["set_precision"] == 2 / 3
    two = eval_lakes.measure(label, _record((["trip", "station", "rider"], []), (["survey", "x"], []), levels=["tables"]))
    assert abs(two["interpretation_tables"]["precision"] - 11 / 18) < 1e-9
    assert abs(two["interpretation_tables"]["set_precision"] - 7 / 12) < 1e-9


def test_interpretation_level_tables():
    # valid sets {s, c} and {s, l}; answers {s, c} then {l, x}: one set found of two, one answer of two valid
    label = [({"d.s", "d.c"}, set()), ({"d.s", "d.l"}, set())]
    got = eval_lakes.measure(label, _record((["d.s", "d.c"], []), (["d.l", "d.x"], [])))
    assert (got["footprint"]["soft"]["recall"], got["footprint"]["soft"]["precision"]) == (0.5, 0.5)
    assert got["effort"] == {"least": (1, 2), "most": (1, 2)}
    # adding {s, l} third: both found, the last after 3 answers and 6 tables
    got = eval_lakes.measure(label, _record((["d.s", "d.c"], []), (["d.l", "d.x"], []), (["d.s", "d.l"], [])))
    assert got["footprint"]["soft"]["recall"] == got["tables"]["complete"] == 1.0
    assert got["effort"] == {"least": (1, 2), "most": (3, 6)}
    assert eval_lakes.measure(label, _record((["d.x"], [])))["effort"] is None


def test_cuts_and_ndcg():
    def one(tables, column, value):
        return {"tables": tables, "bound": [column], "values": [[column, value, []]], "joins": []}

    # the likeliest three all bind d.a.x; the fourth is the only one binding d.b.y
    found = [one(["d.a"], "d.a.x", "v1"), one(["d.a"], "d.a.x", "v1"), one(["d.a", "d.c"], "d.a.x", "v1"),
             one(["d.b"], "d.b.y", "v1")]
    record = {"picked": ["d.a.x", "d.b.y"], "interpretations": found}
    assert eval_lakes.cut(record, "first2")["interpretations"] == found[:2]
    assert eval_lakes.cut(record, "diverse2")["interpretations"] == [found[0], found[3]]
    assert eval_lakes.cut(record, "diverse2")["picked"] == ["d.a.x", "d.b.y"]
    top = eval_lakes.cut(record, "k2")
    assert (top["order"], top["levels"]) == (["d.a", "d.c"], ["tables"])
    # the one relevant table second of two: (1 / log2 3) / 1
    assert abs(eval_lakes.ndcg({"d.c"}, ["d.a", "d.c"]) - 0.6309) < 1e-4
    assert "ndcg" in eval_lakes.measure([({"d.c"}, set())], top, ranked=True)["tables"]


def test_covering_takes_the_tables_holding_most_odds():
    # the cheapest interpretation needs two tables; one table can only hold c's
    found = [{"tables": t, "cost": c} for t, c in ((["a", "b"], 0.0), (["c"], 1.0), (["a"], 3.0))]
    assert eval_lakes._covering(found, 1) == ["c"]
    assert eval_lakes._covering(found, 2) == ["a", "b"]
    # free places go to the tables in the most odds
    assert eval_lakes._covering(found, 3) == ["a", "b", "c"]


def test_needed_window_and_conformal_rank():
    import math
    found = [(0.0, frozenset({"a"})), (1.5, frozenset({"a", "b"})), (3.0, frozenset({"c"}))]
    assert eval_lakes.needed(found, [frozenset({"a"})]) == 0.0
    # each valid query's first holder: b in the second candidate, c in the third
    assert eval_lakes.needed(found, [frozenset({"a"}), frozenset({"b"})]) == 1.5
    assert eval_lakes.needed(found, [frozenset({"b"}), frozenset({"c"})]) == 3.0
    assert eval_lakes.needed(found, [frozenset({"d"})]) == math.inf
    # the window it needs makes the answer complete, as measure counts it; less does not
    label = [({"a"}, set()), ({"b"}, set())]
    assert eval_lakes.measure(label, eval_lakes._tables_record(found, 1.5))["tables"]["complete"] == 1.0
    assert eval_lakes.measure(label, eval_lakes._tables_record(found, 1.4))["tables"]["complete"] == 0.0
    # a query across two interpretations: its footprint is held only by the one list
    across = [({"a", "c"}, set())]
    assert eval_lakes.measure(across, eval_lakes._tables_record(found, 3.0))["footprint"]["soft"]["complete"] == 0.0
    assert eval_lakes.measure(across, eval_lakes._tables_record(found, 3.0, one_list=True))["footprint"]["soft"]["complete"] == 1.0
    # 9 scores at alpha 0.2: the ceil(10 * 0.8) = 8th smallest; too few scores for 0.1
    assert eval_lakes.conformal_window(list(range(9)), 0.2) == 7
    assert eval_lakes.conformal_window(list(range(3)), 0.1) == math.inf
