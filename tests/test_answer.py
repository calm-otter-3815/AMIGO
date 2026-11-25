from dataclasses import replace
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from amigo import answer, clarify, config, llm, solve
from tests.test_bundle import ToyLake, _literal

TITLE = "city_library.books.Title"
ENTITIES = [llm.Entity(attribute="book title", literal=_literal("text", text="arrow of god"))]
LIBRARY = solve.Interpretation(
    id="i1",
    bindings=[solve.Binding("e1", TITLE, "the title as printed", "Arrow of God")],
    tables=["city_library.books"],
)


FILTERED = "SELECT Title FROM books WHERE Title = 'Arrow of God'"
# SQLite compares text case by case, so this finds no row
MISSPELT = "SELECT Title FROM books WHERE Title = 'arrow of god'"


def result(sql="SELECT Title FROM books", rows=(("Arrow of God",),), error=None) -> answer.Result:
    return answer.Result(
        LIBRARY, "The titles of every book.", sql, ["Title"], list(rows), False, error
    )


class TestRunSql(ToyLake):
    def path(self) -> str:
        return str(self.folder / "city_library.sqlite")

    def test_columns_and_rows(self):
        columns, rows, more = answer.run_sql(
            self.path(), "SELECT Title, PublishedYear FROM books ORDER BY book_id"
        )
        self.assertEqual(columns, ["Title", "PublishedYear"])
        self.assertEqual(rows[0], ("Things Fall Apart", 1958))
        self.assertEqual((len(rows), more), (3, False))

    def test_a_whole_number_stored_as_real_prints_whole(self):
        self.assertEqual(answer._grid(["year"], [(1925.0,), (2.5,)]), ["year", "1925", "2.5"])

    def test_the_answer_in_words_sees_a_long_name_whole(self):
        name = "School of Teacher Education and Leadership"
        self.assertEqual(answer._grid(["d"], [(name,)], answer.SAY_CELL_CHARS)[1], name)
        # the printed table may cut it, and shows that it did
        self.assertEqual(answer._grid(["d"], [(name,)])[1], name[:39] + "…")

    def test_row_cap(self):
        with mock.patch.object(config, "SQL_MAX_ROWS", 2):
            columns, rows, more = answer.run_sql(self.path(), "SELECT Title FROM books")
        self.assertEqual((columns, len(rows), more), (["Title"], 2, True))

    def test_a_query_stops_after_a_fixed_number_of_steps(self):
        endless = (
            "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) SELECT max(i) FROM n"
        )
        with mock.patch.object(config, "SQL_MAX_STEPS", 100_000):
            with self.assertRaisesRegex(sqlite3.OperationalError, "interrupted"):
                answer.run_sql(self.path(), endless)
            self.assertEqual(len(answer.run_sql(self.path(), "SELECT Title FROM books")[1]), 3)

    def test_a_write_a_copy_or_an_empty_query_is_refused(self):
        copy = self.folder / "copy.sqlite"
        for sql in (
            "INSERT INTO books VALUES (4, 'Anthills', 1987)",
            f"VACUUM INTO '{copy}'",
            "  ",
        ):
            with self.assertRaises(sqlite3.DatabaseError):
                answer.run_sql(self.path(), sql)
        self.assertFalse(copy.exists())


class TestReadIds(ToyLake):
    def test_an_unaliased_join_and_a_cte_name_their_real_tables(self):
        with sqlite3.connect(self.folder / "city_library.sqlite") as conn:
            conn.execute("CREATE TABLE BookLoans(loan INTEGER, book_id INTEGER, reader_id INTEGER)")
        sql = (
            "WITH lent AS (SELECT book_id FROM BookLoans)"
            " SELECT Title FROM books JOIN lent ON books.book_id = lent.book_id"
        )
        self.assertEqual(answer.read_ids(self.probe, "city_library", sql), ([1, 3], [1, 2, 8]))
        self.assertEqual(
            answer.read_ids(
                self.probe,
                "city_library",
                "SELECT COUNT(*) FROM books JOIN bookloans ON books.book_id = bookloans.book_id",
            ),
            ([1, 3], [1, 8]),
        )


