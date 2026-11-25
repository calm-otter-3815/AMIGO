import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

from amigo import clarify, llm, solve

QUESTION = "which airports carried the most passengers"
ENTITIES = [
    llm.Entity(attribute="airport", literal=None),
    llm.Entity(attribute="number of passengers", literal=None),
    llm.Entity(attribute="year", literal=None),
]


def one(name: str, airport: str, count: str) -> solve.Interpretation:
    columns = {"e1": airport, "e2": count, "e3": "travel.traffic.Year"}
    return solve.Interpretation(
        id=name,
        bindings=[
            solve.Binding(entity=key, column=column, reason="it fits", value=None)
            for key, column in columns.items()
        ],
        tables=["travel.traffic"],
    )


AIRPORT = "travel.airport.Name"
CODE = "travel.airport.IATA"
TOTAL = "travel.traffic.Total_Passengers"
DOMESTIC = "travel.traffic.Domestic_Passengers"
TRANSIT = "travel.traffic.Transit_Passengers"
YEAR = "travel.traffic.Year"

DESCRIBED = {
    AIRPORT: "the name the airport trades under",
    CODE: "the airport's three letter code",
    TOTAL: "every passenger counted at the airport",
    DOMESTIC: "passengers on flights that stayed inside the country",
    TRANSIT: "passengers who only changed planes there",
    YEAR: "the year the traffic was counted in",
}


class FakeProbe:
    """Only what clarify asks of a probe: the path of a card and its description."""

    columns = {
        path: {"description": text, "table_id": path.rsplit(".", 1)[0], "samples": "[]"}
        for path, text in DESCRIBED.items()
    }
    tables = {}
    links = []

    def find(self, name: str) -> tuple[str, str]:
        return "column", name


PROBE = FakeProbe()

CUSTOMERS = "cards.customers.CustomerID"
TRANSACTIONS = "cards.transactions_1k.CustomerID"
YEARMONTH = "cards.yearmonth.CustomerID"
ACCOUNTS = "cards.accounts.AccountID"
KEY_IDS = {CUSTOMERS: 1, TRANSACTIONS: 2, YEARMONTH: 3, ACCOUNTS: 4}


class LinkedProbe(FakeProbe):
    """A lake where one customer key lives in three tables the links join."""

    columns = {
        card_id: {
            "description": "the customer it belongs to",
            "table_id": card_id,
            "distinct_count": 10,
            "samples": "[]",
        }
        for card_id in KEY_IDS.values()
    }
    # customers -> transactions_1k declared, transactions_1k -> yearmonth inferred: one
    # component of three columns, reached only through the second hop
    links = [
        {"from_column": 1, "to_column": 2, "kind": "declared", "score": 1.0},
        {"from_column": 2, "to_column": 3, "kind": "inferred", "score": 0.8},
    ]

    def find(self, name: str) -> tuple[str, int]:
        return "column", KEY_IDS[name]


LINKED = LinkedProbe()

SKIN = "heroes.hero.skin_colour_id"
HAIR = "heroes.hero.hair_colour_id"
COLOUR_IDS = {SKIN: 1, HAIR: 2, "heroes.colour.id": 3}


class RolesProbe(FakeProbe):
    """A lake where one table points at a colour table twice, for two different things."""

    columns = {
        1: {"description": "the colour of the skin", "table_id": 1, "samples": "[]"},
        2: {"description": "the colour of the hair", "table_id": 1, "samples": "[]"},
        3: {"description": "the colour's id", "table_id": 2, "samples": "[]"},
    }
    links = [
        {"from_column": 1, "to_column": 3, "kind": "declared", "score": 1.0},
        {"from_column": 2, "to_column": 3, "kind": "declared", "score": 1.0},
    ]

    def find(self, name: str) -> tuple[str, int]:
        return "column", COLOUR_IDS[name]


def keyed(name: str, column: str, value: str | None = None) -> solve.Interpretation:
    return solve.Interpretation(
        id=name,
        bindings=[
            solve.Binding(entity="e1", column=column, reason="it fits", value=value)
        ],
        tables=[column.rsplit(".", 1)[0]],
    )


KEYED = [keyed("i1", CUSTOMERS), keyed("i2", TRANSACTIONS), keyed("i3", YEARMONTH)]

LIVE = [
    one("i1", AIRPORT, TOTAL),
    one("i2", AIRPORT, DOMESTIC),
    one("i3", AIRPORT, TRANSIT),
    one("i4", CODE, TOTAL),
]


