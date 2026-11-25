import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest import mock

from amigo import clarify, config, links, solve



def _column(column_id: int, table_id: int, distinct: int) -> dict:
    return {
        "id": column_id,
        "name": f"c{column_id}",
        "table_id": table_id,
        "kind": "text",
        "distinct_count": distinct,
        "samples": "[]",
        "is_unique": False,
        "is_pk": False,
    }


class TestRoleRows(unittest.TestCase):
    def test_joins_matching_other_rows_are_roles_and_ones_matching_the_same_rows_fold(self):
        with tempfile.TemporaryDirectory() as folder:
            path = f"{folder}/lake.sqlite"
            with closing(sqlite3.connect(path)) as db, db:
                db.executescript(
                    "CREATE TABLE customer (state, branch_id, branch_code);"
                    "CREATE TABLE bank (state, branch_id, code);"
                    "INSERT INTO bank VALUES ('CA', 1, 'x1'), ('NY', 2, 'x2'), ('CA', 3, 'x3');"
                    "INSERT INTO customer VALUES ('CA', 1, 'x1'), ('NY', 2, 'x2'), ('CA', 3, 'x3');"
                )
            probe = mock.Mock(
                tables={1: {"name": "customer", "database_path": path}, 2: {"name": "bank"}},
                columns={
                    c: {"table_id": 1 + (c > 3), "name": name, "kind": "text", "samples": "[]", "is_unique": False, "is_pk": False}
                    for c, name in enumerate(["state", "branch_id", "branch_code"] * 2, 1)
                },
            )
            probe.columns[6]["name"] = "code"
            # the state link ties the branch key and sorts first: it must not replace it,
            # and the branch code, an alternate key, joins the same rows as the branch id
            state, branch, code = (solve.Join(((c, c + 3),), 1.0) for c in (1, 2, 3))
            self.assertEqual(solve._roles(probe, [code, branch, state], (1, 2)), [state, branch])


class TestLinkedCopies(unittest.TestCase):
    def test_a_key_looked_up_in_full_by_a_unique_key_gives_the_same_answer(self):
        paths = {"d.loans.book_id": 1, "d.books.book_id": 2, "d.loans.reader": 3}
        probe = mock.Mock(find=lambda path: ("column", paths[path]))

        def interpretation(name: str, book: str, tables: list[str], joins: list) -> solve.Interpretation:
            bindings = [solve.Binding("e1", book, "", None), solve.Binding("e2", "d.loans.reader", "", None)]
            return solve.Interpretation(name, bindings, tables, joins=joins)

        narrow = interpretation("i1", "d.loans.book_id", ["d.loans"], [])
        wide = interpretation("i2", "d.books.book_id", ["d.books", "d.loans"], [("d.loans.book_id", "d.books.book_id")])
        for score, unique, empty, same in (
            (1.0, True, 0.0, True), (0.9, True, 0.0, False), (1.0, False, 0.0, False), (1.0, True, 0.1, False)
        ):
            probe.links = [{"from_column": 1, "to_column": 2, "kind": "inferred", "score": score}]
            probe.columns = {1: {"empty_share": empty}, 2: {"is_unique": unique, "is_pk": False}}
            self.assertEqual(solve.reads_as(probe, wide, narrow), same)
            self.assertEqual(clarify.same_answer([wide, narrow], probe), same)
        self.assertFalse(solve.reads_as(probe, narrow, wide))


