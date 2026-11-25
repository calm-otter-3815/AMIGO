import unittest

import numpy as np

from amigo.cutoff import top


class TestCutoff(unittest.TestCase):
    def test_best_first(self):
        scores = np.array([0.1, 0.9, 0.5, 0.7])
        self.assertEqual(list(top(scores, 2)), [1, 3])

    def test_all_when_fewer_than_k(self):
        scores = np.array([0.3, 0.1, 0.2])
        self.assertEqual(list(top(scores, 10)), [0, 2, 1])

    def test_k_is_a_hard_cap(self):
        scores = np.arange(50, dtype=float)
        self.assertEqual(len(top(scores, 20)), 20)

    def test_cards_tied_with_the_last_one_kept_stay_together(self):
        scores = np.array([0.5, 0.9, 0.7, 0.2, 0.7, 0.7])
        self.assertEqual(list(top(scores, 2)), [1, 2, 4, 5])


if __name__ == "__main__":
    unittest.main()
