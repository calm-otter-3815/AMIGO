import sqlite3
import unittest
from uuid import uuid4

from amigo.index import Bloom, column_index, inflections, normalise, word_pattern


class TestIndex(unittest.TestCase):
    def test_normalise(self):
        cases = [
            ("  Hello, World! ", "hello world"),
            ("K-12", "k12"),
            ("O'Brien", "obrien"),
            ("Ça\tva", "ça va"),
        ]
        for original, want in cases:
            with self.subTest(original=original):
                self.assertEqual(normalise(original), want)

    def test_inflections(self):
        self.assertEqual(inflections("savings"), ["saving"])
        self.assertEqual(inflections("seed"), ["seeds"])
        self.assertEqual(inflections("Role-playing games"), ["Role-playing game"])
        self.assertEqual(inflections("B-12"), [])
        # a plural spelling cannot settle gives both singulars; a lone "s" gives none
        self.assertEqual(inflections("courses"), ["course", "cours"])
        self.assertEqual(inflections("branches"), ["branche", "branch"])
        self.assertEqual(inflections("movies"), ["movy", "movie"])
        self.assertEqual(inflections("S"), [])

    def test_bloom(self):
        added = [uuid4().hex for _ in range(1000)]
        bloom = Bloom(len(added))
        for value in added:
            bloom.add(value)
        self.assertEqual(sum(value in bloom for value in added), len(added))

        fresh = [uuid4().hex for _ in range(20000)]
        false_positives = sum(value in bloom for value in fresh)
        self.assertLess(false_positives / len(fresh), 0.03)

        restored = Bloom.from_bytes(bloom.to_bytes())
        self.assertEqual(sum(value in restored for value in added), len(added))
        self.assertEqual(sum(value in restored for value in fresh), false_positives)

    def test_column_index(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE small (c text)")
        conn.executemany(
            "INSERT INTO small VALUES (?)", [(f"Value, {i}!",) for i in range(5)]
        )
        self.assertEqual(
            column_index(conn, "small", "c"), {f"value {i}" for i in range(5)}
        )

        conn.execute("CREATE TABLE big (c text)")
        big = [f"Row-{i}" for i in range(1500)]
        conn.executemany("INSERT INTO big VALUES (?)", [(value,) for value in big])
        index = column_index(conn, "big", "c")
        self.assertIsInstance(index, Bloom)
        self.assertEqual(sum(value in index for value in big), len(big))

    def test_word_pattern(self):
        cases = [
            ("Harlow", "Harlow Traders Ltd.", True),
            ("rota users", "night-rota-users", True),
            ("kiln4-07", "kiln4-07.lab.example.org", True),
            ("Ines Varga", "Varga, Ines K.", True),
            ("Ines Varga", "Vargas, Ines", False),
            ("Harl", "Harlow Traders Ltd.", False),
            ("M", "Hamilton", False),
        ]
        for text, value, want in cases:
            with self.subTest(text=text, value=value):
                self.assertEqual(bool(word_pattern(text).search(value.lower())), want)


if __name__ == "__main__":
    unittest.main()
