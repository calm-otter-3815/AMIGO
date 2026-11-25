"""The guided search: AMIGO's candidates as a tree, which the person walks from the top.

The tree is built once, from the candidates the automatic answer returns (`automatic`): at
most judge.MOST, each once per place in its own tables and per way to link its joins, and
the relaxed ones when none places every part. No search runs after an answer, and a
candidate past the cap is never reached.

The forks, from the top: which part to leave out (only when the relaxed candidates leave
out different parts), which database, which table holds each part, which column of that
table, and how the tables join (the join paths, the tables they go through and the way each
join links). A fork is made only where the candidates under it differ; when several parts
differ at the same level, the part whose options split the odds most evenly comes first.
An option weighs 2^-cost of its cheapest candidate, and the heaviest comes first. Two
candidates that give the same rows are still two interpretations: they are never merged.

The walk goes from the top. Picking one or several options goes into each of them in turn,
the heaviest first. "None of these" rules out the options shown and shows the next ones,
OPTIONS at a time; when every option of a fork is ruled out, so is the option that led to
it, one level up, and that fork is asked again with what is left. "Any of these" keeps
every candidate left under the fork, and "stop" every candidate left anywhere. The answers
are the whole state: `step` replays them from the top, so walking back is cutting the list.
A place the place judge said no to is not in the tree: the person corrects the judge when
reviewing the places, before the tree is built.
"""

import logging
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

from . import candidates as C
from . import clarify, interpret, judge, llm, solve
from .probe import Probe

log = logging.getLogger(__name__)

# options shown per fork, the heaviest; the rest wait behind "none of these"
OPTIONS = interpret.OPTIONS
# the levels of the tree from the top; table and column have a fork per part
LEVELS = ("leave", "database", "table", "column", "join")
# what each kind of fork is about, for the person and the wording call
ABOUT = {"leave": "which part of the question to leave out, since nothing joins with every part",
         "database": "which database", "join": "how the tables join"}


@dataclass(eq=False)
class Node:
    """A candidate (a leaf), or a fork over the candidates under it."""
    leaves: list[int]  # the candidates under it, by their place in Tree.found
    kind: str = "leaf"  # "leaf", or one of LEVELS
    part: int | None = None  # the part a table or column fork is about
    options: list["Option"] = field(default_factory=list)  # heaviest first


@dataclass(eq=False)
class Option:
    node: Node  # what picking it goes into
    best: C.Candidate  # its cheapest candidate
    leaves: list[int]  # every candidate under it
    n: int = 0  # its number in its fork
    share: float = 0.0  # its odds against the other options shown


@dataclass
class Tree:
    found: list[C.Candidate]  # the candidates, cheapest first
    root: Node | None  # None when there is no candidate


@dataclass
class Fork:
    """A fork as asked: the options shown, heaviest first, and how many more wait behind
    none of these."""
    node: Node
    options: list[Option]
    more: int = 0

    @property
    def kind(self) -> str:
        return self.node.kind

    @property
    def part(self) -> int | None:
        return self.node.part


@dataclass
class Answer:
    kind: str  # "pick", "any", "none" or "stop"
    picked: frozenset = frozenset()  # with "pick": the numbers of the options picked
    text: str = ""  # what they answered, as shown in the trail


@dataclass
class Step:
    fork: Fork | None  # the next fork to ask, or None: the walk is over
    leaves: list[C.Candidate] = field(default_factory=list)  # once over, the candidates kept, cheapest first


def automatic(probe: Probe, graph: C.Graph, stage, question: str, places: list[list[C.Holder]],
              log_path: Path) -> list[C.Candidate]:
    """The candidates of the automatic answer (the paper's AMIGO) over the places kept: the
    judge.MOST cheapest, the relaxed ones when none places every part, each once per place
    in its own tables (judge.split) and per way to link its joins that the join judge keeps
    (judge.chosen, one LLM call; when it fails, every way)."""
    found = C.candidates(probe, graph, stage, judge.MOST, graded=places)
    if not found:
        found = judge.relaxed(probe, graph, stage, places, judge.MOST, None)
    found = judge.split(found, places)
    try:
        return judge.chosen(probe, graph, question, stage, found, {}, log_path)[0]
    except llm.ModelError as err:
        log.warning("guide: the join judge failed, every way kept: %s", err)
        return judge.ways(probe, graph, found, {})[:judge.MOST]


def _spread(costs: list[float]) -> float:
    """How evenly options of these costs split the odds: the entropy of their shares, in bits."""
    weights = [2.0 ** (min(costs) - c) for c in costs]
    total = sum(weights)
    return -sum(w / total * math.log2(w / total) for w in weights if w > 0)


