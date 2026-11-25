import json
import sqlite3
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest import mock

import numpy as np

from amigo import bundle, config, index, layer, llm
from amigo.probe import Probe

TABLES = [
    (1, 1, "books", "books", "One row per book the library owns.", 120),
    (2, 1, "readers", "readers", "One row per library member.", 40),
    (3, 1, "BookLoans", "book loans", "One row per book taken out by a reader.", 300),
]

# id, table, name, readable, type, kind, description, value_description, samples,
# min, max, date_min, date_max
COLUMNS = [
    (1, 1, "book_id", "book id", "INTEGER", "number", "The book.", None, [1, 2, 3], 1, 120, None, None),
    (2, 1, "Title", "title", "TEXT", "text", "The title of the book.",
     "the title as printed on the cover",
     ["Things Fall Apart", "No Longer at Ease", "Arrow of God"], None, None, None, None),
    (3, 1, "PublishedYear", "published year", "INTEGER", "number", "Year of publication.",
     None, [1958, 1960, 1964], 1953, 2021, None, None),
    (4, 2, "reader_name", "reader name", "TEXT", "text", "The member's full name.",
     None, ["Ada Kane", "Bo Reyes", "Cyd Okoro"], None, None, None, None),
    (5, 2, "reader_id", "reader id", "INTEGER", "number", "The member.", None, [1, 2, 3], 1, 40, None, None),
    (6, 2, "joined_on", "joined on", "DATE", "date", "When the member joined.",
     "one row per day", ["2015-01-05", "2020-05-14"], None, None, "2015-01-05", "2024-06-30"),
    (7, 3, "loan", "loan", "INTEGER", "number", "The loan.", None, [1, 2, 3], 1, 300, None, None),
    (8, 3, "book_id", "book id", "INTEGER", "number", "The book lent out.", None, [1, 2, 3], 1, 120, None, None),
    (9, 3, "reader_id", "reader id", "INTEGER", "number", "The borrower.", None, [1, 2, 3], 1, 40, None, None),
]

LINKS = [(1, 8, 1, "declared", 1.0), (2, 9, 5, "inferred", 0.87)]


BOOKS = [
    (1, "Things Fall Apart", 1958),
    (2, "No Longer at Ease", 1960),
    (3, "Arrow of God", 1964),
]


