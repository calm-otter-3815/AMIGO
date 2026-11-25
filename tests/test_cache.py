import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pydantic import BaseModel

from amigo import config, llm


class Answer(BaseModel):
    text: str


class TestCache(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.log = Path(folder.name) / "run.jsonl"
        for name, value in (("CACHE", True), ("CACHE_DIR", Path(folder.name) / "cache")):
            patcher = mock.patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def ask(self, prompt="which books?", check=None):
        return llm.call(prompt, Answer, self.log, "test", check=check)

    def test_the_same_prompt_gets_the_first_reply_back(self):
        with mock.patch.object(llm, "_call", side_effect=[Answer(text="a"), Answer(text="b")]) as called:
            first, second = self.ask(), self.ask()
            other = self.ask("which readers?")
        self.assertEqual((first.text, second.text, other.text), ("a", "a", "b"))
        self.assertEqual(called.call_count, 2)
        self.assertIn('"cached": true', self.log.read_text())

    def test_a_kept_reply_the_check_refuses_is_asked_again(self):
        def refuse(answer):
            if answer.text == "a":
                raise llm.ModelError("not a")

        with mock.patch.object(llm, "_call", side_effect=[Answer(text="a"), Answer(text="b")]) as called:
            self.ask()
            again = self.ask(check=refuse)
        self.assertEqual((again.text, called.call_count), ("b", 2))


if __name__ == "__main__":
    unittest.main()