class TestQuery(ToyLake):
    """The repair loop, with the model faked and the toy database real."""

    def query(self, *answers):
        with mock.patch(
            "amigo.answer.llm.call",
            side_effect=[answer.Query(sentence="the books", sql=sql) for sql in answers],
        ) as called:
            found = answer.query(
                self.probe, "which books?", ENTITIES, LIBRARY, Path("unused.jsonl")
            )
        return found, called

    def test_a_repair_after_one_bad_query(self):
        found, called = self.query("SELECT nope FROM books", FILTERED)
        self.assertEqual(called.call_count, 2)
        self.assertIsNone(found.error)
        self.assertEqual((found.columns, len(found.rows)), (["Title"], 1))
        self.assertEqual((found.sql, found.sentence), (FILTERED, "the books"))
        self.assertIn("SQLite error:\nno such column: nope", called.call_args.args[0])

    def test_no_rows_is_repaired_once(self):
        found, called = self.query(MISSPELT, FILTERED)
        self.assertEqual(called.call_count, 2)
        self.assertEqual((len(found.rows), found.error), (1, None))

    def test_no_rows_with_every_value_as_stored_is_the_answer(self):
        # the value is written as stored, so nothing is left to repair: one call
        none = FILTERED + " AND PublishedYear > 3000"
        found, called = self.query(none)
        self.assertEqual(called.call_count, 1)
        self.assertEqual((found.sql, found.rows, found.error), (none, [], None))

    def test_the_same_query_again_is_accepted(self):
        found, called = self.query(MISSPELT, MISSPELT)
        self.assertEqual(called.call_count, 2)
        self.assertEqual((found.rows, found.error, found.sql), ([], None, MISSPELT))

    def test_a_query_that_drops_the_bound_value_is_repaired(self):
        found, called = self.query("SELECT Title FROM books", FILTERED)
        self.assertEqual((called.call_count, len(found.rows)), (2, 1))
        self.assertIn(
            "- it never compares books.Title with the stored value"
            " 'Arrow of God'",
            called.call_args.args[0],
        )

    def test_a_retry_that_reads_a_new_column_keeps_the_empty_answer(self):
        widened = MISSPELT + " OR PublishedYear > 0"
        found, called = self.query(MISSPELT, widened)
        self.assertEqual(called.call_count, 2)
        self.assertEqual((found.sql, found.rows, found.error), (MISSPELT, [], None))
        # the rows it kept are none, under the columns that query returns
        self.assertEqual(found.columns, ["Title"])

    def test_five_bad_queries_give_up(self):
        found, called = self.query(*["SELECT nope FROM books"] * config.SQL_MAX_TRIES)
        self.assertEqual(called.call_count, config.SQL_MAX_TRIES)
        self.assertIn("no such column: nope", found.error)
        self.assertEqual((found.columns, found.rows, found.more), ([], [], False))

    def test_a_model_error_ends_one_interpretation_only(self):
        with mock.patch(
            "amigo.answer.llm.call", side_effect=llm.ModelError("no usable JSON")
        ):
            found = answer.query(
                self.probe, "which books?", ENTITIES, LIBRARY, Path("unused.jsonl")
            )
        self.assertEqual((found.error, found.rows), ("no usable JSON", []))

    def test_the_prompt_carries_the_binding_and_the_context(self):
        prompt = self.query(FILTERED)[1].call_args.args[0]
        self.assertIn(
            "e1: book title = \"arrow of god\" -> books.Title = 'Arrow of God'",
            prompt,
        )
        # the names as the query writes them, without the database
        self.assertIn("name: books\n", prompt)
        self.assertIn("columns: books.book_id, books.Title, books.PublishedYear", prompt)
        self.assertIn("COLUMN books.Title", prompt)
        self.assertIn("LINKS\n  none", prompt)
        # a small bound text column lists its values, so the SQL can use the spelling
        self.assertIn(
            "values: 'Things Fall Apart', 'No Longer at Ease', 'Arrow of God'", prompt
        )
        # a stored value is shown as the SQL literal that matches it, spaces and all
        self.assertEqual(answer._sql_text("O'Brien  "), "'O''Brien  '")
        # the rules mention a rewrite; the block itself is absent without the kwarg
        self.assertNotIn("This is a rewrite. The earlier question was:", prompt)

    def test_a_part_left_out_is_named_so_the_query_never_claims_it(self):
        entities = [*ENTITIES, llm.Entity(attribute="borrower", literal=_literal("text", text="Batman"))]
        left = replace(LIBRARY, left_out=["e2"])
        with mock.patch("amigo.answer.llm.call", side_effect=[answer.Query(sentence="the books", sql=FILTERED)]) as called:
            answer.query(self.probe, "which books did Batman borrow?", entities, left, Path("unused.jsonl"))
        self.assertIn('e2: borrower = "Batman" -> left out', called.call_args.args[0])

    def test_a_rewrite_carries_the_earlier_question_and_its_sql(self):
        with mock.patch(
            "amigo.answer.llm.call",
            side_effect=[answer.Query(sentence="the books", sql="SELECT Title FROM books")],
        ) as called:
            answer.query(
                self.probe,
                "which books?",
                ENTITIES,
                LIBRARY,
                Path("unused.jsonl"),
                rewrite=("earlier q", FILTERED),
            )
        prompt = called.call_args_list[0].args[0]
        self.assertIn(
            "This is a rewrite. The earlier question was:\nearlier q\n\n"
            f"The SQL that answered it:\n{FILTERED}\n",
            prompt,
        )

    def test_a_rewrite_that_reads_a_new_column_is_repaired(self):
        with mock.patch(
            "amigo.answer.llm.call",
            side_effect=[
                answer.Query(sentence="", sql="SELECT Title, PublishedYear FROM books"),
                answer.Query(sentence="", sql="SELECT Title FROM books"),
            ],
        ) as called:
            found = answer.query(
                self.probe, "which books?", ENTITIES, LIBRARY, Path("unused.jsonl"),
                rewrite=("earlier q", FILTERED),
            )
        # dropping the title filter is a rewrite's to make; a new column is not
        self.assertEqual((called.call_count, len(found.rows)), (2, 3))
        self.assertIn(
            "- it uses books.publishedyear, which the earlier query did not",
            called.call_args.args[0],
        )
        # the repair still says it is a rewrite, and of which question
        self.assertIn(
            "This is a rewrite. The earlier question was:\nearlier q", called.call_args.args[0]
        )

    def test_a_rewrite_the_person_chose_may_read_a_new_column(self):
        with mock.patch(
            "amigo.answer.llm.call",
            return_value=answer.Query(sentence="", sql="SELECT Title, PublishedYear FROM books"),
        ) as called:
            found = answer.query(
                self.probe, "which books, and when?", ENTITIES, LIBRARY, Path("unused.jsonl"),
                rewrite=("earlier q", FILTERED), chosen=True,
            )
        self.assertEqual((called.call_count, len(found.rows)), (1, 3))

    def test_a_rewrite_that_counts_the_rows_reads_no_new_column(self):
        count = "SELECT COUNT(*) FROM books"
        with mock.patch(
            "amigo.answer.llm.call", return_value=answer.Query(sentence="", sql=count)
        ) as called:
            found = answer.query(
                self.probe, "how many?", ENTITIES, LIBRARY, Path("unused.jsonl"),
                rewrite=("earlier q", "SELECT Title FROM books"),
            )
        self.assertEqual((called.call_count, found.rows), (1, [(3,)]))


