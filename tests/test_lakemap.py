import numpy as np

from amigo import lakemap


class _Probe:
    def __init__(self):
        rng = np.random.default_rng(0)
        self.columns = {c: {"table_id": 1 + (c - 1) // 4} for c in range(1, 13)}
        self.matrix = rng.normal(size=(12, 8))


def test_columns_sit_around_their_own_table():
    tables = {1: (-0.8, 0.0), 2: (0.0, 0.0), 3: (0.8, 0.0)}
    where = lakemap.columns_xy(_Probe(), tables)
    for c, xy in where.items():
        own = tables[1 + (c - 1) // 4]
        assert min(tables.values(), key=lambda t: np.hypot(t[0] - xy[0], t[1] - xy[1])) == own
