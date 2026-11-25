import json
import sqlite3
import unittest
from unittest import mock

from amigo import layer, llm


class DescribeTest(unittest.TestCase):
    def test_a_wide_table_is_described_in_parts_and_every_column_gets_one(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(layer._SCHEMA)
        conn.execute("INSERT INTO databases VALUES (1, 'shop', 'shop', '')")
        conn.execute(
            "INSERT INTO tables(id, database_id, name, readable, row_count, primary_key)"
            " VALUES (1, 1, 'wide', 'wide', 10, '')"
        )
        conn.executemany(
            "INSERT INTO columns(id, table_id, name, readable, type, is_pk, distinct_count, samples)"
            " VALUES (?, 1, ?, ?, 'TEXT', 0, 1, ?)",
            [(i, f"c{i}", f"c{i}", json.dumps(["x"])) for i in range(1, 251)],
        )
        calls = []

        def fake(database, table, n_rows, cards, log_path):
            calls.append(len(cards))
            return llm.TableDescription(
                table_description=f"part {len(calls)}",
                columns=[llm.ColumnDescription(name=c["name"], description=f"about {c['name']}") for c in cards],
            )

        with mock.patch.object(llm, "describe_table", fake):
            layer._describe(conn, {"name": "shop"})
        self.assertEqual(calls, [100, 100, 50])
        self.assertEqual(conn.execute("SELECT description FROM tables").fetchone()[0], "part 1")
        self.assertEqual(
            conn.execute("SELECT count(*) FROM columns WHERE description = 'about ' || name").fetchone()[0], 250
        )


if __name__ == "__main__":
    unittest.main()
