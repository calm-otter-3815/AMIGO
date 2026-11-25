"""AMIGO for one question: its interpretations, and the questions that tell them apart.

The interpretations come from the search and the judge (candidates.py, judge.py), each
with a cost in bits. The answer is every interpretation the judge says yes to, best
first; with a window (WITHIN, config.WINDOW), only those at most WITHIN bits above the best. A person then picks the one they mean, reading the answer best first, and
after none of these the next candidates. Or a person may be asked where one part of the
question sits: the part whose answer tells the most about the tables returned (the mutual information of answer
and table set, the candidates weighed by their odds), never the same part twice, at most
BUDGET times, and only while some answer would change the tables returned. An answer
reprices the interpretations that disagree with it rather than dropping them.
"""

import math
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from . import bundle, candidates, config, judge, solve
from .pick import PickedColumn
from .probe import Probe

# the answer window in bits, None for none (config.WINDOW)
WITHIN = config.WINDOW
# places shown per question, then "none of these"
OPTIONS = 6
# questions asked at most
BUDGET = 3
NONE = "none"
# an answer is evidence, not a filter: people pick the wrong option now and then, so an
# interpretation that disagrees with an answer costs ANSWER bits more instead of going,
# and a later answer can bring it back (noisy twenty questions: Horstein 1963, Nowak 2009,
# Jedynak et al. 2012).
# Assumed: a person is right 9 times in 10, and a slip lands on any one of the other
# options (OPTIONS places and none of these): odds 0.9 to 0.1 / OPTIONS, some 5.8 bits
ANSWER = math.log2(0.9 / (0.1 / OPTIONS))


def run(probe: Probe, question: str, log_path: Path):
    """The question's parts (one LLM call) and its interpretations, cheapest first (two
    judge calls). Each one places every part, or when none can, leaves out the fewest."""
    graph = candidates.Graph(probe)
    stage = bundle.stage1(probe, question, log_path)
    found, *_ = judge.interpret(probe, graph, stage, question, log_path, WITHIN)
    return stage, found


def relaxed(probe: Probe, stage, question: str, log_path: Path) -> list[tuple[int, list]]:
    """For a person who asks for them: per part, the interpretations that leave that part
    alone out, cheapest first; parts whose leaving out gives none are skipped. The place
    grades come from the cache, so only the whole grades are asked again."""
    graph = candidates.Graph(probe)
    out = []
    for j in range(len(stage.entities) if len(stage.entities) > 1 else 0):
        found, *_ = judge.interpret(probe, graph, stage, question, log_path, WITHIN, drop=frozenset({j}))
        if found:
            out.append((j, found))
    return out


def _binding(probe: Probe, stage, j: int, h) -> solve.Binding:
    """Part j where it is placed, with the stored value it names when one is stored whole
    in that column or split over that column's row (County "Alameda" and StatusType
    "Merged"), so the SQL step filters on it; else no value, and the SQL step reads the
    question."""
    name = f"E{j + 1}"
    path = probe.path("column", h.column)
    found, _ = solve._checked(probe, name, stage.entities[j], PickedColumn(column=path, reason=h.why))
    # one value only, matched whole (a value matched in part is never used unseen)
    if len(found) != 1 or found[0].value is None or (found[0].reason != h.why and not found[0].also):
        return solve.Binding(name, path, h.why, None)
    pairs = [(found[0].column, found[0].value), *found[0].also]
    value = dict(pairs)[path]
    return solve.Binding(name, path, h.why, value, [p for p in pairs if p[0] != path])


