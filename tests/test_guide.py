import unittest

from amigo import candidates as C
from amigo import guide


def _leaf(db, places, cost, way=None, edges=()):
    """A candidate placing part j at places[j] = (table, column), or None to leave it out."""
    holders = tuple(None if p is None else C.Holder(j, p[0], p[1], 1.0, "") for j, p in enumerate(places))
    tables = frozenset(p[0] for p in places if p is not None)
    return C.Candidate(db, tables, holders, edges, cost, extra={"ways": {e: ("one", (way,)) for e in edges}})


def _places(leaves):
    return [[(h.table, h.column) for h in one.holders] for one in leaves]


class TestTree(unittest.TestCase):
    def setUp(self):
        # part 0 sits in table 1 (columns 11 or 12) or table 3 of database d, or in database e;
        # part 1 always in table 2; the cheapest has two ways to link its join
        edge = ((1, 2),)
        self.found = [
            _leaf("d", [(1, 11), (2, 21)], 1.0, "w1", edge),
            _leaf("d", [(1, 11), (2, 21)], 1.0, "w2", edge),
            _leaf("d", [(1, 12), (2, 21)], 2.0, "w1", edge),
            _leaf("d", [(3, 31), (2, 21)], 3.0, "w1", ((2, 3),)),
            _leaf("e", [(5, 51), (6, 61)], 4.0, "w1", ((5, 6),)),
        ]
        self.tree = guide.build(self.found)

    def ask(self, answers):
        return guide.step(self.tree, answers)

    def test_forks_from_the_top_heaviest_first_and_the_walk_down(self):
        self.assertEqual(guide.size(self.tree), {"leaves": 5, "forks": 4, "depth": 4})
        kinds = []
        answers = []
        while (fork := self.ask(answers).fork) is not None:
            kinds.append((fork.kind, fork.part, [o.leaves for o in fork.options]))
            answers.append(guide.Answer("pick", frozenset({fork.options[0].n})))
        self.assertEqual(kinds, [("database", None, [[0, 1, 2, 3], [4]]),
                                 ("table", 0, [[0, 1, 2], [3]]),
                                 ("column", 0, [[0, 1], [2]]),
                                 ("join", None, [[0], [1]])])
        # the heaviest option everywhere ends at the cheapest candidate alone
        self.assertEqual(self.ask(answers).leaves, self.found[:1])
        # "any of these" at the top keeps every candidate
        self.assertEqual(self.ask([guide.Answer("any")]).leaves, self.found)
        # picking two options walks both, the heaviest first; stop keeps what is left
        two = [guide.Answer("pick", frozenset({0})), guide.Answer("pick", frozenset({0, 1}))]
        self.assertEqual(self.ask(two).fork.kind, "column")
        self.assertEqual(self.ask(two + [guide.Answer("stop")]).leaves, self.found[:4])

    def test_none_of_these_goes_up_once_a_fork_has_nothing_left(self):
        pick = [guide.Answer("pick", frozenset({0}))]
        none = guide.Answer("none")
        # every table of database d ruled out: d is too, and the database fork shows what is left
        fork = self.ask(pick + [none]).fork
        self.assertEqual((fork.kind, [o.n for o in fork.options]), ("database", [1]))
        # ruling that out too leaves nothing
        self.assertEqual(self.ask(pick + [none, none]), guide.Step(None, []))
        # one of two options picked and ruled out below: the fork shows the other one again
        fork = self.ask(pick * 3 + [none]).fork
        self.assertEqual((fork.kind, [o.n for o in fork.options]), ("column", [1]))

    def test_none_of_these_shows_the_next_options(self):
        found = [_leaf("d", [(1, 10 + k)], float(k)) for k in range(8)]
        tree = guide.build(found)
        fork = guide.step(tree, []).fork
        self.assertEqual(([o.n for o in fork.options], fork.more), (list(range(guide.OPTIONS)), 2))
        fork = guide.step(tree, [guide.Answer("none")]).fork
        self.assertEqual(([o.n for o in fork.options], fork.more), ([6, 7], 0))

    def test_the_part_that_splits_the_odds_most_evenly_comes_first(self):
        # two parts differ by column: part 1 splits the odds more evenly, so it is asked first
        found = [_leaf("d", [(1, 11), (1, 21)], 1.0), _leaf("d", [(1, 11), (1, 22)], 1.5),
                 _leaf("d", [(1, 12), (1, 21)], 4.0)]
        fork = guide.step(guide.build(found), []).fork
        self.assertEqual((fork.kind, fork.part), ("column", 1))

    def test_relaxed_candidates_ask_first_which_part_to_leave_out(self):
        found = [_leaf("d", [(1, 11), None], 1.0), _leaf("d", [None, (2, 21)], 2.0)]
        fork = guide.step(guide.build(found), []).fork
        self.assertEqual((fork.kind, [o.best.left_out for o in fork.options]), ("leave", [(1,), (0,)]))


if __name__ == "__main__":
    unittest.main()
