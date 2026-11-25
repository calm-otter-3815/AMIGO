import unittest
from types import SimpleNamespace

from baselines.cut import cut
from baselines.lake import record


class TestCut(unittest.TestCase):
    def test_tables_keep_their_start(self):
        one = record(["d.c", "d.a", "d.b"]) | {"seconds": {"total": 2.0}}
        got = cut(one, 2)
        self.assertEqual(got["order"], ["d.c", "d.a"])
        self.assertEqual(got["interpretations"][0]["tables"], ["d.a", "d.c"])
        self.assertEqual(got["seconds"], {"total": 2.0})

    def test_columns_keep_their_start_and_tables(self):
        columns = ["d.b.x", "d.a.y", "d.b.z"]
        one = record(["d.b", "d.a"], columns, levels=("columns", "tables"), pick_order=columns)
        lake = SimpleNamespace(column={c: SimpleNamespace(table=c.rsplit(".", 1)[0]) for c in columns})
        got = cut(one, 1, lake)
        self.assertEqual((got["order"], got["picked"], got["pick_order"]), (["d.b"], ["d.b.x"], ["d.b.x"]))
        self.assertEqual(got["levels"], ["columns", "tables"])

    def test_failure_stays(self):
        self.assertEqual(cut({"error": "x"}, 1), {"error": "x"})