class TestMentions(unittest.TestCase):
    def test_a_number_may_be_bare_but_a_padded_code_must_be_quoted(self):
        self.assertTrue(answer._mentions("SELECT * FROM t WHERE x = -3", "-3"))
        self.assertFalse(answer._mentions("SELECT * FROM t WHERE code = 007", "007"))


class TestContext(ToyLake):
    def test_the_context_prints_only_the_joins_given(self):
        text = answer.context(
            self.probe,
            ["city_library.books", "city_library.BookLoans"],
            [TITLE],
            [("city_library.BookLoans.book_id", "city_library.books.book_id")],
        )
        self.assertIn("LINKS\n  BookLoans.book_id -> books.book_id", text)
        self.assertNotIn("reader_id", text.split("LINKS")[1])

    def test_a_join_on_any_one_link_is_one_line_with_or(self):
        pairs = [("city_library.BookLoans.book_id", "city_library.books.book_id"),
                 ("city_library.BookLoans.reader_id", "city_library.books.book_id")]
        text = answer.context(self.probe, ["city_library.books", "city_library.BookLoans"], [TITLE], pairs, [pairs])
        self.assertEqual(text.split("LINKS\n")[1],
                         "  BookLoans.book_id -> books.book_id or BookLoans.reader_id -> books.book_id")


class TestTableBinding(ToyLake):
    def test_a_bound_table_is_named_and_must_be_read(self):
        loans = "city_library.BookLoans"
        entities = [*ENTITIES, llm.Entity(attribute="book status", literal=_literal("text", text="loans"))]
        binding = solve.Binding("e2", loans, "every loan is one", None)
        one = solve.Interpretation(
            id="i1", bindings=[LIBRARY.bindings[0], binding], tables=["city_library.books", loans]
        )
        self.assertEqual(
            answer._binding_line(self.probe, entities, binding), 'e2: book status = "loans" -> table BookLoans'
        )
        text = answer.context(self.probe, one.tables, [TITLE, loans])
        self.assertIn("COLUMN books.Title", text)
        self.assertNotIn("COLUMN BookLoans", text)
        found = {("books", "title")}
        self.assertIn(
            "it never uses BookLoans, which a binding or a link names",
            answer.departures(self.probe, one, FILTERED, found),
        )
        self.assertTrue(clarify._described(self.probe, loans).startswith("table, 300 rows"))


