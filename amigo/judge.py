"""The judge: one LLM call per question says, for every place in each part's
list, yes or no: could a person asking mean this place for this part. The search runs on
the places kept, each at its own cost; a second call says yes or no for every
interpretation found, as a whole, and the ones it says no to are dropped.

The search (candidates.py) knows how tables join but reads names only by embeddings; the
judge reads meaning but sees no structure. So the judge grades each (part, place) pair on
its own, a few dozen lines, and the search combines the grades over every way to join:
exponentially many interpretations priced from linearly many judgments. Grading places
one by one assumes each part's place can be judged apart from the others; it cannot when
the meaning lies in how they combine (which rows a join relates, a part left out). So the
second call sees every interpretation found, whole, and keeps the ones a person could
mean: the N-best rescoring of speech recognition and parsing, where a cheap factored model
finds a short list and a richer one checks it (Collins 2000).
"""

import heapq
import itertools
import logging
import string
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from pydantic import BaseModel, create_model

from . import bundle as _bundle
from . import candidates as C
from . import config, llm, solve
from .clock import lap
from .probe import Probe

log = logging.getLogger(__name__)

# the most interpretations returned, the cheapest kept: a guard against a question whose
# answer would run into the thousands, set well above what a person reads
MOST = 50


def numbered(name: str, keys: list[str], item: type) -> type[BaseModel]:
    """A reply with exactly these numbers as keys, each holding a list of `item`. The column
    judge's: concept number -> the columns kept, as database.table.column; the join choice's:
    join number -> the numbers of the ways kept. The schema lets the model write no other key."""
    return create_model(name, **{key: (list[item], ...) for key in keys})


class SetsKept(BaseModel):
    """The table set judge's reply: the numbers of the sets kept."""
    keep: list[int]


# Up to 6aec78f (prompts/old/): the replies of the place, whole and join judges.
# class Grade(BaseModel):
#     part: int
#     yes: list[int]
#
#
# class Grades(BaseModel):
#     parts: list[Grade]
#
#
# class Wholes(BaseModel):
#     yes: list[int]
#
#
# class JoinYes(BaseModel):
#     join: int
#     yes: list[int]
#
#
# class JoinGrades(BaseModel):
#     joins: list[JoinYes]


def _concept(entity: llm.Entity) -> str:
    """A concept as the prompts write it: `age = 60`, `gender = "female"`."""
    if entity.literal is None:
        return entity.attribute
    return f"{entity.attribute} = {_bundle._as_written(entity.literal)}"


# Up to 6aec78f: a part as the old prompts wrote it.
# def _written(entity: llm.Entity) -> str:
#     literal = entity.literal
#     if literal is None:
#         return entity.attribute
#     if literal.kind == "text":
#         return f'{entity.attribute} = "{literal.text}" (text)'
#     if literal.kind == "number":
#         return f"{entity.attribute} = {literal.number:g} (number)"
#     span = literal.date_start if literal.date_start == literal.date_end else f"{literal.date_start}..{literal.date_end}"
#     return f"{entity.attribute} = {span} (date)"


def _sentence(text: str | None) -> str:
    one = _bundle._one_line(text)
    return one.split(". ")[0].rstrip(".") if one else ""


def _table(probe: Probe, table_id: int) -> str:
    """database.table"""
    table = probe.tables[table_id]
    return f"{table['database']}.{table['name']}"


def _column(probe: Probe, column_id: int) -> str:
    """database.table.column"""
    column = probe.columns[column_id]
    return f"{_table(probe, column['table_id'])}.{column['name']}"


def _candidate(probe: Probe, graph: C.Graph, stage, h: C.Holder) -> str:
    """One candidate column of a concept: its name, type and meaning, and where the
    concept's value was found, else a few sample values. How columns join is not shown:
    the judge decides from the column alone."""
    stores = {c for k, kind, cols in stage.found if k == h.part and kind == "value" for c in cols}
    column = probe.columns[h.column]
    line = f"- {_column(probe, h.column)} ({column['type'].lower() or 'any'})"
    about = _sentence(column["description"])
    if about:
        line += f": {about}"
    # targets = sorted(graph.references.get(h.column, ()))
    # if targets:
    #     line += f"; refers to {', '.join(_table(probe, t) for t in targets)}"
    # the notes of where this concept's value was found; another concept's are not about it
    found = ([d for d in stage.details.get(h.column, []) if not d.startswith('matches "')]
             if h.column in stores else [])
    samples = _bundle._samples(column)[:3]
    if found:
        note = "; ".join(found)
        line += f". {note[:1].upper()}{note[1:]}"
    else:
        line += f". Sample values: {', '.join(samples)}" if samples else ". No values stored"
    return line