def build(found: list[C.Candidate]) -> Tree:
    """The tree over the candidates."""
    found = sorted(found, key=lambda one: one.cost)
    parts = range(len(found[0].holders)) if found else ()

    def value(kind: str, j: int | None, i: int):
        one = found[i]
        if kind == "leave":
            return one.left_out
        if kind == "database":
            return one.database
        if kind == "join":
            ways = one.extra.get("ways", {})
            return one.tables, one.edges, tuple((e, *ways[e]) for e in one.edges if e in ways)
        h = one.holders[j]
        return None if h is None else h.table if kind == "table" else h.column

    def grow(leaves: list[int]) -> Node:
        if len(leaves) == 1:
            return Node(leaves)
        forks = []
        for kind in LEVELS:
            for j in parts if kind in ("table", "column") else (None,):
                groups: dict = {}
                for i in leaves:
                    groups.setdefault(value(kind, j, i), []).append(i)
                if len(groups) > 1:
                    forks.append((kind, j, list(groups.values())))  # heaviest first: leaves come cheapest first
            if forks:
                break
        else:
            # candidates alike in every way the levels look at: each is its own option
            forks = [("join", None, [[i] for i in leaves])]
        kind, j, groups = max(forks, key=lambda f: (_spread([found[g[0]].cost for g in f[2]]), -(f[1] or 0)))
        return Node(leaves, kind, j, [Option(grow(g), found[g[0]], g, n) for n, g in enumerate(groups)])

    return Tree(found, grow(list(range(len(found)))) if found else None)


def size(tree: Tree) -> dict:
    """The tree's candidates, its forks, and the most forks on one path from the top."""
    out = {"leaves": len(tree.found), "forks": 0, "depth": 0}

    def down(node: Node, depth: int) -> None:
        if node.kind == "leaf":
            out["depth"] = max(out["depth"], depth)
            return
        out["forks"] += 1
        for option in node.options:
            down(option.node, depth + 1)

    if tree.root is not None:
        down(tree.root, 0)
    return out


def _fork(node: Node, shown: list[int], more: int) -> Fork:
    options = [node.options[n] for n in shown]
    weights = [2.0 ** (options[0].best.cost - o.best.cost) for o in options]
    return Fork(node, [replace(o, share=w / sum(weights)) for o, w in zip(options, weights)], more)


def step(tree: Tree, answers: list[Answer]) -> Step:
    """The next fork to ask after these answers, or, once the walk is over, the candidates
    kept (none when every option at the top was ruled out)."""
    if tree.root is None:
        return Step(None)
    out: dict = {}  # fork -> the numbers of its options ruled out
    going: set = set()  # the (fork, option number) picked and not ruled out
    up: dict = {}  # node -> the (fork, option number) it was reached by
    todo, kept = [tree.root], set()
    said = iter(answers)

    def left(fork: Node) -> list[int]:
        return [n for n in range(len(fork.options)) if n not in out.get(fork, ())]

    def under(node: Node) -> set[int]:
        return set(node.leaves) if node.kind == "leaf" else {i for n in left(node) for i in node.options[n].leaves}

    def enter(fork: Node, numbers: list[int]) -> None:
        for n in sorted(numbers, reverse=True):  # the heaviest is walked first
            going.add((fork, n))
            up[fork.options[n].node] = fork, n
            todo.append(fork.options[n].node)

    def ruled_out(node: Node) -> None:
        """Every option of `node` is ruled out: so is the option that led to it, and its fork
        is asked again when nothing it picked is left."""
        if node not in up:
            return  # the top: nothing is left
        fork, n = up[node]
        going.discard((fork, n))
        out.setdefault(fork, set()).add(n)
        if not any((fork, m) in going for m in left(fork)):
            todo.append(fork)

    while todo:
        node = todo.pop()
        if node.kind == "leaf":
            kept |= set(node.leaves)
            continue
        rest = left(node)
        if not rest:
            ruled_out(node)
            continue
        shown = rest[:OPTIONS]
        answer = next(said, None)
        if answer is None:
            return Step(_fork(node, shown, len(rest) - len(shown)))
        if answer.kind == "pick":
            if not answer.picked or not answer.picked <= set(shown):
                raise ValueError(f"pick among the options shown {shown}, not {sorted(answer.picked)}")
            enter(node, list(answer.picked))
        elif answer.kind == "none":
            out.setdefault(node, set()).update(shown)
            todo.append(node)
        elif answer.kind == "any":
            kept |= under(node)
        elif answer.kind == "stop":
            kept |= under(node).union(*map(under, todo))
            todo.clear()
        else:
            raise ValueError(f"no answer {answer.kind!r}")
    return Step(None, [tree.found[i] for i in sorted(kept)])


def _tree(edges) -> list[tuple[int, int]]:
    """The joins in an order where each one adds one table to those already joined."""
    edges, order = list(edges), []
    if not edges:
        return order
    joined = {edges[0][0]}
    while edges:
        a, b = next(e for e in edges if e[0] in joined or e[1] in joined)
        edges.remove((a, b))
        order.append((a, b) if a in joined else (b, a))
        joined |= {a, b}
    return order


