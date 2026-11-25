import sqlite3
import unittest

from amigo import profile


class DateTest(unittest.TestCase):
    def _card(self, values: list[str]) -> dict:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t(v TEXT)")
        conn.executemany("INSERT INTO t VALUES (?)", [(v,) for v in values])
        return profile.profile_column(conn, "t", "v", len(values))

    def test_timestamp_text_with_one_bad_value_in_a_hundred_is_a_date(self):
        values = [f"2016-03-{day:02d}-10.15.{day:02d}.000000" for day in range(1, 29)] * 4
        card = self._card(values[:99] + ["unknown"])
        self.assertEqual(card["kind"], "date")
        self.assertEqual(card["date_format"], "%Y-%m-%d-%H.%M.%S.%f")
        self.assertEqual(card["date_min"], "2016-03-01T10:15:01")
        self.assertEqual(card["date_failures"], 1)

    def test_ids_that_rarely_look_like_months_stay_text(self):
        card = self._card([str(n) for n in range(208500, 208600)])
        self.assertEqual(card["kind"], "text")


if __name__ == "__main__":
    unittest.main()
