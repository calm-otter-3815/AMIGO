"""Top-k cutoff from PLAN.md section 3.3: keep the k best-scoring cards per
lookup, a plain fixed top-k chosen by complete recall over the whole
benchmark, with no held-out half (experiments/results/cutoff_topk.md, removed; in git history at acf8b59).
"""

import numpy as np


def top(scores: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k best scores, best first, in id order among equal scores. Cards
    tied with the k-th are kept too: copies of one card in several databases score the
    same, and the sort order must not choose which copies survive. Fewer only if n < k."""
    order = np.argsort(-scores, kind="stable")
    if len(order) <= k:
        return order
    return order[scores[order] >= scores[order[k - 1]]]
