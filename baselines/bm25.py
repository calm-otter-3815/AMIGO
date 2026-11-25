"""BM25 table retrieval: the k tables whose text best matches the question's words, by
SQLite FTS5's bm25 (k1 = 1.2, b = 0.75, its defaults) with the porter stemmer. A table's
text is its database, its name, its description and every column name. No vectors and
no LLM call: the lexical baseline beside dense.
"""

import re
import sqlite3
import threading

from .lake import lap, record

_INDEX: dict[str, sqlite3.Connection] = {}
_LOCK = threading.Lock()


def query(question: str) -> str:
    """Every word of the question, quoted, joined by OR."""
    return " OR ".join(f'"{w}"' for w in re.findall(r"[a-z0-9]+", question.lower()))


def rank(lake, question: str) -> list[str]:
    """The paths of the tables that share a word with the question, best first."""
    with _LOCK:
        if lake.name not in _INDEX:
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            conn.execute("CREATE VIRTUAL TABLE docs USING fts5(body, tokenize='porter unicode61')")
            conn.executemany("INSERT INTO docs (rowid, body) VALUES (?, ?)", [
                (i, " ".join([t.database, t.name, t.description, *(c.name for c in t.columns)]))
                for i, t in enumerate(lake.tables)])
            _INDEX[lake.name] = conn
        words = query(question)
        if not words:
            return []
        rows = _INDEX[lake.name].execute("SELECT rowid FROM docs WHERE docs MATCH ? ORDER BY bm25(docs)",
                                         (words,)).fetchall()
    return [lake.tables[i].path for (i,) in rows]


def run(lake, question, log_path, k=5):
    rank(lake, "")  # the index, once per lake
    lap("setup")
    ranked = rank(lake, question)
    lap("search")
    if not ranked:
        return record([], fallback="no word of the question is in any table")
    return record(ranked[:k])
