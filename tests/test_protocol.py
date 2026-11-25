import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))


def test_retrieval_scores_match_the_protocol_examples():
    from protocol import holm, matched, question

    f = frozenset
    # the matched set is the one of best recall, not the cleanest one
    assert matched(f("ab"), [f("a"), f("abcde")]) == (1.0, 1.0, 0.4)
    targets = [f("ab"), f("ac")]
    amigo = question(targets, [f("ab"), f("acd")], pooled=True)
    assert amigo["all"]["R"] == 1.0 and amigo["all"]["CR"] == 1.0
    assert abs(amigo["all"]["P"] - 5 / 6) < 1e-9 and amigo["all"]["pooled P"] == 0.75
    assert amigo["sets"] == 2 and amigo["tables"] == 4 and amigo["single"] is None
    assert amigo["size"] == 2.5 and question(targets, [], pooled=True)["size"] is None
    core = question(targets, [f("abc")], pooled=True)
    assert abs(core["all"]["P"] - 2 / 3) < 1e-9 and core["all"]["pooled P"] == 1.0
    nothing = question(targets, [], pooled=True)
    assert all(v == 0.0 for v in nothing["all"].values()) and nothing["sets"] == 0
    # interpretation scores: one big set serves one interpretation; exact copies for the strict ones
    big = question(targets, [f("abcd")], pooled=False)["all"]
    assert (big["CR"], big["IR"], big["ICR"], big["IP"], big["IR="], big["IP="]) == (1.0, 0.5, 0.0, 1.0, 0.0, 0.0)
    y = question(targets, [f("ab"), f("acd"), f("ef")], pooled=False)["all"]
    assert (y["IR"], y["ICR"], y["IR="], y["ICR="], y["CR="]) == (1.0, 1.0, 0.5, 0.0, 0.5)
    assert abs(y["IP"] - 2 / 3) < 1e-9 and abs(y["IP="] - 1 / 3) < 1e-9
    assert holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


def test_sql_scores_match_the_protocol():
    from sqleval import question

    f = frozenset
    answers = [("h1", [f("ab")]), ("h2", [f("c"), f("cd")])]  # h2: one valid query reads one table
    res = [{"status": "ok", "hash": "h1"}, {"status": "error"}, {"status": "empty", "hash": "h0"}]
    s = question(answers, [f("ab"), f("x"), f("y")], res, pooled=True)
    assert s["all"] == 0.5 and s["single"] == 0.0 and s["multi"] == 1.0
    assert s["all found"] == 1.0 and s["all missed"] == 0.0
    assert s["result P"] == 0.5 and s["sqls"] == 3 and s["failed"] == 1


def test_hints_name_only_the_parts_that_differ():
    from sqleval import hints

    shop = ("shop", "the column shop.name")
    a = {"E1": shop, "E2": ("city", "the column shop.City")}
    b = {"E1": shop, "E2": ("city", "the column shop.MailCity")}
    assert hints([a]) == [[]]
    assert hints([a, b]) == [
        ['- "city" is the column shop.City. Another reading takes it as the column shop.MailCity.'],
        ['- "city" is the column shop.MailCity. Another reading takes it as the column shop.City.']]
    assert hints([a, {"E1": shop}])[1] == ['- "city" is left out of this reading.']