class TestPresent(unittest.TestCase):
    def test_everything(self):
        text = answer.present(
            answer.Answer(
                question="which books?",
                entities=ENTITIES,
                fanout=solve.FanOut([LIBRARY], ["e1: nothing else fits"], None),
                results=[result(), result("SELECT nope", (), "no such column")],
            )
        )
        self.assertIn("QUESTION: which books?", text)
        self.assertIn("i1: The titles of every book.", text)
        self.assertIn(
            "  e1 book title -> city_library.books.Title (the title as printed)", text
        )
        self.assertIn("  tables: city_library.books", text)
        self.assertIn("  SELECT Title FROM books", text)
        self.assertIn("  rows: 1", text)
        self.assertIn("  Title\n  Arrow of God", text)
        self.assertIn("  no working query: no such column", text)
        self.assertIn("DROPPED\n  e1: nothing else fits", text)

    def test_too_many_interpretations_are_listed_not_run(self):
        text = answer.present(
            answer.Answer(
                question="which books?",
                entities=ENTITIES,
                fanout=solve.FanOut([LIBRARY], [], None, "13 interpretations, above the 12"),
                results=[],
            )
        )
        self.assertIn("NOT RUN: 13 interpretations, above the 12.", text)
        self.assertIn("i1:\n  e1 book title -> city_library.books.Title", text)

    def test_a_stopped_run_shows_only_the_message(self):
        text = answer.present(
            answer.Answer(
                question="which books?",
                entities=ENTITIES,
                fanout=solve.FanOut([], [], "None of the tables kept holds or implies book title."),
                results=[],
            )
        )
        self.assertEqual(
            text, "QUESTION: which books?\n\nSTOPPED: None of the tables kept holds or implies"
            " book title.\n"
        )


class TestSay(unittest.TestCase):
    def test_a_number_may_be_rounded_but_not_converted(self):
        shown = ["What is the average fare?", "AVG(fare)\n41.8166", "1"]
        self.assertEqual(answer.unshown("It is 41.82, or about 42, over 1,000 rides", shown), ["1000"])
        self.assertEqual(answer.unshown("42% of rides", ["0.4167"]), ["42"])
        self.assertEqual(answer.unshown("about 43, not -3", ["e2: 3 -> t.x", "42.5"]), ["-3"])


if __name__ == "__main__":
    unittest.main()


class TestSummaries(ToyLake):
    def test_shared_choices_are_listed_once_and_a_failed_call_keeps_the_cards(self):
        loans = "city_library.BookLoans"
        entities = [*ENTITIES, llm.Entity(attribute="book status", literal=_literal("text", text="loans"))]
        other = solve.Interpretation(
            id="i2", bindings=[LIBRARY.bindings[0], solve.Binding("e2", loans, "every loan is one", None)],
            tables=["city_library.books", loans],
        )
        cards = [LIBRARY, other]
        reply = answer.Summaries(interpretations=[
            answer.Summary(id="i1", title="Every book", meaning="Counts every book."),
            answer.Summary(id="i2", title="Lent books", meaning="Counts the books lent."),
        ])
        with mock.patch("amigo.answer.llm.call", return_value=reply) as called:
            got = answer.summaries(self.probe, "which books?", entities, cards, Path("unused.jsonl"))
        prompt = called.call_args.args[0]
        self.assertEqual(prompt.count("-> books.Title = 'Arrow of God'"), 1)
        self.assertIn("i2:\n  e2: book status", prompt)
        self.assertEqual([(one.title, one.summary) for one in got],
                         [("Every book", "Counts every book."), ("Lent books", "Counts the books lent.")])
        with mock.patch("amigo.answer.llm.call", side_effect=llm.ModelError("no usable JSON")):
            self.assertEqual(answer.summaries(self.probe, "which books?", entities, cards, Path("unused.jsonl")), cards)


class TestPageOf(unittest.TestCase):
    def test_pages_search_and_the_last_page(self):
        import sqlite3
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "t.sqlite")
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE t (n INTEGER, name TEXT)")
                conn.executemany("INSERT INTO t VALUES (?, ?)", [(k, "Ann" if k % 10 == 0 else "Bo") for k in range(1, 121)])
            sql = "SELECT n, name FROM t ORDER BY n DESC"
            got = answer.page_of(path, sql, 1, 50)
            self.assertEqual((got["columns"], got["matched"], got["pages"]), (["n", "name"], 120, 3))
            # the second page keeps the query's own order
            self.assertEqual(got["rows"][0], (70, "Ann"))
            # a search reads every cell as text, ignoring case; a page past the last gives the last
            found = answer.page_of(path, sql, 9, 5, "ann")
            self.assertEqual((found["matched"], found["page"], len(found["rows"])), (12, 2, 2))
            self.assertEqual(list(answer.every_row(path, sql, "120"))[1:], [(120, "Ann")])
