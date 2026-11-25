"""Greedy JAR (arXiv 2511.13418, section 3; greedy.py of the paper's public code):
JAR's sub-queries and candidate pool, but the k tables are picked one at a time, each the
best gain in coverage of the sub-queries, joins to the tables already picked and closeness
to the question. A ranking: the first n picks are the answer at k = n, so it is cut.

Departures:
1. medium: granite-embedding-english-r2 replaces Contriever (as in jar.py).
2. medium: JAR's decompose prompt (jar.py), on the night model at medium effort.
3. small: the lambdas are the paper's (coverage 2.0, join 1.0, coarse 4.0), not refit.
4. small: the pool is the 20 tables closest to the question on every lake.
5. small: join scores are jar.py's omega.
6. small: ties go to the better-ranked candidate.
"""

import numpy as np

from amigo import embed

from . import jar
from .lake import lap, record

POOL = 20
LAMBDA_COV, LAMBDA_JOIN, LAMBDA_COARSE = 2.0, 1.0, 4.0


def select(fine: np.ndarray, coarse: np.ndarray, omega: np.ndarray, k: int) -> list[int]:
    """k pool indices in pick order. fine[j, i]: sub-query j to table i; coarse[i]: the
    question to table i; omega[i, l]: the join score of tables i and l."""
    fine, coarse = np.asarray(fine, float), np.asarray(coarse, float)
    seed = int(np.argmax(LAMBDA_COARSE * coarse + LAMBDA_COV * np.maximum(fine, 0).sum(axis=0)))
    picked, covered = [seed], fine[:, seed].copy()
    while len(picked) < min(k, len(coarse)):
        gain = (LAMBDA_COV * np.maximum(fine - covered[:, None], 0).sum(axis=0)
                + LAMBDA_JOIN * omega[:, picked].sum(axis=1) + LAMBDA_COARSE * coarse)
        gain[picked] = -np.inf
        best = int(np.argmax(gain))  # the first of equal gains: the better-ranked
        picked.append(best)
        covered = np.maximum(covered, fine[:, best])
    return picked


def run(lake, question, log_path, k=5):
    tables, columns, schema = jar._vectors(lake)
    where = {c.path: i for i, c in enumerate(lake.column_list)}
    lap("setup")
    subs = jar.decompose(question, log_path)
    lap("llm decompose")
    coarse = tables @ embed.embed([question])[0]
    top = np.argsort(-coarse)[:POOL]
    pool = [lake.tables[i] for i in top]
    vectors = embed.embed(subs)
    fine = np.array([[float(np.max(columns[[where[c.path] for c in t.columns]] @ v)) for t in pool] for v in vectors])
    lap("search")
    omega = jar._joins(lake, pool, schema, where, "code")
    lap("joins")
    picked = select(fine, coarse[top], omega, k)
    lap("choose")
    return record([pool[i].path for i in picked], sub_queries=subs)
