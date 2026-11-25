"""JAR, join-aware multi-table retrieval (chen2024table). An LLM call splits the question
into concept:attribute sub-queries. The 20 tables closest to the question are candidates;
a mixed-integer program picks K of them, joined into a tree by compatible columns, that
best fits the question, covers the sub-queries and joins well. One table set, no ranking.

Departures from the paper and its code (github.com/peterbaile/jar):
1. medium: granite-embedding-english-r2 replaces Contriever for the question-table,
   sub-query-column and column-column scores; the text embedded is the paper's (names
   only). Weights w1..w5 were set for Contriever's scores and are kept unchanged.
2. medium: weights are the code's Contriever ones: bird [3, 8, 1, 3, 1] for bird_dev, and
   the spider ones [2, 8, 1, 10, 1] for every other lake, including lakes the paper never saw.
3. medium: the five few-shot examples are invented ones of the same kinds, outside the
   benchmarks' domains; an Output Format statement ends the prompt instead of "Assistant:".
4. small: the default AMIGO model replaces gpt-3.5-turbo; temperature cannot be set.
   The reply is JSON whose one field holds the paper's tagged text, read with its regex.
5. small: no sub-query at all is re-asked once, then an error (the code divides by zero).
6. small: the program is solved exactly by trying every K-subset of the 20 candidates
   (best spanning tree for the joins, best coverage for the sub-queries) instead of
   python-mip with a 60 s limit; ties go to the subset of better-ranked tables.
7. small: two columns may join when their declared types have the same SQLite affinity
   (the datasets' own type labels are not in a lake): bird DATE and DATETIME now match,
   spider INT and REAL no longer do.
8. small: value sets are compared by 64-bit hashes of the distinct values.
9. small: Jaccard is the code's |A & B| / |B|, B the column of the table later in the
   lake's order; jaccard="true" gives the paper's |A & B| / |A | B|.
10. small: tables are embedded whole (granite reads 8192 tokens; Contriever cut at 512).
"""

import hashlib
import itertools
import os
import re
import string
import threading
from contextlib import closing
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from amigo import config, embed, index, llm
from amigo.profile import quote

from .lake import lap, record

POOL = 20  # t_num, the candidate tables
# w1 sub-query to column, w2 sub-query covered, w3 join, w4 question to table, w5 coverage cap
WEIGHTS = {"bird_dev": (3, 8, 1, 3, 1)}
SPIDER_WEIGHTS = (2, 8, 1, 10, 1)
# BL_CACHE_DIR moves the index caches: they are keyed by lake name only, so a rebuilt lake needs its own
CACHE = Path(os.environ.get("BL_CACHE_DIR", config.ROOT / "runs" / "eval" / "bl_cache")) / "jar"

PROMPT = string.Template("""I'm going to ask you a question. I want you to decompose it into a series of non-composite noun concepts and attributes. If you are uncertain about concepts, only output attributes. You should wrap each concept and attribute in <sub_c></sub_c> tags. Once you have all the concepts you need to cover the question, output <FIN></FIN> tags.

Let's go through some examples together. Do you understand the instructions?

Assistant: Yes, I understand that I'm meant to decompose questions into concepts and attributes and wrap each component in the appropriate tags. Once I have all the information I need, I'll output <FIN></FIN> tags.

Human: Question: For glaciers with the status of "retreating", calculate the average ice thickness of these glaciers.

Assistant:
<sub_c>glaciers:status</sub_c>
<sub_c>glaciers:ice thickness</sub_c>
<FIN></FIN>

Human: Question: How many apiaries have a hive capacity of not more than 40 and which apiary made the highest total honey harvest for the year 2019?

Assistant:
<sub_c>apiaries:hive capacity</sub_c>
<sub_c>apiaries:honey harvest</sub_c>
<sub_c>year</sub_c>
<FIN></FIN>

Human: Question: What is the signal name for the track section with number 42?
Assistant:
<sub_c>signal:name</sub_c>
<sub_c>track section:number</sub_c>
<FIN></FIN>

Human: Question: On which day has the tide neither risen above 3 metres nor fallen below 1 metre at the pier code of P22?
Assistant:
<sub_c>pier code</sub_c>
<sub_c>tide</sub_c>
<FIN></FIN>

Human: Question: What is the id of the ascent that started from the mountain hut with the highest bed count?
Assistant:
<sub_c>ascent:id</sub_c>
<sub_c>mountain hut:bed count</sub_c>
<FIN></FIN>

Human: Question: $question

Output Format: a JSON object with exactly the key "answer", whose value is the Assistant's text for this last question: each concept and attribute wrapped in <sub_c></sub_c> tags, one per line, then <FIN></FIN>. No other text.
Return an answer only in this exact Output Format.""")
SUB = re.compile(r"<sub_c>(.*?)</sub_c>")