def _card(probe: Probe, graph: candidates.Graph, stage, one, n: int, best: float) -> solve.Interpretation:
    """One interpretation in the shape the page and the SQL step read: a binding per placed
    part, its tables, the columns of the best link of each join, and a note with its odds
    and whether it is relaxed or judged no as a whole."""
    bindings = [_binding(probe, stage, j, h) for j, h in enumerate(one.holders) if h is not None]
    joins, either = [], []
    for a, b in one.edges:
        ways = graph.ways.get((a, b))
        way = one.extra.get("ways", {}).get((a, b))
        if way and way[1]:
            # the way this join was chosen to link (judge.ways)
            pairs = [(probe.path("column", x), probe.path("column", y)) for join in way[1] for x, y in join.links]
            joins += pairs
            if way[0] == "any" and len(way[1]) > 1:
                either.append(pairs)
        elif ways:
            joins += [(probe.path("column", x), probe.path("column", y))
                      for x, y in max(ways, key=lambda w: w.quality).links]
    notes = ["the best" if n == 1 else f"1 to {2.0 ** (one.cost - best):.1f} against the best"]
    if one.left_out:
        notes.append("relaxed: leaves out " + ", ".join(f'"{stage.entities[j].attribute}"' for j in one.left_out))
    if one.extra.get("judged_no"):
        notes.append("judged no as a whole, shown since every interpretation was")
    return solve.Interpretation(f"I{n}", bindings, sorted(probe.path("table", t) for t in one.tables),
                                joins=joins, either=either, note="; ".join(notes), left_out=[f"E{j + 1}" for j in one.left_out])


def cards(probe: Probe, graph: candidates.Graph, stage, question: str, log_path: Path) -> list[solve.Interpretation]:
    """The question's interpretations as the page shows them, best first; none when the
    lake holds none, even leaving out parts."""
    return judged(probe, graph, stage, question, log_path)[0]


def judged(probe: Probe, graph: candidates.Graph, stage, question: str, log_path: Path,
           keep: list[set | None] | None = None) -> tuple[list[solve.Interpretation], list, list[dict]]:
    """The cards, and the places each part was shown with the judge's yes or no on each, or
    the person's own choice where `keep` names one (judge.interpret)."""
    found, shown, grades, *_ = judge.interpret(probe, graph, stage, question, log_path, WITHIN, keep=keep)
    cards = [_card(probe, graph, stage, one, n, found[0].cost) for n, one in enumerate(found, start=1)]
    return cards, shown, grades


def within(found: list, bits: float | None = WITHIN) -> list:
    if bits is None:
        return found
    # 1e-9: equal costs summed in another order differ in the last digits
    return [one for one in found if one.cost <= found[0].cost + bits + 1e-9] if found else []


def answer_of(one, j: int, options: list) -> tuple | str:
    """Which option an interpretation takes for part j: its place, or none of these."""
    h = one.holders[j]
    key = None if h is None else (h.table, h.column)
    return key if key in options else NONE


def _entropy(labels: list, weights: list[float]) -> float:
    mass = defaultdict(float)
    for label, w in zip(labels, weights):
        mass[label] += w
    total = sum(mass.values())
    return -sum(m / total * math.log2(m / total) for m in mass.values() if m > 0)


def questions(found: list, bits: float = WITHIN, asked: set = frozenset(),
              update=None) -> list[tuple[float, int, list]]:
    """Every question worth asking, in part order: (information gain in bits, the part,
    the places shown). A question is worth asking when some answer to it would change the
    tables returned once `update` (answered, by default) applies it; a part `asked` about
    already is not asked again."""
    update = update or answered
    weights = [2.0 ** (found[0].cost - one.cost) for one in found]
    now = {t for one in within(found, bits) for t in one.tables}
    tables = [one.tables for one in found]
    out = []
    for j in range(len(found[0].holders)):
        if j in asked:
            continue
        mass = defaultdict(float)
        for one, w in zip(found, weights):
            if one.holders[j] is not None:
                mass[(one.holders[j].table, one.holders[j].column)] += w
        options = sorted(mass, key=lambda k: (-mass[k], k[0], k[1]))[:OPTIONS]
        answers = [answer_of(one, j, options) for one in found]
        changes = any(
            {t for one in within(update(found, j, options, {answer}), bits) for t in one.tables} != now
            for answer in set(answers)
        )
        if not changes:
            continue
        gain = _entropy(answers, weights) + _entropy(tables, weights) - _entropy(list(zip(answers, tables)), weights)
        if gain > 1e-9:
            out.append((gain, j, options))
    return out