# Up to 6aec78f: tables named T1, T2, ... and a place line per column.
# class _Tags:
#     """T1, T2, ... for the tables of a prompt, in the order they are first named."""
#
#     def __init__(self) -> None:
#         self.tables: dict[int, str] = {}
#
#     def __call__(self, table_id: int) -> str:
#         if table_id not in self.tables:
#             self.tables[table_id] = f"T{len(self.tables) + 1}"
#         return self.tables[table_id]
#
#     def lines(self, probe: Probe) -> str:
#         lines = []
#         for table_id, name in self.tables.items():
#             table = probe.tables[table_id]
#             line = (f"  {name} | database {table['database_readable']} | table {table['name']}"
#                     f" ({table['row_count']} rows)")
#             about = _sentence(table["description"])
#             lines.append(line + (f": {about}" if about else ""))
#         return "\n".join(lines)
#
#
# def _place(probe: Probe, graph: C.Graph, stage, h: C.Holder, tag: _Tags) -> str:
#     """One place of a part: its table and column, what the column means, where the part's
#     value was found or a few values, and the tables a reference column points to."""
#     stores = {c for k, kind, cols in stage.found if k == h.part and kind == "value" for c in cols}
#     column = probe.columns[h.column]
#     line = f"{tag(h.table)} column {column['name']} ({column['type'].lower() or 'any'})"
#     about = _sentence(column["description"])
#     if about:
#         line += f": {about}"
#     # the notes of where this part's value was found; another part's are not about it
#     found = ([d for d in stage.details.get(h.column, []) if not d.startswith('matches "')]
#              if h.column in stores else [])
#     if found:
#         line += "; " + "; ".join(found)
#     else:
#         samples = _bundle._samples(column)[:3]
#         line += f"; values like {', '.join(samples)}" if samples else "; no values stored"
#     targets = sorted(graph.references.get(h.column, ()))
#     if targets:
#         line += f"; points to {', '.join(tag(t) for t in targets)}"
#     return line


def _tokens(text: str) -> int:
    """A prompt's length in tokens, overestimated: English runs about 4 characters a token."""
    return len(text) // 3


def chunks(items: list, render) -> list[list]:
    """The items in order, in as few runs as keep each run's prompt (`render` of the run)
    within config.PROMPT_TOKENS; an item too long alone still goes, alone."""
    if _tokens(render(items)) <= config.PROMPT_TOKENS:
        return [items]
    out = [[]]
    for item in items:
        if out[-1] and _tokens(render(out[-1] + [item])) > config.PROMPT_TOKENS:
            out.append([])
        out[-1].append(item)
    if len(out) > 1:
        log.info("judge: %d items split over %d calls", len(items), len(out))
    return out


def render(probe: Probe, graph: C.Graph, question: str, stage, shown: list[list[C.Holder]]) -> str:
    """The column judge's prompt: each concept that has candidate columns, numbered as in
    the split, and its candidates."""
    blocks = []
    for j, mine in enumerate(shown):
        if mine:
            blocks.append("\n".join([f"Concept {j + 1}: {_concept(stage.entities[j])}"]
                                    + [_candidate(probe, graph, stage, h) for h in mine]))
    template = string.Template((config.PROMPTS_DIR / "judge_places.txt").read_text())
    return template.substitute(question=question, candidates="\n\n".join(blocks))


# Up to 6aec78f (prompts/old/judge_places.txt):
# def render(probe: Probe, graph: C.Graph, question: str, stage, shown: list[list[C.Holder]]) -> str:
#     """The prompt: the parts, the tables of every place, and the places of each part. A
#     reference column says which tables it points to, since it stores their ids."""
#     tag = _Tags()
#     places = []
#     for j, mine in enumerate(shown):
#         places.append(f'  Part {j + 1} "{_written(stage.entities[j])}"')
#         places += [f"    {n}. {_place(probe, graph, stage, h, tag)}" for n, h in enumerate(mine, start=1)]
#     template = string.Template((config.PROMPTS_DIR / "judge_places.txt").read_text())
#     return template.substitute(
#         question=question,
#         parts="\n".join(f"  {j + 1}. {_written(e)}" for j, e in enumerate(stage.entities)),
#         tables=tag.lines(probe),
#         places="\n".join(places),
#     )