def fake_call(reply):
    """Stands in for llm.call: runs the check the caller passed, then hands the reply back."""

    def call(prompt, schema, log_path, label, check=None, **rest):
        assert "$" not in prompt
        if check is not None:
            check(reply)
        return reply

    return call


class TestAxes(unittest.TestCase):
    def test_only_the_entities_that_disagree_become_axes(self):
        found = clarify.axes(LIVE, ENTITIES, PROBE)
        self.assertEqual([axis.key for axis in found], ["e1", "e2"])
        # e3 agrees everywhere, so it is not a place to ask about
        self.assertEqual(found[0].text, "airport")
        self.assertEqual(
            [(option.id, option.column, option.keeps) for option in found[0].options],
            [("o1", AIRPORT, ["i1", "i2", "i3"]), ("o2", CODE, ["i4"])],
        )
        self.assertEqual(
            [(option.id, option.keeps) for option in found[1].options],
            [("o1", ["i1", "i4"]), ("o2", ["i2"]), ("o3", ["i3"])],
        )
        # each option carries what the catalog says its column holds
        self.assertEqual(found[1].options[0].description, f"{DESCRIBED[TOTAL]}; no values stored")

    def test_options_over_different_tables_say_through_which(self):
        # every interpretation of LIVE sits on one table: nothing to tell apart
        self.assertEqual({o.through for axis in clarify.axes(LIVE, ENTITIES, PROBE) for o in axis.options}, {""})
        far = one("i4", CODE, TOTAL)
        far.tables, far.joins = ["travel.airport", "travel.traffic"], [("travel.traffic.Airport", CODE)]
        airport = clarify.axes(LIVE[:3] + [far], ENTITIES, PROBE)[0]
        self.assertEqual(
            [option.through for option in airport.options],
            ["tables travel.traffic", f"tables travel.airport, travel.traffic; joins travel.traffic.Airport = {CODE}"],
        )
        self.assertTrue(clarify._option_line(airport.options[1]).endswith(f"| through {airport.options[1].through}"))

    def test_a_live_set_that_agrees_has_no_axis(self):
        self.assertEqual(clarify.axes(LIVE[:1], ENTITIES, PROBE), [])
        self.assertIsNone(clarify.choose_axis([]))

    def test_choose_axis_takes_the_one_that_removes_the_most(self):
        # e2's biggest option keeps 2 of 4, e1's keeps 3
        self.assertEqual(clarify.choose_axis(clarify.axes(LIVE, ENTITIES, PROBE)).key, "e2")

    def test_one_key_across_linked_tables_is_one_option(self):
        found = clarify.axes(KEYED, [ENTITIES[0]], LINKED)
        # the three customer ids are the same key in three joined tables, so nothing to ask
        self.assertEqual(found, [])
        self.assertEqual(
            [(option.id, option.column, option.keeps) for option in clarify._grouped(
                LINKED,
                [(one.id, (one.bindings[0].column, None, []), "it fits") for one in KEYED],
            )],
            [("o1", CUSTOMERS, ["i1", "i2", "i3"])],
        )

    def test_columns_that_are_not_linked_stay_two_options(self):
        unlinked = [keyed("i1", CUSTOMERS), keyed("i2", ACCOUNTS)]
        found = clarify.axes(unlinked, [ENTITIES[0]], LINKED)
        self.assertEqual([option.column for option in found[0].options], [CUSTOMERS, ACCOUNTS])

    def test_a_link_too_weak_to_join_on_does_not_merge_two_options(self):
        weak = LinkedProbe()
        weak.columns = {
            c: {**card, "distinct_count": 100 if c == 3 else 10}
            for c, card in weak.columns.items()
        }
        found = clarify.axes(KEYED, [ENTITIES[0]], weak)
        # 0.8 x 10 / 100 is below the join threshold: yearmonth's key is not the customer's
        self.assertEqual([o.column for o in found[0].options], [CUSTOMERS, YEARMONTH])

    def test_a_link_found_by_values_alone_joins_but_does_not_merge_two_options(self):
        found_by_values = LinkedProbe()
        found_by_values.links = [{**LINKED.links[0]}, {**LINKED.links[1], "kind": "values"}]
        found = clarify.axes(KEYED, [ENTITIES[0]], found_by_values)
        self.assertEqual([o.column for o in found[0].options], [CUSTOMERS, YEARMONTH])

    def test_two_columns_of_one_table_linked_to_one_key_stay_two_options(self):
        roles = [keyed("i1", SKIN), keyed("i2", HAIR)]
        found = clarify.axes(roles, [ENTITIES[0]], RolesProbe())
        self.assertEqual([option.column for option in found[0].options], [SKIN, HAIR])

    def test_linked_columns_holding_different_values_stay_two_options(self):
        both = [keyed("i1", CUSTOMERS, "a"), keyed("i2", TRANSACTIONS, "b")]
        found = clarify.axes(both, [ENTITIES[0]], LINKED)
        self.assertEqual(
            [(option.column, option.value) for option in found[0].options],
            [(CUSTOMERS, "a"), (TRANSACTIONS, "b")],
        )

    def test_options_keeping_the_same_rows_are_not_asked(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "school.sqlite")
            with closing(sqlite3.connect(path)) as db:
                db.executescript(
                    "CREATE TABLE course (name TEXT, about TEXT);"
                    " INSERT INTO course VALUES ('statistics', 'statistics'), ('art', 'drawing'),"
                    " ('drawing', 'art');"
                )
                db.commit()
            names = {"school.course.name": 1, "school.course.about": 2}
            probe = mock.Mock(
                tables={1: {"name": "course", "database_path": path}},
                columns={c: {"table_id": 1, "name": n, "is_unique": False, "is_pk": False} for c, n in ((1, "name"), (2, "about"))},
                links=[],
                find=lambda path: ("column", names[path]),
            )
            with mock.patch.object(clarify, "_sampled", return_value=""):
                for value, asked in (("statistics", False), ("art", True)):
                    live = [keyed("i1", "school.course.name", value), keyed("i2", "school.course.about", value)]
                    found = clarify.axes(live, ENTITIES[:1], probe)
                    # still an axis, so the page runs both, but never the one asked
                    self.assertEqual(len(found), 1)
                    self.assertEqual(clarify.choose_axis(found) is not None, asked)

    def test_two_joins_of_one_table_pair_are_a_role_axis(self):
        live = [
            solve.Interpretation(
                id=name,
                bindings=[solve.Binding(entity="e1", column="heroes.colour.id", reason="", value=None)],
                tables=["heroes.colour", "heroes.hero"],
                joins=[(column, "heroes.colour.id")],
            )
            for name, column in (("i1", SKIN), ("i2", HAIR))
        ]
        [axis] = clarify.axes(live, ENTITIES[:1], RolesProbe())
        self.assertEqual([o.column for o in axis.options], [SKIN, HAIR])
        self.assertEqual([o.keeps for o in axis.options], [["i1"], ["i2"]])
        self.assertEqual(axis.options[0].description, "the colour of the skin; no values stored")

    def test_narrow_keeps_the_option_in_the_original_order(self):
        axis = clarify.axes(LIVE, ENTITIES, PROBE)[1]
        self.assertEqual([one.id for one in clarify.narrow(LIVE, axis, "o1")], ["i1", "i4"])
        self.assertEqual([one.id for one in clarify.narrow(LIVE, axis, "o3")], ["i3"])

    def test_several_options_keep_all_their_interpretations(self):
        axis = clarify.axes(LIVE, ENTITIES, PROBE)[1]
        self.assertEqual(
            [one.id for one in clarify.narrow(LIVE, axis, "o1+o3")], ["i1", "i3", "i4"]
        )