def question(found: list, bits: float = WITHIN, asked: set = frozenset()) -> tuple[int, list] | None:
    """The part to ask about and the places shown: the most information gain; None when no
    answer would change the tables returned."""
    worth = questions(found, bits, asked) if found else []
    if not worth:
        return None
    _, j, options = max(worth, key=lambda q: q[0])
    return j, options


def answered(found: list, j: int, options: list, ticked: set) -> list:
    """The interpretations priced by the person's answer, cheapest first: one that disagrees
    with it costs ANSWER bits more."""
    priced = [one if answer_of(one, j, options) in ticked else replace(one, cost=one.cost + ANSWER)
              for one in found]
    return sorted(priced, key=lambda one: one.cost)


def _place(probe: Probe, key: tuple) -> str:
    return probe.path("column", key[1])


def show(probe: Probe, stage, found: list, bits: float = WITHIN, upto: int | None = None) -> str:
    """The answer: each interpretation within `bits` of the best (or the first `upto`), with
    its odds against the best, its tables and the place of each part."""
    lines = []
    kept = within(found, bits) if upto is None else found[:upto]
    for n, one in enumerate(kept, start=1):
        odds = f"1 to {2.0 ** (one.cost - kept[0].cost):.1f} against the best" if n > 1 else "the best"
        relaxed = (" [relaxed: leaves out " + ", ".join(f'"{stage.entities[j].attribute}"' for j in one.left_out)
                   + "]") if one.left_out else ""
        relaxed += " [judged no as a whole]" if one.extra.get("judged_no") else ""
        lines.append(f"{n}. {one.cost:.2f} bits ({odds}){relaxed}: "
                     + ", ".join(sorted(probe.path("table", t) for t in one.tables)))
        for entity, h in zip(stage.entities, one.holders):
            where = _place(probe, (h.table, h.column)) if h is not None else "nowhere"
            lines.append(f"     {entity.attribute}: {where}")
    return "\n".join(lines) if lines else "No interpretation found."


def wording(probe: Probe, stage, j: int, options: list) -> str:
    """The question to the person, as shown: the part, its places numbered, none of these."""
    lines = [f'Where is "{stage.entities[j].attribute}"?']
    lines += [f"  {n}. {_place(probe, key)}" for n, key in enumerate(options, start=1)]
    lines.append("  0. none of these")
    return "\n".join(lines)


def pick(probe: Probe, stage, found: list, reply, bits: float = WITHIN) -> list:
    """The person picks the interpretation they mean from the answer, read best first:
    `reply(prompt)` returns its number, 0 for none of these (the list then grows by the next
    OPTIONS candidates), or nothing to keep the answer. The one picked, alone, or the
    candidates as they were. On BIRD dev, a simulated person picking reached the F1 of
    three questions (ask) with none asked; after none of these, reading on found theirs
    more often than questions did for the same reading."""
    size, prompt = len(within(found, bits)), ""
    while size:
        line = reply(prompt + "Which one do you mean? Its number, 0 for none of these, Enter to keep them all\n> ").strip()
        if not line.isdigit() or int(line) > size:
            return found
        if int(line):
            return [found[int(line) - 1]]
        if size == len(found):
            return found
        size = min(len(found), size + OPTIONS)
        prompt = show(probe, stage, found, upto=size) + "\n"
    return found


def ask(probe: Probe, stage, found: list, reply, bits: float = WITHIN) -> list:
    """Up to BUDGET questions to a person; `reply(prompt)` returns their line: place numbers
    (several allowed), 0 for none of these, or nothing to stop. The candidates priced by
    the answers, cheapest first."""
    asked: set = set()
    while len(asked) < BUDGET:
        got = question(found, bits, asked)
        if got is None:
            break
        j, options = got
        asked.add(j)
        line = reply(wording(probe, stage, j, options) + "\n> ").replace(",", " ").split()
        if not line:
            break
        ticked = {NONE if n == "0" else options[int(n) - 1] for n in line
                  if n.isdigit() and int(n) <= len(options)}
        found = answered(found, j, options, ticked) if ticked else found
    return found