def judge(probe: Probe, graph: C.Graph, question: str, stage, shown: list[list[C.Holder]],
          log_path: Path) -> list[dict]:
    """Per part, whether each place shown may hold it: (table, column) -> True / False,
    from one LLM call, or several over runs of the places when one prompt would pass
    config.PROMPT_TOKENS (each yes or no is about one place, so a run is judged alone);
    with config.JUDGE_SAMPLES n > 1, n replies asked at once, a place kept when at least
    half of them say yes (a reply that fails is left out; self-consistency, Wang et al.
    2023)."""

    def part_lists(run: list) -> list[list[C.Holder]]:
        """The places of a run of (part, place), as one list per part."""
        return [[h for k, h in run if k == j] for j in range(len(shown))]

    runs = [part_lists(run) for run in chunks(
        [(j, h) for j, mine in enumerate(shown) for h in mine],
        lambda run: render(probe, graph, question, stage, part_lists(run)))]

    def one(run: list[list[C.Holder]], sample: int) -> list[dict]:
        names = [{_column(probe, h.column): h for h in mine} for mine in run]
        asked = [str(j + 1) for j, mine in enumerate(run) if mine]

        def check(result: BaseModel) -> None:
            for key, kept in result.model_dump().items():
                bad = [name for name in kept if name not in names[int(key) - 1]]
                if bad:
                    raise llm.ModelError(f"concept {key} has no candidate column {', '.join(bad)}")

        result = llm.call(render(probe, graph, question, stage, run), numbered("Kept", asked, str), log_path,
                          f"judge places {question[:50]}", check=check,
                          effort=config.JUDGE_REASONING_EFFORT, sample=sample,
                          budget=config.JUDGE_BUDGET)
        out = []
        for j, mine in enumerate(run):
            yes = set(result.model_dump().get(str(j + 1), ()))
            out.append({(h.table, h.column): name in yes for name, h in names[j].items()})
        return out

    # Up to 6aec78f (prompts/old/judge_places.txt):
    # def one(run: list[list[C.Holder]], sample: int) -> list[dict]:
    #     def check(result: Grades) -> None:
    #         got = [g.part for g in result.parts]
    #         if got != list(range(1, len(run) + 1)):
    #             raise llm.ModelError(f"parts must be 1 to {len(run)} in order, once each, not {got}")
    #         for g in result.parts:
    #             size = len(run[g.part - 1])
    #             bad = [n for n in g.yes if not 1 <= n <= size]
    #             if bad:
    #                 raise llm.ModelError(f"part {g.part} has places 1 to {size}, not {bad}")
    #
    #     result = llm.call(render(probe, graph, question, stage, run), Grades, log_path,
    #                       f"judge places {question[:50]}", check=check,
    #                       effort=config.JUDGE_REASONING_EFFORT, sample=sample,
    #                       budget=config.JUDGE_BUDGET)
    #     out = []
    #     for g, mine in zip(result.parts, run):
    #         yes = {n - 1 for n in g.yes}
    #         out.append({(h.table, h.column): n in yes for n, h in enumerate(mine)})
    #     return out

    def ask(sample: int) -> list[dict]:
        # the runs do not wait on each other, so they are asked at the same time
        with ThreadPoolExecutor(max_workers=len(runs)) as pool:
            replies = list(pool.map(llm.carry(lambda run: one(run, sample)), runs))
        return [{key: yes for reply in replies for key, yes in reply[j].items()} for j in range(len(shown))]

    if config.JUDGE_SAMPLES == 1:
        return ask(0)

    def tried(sample: int) -> list[dict] | None:
        try:
            return ask(sample)
        except llm.ModelError as err:
            log.warning("judge places, sample %d failed: %s", sample, err)
            return None

    with ThreadPoolExecutor(max_workers=config.JUDGE_SAMPLES) as pool:
        replies = [r for r in pool.map(llm.carry(tried), range(config.JUDGE_SAMPLES)) if r is not None]
    if not replies:
        raise llm.ModelError(f"judge places {question[:50]}: every sample failed")
    return [{key: 2 * sum(r[j][key] for r in replies) >= len(replies) for key in replies[0][j]}
            for j in range(len(shown))]


