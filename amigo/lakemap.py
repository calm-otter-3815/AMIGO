"""The 2D map the page draws a lake on: tables that mean alike sit close (t-SNE over the
table cards), and a part of the question sits near the tables of its closest columns.

scikit-learn comes with sentence-transformers, so the layout needs no new package. It is
computed once per lake and kept under runs/cache/map, keyed by the table embeddings.
"""

import hashlib
import json

import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from . import config, layer, solve
from .probe import Probe


def tables_xy(probe: Probe, dims: int = 2) -> dict[int, tuple[float, ...]]:
    """Every table at a point in [-1, 1] on each of `dims` axes (2 or 3)."""
    ids = sorted(probe.tables)
    vectors = layer.load_embeddings(probe.lake_name)[0][[t - 1 for t in ids]]
    key = hashlib.sha1(vectors.tobytes()).hexdigest()[:16]
    path = config.CACHE_DIR / "map" / f"{probe.lake_name}-{key}{'' if dims == 2 else f'-{dims}d'}.json"
    if path.exists():
        return {int(t): tuple(xy) for t, xy in json.loads(path.read_text()).items()}
    points = TSNE(
        n_components=dims, metric="cosine", init="pca", random_state=0,
        perplexity=min(30.0, max(2.0, (len(ids) - 1) / 4)),
    ).fit_transform(vectors)
    points -= points.mean(axis=0)
    points /= np.abs(points).max() or 1.0
    where = {t: tuple(round(float(v), 4) for v in point) for t, point in zip(ids, points)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(where))
    return where


def columns_xy(probe: Probe, tables: dict[int, tuple[float, ...]]) -> dict[int, tuple[float, ...]]:
    """Every column around its own table, on the side its meaning points to: the column vectors'
    main directions (PCA) set the offset, so a lake of 100k columns needs no t-SNE of its own.
    The offsets reach about half the usual gap between neighbouring tables."""
    dims = len(next(iter(tables.values())))
    ids = sorted(probe.columns)
    offsets = PCA(n_components=dims, random_state=0).fit_transform(probe.matrix[[c - 1 for c in ids]])
    offsets /= np.abs(offsets).max() or 1.0
    points = np.array(list(tables.values()))
    gaps = np.sort(np.linalg.norm(points[:, None] - points[None], axis=2), axis=1)[:, 1] if len(points) <= 3000 else \
        np.full(1, 2 / len(points) ** (1 / dims))
    reach = 0.5 * float(np.median(gaps)) if len(points) > 1 else 0.1
    return {c: tuple(round(float(v), 4) for v in np.array(tables[probe.columns[c]["table_id"]]) + reach * off)
            for c, off in zip(ids, offsets)}


def part_xy(probe: Probe, scores: np.ndarray, where: dict[int, tuple[float, float]]) -> tuple[float, float]:
    """A part at the middle of the tables of its 8 closest columns, the closest weighing most."""
    top = np.argsort(-scores)[:8]
    weights = np.exp((scores[top] - scores[top].max()) / 0.03)
    xy = np.array([where[probe.columns[int(i) + 1]["table_id"]] for i in top])
    x, y = (weights[:, None] * xy).sum(axis=0) / weights.sum()
    return round(float(x), 4), round(float(y), 4)


def lake_map(probe: Probe) -> dict:
    """Every table with its point in 2D and 3D, and every pair of tables good enough to join on."""
    where, where3 = tables_xy(probe), tables_xy(probe, 3)
    return {
        "tables": [
            {"id": t, "path": probe.path("table", t), "readable": row["readable"],
             "database": row["database"], "rows": row["row_count"], "xy": where[t], "xyz": where3[t]}
            for t, row in probe.tables.items()
        ],
        "links": sorted(
            {(min(a, b), max(a, b), round(max(join.quality for join in found), 2))
             for (a, b), found in solve.joins(probe).items()}
        ),
    }


def lake_columns(probe: Probe) -> list[dict]:
    """Every column with its point in 2D and 3D, next to its table's."""
    where, where3 = columns_xy(probe, tables_xy(probe)), columns_xy(probe, tables_xy(probe, 3))
    return [{"id": c, "table": row["table_id"], "name": row["name"], "xy": where[c], "xyz": where3[c]}
            for c, row in probe.columns.items()]
