"""The readable-name rule from PLAN.md section 2.2, and the split of glued names."""

import math
import re

# One alphanumeric run per match, cut at every boundary the rule names:
# an uppercase run not followed by a lowercase letter (HTTP in HTTPServer),
# then Capitalised or lowercase words, then digit runs. Everything the regex
# skips (underscores, hyphens, spaces, parentheses, percent signs) is dropped.
_PIECE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|[0-9]+")

EXAMPLES: tuple[tuple[str, str], ...] = (
    ("student_club", "student club"),
    ("player_fifa_api_id", "player fifa api id"),
    ("Player_Attributes", "player attributes"),
    ("date-of-birth", "date of birth"),
    ("CDSCode", "cds code"),
    ("HTTPServer", "http server"),
    ("OwnerUserId", "owner user id"),
    ("A11", "a 11"),
    ("K12", "k 12"),
    ("12K", "12 k"),
    ("GPA_2020", "gpa 2020"),
    ("Free Meal Count (K-12)", "free meal count k 12"),
    ("Percent (%) Eligible Free (K-12)", "percent eligible free k 12"),
    ("GPA", "GPA"),
    ("SNPP", "SNPP"),
    ("frpm", "frpm"),
)


def readable(name: str) -> str:
    if name.isalpha() and name.isupper():
        return name
    return " ".join(piece.lower() for piece in _PIECE.findall(name))


# a glued piece holds at least two words of three letters (HASCITY); shorter pieces are
# abbreviations (fclt, frpm) and stay whole
GLUED_MIN = 6


def split_glued(piece: str, rank: dict[str, int]) -> list[str] | None:
    """The split of a glued piece into known words that costs least, a word costing the log
    of its frequency rank (Zipf's law): common words are cheap, so "cash and" beats "cas
    hand". None when no split into known words spells the piece."""
    best: list[tuple[float, list[str]] | None] = [(0.0, [])] + [None] * len(piece)
    for end in range(1, len(piece) + 1):
        for start in range(end):
            word = piece[start:end]
            if best[start] is None or word not in rank:
                continue
            cost = best[start][0] + math.log(rank[word] + 1)
            if best[end] is None or cost < best[end][0]:
                best[end] = (cost, best[start][1] + [word])
    return best[-1][1] if best[-1] else None


def stem(word: str) -> str:
    """A plural's singular, near enough to compare words: policies, holders, classes."""
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word