class TestCombine(unittest.TestCase):
    """A name ticked as the first name and the last name: one interpretation reads both."""

    def one(self, name, column, joins=(), tables=("club.member", "club.event")):
        return solve.Interpretation(
            id=name,
            bindings=[
                solve.Binding("e1", column, "", None),
                solve.Binding("e2", "club.event.title", "", "Fair"),
            ],
            tables=list(tables),
            joins=list(joins),
        )

    def test_columns_picked_together_merge_into_one_interpretation(self):
        link = [("club.member.event_id", "club.event.id")]
        live = [self.one("i1", "club.member.first", link), self.one("i2", "club.member.last", link)]
        out, made = clarify.combine(live, "e1", [{"i1"}, {"i2"}])
        self.assertEqual([one.id for one in out], ["i1+i2"])
        self.assertEqual(made[0].bindings[0].columns, ["club.member.first", "club.member.last"])
        self.assertEqual(made[0].bindings[1].value, "Fair")
        self.assertEqual(made[0].joins, link)

    def test_one_table_pair_joined_two_ways_does_not_merge(self):
        live = [
            self.one("i1", "club.member.first", [("club.member.event_id", "club.event.id")]),
            self.one("i2", "club.member.last", [("club.member.host_of", "club.event.id")]),
        ]
        out, made = clarify.combine(live, "e1", [{"i1"}, {"i2"}])
        self.assertEqual(([one.id for one in out], made), (["i1", "i2"], []))

    def test_two_different_paths_do_not_merge(self):
        # the badge through the event, the city through the town: neither path holds the other
        via_event = [("club.member.event_id", "club.event.id")]
        via_town = [("club.member.town", "club.town.id"), ("club.event.town", "club.town.id")]
        live = [
            self.one("i1", "club.member.badge", via_event),
            self.one("i2", "club.town.city", via_town, ("club.member", "club.event", "club.town")),
        ]
        out, made = clarify.combine(live, "e1", [{"i1"}, {"i2"}])
        self.assertEqual(([one.id for one in out], made), (["i1", "i2"], []))


