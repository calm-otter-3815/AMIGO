"""Hybrid retrieval: the BM25 ranking (bm25.py) and the dense ranking fused by reciprocal
rank fusion (Cormack et al. 2009): score(t) = sum over the rankings of 1 / (60 + rank),
rank from 1; 60 is their constant. Ties go to the dense order. No LLM call.
"""

from . import bm25
from .lake import lap, record

RRF = 60


def fuse(rankings: list[list[str]]) -> list[str]:
    """One ranking from several; the first ranking breaks ties, then the others in turn."""
    score: dict[str, float] = {}
    for ranking in rankings:
        for n, one in enumerate(ranking, start=1):
            score[one] = score.get(one, 0.0) + 1 / (RRF + n)
    order = {one: n for n, one in enumerate(dict.fromkeys(t for r in rankings for t in r))}
    return sorted(score, key=lambda t: (-score[t], order[t]))


def run(lake, question, log_path, k=5):
    bm25.rank(lake, "")
    lap("setup")
    dense = [t.path for t, _ in lake.rank_tables(question)]
    lexical = bm25.rank(lake, question)
    lap("search")
    fused = fuse([dense, lexical])
    lap("fuse")
    return record(fused[:k])