def graded(shown: list[list[C.Holder]], grades: list[dict]) -> list[list[C.Holder]]:
    """The places of each part the judge kept, each at its own cost."""
    return [[replace(h, why=f"yes; {h.why}") for h in mine if grades[j][(h.table, h.column)]]
            for j, mine in enumerate(shown)]


def render_wholes(probe: Probe, question: str, sets: list[frozenset[int]]) -> str:
    """The table set judge's prompt: each set of tables, each table with what its rows are."""
    blocks = []
    for n, tables in enumerate(sets, start=1):
        lines = [f"Set {n}"]
        for t in sorted(tables, key=lambda t: _table(probe, t)):
            about = _sentence(probe.tables[t]["description"])
            lines.append(f"- {_table(probe, t)}" + (f": {about}" if about else ""))
        blocks.append("\n".join(lines))
    template = string.Template((config.PROMPTS_DIR / "judge_wholes.txt").read_text())
    return template.substitute(question=question, sets="\n".join(blocks))


def whole_grades(probe: Probe, graph: C.Graph, question: str, stage, found: list[C.Candidate],
                 log_path: Path) -> list[bool]:
    """Yes or no for every interpretation, in order, from a yes or no for each distinct set of
    tables (one LLM call, or several when the prompt would pass config.PROMPT_TOKENS):
    interpretations over the same tables get the same answer. None when there is none."""
    sets = list(dict.fromkeys(one.tables for one in found))

    def one(run: list[frozenset[int]]) -> list[bool]:
        def check(result: SetsKept) -> None:
            bad = [n for n in result.keep if not 1 <= n <= len(run)]
            if bad:
                raise llm.ModelError(f"the sets are 1 to {len(run)}, not {bad}")

        result = llm.call(render_wholes(probe, question, run), SetsKept, log_path,
                          f"judge wholes {question[:50]}", check=check, model=config.WHOLES_MODEL,
                          effort=config.JUDGE_REASONING_EFFORT, budget=config.JUDGE_BUDGET)
        return [n in result.keep for n in range(1, len(run) + 1)]

    runs = chunks(sets, lambda run: render_wholes(probe, question, run)) if sets else []
    # the runs do not wait on each other, so they are asked at the same time
    with ThreadPoolExecutor(max_workers=max(1, len(runs))) as pool:
        kept_sets = dict(zip(sets, (yes for grades in pool.map(llm.carry(one), runs) for yes in grades)))
    return [kept_sets[one.tables] for one in found]