def peek_query(probe: Probe, graph: C.Graph, stage, one: C.Candidate) -> tuple[str, list[str]]:
    """The rows an interpretation reads, for the person to look at, and their headers: per
    placed part its column."""
    shown, names = [], []
    for j, h in enumerate(one.holders):
        if h is None:
            continue
        shown.append(solve._column(probe, h.column))
        names.append(f"{stage.entities[j].attribute} · {probe.path('column', h.column)}")
    return f"SELECT DISTINCT {', '.join(shown)} {_body(probe, graph, stage, one)}", names


def _body(probe: Probe, graph: C.Graph, stage, one: C.Candidate) -> str:
    """The FROM, JOIN and WHERE of an interpretation's rows: its joins, each by the way it
    links (or its best link), and the stored values its parts name."""
    ways = one.extra.get("ways", {})
    query = f"FROM {solve._from(probe, min(one.tables))}"
    for a, b in _tree(one.edges):
        how, links = ways.get((a, b)) or ways.get((b, a)) or (
            "one", (max(graph.ways[tuple(sorted((a, b)))], key=lambda w: w.quality),))
        ons = ["(" + " AND ".join(solve._on(probe, x, y) for x, y in join.links) + ")" for join in links]
        on = (" OR " if how == "any" else " AND ").join(ons) or "1"
        query += f" JOIN {solve._from(probe, b)} ON {on}"
    where = []
    for j, h in enumerate(one.holders):
        if h is None or stage.entities[j].literal is None:
            continue
        b = interpret._binding(probe, stage, j, h)
        for path, value in [(b.column, b.value), *b.also]:
            if value is not None:
                where.append(f"{solve._column(probe, probe.find(path)[1])} = '{value.replace(chr(39), chr(39) * 2)}'")
    if where:
        query += " WHERE " + " AND ".join(where)
    return query


def _links(probe: Probe, graph: C.Graph, one: C.Candidate) -> list[str]:
    """How an interpretation joins, one line per join: the way it links, else its best link;
    a join on any one of its links says "or", one on all of them "and"."""
    ways, out = one.extra.get("ways", {}), []
    for a, b in one.edges:
        how, joins = ways.get((a, b)) or ("one", [max(graph.ways[tuple(sorted((a, b)))], key=lambda w: w.quality)])
        pairs = [f"{probe.path('column', x)} = {probe.path('column', y)}" for join in joins for x, y in join.links]
        out += [(" or " if how == "any" else " and ").join(pairs)] if pairs else []
    return out


def about(stage, fork: Fork) -> str:
    return ABOUT[fork.kind] if fork.part is None else stage.entities[fork.part].attribute


def nothing(lake: str, stage, parts: list[int]) -> str:
    """What is said when no part has a place kept."""
    said = ", ".join(f'"{stage.entities[j].attribute}"' for j in parts)
    return f"I can't find anything in {lake} that looks like {said}. Try rephrasing your question, or pick another lake."


def axis(probe: Probe, graph: C.Graph, stage, fork: Fork) -> clarify.Axis:
    """The fork as the clarify step words it (clarify.phrase): per option, the place of its
    cheapest candidate and the value it filters on, what the catalog says, and the tables
    and joins it goes through when the options differ in them."""
    options = []
    for n, o in enumerate(fork.options, start=1):
        best, name = o.best, f"o{n}"
        if fork.kind == "database":
            tables = sorted({probe.tables[t]["name"] for t in best.tables})
            option = clarify.Option(name, best.database, None, "every part of the question has a place in it",
                                    "its tables include " + ", ".join(tables), kind="database")
        elif fork.kind == "leave":
            option = clarify.Option(name, ", ".join(stage.entities[j].attribute for j in best.left_out), None,
                                    "the rest of the question joins without it", kind="leave")
        elif fork.kind == "join":
            option = clarify.Option(name, ", ".join(sorted(probe.tables[t]["name"] for t in best.tables)), None, "",
                                    kind="join")
        else:
            h = best.holders[fork.part]
            if fork.kind == "table":
                # a table fork is a choice of tables, whichever column of it is likeliest
                path = probe.path("table", h.table)
                option = clarify.Option(name, path, None, h.why, clarify._described(probe, path), kind="table")
            else:
                b = interpret._binding(probe, stage, fork.part, h)
                option = clarify.Option(name, b.column, b.value, h.why, clarify._sampled(probe, b.column), also=b.also)
        option.keeps = [name]
        options.append(option)
    ways = [(sorted(probe.path("table", t) for t in o.best.tables), _links(probe, graph, o.best)) for o in fork.options]
    if fork.kind == "join" or len({tuple(tables) for tables, _ in ways}) > 1:
        for option, (tables, links) in zip(options, ways):
            option.through = ("tables " + ", ".join(tables)
                              + ("; joins " + ", ".join(links) if links else ""))
    return clarify.Axis(f"{fork.kind} {fork.part}", about(stage, fork), options)
