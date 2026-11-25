"""Candidate interpretations, best first, with no LLM call.

An interpretation puts each part of the question in a column of one database; a part
that names the things a table's rows are ("customers") is held by a column of that table,
such as its own id or name. The tables of the holders are joined by the fewest join tables the link graph allows: a group
Steiner tree, the answer shape of keyword search over databases (BANKS, Bhalotia et al.
2002; DPBF, Ding et al. 2007), here with ranked holders instead of exact keyword hits.

Every choice has a cost, read as minus the log2 odds of the evidence for it:
- a holder at rank r of a part's lookup costs log2(1 + r): retrievers' hit rates fall
  roughly as a power of the rank, so the cost grows as the log of the rank;
- a part with a value: the h columns that store it tie at value rank h, the other
  candidate columns at rank N, so a column that does not store it pays
  log2(1 + N) - log2(1 + h) more. A value few columns store says much, one many store
  says little, and a column without it (codes such as "F" for female) can still hold
  the part;
- every part is placed: an interpretation that leaves out a part answers another
  question. Only when none places every part, or when a person asks, are parts left out
  (`drop`), and such an interpretation is marked relaxed (Candidate.left_out);
- a join between tables a and b costs log2(1 + d), d the fewer links of the two: the
  cost of naming that link among the links of one end. Only links join: two tables the
  link graph does not join are not joined;
- each choice of places is joined once, by its cheapest tree with no trap (by its
  cheapest when every tree has one, or in a database that declares no join key). A trap is a join table that holds no part, entered
  by two or more joins from columns that point into its key. It relates their rows only
  by sharing one of its rows (persons and postal addresses in the same country), a
  condition the question never states: Codd's connection trap (1970), the shape
  reporting tools call a chasm trap (two many-to-one joins meeting in one table, SAP
  BusinessObjects). A question that names that table places a part in it, and then it
  is no trap. The join paths of one choice of places are other ways to run the same
  question, not other questions.
Otherwise nothing is cut: a lower cost only moves an interpretation up the list, and the k
cheapest come out in order, exactly (best-first search with lazy join costs).
"""

import heapq
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import config, solve
from .probe import Probe

log = logging.getLogger(__name__)

# holders kept per part, per lookup: columns by name, tables by name
COLUMNS_PER_PART = config.COLUMNS_PER_PART
# the most groups searched exactly (the search doubles with each one)
MAX_GROUPS = 10
# search effort cap, logged when reached
MAX_SOLVES = 3000


@dataclass(frozen=True)
class Holder:
    part: int
    table: int
    column: int
    cost: float
    why: str
    via: int | None = None  # the reference column this place was reached from
    miss: float = 0.0  # the cost added for not storing the part's value
    score: float = 0.0  # its cosine to the part: breaks ties in cost


@dataclass
class Candidate:
    database: str
    tables: frozenset[int]
    holders: tuple[Holder | None, ...]  # one per part, None when unplaced
    edges: tuple[tuple[int, int], ...]  # tree edges, each a link of the graph
    cost: float
    holder_cost: float = 0.0
    join_cost: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def left_out(self) -> tuple[int, ...]:
        """The parts this interpretation leaves out: a relaxed interpretation when any."""
        return tuple(j for j, h in enumerate(self.holders) if h is None)


def _rank_cost(rank: int) -> float:
    return math.log2(1 + rank)


def tie_order(h: Holder):
    """Cheapest first; at equal cost the place closer in meaning to the part."""
    return h.cost, -h.score, h.table, h.column


