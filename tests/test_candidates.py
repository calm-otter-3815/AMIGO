import itertools
from collections import defaultdict
import math
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from amigo import candidates as C
from amigo import judge


def _tree(dist: np.ndarray, terminals: set[int]) -> float:
    """The cheapest tree joining the terminals in a metric: the cheapest spanning tree over
    the terminals and any other nodes (brute force)."""
    if len(terminals) <= 1:
        return 0.0
    others = [v for v in range(len(dist)) if v not in terminals]
    best = math.inf
    for size in range(len(others) + 1):
        for extra in itertools.combinations(others, size):
            nodes = sorted(terminals | set(extra))
            inside, total = {nodes[0]}, 0.0
            while len(inside) < len(nodes):
                d, v = min((dist[a, b], b) for a in inside for b in nodes if b not in inside)
                inside.add(v)
                total += d
            best = min(best, total)
    return best


class TestGroupSteiner(unittest.TestCase):
    def test_matches_brute_force(self):
        rng = np.random.default_rng(7)
        for _ in range(40):
            n, groups = int(rng.integers(2, 6)), int(rng.integers(1, 4))
            # hops on a random connected graph, one per join
            adj = {(i, i + 1) for i in range(n - 1)} | {
                (i, j) for i in range(n) for j in range(i + 2, n) if rng.random() < 0.3}
            hops = np.full((n, n), np.inf)
            np.fill_diagonal(hops, 0)
            for i, j in adj:
                hops[i, j] = hops[j, i] = 1
            for m in range(n):
                hops = np.minimum(hops, hops[:, m:m + 1] + hops[m:m + 1, :])
            dist = hops
            step = np.tile(np.arange(n), (n, 1))
            for a in range(n):
                for b in range(n):
                    if a != b:
                        step[a, b] = next(v for v in range(n) if (min(a, v), max(a, v)) in adj
                                          and hops[v, b] == hops[a, b] - 1)
            cost = np.where(rng.random((groups, n)) < 0.4, np.inf, rng.integers(0, 5, (groups, n)))
            unplaced = rng.integers(2, 8, groups).astype(float)
            total, place, edges = C._group_steiner(dist, step, cost, unplaced)
            expected = min(
                sum(unplaced[g] if v < 0 else cost[g, v] for g, v in enumerate(at))
                + _tree(dist, {v for v in at if v >= 0})
                for at in itertools.product(range(-1, n), repeat=groups)
            )
            self.assertAlmostEqual(total, expected)
            # the tree it returns costs what it says
            kept = sum(unplaced[g] if v < 0 else cost[g, v] for g, v in enumerate(place))
            self.assertAlmostEqual(kept + len(edges), total)


class TestWindow(unittest.TestCase):
    def test_every_candidate_within_the_window(self):
        # tables 1 - 2 - 3 - 4 in a row; two parts with a few places each
        graph = object.__new__(C.Graph)
        graph.adj = {1: {2}, 2: {1, 3}, 3: {2, 4}, 4: {3}}
        graph.ways, graph.references, graph.into = {}, {}, set()
        graph.database = {t: "d" for t in graph.adj}
        graph.keyed = {"d"}
        graph.nodes = {"d": [1, 2, 3, 4]}
        graph._metrics = {}
        places = [[C.Holder(0, 1, 1, 0.0, ""), C.Holder(0, 3, 3, 1.0, ""), C.Holder(0, 4, 4, 3.0, "")],
                  [C.Holder(1, 2, 2, 0.0, ""), C.Holder(1, 4, 4, 2.0, ""), C.Holder(1, 1, 1, 4.0, "")]]
        stage = SimpleNamespace(entities=[None, None])
        key = lambda found: [(c.tables, c.holders, c.cost) for c in found]
        every = C.candidates(None, graph, stage, 1000, graded=places)
        for bits in (0.0, 2.0, 5.0):
            want = [c for c in every if c.cost <= every[0].cost + bits]
            self.assertEqual(key(C.candidates(None, graph, stage, 1, graded=places, bits=bits)), key(want))
        # the k cheapest stay when the window holds fewer
        self.assertEqual(key(C.candidates(None, graph, stage, 3, graded=places, bits=0.0)), key(every[:3]))


