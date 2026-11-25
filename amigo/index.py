"""Text value index from PLAN.md section 2.2: exact values, or a Bloom filter."""

import hashlib
import math
import re
import sqlite3
import string
from pathlib import Path

from . import config
from .profile import quote as _quote

_PUNCTUATION = str.maketrans("", "", string.punctuation)
_WHITESPACE = re.compile(r"\s+")
_WORD = re.compile(r"[^\W_]+")


def normalise(value: str) -> str:
    return _WHITESPACE.sub(" ", value.lower().translate(_PUNCTUATION)).strip()


def words(value: str) -> list[str]:
    """The words of a value, cut at every character that is not a letter or a digit:
    "cosmo3-23.yahoo.ca.com" is cosmo3, 23, yahoo, ca, com."""
    return _WORD.findall(value.lower())


def word_pattern(text: str) -> re.Pattern | None:
    """Where a stored value holds `text` as a run of whole words: "Alphabet" in "Alphabet
    Inc.", "duo users" in "cat-duo-users". A name of two or three words also matches
    written last name first, with the comma that marks that form: "Summer Haynes" in
    "Haynes, Summer M.". None when `text` has no word."""
    found = words(text)
    if not found:
        return None
    run = r"[\W_]+".join(map(re.escape, found))
    forms = [run]
    if 2 <= len(found) <= 3:
        forms.append(re.escape(found[-1]) + r"\s*,\s*" + r"[\W_]+".join(map(re.escape, found[:-1])))
    return re.compile(r"(?<![^\W_])(?:" + "|".join(forms) + r")(?![^\W_])")


def source_path(path: str) -> str:
    """A lake keeps each database's absolute path from the machine that built it; on
    another checkout the same file sits under this repo's benchmarks/ folder."""
    if "/benchmarks/" in path and not Path(path).exists():
        return str(config.ROOT / "benchmarks" / path.split("/benchmarks/", 1)[1])
    return path


def open_source(path: str) -> sqlite3.Connection:
    """Read-only connection to a benchmark database; one spider row holds invalid UTF-8, so decode leniently."""
    conn = sqlite3.connect(f"file:{source_path(path)}?mode=ro", uri=True)
    conn.text_factory = lambda data: data.decode("utf-8", "replace")
    return conn


def variants(text: str) -> list[str]:
    """The same value with words trimmed off, the end first, then the start.

    "Alameda County" gives "Alameda", then "County": the question often says more
    than the column stores. The value itself is not in the list.
    """
    words = text.split()
    shorter = [" ".join(words[:n]) for n in range(len(words) - 1, 0, -1)]
    shorter += [" ".join(words[n:]) for n in range(1, len(words))]
    return list(dict.fromkeys(shorter))


def inflections(text: str) -> list[str]:
    """The same value with its last word in the other number: "savings" gives "saving",
    "seed" gives "seeds". Spelling alone cannot tell "houses" from "classes" or "movies"
    from "policies", so such a plural gives both singulars: "house" and "hous", "classe"
    and "class". Empty when the last word is not all letters; the value itself is not in
    the list."""
    words = text.split()
    if not words or not words[-1].isalpha():
        return []
    last = words[-1].lower()
    if last.endswith("ies"):
        others = [last[:-3] + "y", last[:-1]]
    elif last.endswith(("ses", "xes", "ches", "shes")):
        others = [last[:-1], last[:-2]]
    elif last.endswith("s") and not last.endswith(("ss", "us", "is")):
        others = [last[:-1]]
    elif last.endswith(("s", "x", "ch", "sh")):
        others = [last + "es"]
    elif last.endswith("y") and last[-2:-1] not in ("", *"aeiou"):
        others = [last[:-1] + "ies"]
    else:
        others = [last + "s"]
    return [" ".join([*words[:-1], other]) for other in others if other]


class Bloom:
    def __init__(self, n_values: int) -> None:
        self.bits = bytearray(max(1, math.ceil(config.BLOOM_BITS_PER_VALUE * n_values / 8)))

    def _positions(self, text: str) -> list[int]:
        # double hashing (Kirsch and Mitzenmacher 2006): one digest, k derived positions
        digest = hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()
        h1 = int.from_bytes(digest[:8], "big")
        h2 = int.from_bytes(digest[8:], "big") | 1
        m = len(self.bits) * 8
        return [(h1 + i * h2) % m for i in range(config.BLOOM_HASHES)]

    def add(self, value: str) -> None:
        text = normalise(value)
        if not text:
            return
        for i in self._positions(text):
            self.bits[i // 8] |= 1 << (i % 8)

    def __contains__(self, value: str) -> bool:
        text = normalise(value)
        if not text:
            return False
        return all(self.bits[i // 8] >> (i % 8) & 1 for i in self._positions(text))

    def to_bytes(self) -> bytes:
        return bytes(self.bits)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Bloom":
        bloom = cls(0)
        bloom.bits = bytearray(data)
        return bloom


def column_index(conn: sqlite3.Connection, table: str, column: str) -> set[str] | Bloom:
    c = _quote(column)
    source = f"FROM {_quote(table)} WHERE typeof({c}) = 'text' AND trim({c}) <> ''"
    (n_values,) = conn.execute(f"SELECT count(DISTINCT {c}) {source}").fetchone()
    rows = conn.execute(f"SELECT DISTINCT {c} {source}")
    if n_values <= config.EXACT_VALUE_LIMIT:
        return {text for (value,) in rows if (text := normalise(value))}
    bloom = Bloom(n_values)
    for (value,) in rows:
        bloom.add(value)
    return bloom