class TestPhrase(unittest.TestCase):
    def setUp(self):
        self.axis = clarify.axes(LIVE, ENTITIES, PROBE)[1]

    def phrase(self, reply):
        with mock.patch.object(clarify.llm, "call", fake_call(reply)):
            return clarify.phrase(self.axis, QUESTION, Path("unused.jsonl"))

    def test_the_labels_come_back_on_the_axis_options(self):
        asked = self.phrase(
            clarify.Phrasing(
                question="Which passengers should be counted?",
                options=[
                    clarify.PhrasedOption(id="o2", label="domestic only"),
                    clarify.PhrasedOption(id="o1", label="everyone"),
                    clarify.PhrasedOption(id="o3", label="in transit only"),
                ],
            )
        )
        self.assertEqual(asked.axis, "e2")
        self.assertEqual(asked.text, "Which passengers should be counted?")
        self.assertEqual(
            asked.options,
            [
                {"id": "o1", "label": "everyone", "column": TOTAL, "value": None, "also": [], "keeps": ["i1", "i4"]},
                {"id": "o2", "label": "domestic only", "column": DOMESTIC, "value": None, "also": [], "keeps": ["i2"]},
                {"id": "o3", "label": "in transit only", "column": TRANSIT, "value": None, "also": [], "keeps": ["i3"]},
            ],
        )

    def test_an_option_the_model_invented_is_refused(self):
        with self.assertRaises(llm.ModelError) as caught:
            self.phrase(
                clarify.Phrasing(
                    question="Which ones?",
                    options=[
                        clarify.PhrasedOption(id="o1", label="everyone"),
                        clarify.PhrasedOption(id="o2", label="domestic only"),
                        clarify.PhrasedOption(id="o9", label="something else"),
                    ],
                )
            )
        self.assertIn("must be exactly", str(caught.exception))

    def test_an_empty_overlong_or_repeated_label_is_refused(self):
        for label in ("  ", "x" * 61, "Domestic only"):
            with self.assertRaises(llm.ModelError):
                self.phrase(
                    clarify.Phrasing(
                        question="Which ones?",
                        options=[
                            clarify.PhrasedOption(id="o1", label=label),
                            clarify.PhrasedOption(id="o2", label="domestic only"),
                            clarify.PhrasedOption(id="o3", label="in transit only"),
                        ],
                    )
                )

    def test_the_option_line_carries_the_description(self):
        line = clarify._option_line(self.axis.options[0])
        self.assertIn(DESCRIBED[TOTAL], line)
        self.assertEqual(line.split(" | ")[:2], ["  o1", TOTAL])

    def test_the_fallback_question_names_the_axis_and_the_columns(self):
        asked = clarify.fallback(self.axis)
        self.assertEqual(asked.text, 'Which one do you mean for "number of passengers"?')
        self.assertEqual(
            [option["label"] for option in asked.options], [TOTAL, DOMESTIC, TRANSIT]
        )