_SETUP_LOCK, _VALUES_LOCK = threading.Lock(), threading.Lock()
_VECTORS: dict = {}  # lake name -> table, column and schema vectors
_VALUES: dict = {}  # (lake, table path) -> uniqueness and hashed distinct values of each column
_COMMON: dict = {}  # (lake, column path, column path) -> number of shared distinct values


class Decomposition(BaseModel):
    answer: str


def decompose(question: str, log_path) -> list[str]:
    def check(reply: Decomposition) -> None:
        if not SUB.findall(reply.answer):
            raise llm.ModelError("the answer holds no <sub_c></sub_c> tag")

    reply = llm.call(PROMPT.substitute(question=question), Decomposition, log_path,
                     f"baseline jar {question[:50]}", check=check)
    return SUB.findall(reply.answer)


def _process(text: str) -> str:
    return text.replace("_", " ").replace(".", "").lower().strip()


def _affinity(declared: str | None) -> str:
    """SQLite's affinity of a declared type (sqlite.org/datatype3.html, 3.1)."""
    t = (declared or "").upper()
    if "INT" in t:
        return "INTEGER"
    if any(s in t for s in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if "BLOB" in t or not t:
        return "BLOB"
    return "REAL" if any(s in t for s in ("REAL", "FLOA", "DOUB")) else "NUMERIC"


def _save(path, write) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "wb") as handle:
        write(handle)
    os.replace(tmp, path)


def _vectors(lake):
    """Each table as "db table col1 col2 ...", each column as "table:column" and as
    "db table column" processed, embedded once per lake."""
    with _SETUP_LOCK:
        if lake.name not in _VECTORS:
            texts = [" ".join([t.database, t.name, *(c.name for c in t.columns)]) for t in lake.tables]
            texts += [f"{lake.table[c.table].name}:{c.name}" for c in lake.column_list]
            texts += [_process(f"{lake.table[c.table].database} {lake.table[c.table].name} {c.name}")
                      for c in lake.column_list]
            key = hashlib.sha1("\n".join(texts).encode()).hexdigest()[:12]
            path = CACHE / lake.name / f"vectors_{key}.npy"
            if path.exists():
                vectors = np.load(path)
            else:
                vectors = embed.embed(texts)
                _save(path, lambda handle: np.save(handle, vectors))
            n, m = len(lake.tables), len(lake.column_list)
            _VECTORS[lake.name] = vectors[:n], vectors[n:n + m], vectors[n + m:]
        return _VECTORS[lake.name]


def _hash(value) -> int:
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # as a Python set holds 1 and 1.0 once
    return int.from_bytes(hashlib.blake2b(repr(value).encode(), digest_size=8).digest(), "little")


def _values(lake, t):
    """Uniqueness (distinct values over rows, NULL one value) and the sorted hashed
    distinct values of each column of `t`, read from every row."""
    key = lake.name, t.path
    if key not in _VALUES:
        path = CACHE / lake.name / "values" / f"{t.path}.npz"
        if path.exists():
            with np.load(path) as z:
                _VALUES[key] = z["u"], [z[f"v{i}"] for i in range(len(t.columns))]
        else:
            with closing(index.open_source(lake.paths[t.database])) as conn:
                rows = conn.execute(f"SELECT COUNT(*) FROM {quote(t.name)}").fetchone()[0]
                sets = [np.unique(np.array([_hash(v) for (v,) in conn.execute(
                    f"SELECT DISTINCT {quote(c.name)} FROM {quote(t.name)}")], dtype=np.uint64))
                    for c in t.columns]
            u = np.array([len(s) / rows if rows else 0.0 for s in sets])
            _save(path, lambda handle: np.savez(handle, u=u, **{f"v{i}": s for i, s in enumerate(sets)}))
            _VALUES[key] = u, sets
    return _VALUES[key]