def holders(probe: Probe, stage, k: int, within: frozenset[int] | None = None) -> list[Holder]:
    """Part k's holders over the whole lake, or among the tables `within`, cheapest first;
    one per column. Ranks count only the places considered, so a column that ranks low
    over the lake can rank first among the tables near the rest of the question."""
    entity = stage.entities[k]

    def inside(table: int) -> bool:
        return within is None or table in within

    def ranked(scores: np.ndarray, considered: list[int], top: int, hits: set[int]):
        """The top places by cosine plus the ones the value points to, each with its meaning
        rank (its place by cosine among those considered, even far down the list), and the
        value cost of a place the value does not point to: the h it points to tie at value
        rank h, the others at N; a value that points nowhere says nothing."""
        ids = np.array(considered, dtype=int)
        order = ids[np.argsort(-scores[ids - 1], kind="stable")]
        falling = -scores[order - 1]
        places = list(dict.fromkeys(order[:top].tolist() + sorted(hits)))
        miss = _rank_cost(len(places)) - _rank_cost(len(hits)) if hits else 0.0
        for place in places:
            yield place, int(np.searchsorted(falling, -scores[place - 1], side="left")) + 1, miss

    # the columns closest in meaning, and the columns the value is stored in
    scores = stage.column_scores[k]
    hits = {c for kk, kind, cols in stage.found if kk == k and kind == "value" for c in cols
            if inside(probe.columns[c]["table_id"])}
    considered = [c for c in range(1, len(scores) + 1) if inside(probe.columns[c]["table_id"])]
    out = []
    for column, rank, miss in ranked(scores, considered, COLUMNS_PER_PART, hits):
        table, score = probe.columns[column]["table_id"], float(scores[column - 1])
        if column in hits:
            why = "; ".join(stage.details.get(column, [])) or "stores the value"
            out.append(Holder(k, table, column, _rank_cost(rank), why, score=score))
        else:
            out.append(Holder(k, table, column, _rank_cost(rank) + miss,
                              f'named like "{entity.attribute}" (rank {rank})', miss=miss, score=score))
    return sorted(out, key=tie_order)


class Graph:
    """The lake's join graph: an edge per table pair the link graph joins."""

    def __init__(self, probe: Probe, kinds: frozenset | None = None) -> None:
        self.ways = solve.joins(probe, kinds)
        self.adj: dict[int, set[int]] = defaultdict(set)
        for a, b in self.ways:
            self.adj[a].add(b)
        self.database = {t: probe.tables[t]["database"] for t in probe.tables}
        # the databases whose schema declares a join key: in one that declares none, every
        # join is a guess from the data, so a choice of places keeps its cheapest tree
        self.keyed = {self.database[probe.columns[link["from_column"]]["table_id"]]
                      for link in probe.links if link["kind"] == "declared"}
        # a table's own key: a primary key of one column; one part of a composite key
        # (lapTimes.driverId) names another table's row, as in solve.keyed
        primary = defaultdict(int)
        for card in probe.columns.values():
            primary[card["table_id"]] += bool(card["is_pk"])

        def own(column: int) -> bool:
            card = probe.columns[column]
            return bool(card["is_pk"]) and primary[card["table_id"]] == 1

        # what each reference column points to: the tables whose key it holds
        self.references: dict[int, set[int]] = defaultdict(set)
        for ways in self.ways.values():
            for join in ways:
                for source, target in join.links:
                    if not own(source):
                        self.references[source].add(probe.columns[target]["table_id"])
        # (a, b) when a column of a that is not a key points into b's key: a's rows each
        # name one row of b, and many may name the same one
        self.into: set[tuple[int, int]] = set()
        for (a, b), ways in self.ways.items():
            for join in ways:
                for x, y in join.links:
                    for s, t in ((x, y), (y, x)):
                        source, target = probe.columns[s], probe.columns[t]
                        if (source["table_id"] == a and target["table_id"] == b
                                and not (own(s) or source["is_unique"])
                                and (own(t) or target["is_unique"])):
                            self.into.add((a, b))
        self.nodes: dict[str, list[int]] = defaultdict(list)
        for t in sorted(probe.tables):
            self.nodes[self.database[t]].append(t)
        self._metrics: dict[str, tuple] = {}

    def weight(self, a: int, b: int) -> float:
        """The cost of the join between linked tables a and b: naming it among the links of
        the end that has fewer."""
        return math.log2(1 + min(len(self.adj[a]), len(self.adj[b])))

    def _load(self, db: str) -> tuple:
        """A database's joins as index arrays (a, b, weight), a < b, with each table pair's
        place in them; and the cheapest join cost between every two tables with the table
        before each end on the way (Dijkstra)."""
        if db not in self._metrics:
            nodes = self.nodes[db]
            index = {t: i for i, t in enumerate(nodes)}
            pairs = [(t, u) for t in nodes for u in self.adj[t] if t < u]
            a = np.array([index[t] for t, _ in pairs], dtype=int)
            b = np.array([index[u] for _, u in pairs], dtype=int)
            w = np.array([self.weight(t, u) for t, u in pairs])
            joins = csr_matrix((w, (a, b)), shape=(len(nodes), len(nodes)))
            dist, before = dijkstra(joins, directed=False, return_predecessors=True)
            self._metrics[db] = (a, b, w, {p: i for i, p in enumerate(pairs)}), dist, before
        return self._metrics[db]

    def joins(self, db: str) -> tuple:
        """A database's joins: index arrays (a, b, weight), a < b, and each table pair's place."""
        return self._load(db)[0]

    def metric(self, db: str) -> tuple[np.ndarray, np.ndarray]:
        """The join cost between every two tables of a database (infinite when no links
        join them), and the next table on the cheapest way."""
        _, dist, before = self._load(db)
        n = len(dist)
        # the next table from a towards b: the one before a on the cheapest way from b
        step = before.T.copy()
        alone = step < 0
        step[alone] = np.broadcast_to(np.arange(n), (n, n))[alone]
        return dist, step

    def traps(self, held: set[int], edges) -> int:
        """The join tables of a tree holding no part that two or more of its joins point
        into."""
        entered: dict[int, int] = defaultdict(int)
        for a, b in edges:
            if (a, b) in self.into:
                entered[b] += 1
            if (b, a) in self.into:
                entered[a] += 1
        return sum(1 for t, n in entered.items() if n >= 2 and t not in held)

