import sqlite3
import unittest

from amigo import layer


class RolesTest(unittest.TestCase):
    def test_link_words_land_on_the_columns_of_the_table_it_points_to(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(layer._SCHEMA)
        conn.execute("INSERT INTO databases VALUES (1, 'shop', 'shop', '')")
        conn.executemany(
            "INSERT INTO tables(id, database_id, name, readable, row_count, primary_key)"
            " VALUES (?, 1, ?, ?, 10, '')",
            [(1, "LISTING", "listing"), (2, "PRICE", "price")],
        )
        conn.executemany(
            "INSERT INTO columns(id, table_id, name, readable, type, is_pk) VALUES (?, ?, ?, ?, '', ?)",
            [
                (1, 1, "LISTINGID", "listing id", 1),
                (2, 1, "HASLASTSALEPRICE", "has last sale price", 0),
                (3, 1, "HASTITLE", "has title", 0),
                (4, 2, "PRICEID", "price id", 1),
                (5, 2, "HASAMOUNT", "has amount", 0),
                (6, 2, "HASCURRENCY", "has currency", 0),
            ],
        )
        conn.execute("INSERT INTO links VALUES (1, 2, 4, 'declared', 1.0, NULL)")
        layer._roles(conn, {})
        # "has" is in more than a third of the column names, so it names no role
        self.assertEqual(
            [tuple(r) for r in conn.execute("SELECT column_id, words FROM roles ORDER BY column_id")],
            [(5, "last sale price"), (6, "last sale price")],
        )


if __name__ == "__main__":
    unittest.main()