class TestDecimalIds(unittest.TestCase):
    def test_an_id_written_as_a_decimal_joins_as_its_number(self):
        self.assertEqual([links.whole(v) for v in ("149.0", "149", "1.5", "A1.0")], ["149", "149", "1.5", "A1.0"])
        columns = {1: {**_column(1, 1, 20), "samples": '["149.0", "236.0"]'}, 2: _column(2, 2, 20)}
        on = solve._on(mock.Mock(columns=columns), 1, 2)
        self.assertTrue(on.startswith("CAST("))
        with closing(sqlite3.connect(":memory:")) as db:
            db.executescript("CREATE TABLE a (c1 TEXT); CREATE TABLE b (c2 TEXT);"
                             " INSERT INTO a VALUES ('149.0'); INSERT INTO b VALUES ('149');")
            self.assertEqual(db.execute(f"SELECT count(*) FROM a AS t1 JOIN b AS t2 ON {on}").fetchone(), (1,))

    def test_a_key_stored_with_spaces_at_the_ends_joins_trimmed(self):
        columns = {1: {**_column(1, 1, 20), "samples": '[" APG", " ASY"]'}, 2: _column(2, 2, 20)}
        on = solve._on(mock.Mock(columns=columns), 1, 2)
        self.assertTrue(on.startswith("TRIM("))
        with closing(sqlite3.connect(":memory:")) as db:
            db.executescript("CREATE TABLE a (c1 TEXT); CREATE TABLE b (c2 TEXT);"
                             " INSERT INTO a VALUES (' APG'); INSERT INTO b VALUES ('APG');")
            self.assertEqual(db.execute(f"SELECT count(*) FROM a AS t1 JOIN b AS t2 ON {on}").fetchone(), (1,))


class TestRowKey(unittest.TestCase):
    def test_a_row_is_named_by_a_unique_column_the_key_first_else_by_all_its_columns(self):
        card = lambda t, unique, pk: {"table_id": t, "name": f"c{unique}{pk}", "is_unique": unique, "is_pk": pk}  # noqa: E731
        probe = mock.Mock(columns={1: card(1, 1, 0), 2: card(1, 1, 1), 3: card(2, 0, 0), 4: card(2, 0, 1)})
        self.assertEqual(solve.row_key(probe, 1), 't1."c11"')
        # a declared key the data shows repeated names nothing: the whole row does
        self.assertEqual(solve.row_key(probe, 2), 't2."c00", t2."c01"')


class TestKeyed(unittest.TestCase):
    def test_a_join_reaches_one_row_only_through_a_whole_key(self):
        # 1 section(course, sec); 2 takes(student, course, sec) points at it;
        # 3 attendance(course, sec) holds one row per section; all key columns
        tables = {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3}
        probe = mock.Mock(columns={c: {"table_id": t, "is_pk": True, "is_unique": False} for c, t in tables.items()})
        takes = [solve.Join(((4, 1), (5, 2)), 1.0)]
        attendance = [solve.Join(((6, 1), (7, 2)), 1.0)]
        ways = {(2, 1): takes, (1, 2): takes, (3, 1): attendance, (1, 3): attendance}
        self.assertEqual(
            solve.keyed(probe, ways), {(2, 1): True, (1, 2): False, (3, 1): False, (1, 3): False}
        )


class TestDifferentRows(unittest.TestCase):
    def test_only_a_finished_check_with_no_difference_says_same_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = f"{folder}/lake.sqlite"
            with closing(sqlite3.connect(path)) as db, db:
                # enough rows for the check to pass its first step count
                db.executescript(
                    "CREATE TABLE a (x); CREATE TABLE b (x); CREATE TABLE c (x);"
                    "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n"
                    " WHERE x < 5000) INSERT INTO a SELECT x FROM n;"
                    "INSERT INTO b SELECT x FROM a ORDER BY x DESC;"
                    "INSERT INTO c SELECT x FROM a WHERE x > 1; INSERT INTO c VALUES (0);"
                )
            a, b, c = (f"SELECT x FROM {t}" for t in "abc")
            self.assertFalse(solve._different_rows(path, a, b))
            self.assertTrue(solve._different_rows(path, a, c))
            self.assertTrue(solve._different_rows(path, a, "SELECT x FROM nowhere"))
            solve._different_rows.cache_clear()
            with mock.patch.object(config, "SAME_ROWS_STEPS", 0):
                self.assertTrue(solve._different_rows(path, a, b))
            solve._different_rows.cache_clear()


if __name__ == "__main__":
    unittest.main()
