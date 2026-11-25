import unittest
from types import SimpleNamespace

from amigo import interpret
from amigo.candidates import Candidate


def _one(cost, *places):
    holders = tuple(SimpleNamespace(table=t, column=c) for t, c in places)
    return Candidate("db", frozenset(t for t, _ in places), holders, (), cost)


class TestPick(unittest.TestCase):
    def test_picks_one_and_none_of_these_shows_the_next(self):
        # two within the window, then eight more beyond it
        found = [_one(0.0, (1, 11)), _one(1.0, (2, 21))] + [_one(9.0 + k, (3 + k, 31)) for k in range(8)]
        stage = SimpleNamespace(entities=[SimpleNamespace(attribute="a")])
        probe = SimpleNamespace(path=lambda kind, i: f"{kind} {i}")
        answers = iter(["2"])
        self.assertEqual(interpret.pick(probe, stage, found, lambda p: next(answers), 1.0), [found[1]])
        # none of these: the list grows by OPTIONS, numbered on from the first ones
        prompts, answers = [], iter(["0", "8"])
        got = interpret.pick(probe, stage, found, lambda p: prompts.append(p) or next(answers), 1.0)
        self.assertEqual(got, [found[7]])
        self.assertIn(f"{2 + interpret.OPTIONS}. ", prompts[1])
        self.assertNotIn(f"{3 + interpret.OPTIONS}. ", prompts[1])
        # Enter keeps the answer as it was
        self.assertIs(interpret.pick(probe, stage, found, lambda p: "", 1.0), found)


class TestQuestions(unittest.TestCase):
    def test_asks_the_part_that_tells_most_and_reprices(self):
        found = [_one(0.0, (1, 11), (2, 21)), _one(1.0, (1, 11), (3, 31)), _one(1.5, (4, 41), (2, 21))]
        # part 2 splits the odds 1.35 to 0.5 (0.84 bits), part 1 splits them 1.5 to 0.35 (0.70)
        gains = {j: round(g, 2) for g, j, _ in interpret.questions(found, 1.0)}
        self.assertEqual(gains, {0: 0.70, 1: 0.84})
        stage = SimpleNamespace(entities=[SimpleNamespace(attribute="a"), SimpleNamespace(attribute="b")])
        probe = SimpleNamespace(path=lambda kind, i: f"{kind} {i}")
        prompts = []

        def reply(prompt):
            prompts.append(prompt)
            # the second place shown for part b (column 31), then Enter: stop
            return "2" if len(prompts) == 1 else ""

        kept = interpret.ask(probe, stage, found, reply, 1.0)
        # the two that disagree stay, ANSWER bits dearer: a later answer could bring them back
        self.assertEqual([one.cost for one in kept], [1.0, interpret.ANSWER, 1.5 + interpret.ANSWER])
        self.assertEqual(kept[0].holders, found[1].holders)
        self.assertIn('Where is "b"?', prompts[0])
        self.assertIn('Where is "a"?', prompts[1])

    def test_not_worth_asking_when_no_answer_moves_the_top(self):
        # the only other place is so unlikely that even an answer for it leaves the first on top
        found = [_one(0.0, (1, 11)), _one(interpret.ANSWER + 2.0, (2, 21))]
        self.assertEqual(interpret.questions(found, 1.0), [])
        # dropping what disagrees would move it
        drop = lambda f, j, options, ticked: [o for o in f if interpret.answer_of(o, j, options) in ticked]
        self.assertEqual(len(interpret.questions(found, 1.0, update=drop)), 1)


if __name__ == "__main__":
    unittest.main()


from unittest import mock

from amigo import llm
from amigo.candidates import Holder
from tests.test_bundle import ToyLake, _literal

TITLE, YEAR = "city_library.books.Title", "city_library.books.PublishedYear"


class TestBinding(ToyLake):
    def bind(self, text):
        stage = SimpleNamespace(entities=[llm.Entity(attribute="book title", literal=_literal("text", text=text))])
        column = self.probe.column_ids[TITLE]
        h = Holder(0, self.probe.columns[column]["table_id"], column, 0.0, "stores the value")
        b = interpret._binding(self.probe, stage, 0, h)
        return b.column, b.value, b.also

    def test_the_card_carries_the_value_stored_whole_or_split_over_the_row(self):
        self.assertEqual(self.bind("arrow of god"), (TITLE, "Arrow of God", []))
        # matched only in part: no value, the SQL step reads the question
        self.assertEqual(self.bind("Arrow of God Returns"), (TITLE, None, []))
        group = [[(self.probe.column_ids[YEAR], "1964"), (self.probe.column_ids[TITLE], "Arrow of God")]]
        with mock.patch.object(self.probe, "split_value", return_value=group):
            # the placed column stays first, whatever order the split lists them in
            self.assertEqual(self.bind("Arrow of God 1964"), (TITLE, "Arrow of God", [(YEAR, "1964")]))