def _toy_source(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE books(book_id INTEGER, Title TEXT, PublishedYear INTEGER)")
    conn.executemany("INSERT INTO books VALUES (?, ?, ?)", BOOKS)
    conn.commit()
    conn.close()


def _toy_lake(folder: Path) -> None:
    folder.mkdir(parents=True)
    source_path = folder / "city_library.sqlite"
    _toy_source(source_path)
    conn = sqlite3.connect(folder / "layer.sqlite")
    conn.executescript(layer._SCHEMA)
    conn.execute(
        "INSERT INTO databases(id, name, readable, path) VALUES (1, 'city_library',"
        " 'city library', ?)",
        (str(source_path),),
    )
    conn.executemany(
        "INSERT INTO tables(id, database_id, name, readable, description,"
        " description_source, row_count, primary_key)"
        " VALUES (?, ?, ?, ?, ?, 'model', ?, '[]')",
        TABLES,
    )
    conn.executemany(
        "INSERT INTO columns(id, table_id, name, readable, type, is_pk, kind, description,"
        " description_source, value_description, distinct_count, empty_share, samples,"
        " is_unique, min, max, date_format, date_min, date_max, date_failures)"
        " VALUES (?, ?, ?, ?, ?, 0, ?, ?, 'model', ?, 3, 0.0, ?, 0, ?, ?,"
        " CASE WHEN ?6 = 'date' THEN '%Y-%m-%d' END, ?, ?, NULL)",
        [
            (*card[:8], json.dumps(card[8]), *card[9:])
            for card in COLUMNS
        ],
    )
    # book_id and Title both identify a book on their own
    conn.execute("UPDATE columns SET is_unique = 1 WHERE id IN (1, 2)")
    conn.executemany("INSERT INTO links(id, from_column, to_column, kind, score) VALUES (?, ?, ?, ?, ?)", LINKS)
    conn.executemany(
        "INSERT INTO text_values(column_id, value) VALUES (2, ?)",
        [("things fall apart",), ("no longer at ease",)],
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('embedding_revision', ?)",
        (config.EMBEDDING_REVISION,),
    )
    conn.commit()
    conn.close()
    rng = np.random.default_rng(0)
    matrices = {
        "tables": rng.normal(size=(3, 8)),
        "columns": rng.normal(size=(9, 8)),
        "roles": np.zeros((0, 8)),
    }
    # the toy columns store no examples, so their meaning is their whole text
    matrices["meanings"] = matrices["columns"]
    np.savez(
        folder / "embeddings.npz",
        **{
            name: (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype(np.float32)
            for name, matrix in matrices.items()
        },
    )


def _literal(kind, text=None, number=None, date_start=None, date_end=None) -> llm.Literal:
    return llm.Literal(
        kind=kind, text=text, number=number, date_start=date_start, date_end=date_end
    )


class ToyLake(unittest.TestCase):
    """The toy lake above, built once per class and opened as `cls.probe`."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls._tmp.name) / "toy"
        _toy_lake(cls.folder)
        cls._lakes = config.LAKES_DIR
        config.LAKES_DIR = Path(cls._tmp.name)
        with mock.patch("amigo.embed._model", side_effect=AssertionError("embedded")):
            cls.probe = Probe("toy")

    @classmethod
    def tearDownClass(cls):
        config.LAKES_DIR = cls._lakes
        cls._tmp.cleanup()


class TestBundle(ToyLake):
    def test_fusion_orders_tables_and_marks_bridges(self):
        # lookup 1 ranks readers first; fusion must still put books first
        order, bridges = bundle.order_tables(self.probe, [[2, 1], [2], [1], [1]])
        self.assertEqual(order, [1, 2, 3])
        self.assertEqual(bridges, {3})

    def test_lookup_3_trims_the_question_down_to_the_stored_value(self):
        # the question says more than the column stores, so a shorter spelling is tried
        asked = _literal("text", text="Things Fall Apart Deluxe")
        decomposed = llm.Decomposition(entities=[llm.Entity(attribute="title", literal=asked)])
        with mock.patch.object(llm, "decompose", return_value=decomposed), mock.patch.object(
            Probe, "search_cards", return_value=([], np.zeros(9))
        ):
            stage = bundle.stage1(self.probe, "which books?", Path("unused.jsonl"))
        self.assertEqual(
            stage.details[2],
            ['contains "Things Fall Apart" (for "Things Fall Apart Deluxe")'],
        )
        self.assertEqual(stage.not_found, [])

    def test_lookup_3_tries_the_other_number_of_the_last_word(self):
        asked = _literal("text", text="Things Fall Aparts")
        decomposed = llm.Decomposition(entities=[llm.Entity(attribute="title", literal=asked)])
        with mock.patch.object(llm, "decompose", return_value=decomposed), mock.patch.object(
            Probe, "search_cards", return_value=([], np.zeros(9))
        ):
            stage = bundle.stage1(self.probe, "which books?", Path("unused.jsonl"))
        self.assertEqual(
            stage.details[2], ['contains "Things Fall apart" (for "Things Fall Aparts")']
        )
        self.assertEqual(stage.not_found, [])
        # the value check that binds it later agrees
        self.assertEqual(self.probe.stored_values(2, "Arrows of God"), [])
        self.assertEqual(self.probe.stored_values(2, "Arrow of Gods"), ["Arrow of God"])

    def test_a_value_named_like_a_table_the_question_names_is_that_table(self):
        asked = _literal("text", text="loans")
        decomposed = llm.Decomposition(entities=[llm.Entity(attribute="record kind", literal=asked)])
        with mock.patch.object(llm, "decompose", return_value=decomposed), mock.patch.object(
            Probe, "search_cards", return_value=([], np.zeros(9))
        ):
            stage = bundle.stage1(self.probe, "Which books are out on loans?", Path("unused.jsonl"))
            # the table is book loans, and this question never says book
            other = bundle.stage1(self.probe, "Which loans are late?", Path("unused.jsonl"))
        self.assertEqual((stage.named, stage.not_found), ([(0, [3])], []))
        self.assertIn(3, stage.order)
        self.assertEqual((other.named, len(other.not_found)), ([], 1))

    def test_a_plural_names_its_singular_table_and_finds_its_singular_value(self):
        class Lake:
            tables = {
                1: {"readable": "branch", "database": "bank"},
                2: {"readable": "address", "database": "bank"},
                3: {"readable": "movies", "database": "cinema"},
            }
            columns = {7: {"table_id": 1}, 9: {"table_id": 2}, 10: {"table_id": 3}}

            def lookup_value(self, text):
                return [7] if text == "owner" else []

            def split_value(self, text):
                return []

            def lookup_words(self, text, skip):
                found = {9: ["notes on the owners"], 10: ["The Owners"]}
                return {c: v for c, v in found.items() if self.tables[self.columns[c]["table_id"]]["database"] not in skip}

        lake = Lake()
        self.assertEqual(bundle.named_tables(lake, "branches", "accounts at the branches"), [1])
        self.assertEqual(bundle.named_tables(lake, "addresses", "the addresses on file"), [2])
        self.assertEqual(bundle.named_tables(lake, "movie", "the movie"), [3])
        # a stored singular beats a word inside free text in its own database, not in another
        self.assertEqual(list(bundle.text_hits(lake, "owners", '"owners"')), [7, 10])

    def test_the_words_search_skips_matched_databases_and_reads_a_column_once(self):
        self.probe.conn.executemany("INSERT INTO value_words(word, column_id) VALUES (?, 2)", [("fall",), ("apart",)])
        self.addCleanup(self.probe.conn.rollback)
        self.assertEqual(self.probe.lookup_words("fall apart"), {2: ["Things Fall Apart"]})
        self.assertEqual(self.probe.lookup_words("fall apart", frozenset({"city_library"})), {})
        with mock.patch("amigo.index.open_source", side_effect=AssertionError("read again")):
            self.assertEqual(self.probe.word_values(2, "Fall Apart"), ["Things Fall Apart"])

    def test_stored_values_stops_at_the_first_level_that_matches(self):
        stored = self.probe.stored_values
        self.assertEqual(stored(2, "arrow of god"), ["Arrow of God"])
        # a word trimmed off the end, then containment either way
        self.assertEqual(stored(2, "Arrow of God Part Two"), ["Arrow of God"])
        self.assertEqual(stored(2, "Arrow"), ["Arrow of God"])
        self.assertEqual(stored(2, "Anthills"), [])
        # whole words only, but a stored code may start a word of the value
        self.assertEqual(stored(2, "Arro"), [])
        with mock.patch.object(self.probe, "peek", return_value=["F", "M"]):
            self.assertEqual(stored(2, "female"), ["F"])
            self.assertEqual(stored(2, "Lewis Hamilton"), [])
            self.assertEqual(stored(2, "Mary Smith"), [])
        # a number column has no stored spelling to look up
        self.assertEqual(stored(3, "1958"), [])

    def test_a_value_split_over_one_row(self):
        # the title and the year as if both were stored as text, in books row 3 only
        index_of = {"arrow of god": [2], "1964": [3], "1958": [3]}
        with mock.patch.object(
            self.probe, "lookup_value", lambda text: index_of.get(index.normalise(text), [])
        ):
            self.assertEqual(
                self.probe.split_value("Arrow of God 1964"), [[(2, "Arrow of God"), (3, "1964")]]
            )
            # both parts are stored, but in two different rows
            self.assertEqual(self.probe.split_value("Arrow of God 1958"), [])
            # one part the lake does not store
            self.assertEqual(self.probe.split_value("Arrow of God 2001"), [])

    def test_stored_values_through_the_bloom_filter(self):
        bloom = index.Bloom(3)
        bloom.add("Things Fall Apart")
        wide = {**dict(self.probe.columns[2]), "distinct_count": config.EXACT_VALUE_LIMIT + 1}
        with mock.patch.dict(self.probe.columns, {2: wide}), mock.patch.dict(
            self.probe.blooms, {2: bloom}
        ):
            stored = self.probe.stored_values
            self.assertEqual(stored(2, "things fall apart"), ["Things Fall Apart"])
            # the filter normalises punctuation away, and so does the lookup behind it
            self.assertEqual(stored(2, "Things Fall Apart!"), ["Things Fall Apart"])
            self.assertEqual(stored(2, "Anthills"), [])

    def test_stored_values_without_a_bloom_reads_the_column(self):
        # the index counts distinct text values, the profile counts them all, so a
        # column over the limit by the profile count can still have no Bloom filter
        wide = {**dict(self.probe.columns[2]), "distinct_count": config.EXACT_VALUE_LIMIT + 1}
        with mock.patch.dict(self.probe.columns, {2: wide}):
            self.assertEqual(self.probe.stored_values(2, "Arrow of God"), ["Arrow of God"])

    def test_bridge_rule(self):
        # books and readers are linked only through loans
        self.assertEqual(bundle._bridges(self.probe, {1, 2}), {3})
        # books and loans are linked directly, so readers bridges nothing
        self.assertEqual(bundle._bridges(self.probe, {1, 3}), set())

    def test_probe_without_the_embedding_model(self):
        with mock.patch("amigo.embed._model", side_effect=AssertionError("embedded")):
            self.assertEqual(self.probe.lookup_value("Things Fall Apart!"), [2])
            self.assertEqual(self.probe.find("city_library.books"), ("table", 1))
            self.assertEqual(self.probe.path("table", 1), "city_library.books")
            self.assertEqual(
                self.probe.find("city_library.books.Title"), ("column", 2)
            )
            self.assertEqual(self.probe.path("column", 2), "city_library.books.Title")
            with self.assertRaises(KeyError):
                self.probe.find("city_library.nothing")
            self.assertEqual(
                self.probe.peek(2, 2), ["Things Fall Apart", "No Longer at Ease"]
            )
            self.assertEqual(
                self.probe.neighbours(1),
                [
                    {
                        "table_id": 3,
                        "from_column": 8,
                        "to_column": 1,
                        "kind": "declared",
                        "score": 1.0,
                    }
                ],
            )
        year, book_id, joined_on = (self.probe.columns[i] for i in (3, 1, 6))
        number = _literal("number", number=1958.0)
        self.assertTrue(bundle._covers(year, number))
        self.assertFalse(bundle._covers(book_id, number))
        self.assertFalse(bundle._covers(joined_on, number))
        # an open end of the asked range is unbounded
        self.assertTrue(
            bundle._covers(joined_on, _literal("date", date_start="2020-01-01"))
        )
        self.assertFalse(
            bundle._covers(joined_on, _literal("date", date_end="2010-01-01"))
        )
        self.assertTrue(
            bundle._covers(
                joined_on, _literal("date", date_start="2016-01-01", date_end="2016-12-31")
            )
        )
        self.assertEqual(
            bundle._as_written(_literal("date", date_start="2020-01-01")),
            "from 2020-01-01",
        )
        # a date literal against a plain year (number) column: compare by year
        self.assertTrue(
            bundle._covers(
                year, _literal("date", date_start="2000-01-01", date_end="2005-12-31")
            )
        )
        self.assertFalse(
            bundle._covers(
                year, _literal("date", date_start="2100-01-01", date_end="2105-12-31")
            )
        )
        self.assertTrue(
            bundle._covers(year, _literal("date", date_start="2010-01-01"))
        )
        # a month column stores 2013-11 as its first day, and still holds 2013-11-15
        month = {
            "kind": "date", "date_format": "%Y%m", "date_min": "2012-01-01", "date_max": "2013-11-01"
        }
        self.assertTrue(bundle._covers(month, _literal("date", date_start="2013-11-15")))
        self.assertFalse(bundle._covers(month, _literal("date", date_start="2013-12-01")))
        # an amount whose range spans the year is not a column of years
        amount = {"kind": "number", "min": -582092.0, "max": 2052187.0}
        self.assertFalse(bundle._covers(amount, _literal("date", date_start="2013-10-01")))


class TestMinimalSets(unittest.TestCase):
    # the BIRD financial shape: client, disp, card, account, loan, district
    CLIENT, DISP, CARD, ACCOUNT, LOAN, DISTRICT = 1, 2, 3, 4, 5, 6
    LINKED = {
        1: {2, 6},
        2: {1, 3, 4},
        3: {2},
        4: {2, 5, 6},
        5: {4},
        6: {1, 4},
    }
    ALL = {1, 2, 3, 4, 5, 6}

    def sets(self, *terminals):
        return bundle.minimal_sets(set(terminals), self.ALL, self.LINKED)

    def test_both_bridges_are_forced_and_district_is_not(self):
        self.assertEqual(
            self.sets(self.CLIENT, self.CARD, self.LOAN),
            [{self.CLIENT, self.DISP, self.CARD, self.ACCOUNT, self.LOAN}],
        )

    def test_two_join_paths_give_two_sets(self):
        found = self.sets(self.CLIENT, self.LOAN)
        self.assertEqual(
            sorted(sorted(one) for one in found),
            [[self.CLIENT, self.DISP, self.ACCOUNT, self.LOAN],
             [self.CLIENT, self.ACCOUNT, self.LOAN, self.DISTRICT]],
        )

    def test_one_terminal_is_its_own_set(self):
        self.assertEqual(self.sets(self.LOAN), [{self.LOAN}])

    def test_no_path_gives_nothing(self):
        self.assertEqual(
            bundle.minimal_sets({self.CARD, self.LOAN}, {self.CARD, self.LOAN}, self.LINKED),
            [],
        )

    def test_unlinked_extras_do_not_blow_up_the_search(self):
        # 1-2 linked through 3, plus 22 isolated tables 10..31: without the
        # reachability cut this is 2^23 subsets over the unrelated tables.
        linked = defaultdict(set, {1: {3}, 2: {3}, 3: {1, 2}})
        tables = set(range(1, 32))
        self.assertEqual(bundle.minimal_sets({1, 2}, tables, linked), [{1, 2, 3}])

    def test_a_chain_needing_more_than_the_cap_returns_nothing(self):
        # A(1)-B(2)-C(3)-D(4)-F(5)-E(6): 4 join tables between the terminals,
        # one more than config.MAX_JOIN_TABLES (3), so the cap never reaches it.
        a, b, c, d, f, e = 1, 2, 3, 4, 5, 6
        linked = defaultdict(
            set, {a: {b}, b: {a, c}, c: {b, d}, d: {c, f}, f: {d, e}, e: {f}}
        )
        tables = {a, b, c, d, f, e}
        self.assertEqual(bundle.minimal_sets({a, e}, tables, linked), [])

    def test_a_chain_needing_exactly_the_cap_returns_that_set(self):
        # A(1)-B(2)-C(3)-D(4)-E(5): 3 join tables between the terminals, exactly
        # config.MAX_JOIN_TABLES (3).
        a, b, c, d, e = 1, 2, 3, 4, 5
        linked = defaultdict(set, {a: {b}, b: {a, c}, c: {b, d}, d: {c, e}, e: {d}})
        tables = {a, b, c, d, e}
        self.assertEqual(bundle.minimal_sets({a, e}, tables, linked), [{a, b, c, d, e}])

    def test_a_path_two_join_tables_longer_than_the_shortest_is_not_searched(self):
        # 1 and 2 join through 3 alone, or through 4-5-6: the search stops before three
        # join tables, since those cannot beat the one-table path by one table or less
        linked = defaultdict(
            set, {1: {3, 4}, 3: {1, 2}, 2: {3, 6}, 4: {1, 5}, 5: {4, 6}, 6: {5, 2}}
        )
        self.assertEqual(bundle.minimal_sets({1, 2}, set(range(1, 7)), linked), [{1, 2, 3}])


if __name__ == "__main__":
    unittest.main()