def _common(key, a: np.ndarray, b: np.ndarray) -> int:
    if key not in _COMMON:
        small, big = sorted((a, b), key=len)
        at = np.minimum(np.searchsorted(big, small), len(big) - 1)
        _COMMON[key] = int(np.sum(big[at] == small)) if len(big) else 0
    return _COMMON[key]


def _joins(lake, pool, schema, where, jaccard) -> np.ndarray:
    """The best join weight omega between each two candidate tables, 0 when no column
    pair has omega > 0: (0.5 Jaccard + 0.5 (0.5 cosine + 0.5 token overlap)) times the
    larger uniqueness, for columns of the same type (compatibility.py)."""
    with _VALUES_LOCK:
        values = [_values(lake, t) for t in pool]
    order = {t.path: i for i, t in enumerate(lake.tables)}
    kind = {c.path: _affinity(c.type) for t in pool for c in t.columns}
    tokens = {c.path: set(_process(f"{t.database} {t.name} {c.name}").split()) for t in pool for c in t.columns}
    weight = np.zeros((len(pool), len(pool)))
    for a, b in itertools.combinations(range(len(pool)), 2):
        first, later = sorted((a, b), key=lambda i: order[pool[i].path])
        (u1, v1), (u2, v2) = values[first], values[later]
        for k, c in enumerate(pool[first].columns):
            for l, d in enumerate(pool[later].columns):
                u = max(u1[k], u2[l])
                if u == 0 or kind[c.path] != kind[d.path]:
                    continue
                common = _common((lake.name, c.path, d.path), v1[k], v2[l])
                size = len(v2[l]) if jaccard == "code" else len(v1[k]) + len(v2[l]) - common
                exact = len(tokens[c.path] & tokens[d.path]) / min(len(tokens[c.path]), len(tokens[d.path]))
                semantic = float(schema[where[c.path]] @ schema[where[d.path]])
                omega = (0.5 * (common / size if size else 0.0) + 0.5 * (0.5 * semantic + 0.5 * exact)) * u
                weight[a, b] = weight[b, a] = max(weight[a, b], omega)
    return weight


def run(lake, question, log_path, k=3, jaccard="code"):
    if jaccard not in ("code", "true"):
        raise ValueError(f"jaccard is code or true, not {jaccard!r}")
    tables, columns, schema = _vectors(lake)
    where = {c.path: i for i, c in enumerate(lake.column_list)}
    w1, w2, w3, w4, w5 = WEIGHTS.get(lake.name, SPIDER_WEIGHTS)
    lap("setup")
    subs = decompose(question, log_path)
    lap("llm decompose")
    coarse = tables @ embed.embed([question])[0]
    top = np.argsort(-coarse)[:POOL]
    pool, near = [lake.tables[i] for i in top], [float(coarse[i]) for i in top]
    vectors = embed.embed(subs)
    # w1 times the best column of each table for each sub-query
    fine = [[w1 * float(np.max(columns[[where[c.path] for c in t.columns]] @ v)) for t in pool] for v in vectors]
    lap("search")
    weight = _joins(lake, pool, schema, where, jaccard)
    lap("joins")

    def cover(chosen):
        # each sub-query's first column gains w2 more, so taking the top w5 |Q| gains is exact
        gains = []
        for row in fine:
            got = sorted((row[i] for i in chosen), reverse=True)
            gains += [w2 + got[0], *got[1:]]
        return sum(g for g in sorted(gains, reverse=True)[:int(w5 * len(subs))] if g > 0)

    def tree(chosen):
        # the best spanning tree on omega > 0 edges, or None when they do not connect `chosen`
        inside, rest, total = [chosen[0]], list(chosen[1:]), 0.0
        while rest:
            edge, j = max((weight[i, j], j) for i in inside for j in rest)
            if edge <= 0:
                return None
            inside.append(j)
            rest.remove(j)
            total += edge
        return total

    best, picked = None, None
    for chosen in itertools.combinations(range(len(pool)), k):
        joined = tree(chosen)
        if joined is None:
            continue
        score = w4 * sum(near[i] for i in chosen) + cover(chosen) + w3 * joined
        if best is None or score > best:
            best, picked = score, chosen
    lap("choose")
    if picked is None:
        return record([], fallback=f"no {k} of the {POOL} candidate tables connect by join edges",
                      sub_queries=subs)
    return record([pool[i].path for i in picked], sub_queries=subs)