class TestMapReply(unittest.TestCase):
    def setUp(self):
        self.question = clarify.fallback(clarify.axes(LIVE, ENTITIES, PROBE)[1])
        self.turns = [
            {
                "question": "Which airport name do you mean?",
                "options": [{"id": "o1", "label": "the full name"}],
                "answer": "o1",
                "typed": None,
            }
        ]

    def map(self, option, question=None):
        reply = clarify.Replied(option=option, question=question)
        with mock.patch.object(clarify.llm, "call", fake_call(reply)):
            return clarify.map_reply(
                self.question, self.turns, QUESTION, "domestic", Path("unused.jsonl")
            )

    def test_typed_words_map_to_one_option(self):
        self.assertEqual(self.map("o2"), clarify.Reply("o2", None))

    def test_typed_words_can_refine_the_question_instead(self):
        refined = "which airports carried the most domestic passengers"
        self.assertEqual(self.map(None, refined), clarify.Reply(None, refined))

    def test_words_that_do_neither_leave_both_empty(self):
        self.assertEqual(self.map(None), clarify.Reply(None, None))

    def test_an_option_and_a_question_at_once_is_refused(self):
        with self.assertRaises(llm.ModelError) as caught:
            self.map("o2", "which airports carried the most domestic passengers")
        self.assertIn("never both", str(caught.exception))

    def test_an_option_that_is_not_on_offer_is_refused(self):
        with self.assertRaises(llm.ModelError):
            self.map("o9")

    def test_an_empty_question_or_the_original_one_is_refused(self):
        for question in ("   ", QUESTION):
            with self.assertRaises(llm.ModelError):
                self.map(None, question)

    def test_with_no_option_on_the_table_only_a_question_answers(self):
        self.question = clarify.Question("", "", [])
        refined = "which airports carried the most domestic passengers"
        self.assertEqual(self.map(None, refined), clarify.Reply(None, refined))
        with self.assertRaises(llm.ModelError):
            self.map(None)


class TestTurnLines(unittest.TestCase):
    def test_reads_the_server_shape_and_the_page_shape_alike(self):
        server = {
            "question": "Which branch?",
            "options": [{"id": "o1", "label": "Riverside"}, {"id": "o2", "label": "Hill"}],
            "answer": "o2",
            "typed": None,
        }
        page = {"question": "Which branch?", "options": ["Riverside", "Hill"], "answer": "Hill", "typed": None}
        expected = "  asked: Which branch? | options: Riverside, Hill | they answered: Hill"
        self.assertEqual(clarify.turn_lines([server]), expected)
        self.assertEqual(clarify.turn_lines([page]), expected)
        self.assertEqual(clarify.turn_lines([]), "  none")


class TestSuggest(unittest.TestCase):
    """The did-you-mean call: the model may only name columns it was shown."""

    CANDIDATES = [(AIRPORT, "the airport's name"), (CODE, "its three letter code")]

    def suggest(self, reply: clarify.Suggestion):
        with mock.patch.object(clarify.llm, "call", fake_call(reply)):
            return clarify.suggest("airport", QUESTION, self.CANDIDATES, Path("log.jsonl"))

    def test_the_columns_and_labels_come_back_in_the_model_s_order(self):
        text, options = self.suggest(
            clarify.Suggestion(
                question="Which airport do you mean?",
                options=[
                    clarify.SuggestedColumn(column=CODE, label="the code"),
                    clarify.SuggestedColumn(column=AIRPORT, label="the name"),
                ],
            )
        )
        self.assertEqual(text, "Which airport do you mean?")
        self.assertEqual(options, [(CODE, "the code"), (AIRPORT, "the name")])

    def test_no_column_fits_is_an_empty_list(self):
        self.assertEqual(self.suggest(clarify.Suggestion(question="Drop it?", options=[]))[1], [])

    def test_a_column_outside_the_candidates_is_refused(self):
        with self.assertRaises(llm.ModelError):
            self.suggest(
                clarify.Suggestion(
                    question="Which one?",
                    options=[clarify.SuggestedColumn(column=TOTAL, label="passengers")],
                )
            )

    def test_the_same_column_twice_is_refused(self):
        with self.assertRaises(llm.ModelError):
            self.suggest(
                clarify.Suggestion(
                    question="Which one?",
                    options=[
                        clarify.SuggestedColumn(column=CODE, label="the code"),
                        clarify.SuggestedColumn(column=CODE, label="the letters"),
                    ],
                )
            )

    def test_an_empty_or_overlong_label_is_refused(self):
        for label in ("  ", "x" * (clarify.LABEL_CHARS + 1)):
            with self.assertRaises(llm.ModelError):
                self.suggest(
                    clarify.Suggestion(
                        question="Which one?",
                        options=[clarify.SuggestedColumn(column=CODE, label=label)],
                    )
                )


if __name__ == "__main__":
    unittest.main()