class TestJoinPaths(unittest.TestCase):
    def test_places_and_join_paths_in_one_exact_order(self):
        # a ring 1-2-3-4-5-1 with a chord 2-5: several join paths between most tables
        graph = object.__new__(C.Graph)
        pairs = [(1, 2), (2, 3), (3, 4), (4, 5), (1, 5), (2, 5)]
        graph.adj = defaultdict(set)
        for a, b in pairs:
            graph.adj[a].add(b)
            graph.adj[b].add(a)
        graph.ways, graph.references, graph.into = {}, {}, set()
        graph.database = {t: "d" for t in graph.adj}
        graph.keyed = {"d"}
        graph.nodes = {"d": [1, 2, 3, 4, 5]}
        graph._metrics = {}
        places = [[C.Holder(0, 1, 1, 0.0, ""), C.Holder(0, 3, 3, 1.0, "")],
                  [C.Holder(1, 4, 4, 0.0, ""), C.Holder(1, 2, 2, 2.0, "")]]
        stage = SimpleNamespace(entities=[None, None])
        # brute force: every place per part and every tree whose leaves all hold a part
        want = set()
        for h1, h2 in itertools.product(*places):
            held = {h1.table, h2.table}
            for size in range(len(pairs) + 1):
                for edges in itertools.combinations(pairs, size):
                    nodes = held | {t for e in edges for t in e}
                    degree = defaultdict(int)
                    for a, b in edges:
                        degree[a] += 1
                        degree[b] += 1
                    seen, todo = set(), [h1.table]
                    while todo:
                        t = todo.pop()
                        if t not in seen:
                            seen.add(t)
                            todo += [b if a == t else a for a, b in edges if t in (a, b)]
                    if (seen == nodes and len(edges) == len(nodes) - 1
                            and all(degree[t] > 1 or t in held for t in nodes)):
                        cost = h1.cost + h2.cost + sum(graph.weight(a, b) for a, b in edges)
                        want.add((round(cost, 9), tuple(sorted(edges)), (h1.table, h2.table)))
        # each choice of places once, by its cheapest tree (no trap here)
        cheapest = {}
        for cost, edges, held in sorted(want):
            cheapest.setdefault(held, cost)
        got = C.candidates(None, graph, stage, 1000, graded=places)
        self.assertEqual({tuple(h.table for h in c.holders): round(c.cost, 9) for c in got}, cheapest)
        self.assertEqual(len(got), len(cheapest))
        self.assertEqual([c.cost for c in got], sorted(c.cost for c in got))

    def test_the_cheapest_tree_with_no_trap(self):
        # client 1, disp 2, account 3, district 4, loan 5 (one per account): client and
        # account both point into district, disp points into both. Through district is
        # cheaper, but relates a client to an account only by their district: the join
        # through disp is kept.
        graph = object.__new__(C.Graph)
        graph.adj = defaultdict(set)
        for a, b in [(1, 2), (2, 3), (1, 4), (3, 4), (3, 5)]:
            graph.adj[a].add(b)
            graph.adj[b].add(a)
        for t in (6, 7, 8):  # more links on disp, so its joins cost more
            graph.adj[2].add(t)
            graph.adj[t].add(2)
        graph.ways, graph.references = {}, {}
        graph.into = {(1, 4), (3, 4), (2, 1), (2, 3)}
        graph.database = {t: "d" for t in graph.adj}
        graph.keyed = {"d"}
        graph.nodes = {"d": sorted(graph.adj)}
        graph._metrics = {}
        places = [[C.Holder(0, 1, 1, 0.0, "")], [C.Holder(1, 5, 5, 0.0, "")]]
        stage = SimpleNamespace(entities=[None, None])
        trap = graph.weight(1, 4) + graph.weight(3, 4)
        self.assertLess(trap, graph.weight(1, 2) + graph.weight(2, 3))
        got = C.candidates(None, graph, stage, 50, graded=places)
        self.assertEqual([c.edges for c in got], [((1, 2), (2, 3), (3, 5))])
        # a database that declares no join key: its cheapest tree, with no search past it
        graph.keyed, graph._metrics = set(), {}
        got = C.candidates(None, graph, stage, 50, graded=places)
        self.assertEqual([c.edges for c in got], [((1, 4), (3, 4), (3, 5))])
        graph.keyed = {"d"}
        # many loans per account: through disp has a trap too, so the cheapest tree stays
        graph.into.add((5, 3))
        got = C.candidates(None, graph, stage, 50, graded=places)
        self.assertEqual([c.edges for c in got], [((1, 4), (3, 4), (3, 5))])