def _place(graph: Graph, db: str, per_part: list[dict[int, Holder]], leave: list[float],
           fixed: dict, banned: frozenset, required: frozenset = frozenset(),
           barred: frozenset = frozenset()):
    """The cheapest interpretation in one database that keeps each part in `fixed` where it
    says and no part where `banned` says (None: unplaced), as (cost, holders, tables, edges,
    join cost), or None when there is none. A part is left out only at its cost in `leave`
    (infinite: never). When every part is fixed, the tree keeps the joins in `required`
    and none in `barred` (table pairs, lower id first).

    Exact up to MAX_GROUPS parts. Beyond, parts whose cheapest holder is in the same table
    are searched as one group, the smallest groups are left out of the tree search, and
    every part then takes its cheapest holder among the tree's tables."""
    nodes = graph.nodes[db]
    index = {t: i for i, t in enumerate(nodes)}
    free = [j for j in range(len(per_part)) if j not in fixed]
    held = sorted({fixed[j] for j in fixed if fixed[j] is not None})
    if not free:
        # every part placed: the cheapest tree joining the held tables
        found = _steiner(graph, db, held, required, barred)
        if found is None:
            return None
        pairs, join = found
        chosen = tuple(per_part[j][t] if t is not None else None for j, t in sorted(fixed.items()))
        holder = sum(h.cost if h else leave[j] for j, h in enumerate(chosen))
        return holder + join, chosen, frozenset(held) | {t for e in pairs for t in e}, pairs, join
    dist, step = graph.metric(db)
    rows, unplaced = {}, {}
    for j in free:
        row = np.full(len(nodes), np.inf)
        for t, h in per_part[j].items():
            if t in index and (j, t) not in banned:
                row[index[t]] = h.cost
        rows[j] = row
        unplaced[j] = math.inf if (j, None) in banned else leave[j]
    room = max(MAX_GROUPS - len(held), 1)
    if len(free) <= room:
        groups = [[j] for j in free]
    else:
        same: dict[int, list[int]] = defaultdict(list)
        for j in free:
            same[int(rows[j].argmin()) if np.isfinite(rows[j]).any() else -1].append(j)
        groups = sorted(same.values(), key=lambda g: (-len(g), g))[:room]
    cost = [np.sum([np.minimum(rows[j], unplaced[j]) for j in g], axis=0) for g in groups]
    out = [sum(unplaced[j] for j in g) for g in groups]
    for t in held:
        row = np.full(len(nodes), np.inf)
        row[index[t]] = 0.0
        cost.append(row)
        out.append(math.inf)
    if not cost:
        return None
    total, place, edges = _group_steiner(dist, step, np.array(cost), np.array(out))
    if not math.isfinite(total):
        return None
    # each part takes its cheapest holder among the tree's tables
    tree = {nodes[i] for e in edges for i in e} | {nodes[i] for i in place if i >= 0}
    chosen: list[Holder | None] = [None] * len(per_part)
    for j in fixed:
        if fixed[j] is not None:
            chosen[j] = per_part[j][fixed[j]]
    for j in free:
        options = [per_part[j][t] for t in tree if t in per_part[j] and (j, t) not in banned]
        best = min(options, key=tie_order, default=None)
        if best is not None and best.cost < unplaced[j]:
            chosen[j] = best
        elif not math.isfinite(unplaced[j]):
            return None
    # drop join tables left hanging with no holder
    pairs = {(nodes[a], nodes[b]) for a, b in edges}
    needed = {h.table for h in chosen if h is not None}
    while True:
        degree: dict[int, int] = defaultdict(int)
        for x, y in pairs:
            degree[x] += 1
            degree[y] += 1
        loose = {t for t, d in degree.items() if d == 1 and t not in needed}
        if not loose:
            break
        pairs = {e for e in pairs if not loose & set(e)}
    if not needed:
        return None
    pairs = tuple(sorted(pairs))
    join = sum(graph.weight(x, y) for x, y in pairs)
    tables = frozenset(needed) | frozenset(t for e in pairs for t in e)
    holder = sum(h.cost if h else leave[j] for j, h in enumerate(chosen))
    return holder + join, tuple(chosen), tables, pairs, join