# Up to 6aec78f (prompts/old/judge_wholes.txt): each interpretation judged whole, with its
# joins and the place of each part.
# def _joins(probe: Probe, graph: C.Graph, one: C.Candidate, tag: _Tags) -> str:
#     """How an interpretation's tables join: the columns of the best link of each join."""
#     out = []
#     for a, b in one.edges:
#         ways = graph.ways.get((a, b))
#         if not ways:
#             out.append(f"{tag(a)} and {tag(b)} with no known link")
#             continue
#         for x, y in max(ways, key=lambda w: w.quality).links:
#             cx, cy = probe.columns[x], probe.columns[y]
#             out.append(f"{tag(cx['table_id'])}.{cx['name']} = {tag(cy['table_id'])}.{cy['name']}")
#     return ", ".join(out) or "none"
#
#
# def render_wholes(probe: Probe, graph: C.Graph, question: str, stage, wholes: list[C.Candidate]) -> str:
#     """The second prompt: the parts, the tables, the places the interpretations read, and
#     each interpretation: its tables, its joins and the place of each part."""
#     tag = _Tags()
#     lines = []
#     for n, one in enumerate(wholes, start=1):
#         joins = _joins(probe, graph, one, tag)
#         tables = ", ".join(sorted((tag(t) for t in one.tables), key=lambda t: int(t[1:])))
#         lines.append(f"  {n}. tables {tables}; joins {joins}")
#         for j, h in enumerate(one.holders):
#             where = "nowhere" if h is None else f"{tag(h.table)} column {probe.columns[h.column]['name']}"
#             lines.append(f"     part {j + 1}: {where}")
#     places = []
#     for j, entity in enumerate(stage.entities):
#         used = {(h.table, h.column): h for one in wholes for h in [one.holders[j]] if h is not None}
#         if used:
#             places.append(f'  Part {j + 1} "{_written(entity)}"')
#             places += [f"    {_place(probe, graph, stage, h, tag)}" for h in used.values()]
#     template = string.Template((config.PROMPTS_DIR / "judge_wholes.txt").read_text())
#     return template.substitute(
#         question=question,
#         parts="\n".join(f"  {j + 1}. {_written(e)}" for j, e in enumerate(stage.entities)),
#         tables=tag.lines(probe),
#         places="\n".join(places),
#         wholes="\n".join(lines),
#     )
#
#
# def whole_grades(probe: Probe, graph: C.Graph, question: str, stage, found: list[C.Candidate],
#                  log_path: Path) -> list[bool]:
#     """Yes or no for every interpretation as a whole (one LLM call, or several when the
#     prompt would pass config.PROMPT_TOKENS), in order; none when there is none."""
#     def one(run: list[C.Candidate]) -> list[bool]:
#         def check(result: Wholes) -> None:
#             bad = [n for n in result.yes if not 1 <= n <= len(run)]
#             if bad:
#                 raise llm.ModelError(f"interpretations are 1 to {len(run)}, not {bad}")
#
#         result = llm.call(render_wholes(probe, graph, question, stage, run), Wholes, log_path,
#                           f"judge wholes {question[:50]}", check=check, model=config.WHOLES_MODEL,
#                           effort=config.JUDGE_REASONING_EFFORT, budget=config.JUDGE_BUDGET)
#         return [n in result.yes for n in range(1, len(run) + 1)]
#
#     runs = chunks(found, lambda run: render_wholes(probe, graph, question, stage, run)) if found else []
#     # the runs do not wait on each other, so they are asked at the same time
#     with ThreadPoolExecutor(max_workers=max(1, len(runs))) as pool:
#         return [yes for grades in pool.map(llm.carry(one), runs) for yes in grades]


def split(found: list[C.Candidate], places: list[list[C.Holder]]) -> list[C.Candidate]:
    """Each interpretation once per choice of graded places in its own tables, cheapest
    first. The search keeps one place per table, since two columns of one table give the
    same tables and joins; a copy swaps in another place of the same table and pays the
    difference in cost. A copy is kept when it costs no more than the dearest one found,
    the limit the search kept them by. At most MOST are kept, the cheapest."""
    if not found:
        return found
    limit = found[-1].cost + 1e-9
    by_table = [{} for _ in places]
    for j, mine in enumerate(places):
        for h in mine:
            by_table[j].setdefault(h.table, []).append(h)
    # Each part keeps its place or swaps in another place of the same table, which costs no
    # less, since the search keeps the cheapest place per table. So copies come cheapest first
    # from a heap, and only MOST are made: with no judged places, a question can have hundreds
    # of millions. A copy's children each move one part, at or after the last part moved, to
    # its next costlier place. At equal cost, copies keep the order of listing them all:
    # interpretation by interpretation, the later parts' swaps after the earlier ones'.
    heap, out, seen = [], [], set()

    def push(i, alts, v, last):
        one, extra, key = found[i], 0.0, ()
        for j, n in enumerate(v):
            _, rank, o = alts[j][n]
            if rank:
                extra = extra + o.cost - one.holders[j].cost
            key = (rank > 0, key, rank)
        if one.cost + extra <= limit:
            heapq.heappush(heap, (one.cost + extra, i, key, v, last, alts, extra))

    for i, one in enumerate(found):
        alts = []
        for j, h in enumerate(one.holders):
            more = [] if h is None else [o for o in by_table[j].get(h.table, ()) if o.column != h.column]
            alts.append([(0.0, 0, h)] + sorted(((o.cost - h.cost, n + 1, o) for n, o in enumerate(more)),
                                               key=lambda a: a[:2]))
        push(i, alts, (0,) * len(alts), 0)
    while heap and len(out) < MOST:
        cost, i, _, v, last, alts, extra = heapq.heappop(heap)
        one = found[i]
        hs = tuple(alts[j][n][2] for j, n in enumerate(v))
        key = (one.database, one.tables, one.edges, tuple(h and (h.table, h.column) for h in hs))
        if key not in seen:
            seen.add(key)
            out.append(replace(one, holders=hs, cost=cost, holder_cost=one.holder_cost + extra,
                               extra=dict(one.extra)))
        for p in range(last, len(v)):
            if v[p] + 1 < len(alts[p]):
                push(i, alts, v[:p] + (v[p] + 1,) + v[p + 1:], p)
    if heap:
        log.info("split: more than %d interpretations, the %d cheapest kept", MOST, MOST)
    return out


