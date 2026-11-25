import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import guided_eval  # noqa: E402

from amigo import guide  # noqa: E402


def _fork(*leaves):
    node = guide.Node([i for mine in leaves for i in mine], "table", 0)
    return guide.Fork(node, [guide.Option([], None, list(mine), n) for n, mine in enumerate(leaves)])


def test_the_informed_person_ticks_the_options_that_lead_closest_and_says_none_otherwise():
    def leads(*good, exact=()):  # one wanted table set
        return lambda option: (2 if option.n in exact else int(option.n in good),)

    fork = _fork([0], [1], [2])
    # every option that keeps their tables is ticked, the others are not
    assert guided_eval.informed(fork, leads(0, 1)) == guide.Answer("pick", frozenset({0, 1}))
    # an option that leads to exactly their tables beats one that leads to a larger set
    assert guided_eval.informed(fork, leads(0, exact=(1,))) == guide.Answer("pick", frozenset({1}))
    # nothing keeps them: none of these
    assert guided_eval.informed(fork, leads()) == guide.Answer("none")
    # two wanted table sets: the options closest to each are ticked together
    fits = {0: (2, 0), 1: (1, 0), 2: (0, 1)}
    assert guided_eval.informed(fork, lambda o: fits[o.n]) == guide.Answer("pick", frozenset({0, 2}))
    # the lazy person keeps everything, the conservative one takes the heaviest option
    assert guided_eval.lazy(fork, leads()) == guide.Answer("any")
    assert guided_eval.conservative(fork, leads()) == guide.Answer("pick", frozenset({0}))


def test_a_case_ends_with_exactly_their_tables_a_larger_set_a_miss_or_nothing():
    theirs = frozenset({"db.a", "db.b"})
    assert guided_eval.outcome(theirs, [frozenset({"db.c"}), theirs]) == "exact"
    assert guided_eval.outcome(theirs, [theirs | {"db.c"}]) == "larger"
    assert guided_eval.outcome(theirs, [frozenset({"db.a"})]) == "missed"
    assert guided_eval.outcome(theirs, []) == "nothing"
