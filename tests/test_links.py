import sqlite3
import unittest

from amigo import links


class TestLinks(unittest.TestCase):
    def test_declared_skips_missing_target_column(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE b(id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE a(id INTEGER PRIMARY KEY, b_id INTEGER REFERENCES b(nope))")
        self.assertEqual(links.declared(conn, "a", ["a", "b"]), [])

    def test_declared_numbers_the_columns_of_one_composite_key_alike(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE section(course TEXT, year INTEGER, PRIMARY KEY (course, year))")
        conn.execute(
            "CREATE TABLE takes(course TEXT, year INTEGER, room TEXT REFERENCES room(name),"
            " FOREIGN KEY (course, year) REFERENCES section(course, year))"
        )
        conn.execute("CREATE TABLE room(name TEXT PRIMARY KEY)")
        found = links.declared(conn, "takes", ["section", "takes", "room"])
        by_column = {from_column: constraint for constraint, from_column, _, _ in found}
        self.assertEqual(by_column["course"], by_column["year"])
        self.assertNotEqual(by_column["course"], by_column["room"])

    def test_inferred_integer_key_with_agreeing_names(self):
        conn = _database()
        links_found = links.inferred(conn, _cards(), set())
        self.assertEqual(links_found, [(2, 3, 0.75)])

    def test_inferred_ignores_integers_whose_names_disagree(self):
        conn = _database()
        cards = _cards()
        cards[1]["name"], cards[2]["name"] = "era", "hr"
        self.assertEqual(links.inferred(conn, cards, set()), [])

    def test_inferred_ignores_integers_when_the_key_side_is_not_a_key(self):
        conn = _database()
        cards = _cards()
        cards[2]["is_pk"] = cards[2]["is_unique"] = False
        self.assertEqual(links.inferred(conn, cards, set()), [])

    def test_inferred_ignores_one_part_of_a_composite_primary_key(self):
        conn = _database()
        cards = _cards()
        cards[2]["is_unique"] = False  # still is_pk, as one column of a two-column key
        self.assertEqual(links.inferred(conn, cards, set()), [])

    def test_name_fit_accepts_a_column_named_after_the_key_without_its_id_suffix(self):
        card = {"table": "match_season", "name": "Team"}
        self.assertTrue(links._name_fit(card, {"table": "team", "name": "Team_id"}))
        self.assertFalse(links._name_fit(card, {"table": "country", "name": "Country_id"}))

    def test_name_fit_takes_a_role_of_an_id_key_last(self):
        def fit(table, name, key_table, key_name):
            return links._name_fit(
                {"table": table, "name": name}, {"table": key_table, "name": key_name}
            )

        self.assertEqual(fit("farm_competition", "Host_city_ID", "city", "City_ID"), 1)
        self.assertEqual(fit("death", "caused_by_ship_id", "ship_2", "id"), 1)
        # a year is no key, and a table's own key points at no other table
        self.assertEqual(fit("chip_model", "Launch_year", "budget", "Year"), 0)
        self.assertEqual(fit("book_club", "book_club_id", "club", "Club_ID"), 0)
        self.assertEqual(fit("trip", "station_id", "station", "id"), 3)

    def test_inferred_links_a_prefix_to_the_table_it_names_not_a_longer_one(self):
        conn = sqlite3.connect(":memory:")
        for table in ("posts", "postHistory"):
            conn.execute(f"CREATE TABLE {table}(Id INTEGER PRIMARY KEY)")
            conn.executemany(f"INSERT INTO {table} VALUES (?)", [(1,), (2,), (3,)])
        conn.execute("CREATE TABLE votes(PostId INTEGER)")
        conn.executemany("INSERT INTO votes VALUES (?)", [(1,), (2,)])
        cards = [
            {"id": 1, "table": "posts", "name": "Id", "kind": "number",
             "is_unique": True, "is_pk": True},
            {"id": 2, "table": "postHistory", "name": "Id", "kind": "number",
             "is_unique": True, "is_pk": True},
            {"id": 3, "table": "votes", "name": "PostId", "kind": "number",
             "is_unique": False, "is_pk": False},
        ]
        self.assertEqual(links.inferred(conn, cards, set()), [(3, 1, 1.0)])
        # posts is still the table named when that link is declared
        self.assertEqual(links.inferred(conn, cards, {(3, 1)}), [])

    def test_inferred_skips_two_keys_both_named_id(self):
        conn = sqlite3.connect(":memory:")
        for table in ("battle", "death"):
            conn.execute(f"CREATE TABLE {table}(id INTEGER PRIMARY KEY)")
            conn.executemany(f"INSERT INTO {table} VALUES (?)", [(1,), (2,), (3,)])
        cards = [
            {"id": 1, "table": "battle", "name": "id", "kind": "number",
             "is_unique": True, "is_pk": True},
            {"id": 2, "table": "death", "name": "id", "kind": "number",
             "is_unique": True, "is_pk": True},
        ]
        self.assertEqual(links.inferred(conn, cards, set()), [])

    def test_inferred_skips_a_declared_pair(self):
        conn = _database()
        self.assertEqual(links.inferred(conn, _cards(), {(2, 3)}), [])

    def test_inferred_still_links_text(self):
        conn = _database()
        conn.execute("CREATE TABLE city(name TEXT UNIQUE)")
        conn.executemany("INSERT INTO city VALUES (?)", [("Paris",), ("Lyon",)])
        conn.execute("CREATE TABLE trip(city TEXT)")
        conn.executemany("INSERT INTO trip VALUES (?)", [("Paris",), ("Lyon",)])
        cards = [
            {"id": 5, "table": "city", "name": "name", "kind": "text",
             "is_unique": True, "is_pk": False},
            {"id": 6, "table": "trip", "name": "city", "kind": "text",
             "is_unique": False, "is_pk": False},
        ]
        self.assertEqual(links.inferred(conn, cards, set()), [(6, 5, 1.0)])

    def test_inferred_links_ids_written_as_decimals_only_where_names_agree(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE dept(dept_key TEXT UNIQUE)")
        conn.executemany("INSERT INTO dept VALUES (?)", [(str(n),) for n in range(1, 30)])
        conn.execute("CREATE TABLE room(dept_key TEXT, units TEXT)")
        conn.executemany("INSERT INTO room VALUES (?, ?)", [("12.0", "3.0"), ("19.0", "6.0")])
        cards = [
            {"id": 1, "table": "dept", "name": "dept_key", "kind": "text",
             "is_unique": True, "is_pk": False},
            {"id": 2, "table": "room", "name": "dept_key", "kind": "text",
             "is_unique": False, "is_pk": False},
            {"id": 3, "table": "room", "name": "units", "kind": "text",
             "is_unique": False, "is_pk": False},
        ]
        self.assertEqual(links.inferred(conn, cards, set()), [(2, 1, 1.0)])

    def test_contained_points_at_the_key_whatever_the_names_and_not_at_a_count(self):
        conn = sqlite3.connect(":memory:")
        # account ids with gaps between them, which the trades all avoid
        ids = [5000 + 7 * n + n * n % 5 for n in range(50)]
        rows = {
            "account": [(i,) for i in ids],
            "trade": [(ids[n % 40],) for n in range(120)],
            # a second copy of the account ids, two rows each: not a key to point at
            "holding": [(ids[n % 50],) for n in range(100)],
            "person": [(n,) for n in range(1, 101)],
            "visit": [(n % 30 + 1,) for n in range(90)],
            "station": [(n,) for n in range(44, 144)],
            "sale": [(50 + n % 40,) for n in range(80)],
        }
        cards = []
        for number, (table, name) in enumerate(
            [("account", "id"), ("trade", "facilitated_by"), ("holding", "held_by"),
             ("person", "id"), ("visit", "times"), ("station", "id"), ("sale", "litres")],
            start=1,
        ):
            conn.execute(f"CREATE TABLE {table}({name} INTEGER)")
            conn.executemany(f"INSERT INTO {table} VALUES (?)", rows[table])
            distinct = len(set(rows[table]))
            cards.append({"id": number, "table": table, "name": name, "kind": "number",
                          "is_unique": distinct == len(rows[table]), "is_pk": False,
                          "distinct_count": distinct, "rows": len(rows[table])})
        # visit.times sits inside person.id, and sale.litres inside station.id, by chance:
        # those keys hold every number around them
        self.assertEqual(links.contained(conn, cards, set()), [(2, 1, 1.0), (3, 1, 1.0)])

    def test_a_few_ids_point_at_a_key_chance_would_not_fill(self):
        conn = sqlite3.connect(":memory:")
        ids = [113, 127, 131, 149, 152, 168, 174, 189]
        columns = {
            "person": {"id": ids},
            "kind": {"id": list(range(1, 8))},
            "dept": {"id": list(range(10, 280, 10))},
            # two rows per person, so no column of it is a key
            "exam": {"person": ids * 2, "level": [1, 2, 3, 5] * 4, "passed": [0, 1] * 8,
                     "fee": [30, 50, 100, 120] * 4},
            # boss points at the staff's own ids, which person also holds
            "staff": {"id": ids, "boss": [127, 149] * 4},
        }
        cards = []
        for table, values in columns.items():
            names = list(values)
            conn.execute(f"CREATE TABLE {table}({', '.join(names)} INTEGER)")
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(names))})",
                             zip(*values.values()))
            for name, column in values.items():
                cards.append({"id": len(cards) + 1, "table": table, "name": name, "kind": "number",
                              "is_unique": len(set(column)) == len(column), "is_pk": False,
                              "distinct_count": len(set(column)), "rows": len(column)})
        # exam.person points at person.id and staff.id, which hold the same ids
        self.assertEqual(links.small_links(conn, cards, set(), set()), [(4, 1, 1.0), (4, 8, 1.0)])
        # exam.level is dense in kind.id, exam.passed a flag, exam.fee round numbers among
        # round numbers, staff.boss points into its own table, and a pair already linked
        # is left as it is
        self.assertEqual(links.small_links(conn, cards, set(), {(8, 4)}), [(4, 1, 1.0)])

    def test_agreeing_links_a_few_values_named_for_a_key_but_not_a_copy_or_a_count(self):
        conn = sqlite3.connect(":memory:")
        columns = {
            "station": {"station_code": [f"S{n}" for n in range(50)]},
            # a copy of some stations, pointing at station
            "busy_station": {"station_code": [f"S{n}" for n in range(30)]},
            "person": {"person_id": list(range(1, 101))},
            "trip": {"station_code": ["S3", "S7", "S9"] * 2, "person_id": [4, 8, 15, 16, 23, 42]},
        }
        cards = []
        for table, values in columns.items():
            names = list(values)
            conn.execute(f"CREATE TABLE {table}({', '.join(names)})")
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(names))})",
                             zip(*values.values()))
            for name, column in values.items():
                cards.append({"id": len(cards) + 1, "table": table, "name": name,
                              "kind": "number" if name == "person_id" else "text",
                              "is_unique": len(set(column)) == len(column), "is_pk": False,
                              "distinct_count": len(set(column)), "rows": len(column)})
        # the copy and the trips point at station, past the tighter copy; six small numbers
        # sit in an id counting up from 1 by chance
        self.assertEqual(links.agreeing(conn, cards, set(), {(2, 1)}), [(2, 1, 1.0), (4, 1, 1.0)])
        # with no sure link from the copy, it is no copy the trips reach station through
        self.assertEqual(links.agreeing(conn, cards, set(), set()),
                         [(2, 1, 1.0), (4, 1, 1.0), (4, 2, 1.0)])

    def test_candidates_leave_out_a_counting_id_and_a_column_whose_keys_are_all_sure(self):
        conn = sqlite3.connect(":memory:")
        columns = {
            "term": {"code": [f"T{n}" for n in range(30)]},
            # a history table repeats each term: different on half its rows
            "term_hist": {"code": [f"T{n}" for n in range(30)] * 2},
            "person": {"id": list(range(1, 101))},
            "visit": {"person": list(range(1, 22)), "term": ["T1", "T2", "T3"] * 7},
        }
        cards = []
        for table, values in columns.items():
            names = list(values)
            conn.execute(f"CREATE TABLE {table}({', '.join(names)})")
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(names))})",
                             zip(*values.values()))
            for name, column in values.items():
                cards.append({"id": len(cards) + 1, "table": table, "name": name,
                              "kind": "text" if isinstance(column[0], str) else "number",
                              "is_unique": len(set(column)) == len(column), "is_pk": False,
                              "distinct_count": len(set(column)), "rows": len(column)})
        found = links.candidates(conn, cards, set(), {(4, 3)})
        # person.id counts up and every wider id holds it; visit.person's one key is sure;
        # three terms are too few to point anywhere unless every one is held
        self.assertEqual(sorted(found), [1, 2, 5])
        self.assertEqual(sorted(found[5]), [(1, 1.0), (2, 1.0)])


def _database() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE department(id INTEGER PRIMARY KEY, budget INTEGER)")
    conn.executemany("INSERT INTO department VALUES (?, ?)", [(1, 10), (2, 20), (3, 30)])
    conn.execute("CREATE TABLE employee(department_id INTEGER)")
    conn.executemany("INSERT INTO employee VALUES (?)", [(1,), (2,), (3,), (9,)])
    return conn


def _cards() -> list[dict]:
    # department.budget is a decoy: a number column with no name agreement.
    return [
        {"id": 1, "table": "department", "name": "budget", "kind": "number",
         "is_unique": False, "is_pk": False},
        {"id": 2, "table": "employee", "name": "department_id", "kind": "number",
         "is_unique": False, "is_pk": False},
        {"id": 3, "table": "department", "name": "id", "kind": "number",
         "is_unique": True, "is_pk": True},
    ]