@lru_cache(maxsize=None)
def _splits(p: int) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Per size from 2 to p: the subsets of p groups of that size, as bit masks, and each
    one's splits in two (the half holding its lowest group, and the other half)."""
    out = []
    for size in range(2, p + 1):
        wholes = [w for w in range(1 << p) if w.bit_count() == size]
        halves = []
        for whole in wholes:
            low = whole & -whole
            rest, sub, mine = whole ^ low, whole ^ low, []
            while sub:
                sub = (sub - 1) & rest
                mine.append(low | sub)
            halves.append(mine)
        w, a = np.array(wholes), np.array(halves)
        out.append((w, a, w[:, None] ^ a))
    return out


def _group_steiner(dist: np.ndarray, step: np.ndarray, cost: np.ndarray, unplaced: np.ndarray):
    """The cheapest tree that holds each group at one of its nodes or leaves it unplaced
    (dynamic program over subsets of groups, Dreyfus and Wagner 1971, as DPBF does for
    keyword groups). cost[g, i]: group g held at node i; unplaced[g]: g left out. Returns
    (total, node of each group or -1, tree edges as node pairs)."""
    groups, n = cost.shape
    full = (1 << groups) - 1
    best = np.full((full + 1, n), np.inf)
    split = np.zeros((full + 1, n), dtype=np.int64)
    root = np.zeros((full + 1, n), dtype=np.int64)
    seed = np.zeros((groups, n), dtype=np.int64)
    columns = np.arange(n)
    for g in range(groups):
        grown = cost[g][:, None] + dist
        at = grown.argmin(axis=0)
        reach = grown[at, columns]
        out = unplaced[g] <= reach
        best[1 << g] = np.where(out, unplaced[g], reach)
        seed[g] = np.where(out, -1, at)
    for wholes, halves, others in _splits(groups):
        chunk = max(1, 4_000_000 // (n * max(n, halves.shape[1])))
        for lo in range(0, len(wholes), chunk):
            w, a, b = wholes[lo:lo + chunk], halves[lo:lo + chunk], others[lo:lo + chunk]
            merged = best[a] + best[b]
            pick = merged.argmin(axis=1)
            joined = np.take_along_axis(merged, pick[:, None, :], axis=1)[:, 0]
            grown = joined[:, :, None] + dist[None]
            at = grown.argmin(axis=1)
            best[w] = np.take_along_axis(grown, at[:, None, :], axis=1)[:, 0]
            split[w] = np.take_along_axis(a, pick, axis=1)
            root[w] = at
    v = int(best[full].argmin())
    total = float(best[full, v])
    place, edges = [-1] * groups, set()
    if not math.isfinite(total):
        return total, place, edges

    def path(a: int, b: int) -> None:
        while a != b:
            nxt = int(step[a, b])
            edges.add((min(a, nxt), max(a, nxt)))
            a = nxt

    todo = [(full, v)]
    while todo:
        whole, v = todo.pop()
        if whole & (whole - 1) == 0:
            g = whole.bit_length() - 1
            if seed[g, v] >= 0:
                place[g] = int(seed[g, v])
                path(place[g], v)
            continue
        u = int(root[whole, v])
        path(u, v)
        a = int(split[whole, u])
        todo += [(a, u), (whole ^ a, u)]
    return total, place, edges


def _labels(joins, n: int, cost: np.ndarray):
    """For each set of groups and each node, the cheapest tree holding every group of the
    set at one of its nodes and reaching the node: Dreyfus and Wagner's merge over the
    set's splits, then the growth to every node as one Dijkstra from a source joined to
    each node at its merged cost (Erickson, Monma and Veinott 1987), so the joins may be
    any (zero, or barred) with no all-pairs metric. joins: index arrays (a, b, weight).
    Returns (best, before, split): the cost, the node before each on the way from the
    tree's root (n at the root), and the split of the set at the root."""
    a, b, w = joins
    groups = cost.shape[0]
    full = (1 << groups) - 1
    best = np.full((full + 1, n), np.inf)
    before = np.full((full + 1, n), n, dtype=np.int64)
    split = np.zeros((full + 1, n), dtype=np.int64)
    rows = np.concatenate([a, b, np.full(n, n)])
    cols = np.concatenate([b, a, np.arange(n)])
    weight = np.concatenate([w, w])

    def grow(whole: int, base: np.ndarray) -> None:
        graph = csr_matrix((np.concatenate([weight, base]), (rows, cols)), shape=(n + 1, n + 1))
        d, p = dijkstra(graph, directed=True, indices=n, return_predecessors=True)
        best[whole], before[whole] = d[:n], p[:n]

    for g in range(groups):
        grow(1 << g, cost[g])
    for wholes, halves, others in _splits(groups):
        for whole, half, other in zip(wholes, halves, others):
            merged = best[half] + best[other]
            pick = merged.argmin(axis=0)
            split[whole] = half[pick]
            grow(int(whole), merged[pick, np.arange(n)])
    return best, before, split


def _tree(before: np.ndarray, split: np.ndarray, whole: int, v: int, n: int) -> set:
    """The edges, as node pairs, of the tree the labels found for the group set `whole`
    reaching node v."""
    edges, todo = set(), [(whole, v)]
    while todo:
        whole, v = todo.pop()
        while before[whole, v] != n:
            u = int(before[whole, v])
            edges.add((min(u, v), max(u, v)))
            v = u
        if whole & (whole - 1):
            half = int(split[whole, v])
            todo += [(half, v), (whole ^ half, v)]
    return edges


def _steiner(graph: Graph, db: str, held: list[int], required: frozenset, barred: frozenset):
    """The cheapest tree joining the held tables with the joins in `required`, none in
    `barred`, and no leaf holding no part, as (edges, join cost), or None. The required
    joins cost nothing here and their tables count as one group. A required table with
    one required join that holds no part (the tip: at most one, by the order join children
    are made in) must go on: the tree is the branch from the tip, which cannot touch the
    other required tables, plus the rest, which cannot touch the tip, with the held tables
    split between them every way. The cheapest split never overlaps, since joining
    overlapping branches at the overlap would cost less."""
    nodes = graph.nodes[db]
    index = {t: i for i, t in enumerate(nodes)}
    n = len(nodes)
    a, b, w, pos = graph.joins(db)
    w = w.copy()
    w[[pos[e] for e in required]] = 0.0
    live = np.ones(len(w), dtype=bool)
    live[[pos[e] for e in barred]] = False
    degree: dict[int, int] = defaultdict(int)
    for x, y in required:
        degree[x] += 1
        degree[y] += 1
    tips = [t for t, d in degree.items() if d == 1 and t not in held]
    out = [t for t in held if t not in degree]

    def row(tables) -> np.ndarray:
        r = np.full(n, np.inf)
        r[[index[t] for t in tables]] = 0.0
        return r

    def without(tables):
        dead = np.isin(a, [index[t] for t in tables]) | np.isin(b, [index[t] for t in tables])
        keep = live & ~dead
        return a[keep], b[keep], w[keep]

    if not tips:
        cost = np.array([row([t]) for t in out] + ([row(degree)] if degree else []))
        best, before, split = _labels(without([]), n, cost)
        full = (1 << len(cost)) - 1
        v = int(best[full].argmin())
        if not math.isfinite(best[full, v]):
            return None
        edges = _tree(before, split, full, v, n)
    else:
        (tip,) = tips
        if not out:
            return None
        others = [t for t in degree if t != tip]
        branch_best, branch_before, branch_split = _labels(
            without(others), n, np.array([row([t]) for t in out]))
        rest_best, rest_before, rest_split = _labels(
            without([tip]), n, np.array([row(others)] + [row([t]) for t in out]))
        full = (1 << len(out)) - 1
        total, choice = math.inf, None
        for branch in range(1, full + 1):
            rest = ((full ^ branch) << 1) | 1  # the rest, with the required tables (bit 0)
            v = int(rest_best[rest].argmin())
            c = branch_best[branch, index[tip]] + rest_best[rest, v]
            if c < total:
                total, choice = c, (branch, rest, v)
        if choice is None:
            return None
        branch, rest, v = choice
        edges = (_tree(branch_before, branch_split, branch, index[tip], n)
                 | _tree(rest_before, rest_split, rest, v, n))
    pairs = {(nodes[i], nodes[j]) for i, j in edges} | set(required)
    return tuple(sorted(pairs)), sum(graph.weight(x, y) for x, y in pairs)


def _order(edges, required: frozenset, held: list[int]) -> list:
    """The joins of a found tree not yet required, in the order join children keep them:
    a depth-first walk from the tip of the required joins (the table with one required
    join holding no part), or from a held table, taking joins not yet required before
    required ones at each table. So the required joins of each child have at most one
    tip: the near table of the join it bars."""
    adj: dict[int, list[int]] = defaultdict(list)
    for x, y in edges:
        adj[x].append(y)
        adj[y].append(x)
    degree: dict[int, int] = defaultdict(int)
    for x, y in required:
        degree[x] += 1
        degree[y] += 1
    root = next((t for t, d in degree.items() if d == 1 and t not in held), held[0])
    order, seen = [], {root}

    def walk(t: int) -> None:
        for u in sorted(adj[t], key=lambda u: (min(t, u), max(t, u)) in required):
            if u not in seen:
                seen.add(u)
                if (min(t, u), max(t, u)) not in required:
                    order.append((min(t, u), max(t, u)))
                walk(u)

    walk(root)
    return order


def _untrapped(graph: Graph, db: str, per_part: list[dict[int, Holder]], leave: list[float], found: tuple):
    """The cheapest tree of the places in `found` with no trap (Graph.traps), as `_place`
    returns it: `found` itself when it has none, or when every tree of its places has one.
    The trees come cheapest first: keep the first i joins of one found and bar the i-th,
    so each other tree of these places is searched once (Lawler 1972)."""
    total, chosen, tables, edges, join = found
    held = sorted({h.table for h in chosen if h is not None})
    fixed = {j: h.table if h else None for j, h in enumerate(chosen)}
    heap, tie, solved = [(total, 0, frozenset(), frozenset(), found)], 1, 0
    while heap:
        cost, _, required, barred, tree = heapq.heappop(heap)
        if tree is None:
            solved += 1
            if solved > MAX_SOLVES:
                break
            tree = _place(graph, db, per_part, leave, fixed, frozenset(), required, barred)
            if tree is not None:
                heapq.heappush(heap, (tree[0], tie, required, barred, tree))
                tie += 1
            continue
        if not graph.traps(set(held), tree[3]):
            return tree
        joins = _order(tree[3], required, held) if tree[3] else []
        for i, edge in enumerate(joins):
            heapq.heappush(heap, (tree[0], tie, required | frozenset(joins[:i]), barred | {edge}, None))
            tie += 1
    return found


def candidates(probe: Probe, graph: Graph, stage, k: int = 50,
               graded: list[list[Holder]] | None = None, bits: float | None = None,
               drop: frozenset[int] = frozenset()) -> list[Candidate]:
    """The k cheapest interpretations over the whole lake, one per choice of places,
    cheapest first, and past k every one at most `bits` above the cheapest: the best of
    each database, then Lawler's partition (1972) of the rest below each one found: keep
    its first i parts where they are and move part i elsewhere. Each choice of places is
    joined once: by its cheapest tree with no trap (`_untrapped`), or when every tree has
    one, by its cheapest. In a database that declares no join key, every join is a guess
    from the data and most trees go through wrong links: its cheapest tree, with no search
    for one with no trap. `graded` gives each part's holders with judged costs,
    in place of `holders`. Every part is placed, except the parts in `drop`, which are left
    out.

    The search runs over tables: each part's options hold its cheapest holder per table,
    so two columns of one table never make two searches."""
    parts = len(stage.entities)
    if not parts:
        return []
    per_part: list[dict[int, Holder]] = []
    leave: list[float] = []
    for j in range(parts):
        best: dict[int, Holder] = {}
        for h in [] if j in drop else sorted(graded[j], key=tie_order) if graded else holders(probe, stage, j):
            best.setdefault(h.table, h)
        per_part.append(best)
        leave.append(0.0 if j in drop else math.inf)
    databases = sorted({graph.database[t] for one in per_part for t in one})
    heap: list = []
    tie = 0
    for db in databases:
        heapq.heappush(heap, (0.0, tie, db, (), frozenset(), None, False))
        tie += 1
    out: list[Candidate] = []
    kept: set = set()
    solved = 0

    def wanted(cost: float) -> bool:
        """Whether the search goes on below a part of the space whose cost so far is
        `cost`: one at least the k-th cheapest found and above the window holds nothing
        kept."""
        if len(out) < k:
            return True
        if bits is not None and cost <= min(c.cost for c in out) + bits + 1e-9:
            return True
        return cost < sorted(c.cost for c in out)[k - 1]

    while heap and wanted(heap[0][0]):
        cost, _, db, fixed, banned, found, joined = heapq.heappop(heap)
        if found is None:
            # a part of the space not yet solved: solve it, and queue it by its true cost
            solved += 1
            if solved > MAX_SOLVES:
                log.info("candidates: search cap reached with %d found", len(out))
                break
            found = _place(graph, db, per_part, leave, dict(fixed), banned)
            if found is not None:
                heapq.heappush(heap, (found[0], tie, db, fixed, banned, found, False))
                tie += 1
            continue
        total, chosen, tables, edges, join = found
        if not joined:
            free = [j for j in range(parts) if j not in dict(fixed)]
            for i, j in enumerate(free):
                place = chosen[j].table if chosen[j] else None
                child = fixed + tuple((f, chosen[f].table if chosen[f] else None) for f in free[:i])
                heapq.heappush(heap, (total, tie, db, child, banned | {(j, place)}, None, False))
                tie += 1
            other = _untrapped(graph, db, per_part, leave, found) if db in graph.keyed else found
            if other is not found:
                # a tree with no trap costs more: queued by its own cost
                heapq.heappush(heap, (other[0], tie, db, fixed, banned, other, True))
                tie += 1
                continue
        key = (db, tuple(h.table if h else None for h in chosen))
        if tables and key not in kept:
            kept.add(key)
            out.append(Candidate(db, tables, chosen, edges, total, total - join, join))
    out.sort(key=lambda c: c.cost)
    return [c for n, c in enumerate(out) if n < k or (bits is not None and c.cost <= out[0].cost + bits + 1e-9)]
