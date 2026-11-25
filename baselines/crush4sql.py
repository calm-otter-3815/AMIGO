"""CRUSH4SQL: one LLM call hallucinates a minimal schema for the question; each made-up
table.column is a probe; the lake's columns closest to the probes form a candidate pool,
and a greedy picks b columns that cover every probe in turn, probes that match many
columns alike weighing less. The tables of the picked columns are the answer.
kothyari2023crush4sql.

Departures from the paper:
1. (medium) The LLM is the default chat model with its reasoning effort, not
   text-davinci-003; temperature cannot be set (the paper uses 0).
2. (small) The reply is JSON by schema, tables as {"name", "columns"} objects, instead of
   "N:table(col, col)" lines read by a regex; the code's cleaning is kept ("/" and "-" to
   spaces, spaces to "_"), and names the regex would reject are kept. The prompt states
   its output format. No probe after one re-ask fails the question (no paper fallback).
3. (medium) Six invented out-of-domain examples, one per kind of the paper's six, in one
   prompt for every lake (the paper writes one prompt per benchmark).
4. (medium) granite-embedding-english-r2 replaces SGPT for columns and probes.
5. (medium) A probe is embedded as plain "table.column", without the question: the
   paper's ablation "-x-contextual" (SpiderUnion recall@20 0.90 -> 0.86).
6. (small) Selection is the released round-robin greedy with its own edge rewards, 0,
   not the soft-max objective of Eq. 6 that the paper solves by an unpublished greedy. So
   no edge term: the paper's ablation "-Edge scores" (SpiderUnion recall@20 unchanged).
7. (small) Tables come best first by the pick order of their first column; the released
   code returns an unordered set.
"""

import os
import string
import threading
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from amigo import embed, llm

from .lake import lap, record

# BL_CACHE_DIR moves the index caches: they are keyed by lake name only, so a rebuilt lake needs its own
CACHE = Path(os.environ.get("BL_CACHE_DIR", Path(__file__).resolve().parents[1] / "runs" / "eval" / "bl_cache")) / "crush4sql"
CANDIDATES = 100

PROMPT = string.Template('''Hallucinate a minimal schema of a relational database that can be used to answer the natural language question. Here are some examples:

Example 1:

Question: What are the names of all glaciers with a length greater than 12.5 kilometres?

Tables:
{"tables": [{"name": "glacier", "columns": ["name", "length"]}]}

Example 2:

Question: Count the number of keepers in the Hollow Oak beekeeping association who are older than 60.

Tables:
{"tables": [{"name": "association", "columns": ["name", "association id", "association description", "location"]}, {"name": "member_of_association", "columns": ["association id", "keeper id"]}, {"name": "keeper", "columns": ["keeper id", "age"]}]}

Example 3:

Question: Show the sailing date, the captain, and the name of the harbour that each ferry crossing departs from.

Tables:
{"tables": [{"name": "ferry_crossing", "columns": ["sailing date", "captain", "harbour"]}, {"name": "harbour", "columns": ["name", "harbour identifier"]}]}

Example 4:

Question: Find the model name and wattage of the lighting fixtures used in both Hamlet and The Tempest.

Tables:
{"tables": [{"name": "fixture", "columns": ["model name", "wattage", "fixture id"]}, {"name": "fixture_in_production", "columns": ["fixture id", "production title"]}]}

Example 5:

Question: What are the names of signal boxes that can be reached by footpath or are at address 17 Quarry Lane?

Tables:
{"tables": [{"name": "locations", "columns": ["address", "location id"]}, {"name": "signal_boxes", "columns": ["location id", "name", "how to get there"]}]}

Example 6:

Question: Give the name of the tallest lighthouse.

Tables:
{"tables": [{"name": "lighthouse", "columns": ["name", "height"]}]}

Example 7:

Question: $question

Output Format: a JSON object with exactly the key "tables", whose value is the list of the tables of the schema; each table is a JSON object with exactly the keys "name" (the table name, a string) and "columns" (its column names, a list of strings). No other text.
Return an answer only in this exact Output Format.''')


class Relation(BaseModel):
    name: str
    columns: list[str]


class Schema(BaseModel):
    tables: list[Relation]


_LOCK = threading.Lock()
_DOCS: dict[str, np.ndarray] = {}


def _docs(lake) -> np.ndarray:
    """One vector per column of its "db.table.column" text in lower case, as the paper's
    union files write it; embedded once per lake, kept on disk and in memory."""
    with _LOCK:
        if lake.name not in _DOCS:
            texts = [c.path.lower() for c in lake.column_list]
            path = CACHE / lake.name / "docs.npz"
            kept = np.load(path) if path.exists() else None
            if kept is not None and kept["texts"].tolist() == texts:
                vectors = kept["vectors"]
            else:
                vectors = embed.embed(texts)
                path.parent.mkdir(parents=True, exist_ok=True)
                np.savez(path, texts=np.array(texts), vectors=vectors)
            _DOCS[lake.name] = vectors
        return _DOCS[lake.name]


def _clean(text: str) -> str:
    return "_".join(text.replace("/", " ").replace("-", " ").split())


def _probes(schema: Schema) -> list[str]:
    """Each hallucinated column as "table.column", as the released code writes it."""
    got = (f"{_clean(t.name)}.{_clean(c)}" for t in schema.tables for c in t.columns)
    return list(dict.fromkeys(p for p in got if not p.startswith(".") and not p.endswith(".")))


def _check(schema: Schema) -> None:
    if not _probes(schema):
        raise llm.ModelError("the schema has no table with a named column")


def run(lake, question, log_path, b=20):
    docs = _docs(lake)
    lap("setup")
    schema = llm.call(PROMPT.substitute(question=question), Schema, log_path,
                      f"crush4sql {question[:50]}", check=_check)
    lap("llm schema")
    probes = _probes(schema)
    cos = embed.embed(probes) @ docs.T
    pool = np.argsort(-cos.max(0), kind="stable")[:CANDIDATES]
    near = (1 + cos[:, pool]) / 2
    p = near / near.sum(1, keepdims=True)
    entropy = -(p * np.log(p)).sum(1)
    score = near / (1 + np.exp(entropy - entropy.mean()))[:, None]

    lap("search")
    columns = [lake.column_list[i] for i in pool]
    chosen, covered = [], np.zeros(len(probes), bool)
    while len(chosen) < min(b, len(columns)):
        if covered.all():
            covered[:] = False
        total = score.copy()
        total[covered] = -np.inf
        total[:, chosen] = -np.inf
        probe, n = np.unravel_index(np.argmax(total), total.shape)
        covered[probe] = True
        chosen.append(int(n))

    lap("choose")
    picked = [columns[n] for n in chosen]
    tables = list(dict.fromkeys(c.table for c in picked))
    # pick_order: b only stops the picking, so a smaller b's answer is its start (baselines/cut.py)
    return record(tables, [c.path for c in picked], levels=("columns", "tables"), probes=probes,
                  pick_order=[c.path for c in picked])