def kept(found: list[C.Candidate], grades: list[bool]) -> list[C.Candidate]:
    """The interpretations the whole grades say yes to, in order. No grades: unchanged.
    When they say no to every one, all are kept, each marked judged no (extra["judged_no"])."""
    if grades and not any(grades):
        return [replace(one, extra={**one.extra, "judged_no": True}) for one in found]
    return [one for one, yes in zip(found, grades) if yes] if grades else found


def _options(probe: Probe, graph: C.Graph, edge: tuple[int, int], memo: dict) -> list[tuple[str, tuple]]:
    """The ways to link one join's two tables, as (how, links): each link that pairs other
    rows than the others alone (solve._roles), how always "one". A join with no known link
    has one way, with no link. `memo` keeps
    them per table pair, since a check reads the database."""
    key = tuple(sorted(edge))
    if key not in memo:
        roles = solve._roles(probe, graph.ways.get(key, []), key)
        memo[key] = [("one", (r,)) for r in roles] or [("one", ())]
        # Up to 6aec78f, two more ways when there were two or more links: all of them on
        # the same rows, and any of them. Dropped with prompts/old/judge_joins.txt.
        # if len(roles) > 1:
        #     memo[key] += [("all", tuple(roles)), ("any", tuple(roles))]
    return memo[key]


def ways(probe: Probe, graph: C.Graph, found: list[C.Candidate], memo: dict,
         yes: dict | None = None) -> list[C.Candidate]:
    """Each interpretation once per way to link its joins, in order: the search prices a join
    by its two tables, not by which link of theirs it uses, so every link that pairs other rows
    is its own interpretation; with `yes`, only the ways of a join (sorted table pair -> their
    numbers) said yes to. The way of each join is in extra["ways"], edge -> (how, links)."""
    def kept(e):
        options = _options(probe, graph, e, memo)
        mine = (yes or {}).get(tuple(sorted(e)))
        return [options[n] for n in sorted(mine)] if mine else options

    return [replace(one, extra={**one.extra, "ways": dict(zip(one.edges, pick))})
            for one in found for pick in itertools.product(*(kept(e) for e in one.edges))]


def _way(probe: Probe, graph: C.Graph, links: tuple) -> str:
    """One way to join two tables, in words: its column pairs and, in brackets, what the
    referring column of each pair means."""
    pairs, notes = [], []
    for join in links:
        for x, y in join.links:
            pairs.append(f"{_column(probe, x)} = {_column(probe, y)}")
            # the column that refers to the other table says what the link means
            note = _sentence(probe.columns[y if y in graph.references and x not in graph.references else x]["description"])
            if note:
                notes.append(note)
    if not pairs:
        return "no known link"
    return " and ".join(pairs) + (f" ({'; '.join(notes)})" if notes else "")


def render_joins(probe: Probe, graph: C.Graph, question: str, stage, run: list, memo: dict) -> str:
    """The join choice's prompt over a run of joins (table pairs) with two or more ways to
    link: each pair of tables, with what their rows are, and its ways."""
    def table(t: int) -> str:
        about = _sentence(probe.tables[t]["description"])
        return _table(probe, t) + (f" ({about})" if about else "")

    blocks = []
    for n, key in enumerate(run, start=1):
        lines = [f"Join {n}: {table(key[0])} and {table(key[1])}"]
        lines += [f"  {i}. {_way(probe, graph, links)}"
                  for i, (_how, links) in enumerate(_options(probe, graph, key, memo), start=1)]
        blocks.append("\n".join(lines))
    template = string.Template((config.PROMPTS_DIR / "judge_joins.txt").read_text())
    return template.substitute(question=question, joins="\n\n".join(blocks))


