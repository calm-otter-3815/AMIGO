import unittest

from amigo.names import EXAMPLES, readable, split_glued


class TestReadable(unittest.TestCase):
    def test_examples(self):
        for original, want in EXAMPLES:
            with self.subTest(original=original):
                self.assertEqual(readable(original), want)


class TestSplitGlued(unittest.TestCase):
    # made-up ranks: small is frequent
    RANK = {"and": 3, "cash": 400, "hand": 300, "cas": 9000}

    def test_common_words_win_over_rare_ones(self):
        self.assertEqual(split_glued("cashandcash", self.RANK), ["cash", "and", "cash"])

    def test_no_split_when_a_letter_is_left_over(self):
        self.assertIsNone(split_glued("cashx", self.RANK))


if __name__ == "__main__":
    unittest.main()