class TestRelaxed(unittest.TestCase):
    def test_fewest_parts_left_out_and_marked(self):
        # tables 1 - 2 linked, table 3 alone
        graph = object.__new__(C.Graph)
        graph.adj = defaultdict(set, {1: {2}, 2: {1}, 3: set()})
        graph.ways, graph.references, graph.into = {}, {}, set()
        graph.database = {t: "d" for t in graph.adj}
        graph.keyed = {"d"}
        graph.nodes = {"d": [1, 2, 3]}
        graph._metrics = {}
        stage = SimpleNamespace(entities=[None, None, None])
        # part 2 has no place: it alone is left out
        places = [[C.Holder(0, 1, 1, 0.0, "")], [C.Holder(1, 2, 2, 0.0, "")], []]
        found = judge.relaxed(None, graph, stage, places, 50, None)
        self.assertTrue(found)
        self.assertTrue(all(c.left_out == (2,) for c in found))
        # every part has a place but table 3 joins none: one part more is left out
        places[2] = [C.Holder(2, 3, 3, 0.0, "")]
        self.assertEqual(C.candidates(None, graph, stage, 50, graded=places), [])
        found = judge.relaxed(None, graph, stage, places, 50, None)
        self.assertEqual({c.left_out for c in found}, {(2,)})


class TestKept(unittest.TestCase):
    def test_all_judged_no_are_kept_and_marked(self):
        one, two = (C.Candidate("d", frozenset({t}), (), (), float(t)) for t in (1, 2))
        self.assertEqual(judge.kept([one, two], [False, True]), [two])
        self.assertEqual([c.extra for c in judge.kept([one, two], [False, False])], [{"judged_no": True}] * 2)
        self.assertEqual(one.extra, {})

    def test_reply_takes_only_the_asked_numbers(self):
        reply = judge.numbered("Kept", ["1", "3"], str)
        self.assertEqual(reply.model_json_schema()["required"], ["1", "3"])
        self.assertEqual(reply.model_validate_json('{"1": ["a"], "3": []}').model_dump(), {"1": ["a"], "3": []})
        with self.assertRaises(ValueError):
            reply.model_validate_json('{"": ["a"], "3": []}')


class TestTraps(unittest.TestCase):
    def test_join_table_entered_twice_from_outside(self):
        # persons (1) and addresses (2) both point into countries (3)
        graph = object.__new__(C.Graph)
        graph.into = {(1, 3), (2, 3)}
        self.assertEqual(graph.traps({1, 2}, [(1, 3), (3, 2)]), 1)
        # a part held in countries makes it more than a join table
        self.assertEqual(graph.traps({1, 2, 3}, [(1, 3), (3, 2)]), 0)
        # entered once is a plain join
        self.assertEqual(graph.traps({1}, [(1, 3)]), 0)
        # a table pointing out to both (enrolments of persons in courses) is no trap
        graph.into = {(3, 1), (3, 2)}
        self.assertEqual(graph.traps({1, 2}, [(1, 3), (3, 2)]), 0)


class TestGraded(unittest.TestCase):
    def test_chunks_keep_each_prompt_within_the_limit(self):
        render = lambda run: "x" * (300 + 30 * sum(run))  # 100 tokens, plus 10 per unit
        with mock.patch.object(judge.config, "PROMPT_TOKENS", 200):
            self.assertEqual(judge.chunks([1, 2, 3, 4, 5], render), [[1, 2, 3, 4], [5]])
            # one item too long alone still goes, alone
            self.assertEqual(judge.chunks([1, 20, 1], render), [[1], [20], [1]])
            self.assertEqual(judge.chunks([1, 2], render), [[1, 2]])

    def test_split_keeps_each_column_of_a_table(self):
        city, mail, far = C.Holder(0, 1, 11, 1.0, ""), C.Holder(0, 1, 12, 1.2, ""), C.Holder(0, 1, 13, 9.0, "")
        found = [C.Candidate("db", frozenset({1}), (city,), (), 1.0, 1.0),
                 C.Candidate("db", frozenset({2}), (C.Holder(0, 2, 21, 2.0, ""),), (), 2.0, 2.0)]
        out = judge.split(found, [[city, mail, far]])
        self.assertEqual([(c.holders[0].column, c.cost) for c in out], [(11, 1.0), (12, 1.2), (21, 2.0)])

    def test_split_makes_only_the_cheapest(self):
        # 3 parts, 4 columns each in one table: 64 copies, the 5 cheapest kept
        places = [[C.Holder(0, 1, 10 * j + n, 1.0 + n * (0.37, 0.53, 0.91)[j], "") for n in range(4)]
                  for j in range(3)]
        first = tuple(mine[0] for mine in places)
        cost = sum(h.cost for h in first)
        far = (C.Holder(0, 2, 99, 50.0, ""),) * 3  # a costlier interpretation sets a high limit
        found = [C.Candidate("db", frozenset({1}), first, (), cost, cost),
                 C.Candidate("db", frozenset({2}), far, (), 150.0, 150.0)]
        every = sorted(itertools.product(*places), key=lambda hs: sum(h.cost for h in hs))
        with mock.patch.object(judge, "MOST", 5):
            out = judge.split(found, places)
        self.assertEqual([c.holders for c in out], every[:5])


if __name__ == "__main__":
    unittest.main()