# Up to 6aec78f (prompts/old/judge_joins.txt): tables as T1, T2, ... and the parts, tables and
# linked columns listed apart.
# def _link(probe: Probe, tag: _Tags, how: str, links: tuple, about: dict) -> str:
#     """One way to link a join, in words; the columns it links go into `about`."""
#     texts = []
#     for join in links:
#         pairs = []
#         for x, y in join.links:
#             for c in (x, y):
#                 column = probe.columns[c]
#                 about[f"{tag(column['table_id'])}.{column['name']}"] = _sentence(column["description"])
#             cx, cy = probe.columns[x], probe.columns[y]
#             pairs.append(f"{tag(cx['table_id'])}.{cx['name']} = {tag(cy['table_id'])}.{cy['name']}")
#         text = " and ".join(pairs)
#         texts.append(f"({text})" if how != "one" and len(pairs) > 1 else text)
#     if how == "all":
#         return " and ".join(texts) + " (all these links on the same rows)"
#     if how == "any":
#         return " or ".join(texts) + " (any of these links)"
#     return texts[0] if texts else "no known link"
#
#
# def render_joins(probe: Probe, graph: C.Graph, question: str, stage, run: list, memo: dict) -> str:
#     """The prompt of the join choices over a run of joins (table pairs) with two or more ways
#     to link: the ways, the parts, the tables, and the columns the joins link."""
#     tag, about = _Tags(), {}
#     joins = []
#     for n, key in enumerate(run, start=1):
#         joins.append(f"  J{n}, {tag(key[0])} to {tag(key[1])}:")
#         joins += [f"    {i}. {_link(probe, tag, how, links, about)}"
#                   for i, (how, links) in enumerate(_options(probe, graph, key, memo), start=1)]
#     template = string.Template((config.PROMPTS_DIR / "judge_joins.txt").read_text())
#     return template.substitute(
#         question=question,
#         parts="\n".join(f"  {j + 1}. {_written(e)}" for j, e in enumerate(stage.entities)),
#         tables=tag.lines(probe),
#         columns="\n".join(f"  {name}: {text}" if text else f"  {name}" for name, text in about.items()),
#         joins="\n".join(joins),
#     )


def chosen(probe: Probe, graph: C.Graph, question: str, stage, found: list[C.Candidate], memo: dict,
           log_path: Path) -> tuple[list[C.Candidate], dict]:
    """The interpretations, each once per way to link its joins (`ways`), keeping only what a
    person could mean. One LLM call (or several, past config.PROMPT_TOKENS) says yes or no for
    each way to link each join with two or more. A join said no to entirely keeps every way,
    marked (extra["joins_no"]). At most MOST are kept, the cheapest. Also counts: joins asked,
    joins said no to entirely, and the ways before the cap."""
    pairs = list(dict.fromkeys(tuple(sorted(e)) for one in found for e in one.edges
                               if len(_options(probe, graph, e, memo)) > 1))
    yes, no_joins = {}, set()
    for run in chunks(pairs, lambda run: render_joins(probe, graph, question, stage, run, memo)) if pairs else []:
        sizes = [len(_options(probe, graph, k, memo)) for k in run]
        asked = [str(n) for n in range(1, len(sizes) + 1)]

        def check(result: BaseModel) -> None:
            for key, size in zip(asked, sizes):
                bad = [n for n in getattr(result, key) if not 1 <= n <= size]
                if bad:
                    raise llm.ModelError(f"join {key} has ways 1 to {size}, not {bad}")

        result = llm.call(render_joins(probe, graph, question, stage, run, memo), numbered("JoinKept", asked, int), log_path,
                          f"judge joins {question[:50]}", check=check,
                          effort=config.JUDGE_REASONING_EFFORT, budget=config.JUDGE_BUDGET)
        for n, key in enumerate(run, start=1):
            if getattr(result, str(n)):
                yes[key] = {m - 1 for m in getattr(result, str(n))}
            else:
                no_joins.add(key)
        # Up to 6aec78f (prompts/old/judge_joins.txt):
        # def check(result: JoinGrades) -> None:
        #     sizes = [len(_options(probe, graph, k, memo)) for k in run]
        #     got = [g.join for g in result.joins]
        #     if got != list(range(1, len(sizes) + 1)):
        #         raise llm.ModelError(f"joins must be 1 to {len(sizes)} in order, once each, not {got}")
        #     for g, size in zip(result.joins, sizes):
        #         bad = [n for n in g.yes if not 1 <= n <= size]
        #         if bad:
        #             raise llm.ModelError(f"join {g.join} has 1 to {size}, not {bad}")
        #
        # result = llm.call(render_joins(probe, graph, question, stage, run, memo), JoinGrades, log_path,
        #                   f"judge joins {question[:50]}", check=check,
        #                   effort=config.JUDGE_REASONING_EFFORT, budget=config.JUDGE_BUDGET)
        # for g, key in zip(result.joins, run):
        #     if g.yes:
        #         yes[key] = {n - 1 for n in g.yes}
        #     else:
        #         no_joins.add(key)
    out = []
    for one in found:
        no = any(tuple(sorted(e)) in no_joins for e in one.edges)
        out += [replace(w, extra={**w.extra, "joins_no": True}) if no else w for w in ways(probe, graph, [one], memo, yes)]
    return out[:MOST], {"joins": len(pairs), "refused": len(no_joins), "ways": len(out),
                        "capped": max(0, len(out) - MOST)}


