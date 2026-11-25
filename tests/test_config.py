import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from amigo import config


class TestQuestions(unittest.TestCase):
    def test_the_label_comes_from_SQL_query_or_a_string_sql(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dev.json"
            path.write_text(
                json.dumps(
                    [
                        {"question": "bird", "SQL": "SELECT 1", "evidence": "a note", "question_id": 7},
                        {"question": "spider", "query": "SELECT 2", "sql": {"from": {}}},
                        {"question": "beaver", "sql": "SELECT 3", "gold_tables": ["t"]},
                    ]
                )
            )
            with mock.patch.object(config, "lake", lambda name: {"questions": path}):
                records = config.questions("toy")
        self.assertEqual([one["SQL"] for one in records], ["SELECT 1", "SELECT 2", "SELECT 3"])
        self.assertEqual([one["question_id"] for one in records], [7, 2, 3])
        self.assertEqual([one["evidence"] for one in records], ["a note", "", ""])
        # every other key of the original record survives
        self.assertEqual(records[1]["sql"], {"from": {}})
        self.assertEqual(records[2]["gold_tables"], ["t"])


if __name__ == "__main__":
    unittest.main()