def relaxed(probe: Probe, graph: C.Graph, stage, places: list[list[C.Holder]], k: int,
            bits: float | None) -> list[C.Candidate]:
    """When no interpretation places every part: those that leave out the fewest parts,
    cheapest first. A part with no place the judge said yes to is always left out; then
    one more part at a time, each in turn, until some interpretation is found."""
    parts = len(places)
    forced = {j for j, mine in enumerate(places) if not mine}
    others = [j for j in range(parts) if j not in forced]
    for more in range(0 if forced else 1, len(others)):
        found = [one for extra in itertools.combinations(others, more)
                 for one in C.candidates(probe, graph, stage, k, graded=places, bits=bits,
                                         drop=frozenset(forced | set(extra)))]
        if found:
            return sorted(found, key=lambda one: one.cost)
    return []


def interpret(probe: Probe, graph: C.Graph, stage, question: str, log_path: Path,
              within: float | None = None, drop: frozenset[int] = frozenset(),
              keep: list[set | None] | None = None):
    """The interpretations of a question, cheapest first: the judge's yes or no on every
    place of each part's list, the search over the places kept (the cheapest, and every one
    within `within` bits of it; with no window, the MOST cheapest), each split per place of its own tables, and the yes or no
    for each as a whole. Every part is placed; when none places every part, the relaxed
    ones that leave out the fewest parts (`relaxed`), and with `drop`, those parts are left
    out. A relaxed interpretation gets no whole grade, since it leaves out what was asked,
    and says which parts it leaves out (Candidate.left_out). Also the places shown, their
    grades, the interpretations before the whole grades, and those grades (None when that
    call failed: all are then kept; all are kept too, marked, when it says no to every one).
    With `keep`, a person's own choice of places replaces the judge's for each part it names:
    a set of (table, column) per part, or None to leave that part's grades as they are."""
    shown = [C.holders(probe, stage, j) for j in range(len(stage.entities))]
    lap("places")
    grades = judge(probe, graph, question, stage, shown, log_path)
    lap("llm judge places")
    for j, mine in enumerate(keep or []):
        if mine is not None:
            grades[j] = {(h.table, h.column): (h.table, h.column) in mine for h in shown[j]}
    places = graded(shown, grades)
    k, bits = (MOST, None) if within is None else (1, within)
    found = C.candidates(probe, graph, stage, k, graded=places, bits=bits, drop=drop)
    if not found and not drop:
        found = relaxed(probe, graph, stage, places, k, bits)
    placed = split(found, places)
    lap("search")
    try:
        wholes = [] if any(one.left_out for one in placed) else whole_grades(
            probe, graph, question, stage, placed, log_path)
    except llm.ModelError as err:
        log.warning("judge wholes failed: %s", err)
        wholes = None
    lap("llm judge wholes")
    return kept(placed, wholes or []), shown, grades, placed, wholes
