"""Step 3: candidates for each gold item the question names (code and a small embedding model).

  .venv/bin/python -m labeler.pool

For each table or column that step 2 tied to words of the question (join columns and
items with no words have no candidates), every table or column of the lake is ranked by
four signals that belong to no retrieval method under test, and the top TOP of each kept
(TOP_MEANING for meaning, the signal most often right):
  meaning   cosine between the words (with the question) and the item's name, type and
            sample values, embedded by Qwen3-Embedding-0.6B (not AMIGO's granite model);
  keyword   BM25 over table or column names;
  spelling  difflib similarity between the words and the bare name (temp ~ temperature);
  value     columns of the lake holding the gold literal of a filter column;
plus copy: tables of the lake that hold every column name and nearly all rows of a gold
table (and their same-named columns). The gold item is left out of its own candidates;
`gold_found_by` says which signals would have ranked it in their top TOP, a check that the
signals find what they should. DECOYS columns (or tables) from the bottom half of the
meaning ranking are added as planted wrong answers for the judge.
Code settles what needs no judge: id-like columns are dropped unless the gold is one; a
table item is skipped when a column of that table is judged (a column accepted elsewhere
already names its table); copies are marked; a candidate with the same column name and
nearly the same values as another (X and X_HIST) is marked a clone of it, judged once.
Writes runs/labeler/pool.jsonl.
"""

import difflib
import json
import math
import random
import re
import sqlite3
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import numpy as np

from labeler import OUT, column_of, databases, full, read, run, split_item, table_of
from labeler.gold import connect, ident

TOP = 10
TOP_MEANING = 20
TOP_VALUE = 50  # a value stored in more columns (Yes, 0 in taco_us) keeps those closest in meaning; the old lakes reach 35
DECOYS = 1
CLONE_SHARE = 0.95
CLONE_MIN = 20  # fewer distinct values say too little to call two columns clones
SAMPLES = 3
COPY_SHARE = 0.95
COPY_MIN = 5
COPY_ROWS = 500_000
NAME = 200  # longest name shown to the models (taco_us has column names of thousands of characters)
WIDE = 900  # columns flagged per query: SQLite returns at most 2000 columns (taco_us has a table of 1217)
SCANS = 8  # tables scanned at once by hold()
BATCH = 50_000  # columns: a wider lake (taco_us; the others have under 5,000) looks up all gold values in one pass
TEXT = ("CHAR", "CLOB", "TEXT", "DATE", "TIME")  # SQLite keeps dates and times as text
EMBEDDER = "Qwen/Qwen3-Embedding-0.6B"
TASK = ("Instruct: Given words from a question asked to a database, find the database {kind} "
        "that holds what these words mean in that question\nQuery: ")


def short(name: str) -> str:
    """A name as shown to the models: line breaks made spaces and cut at NAME characters
    (names that need neither, every name of the lakes labeled before taco_us, stay as they are)."""
    if len(name) <= NAME and not any(c in name for c in "\n\r\t"):
        return name
    name = " ".join(name.split())
    return name if len(name) <= NAME else name[:NAME - 3] + "..."


def words(text: str) -> list[str]:
    """Lower-case word stems: split on non-letters and camelCase, trailing s dropped."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return [w.lower().removesuffix("s") for w in re.findall(r"[A-Za-z]+|\d+", text)]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75):
        self.docs, self.k1, self.b = [Counter(d) for d in docs], k1, b
        self.size = [len(d) for d in docs]
        self.mean = sum(self.size) / max(len(docs), 1)
        df = Counter(w for d in self.docs for w in d)
        self.idf = {w: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for w, n in df.items()}

    def top(self, query: list[str], k: int) -> list[int]:
        scores = []
        for i, doc in enumerate(self.docs):
            s = sum(
                self.idf[w] * doc[w] * (self.k1 + 1)
                / (doc[w] + self.k1 * (1 - self.b + self.b * self.size[i] / self.mean))
                for w in query if w in doc
            )
            if s > 0:
                scores.append((s, i))
        return [i for _, i in sorted(scores, reverse=True)[:k]]


_model = None


def embed(texts: list[str], prompt: str | None = None) -> np.ndarray:
    """Unit vectors for `texts`, on the GPU memory vLLM leaves free."""
    global _model
    if _model is None:
        import torch
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDER, device="cuda", model_kwargs={"torch_dtype": torch.float16})
        _model.max_seq_length = 256
    return _model.encode(texts, prompt=prompt, batch_size=64, normalize_embeddings=True)


class Lake:
    """Every table (db.table) and column (db.table.column) of a lake, with what the judge
    and the embedder are shown for each."""

    def __init__(self, lake: str):
        self.name, self.paths = lake, databases(lake)
        self.columns: dict[str, list[tuple[str, str]]] = defaultdict(list)  # db.table -> (column, type)
        self.shown: dict[str, str] = {}
        saved = OUT / "emb" / f"{lake}-shown.json"  # sampling values reads whole tables: do it once
        if saved.exists():
            columns, self.shown = json.loads(saved.read_text())
            self.columns.update({t: [tuple(c) for c in cs] for t, cs in columns.items()})
        for db, path in self.paths.items() if not saved.exists() else ():
            with closing(connect(path)) as conn:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'")]
                for table in tables:
                    full = f"{db}.{table}"
                    for row in conn.execute(f"PRAGMA table_info({ident(table)})"):
                        column, kind = row[1], (row[2] or "").upper()
                        self.columns[full].append((column, kind))
                        values = [str(v[0])[:40] for v in conn.execute(
                            f"SELECT DISTINCT {ident(column)} FROM {ident(table)} WHERE {ident(column)} IS NOT NULL LIMIT {SAMPLES}")]
                        self.shown[f"{full}.{column}"] = f"{short(table)}.{short(column)} ({kind or 'ANY'}) values: " + ", ".join(values)
                    self.shown[full] = f"{short(table)} columns: " + ", ".join(short(c) for c, _ in self.columns[full][:20])
        if not saved.exists():
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_text(json.dumps([self.columns, self.shown]))
        self.tables = sorted(self.columns)
        self.flat = [f"{t}.{c}" for t in self.tables for c, _ in self.columns[t]]
        # SQLite names ignore case; the gold SQL may spell a table or column differently
        self.case = {n.lower(): n for n in self.tables + self.flat}
        self.bm25 = {"table": BM25([words(t.split(".", 1)[1]) for t in self.tables]),
                     "column": BM25([words(c.split(".", 1)[1]) for c in self.flat])}
        self.vectors = {kind: self._vectors(kind, names) for kind, names in (("table", self.tables), ("column", self.flat))}
        self._copies: dict[str, list[str]] = {}
        self._held: dict[str, list[str]] = {}
        self._values: dict[str, set[str]] = {}

    def names(self, kind: str) -> list[str]:
        return self.tables if kind == "table" else self.flat

    def _vectors(self, kind: str, names: list[str]) -> np.ndarray:
        path = OUT / "emb" / f"{self.name}-{kind}.npy"
        if path.exists():
            return np.load(path)
        vectors = embed([self.shown[n] for n in names])
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, vectors)
        return vectors

    def meaning(self, kind: str, phrase: str, question: str) -> np.ndarray:
        """Indices of all tables or columns, most similar in meaning first."""
        query = embed([f"{phrase} (in the question: {question})"], prompt=TASK.format(kind=kind))[0]
        return np.argsort(-(self.vectors[kind] @ query))

    def spelling(self, kind: str, phrase: str, k: int) -> list[int]:
        target = " ".join(words(phrase))
        bare = [" ".join(words(n.split(".", 2)[-1])) for n in self.names(kind)]  # a column name may hold a dot
        scores = [(difflib.SequenceMatcher(None, target, b).ratio(), i) for i, b in enumerate(bare)]
        return [i for _, i in sorted(scores, reverse=True)[:k]]

    def holding(self, literal: str) -> list[str]:
        """Text columns of the lake that hold `literal`, exact first, else lower case.
        One pass per table flags its text columns, WIDE at a time."""
        if literal not in self._held:
            exact, nocase = [], []
            for table in self.tables:
                db, name = table.split(".", 1)
                text = [c for c, kind in self.columns[table] if not kind or any(t in kind for t in TEXT)]
                if not text:
                    continue
                with closing(connect(self.paths[db])) as conn:
                    for start in range(0, len(text), WIDE):
                        part = text[start:start + WIDE]
                        flags = ", ".join(f"max({ident(c)} = :v), max(lower({ident(c)}) = lower(:v))" for c in part)
                        got = conn.execute(f"SELECT {flags} FROM {ident(name)}", {"v": literal}).fetchone()
                        for i, column in enumerate(part):
                            if got[2 * i]:
                                exact.append(f"{table}.{column}")
                            if got[2 * i + 1]:
                                nocase.append(f"{table}.{column}")
            self._held[literal] = exact or nocase
        return self._held[literal]

    def hold(self, literals: list[str]) -> None:
        """holding() for many literals at once, for a lake too big to scan once per value: one
        pass per table collects which of the literals each text column holds, as stored and in
        lower case. Kept in emb/<lake>-held.json, so a restarted run does not scan again."""
        path = OUT / "emb" / f"{self.name}-held.json"
        saved = json.loads(path.read_text()) if path.exists() else {}
        todo = sorted(set(literals) - set(saved))
        if todo:
            with closing(sqlite3.connect(":memory:")) as conn:  # SQLite's lower(), as the scan compares
                lower = {v: conn.execute("SELECT lower(?)", (v,)).fetchone()[0] for v in todo}
            given = f"WITH lits(v) AS (VALUES {', '.join('(?)' for _ in todo)}), low(v) AS (SELECT lower(v) FROM lits)"

            def scan(table: str) -> list[tuple[str, list, list]]:
                db, name = table.split(".", 1)
                text = [c for c, kind in self.columns[table] if not kind or any(t in kind for t in TEXT)]
                hits = []
                with closing(connect(self.paths[db])) as conn:
                    for start in range(0, len(text), WIDE):
                        part = text[start:start + WIDE]
                        flags = ", ".join(f"json_group_array(DISTINCT {ident(c)}) FILTER (WHERE {ident(c)} IN lits), "
                                          f"json_group_array(DISTINCT lower({ident(c)})) FILTER (WHERE lower({ident(c)}) IN low)"
                                          for c in part)
                        got = conn.execute(f"{given} SELECT {flags} FROM {ident(name)}", todo).fetchone()
                        hits += [(f"{table}.{c}", json.loads(got[2 * i]), json.loads(got[2 * i + 1]))
                                 for i, c in enumerate(part) if got[2 * i + 1] != "[]"]
                return hits

            with ThreadPoolExecutor(SCANS) as pool:
                hits = [h for found in pool.map(scan, self.tables) for h in found]
            for v in todo:
                saved[v] = [c for c, exact, _ in hits if v in exact] or [c for c, _, low in hits if lower[v] in low]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(saved))
        self._held.update(saved)

    def values(self, column: str) -> set[str]:
        """Up to CLONE_ROWS distinct values of db.table.column, as lower-case text."""
        if column not in self._values:
            db, table, name = column.split(".", 2)
            with closing(connect(self.paths[db])) as conn:
                self._values[column] = {r[0] for r in conn.execute(
                    f"SELECT DISTINCT lower(CAST({ident(name)} AS TEXT)) FROM {ident(table)} WHERE {ident(name)} IS NOT NULL LIMIT 2000")}
        return self._values[column]

    def rows(self, table: str, columns: list[str]) -> set[tuple]:
        db, name = table.split(".", 1)
        picked = ", ".join(f"lower(CAST({ident(c)} AS TEXT))" for c in columns)
        with closing(connect(self.paths[db])) as conn:
            return set(conn.execute(f"SELECT DISTINCT {picked} FROM {ident(name)} LIMIT {COPY_ROWS}"))

    def copies(self, table: str) -> list[str]:
        """Other tables holding every column name of `table` and at least COPY_SHARE of
        its rows, over at least COPY_MIN rows."""
        if table not in self._copies:
            mine = [c for c, _ in self.columns[table]]
            want = {c.lower() for c in mine}
            rows = self.rows(table, mine) if mine else set()
            found = []
            if len(rows) >= COPY_MIN:
                for other in self.tables:
                    theirs = {c.lower(): c for c, _ in self.columns[other]}
                    if other != table and want <= set(theirs):
                        held = rows & self.rows(other, [theirs[c.lower()] for c in mine])
                        if len(held) >= COPY_SHARE * len(rows):
                            found.append(other)
            self._copies[table] = found
        return self._copies[table]


def keylike(name: str) -> bool:
    """An id or key column by its name: ..._id, ..._key, uuid, CustomerId."""
    bare = name.rsplit(".", 1)[-1]
    return bool(re.search(r"(^|_)(id|key|uuid|rowid)$", bare, re.I) or re.search(r"[a-z](Id|ID|Key)$", bare))


def clones(lake: "Lake", found: list[dict]) -> list[dict]:
    """Mark a candidate as `clone_of` an earlier one with the same column name and at least
    CLONE_SHARE of the smaller value set in common (over CLONE_MIN values)."""
    firsts: dict[str, list[str]] = defaultdict(list)
    for c in found:
        bare = column_of(c["name"]).lower()
        mine = lake.values(c["name"])
        for first in firsts[bare]:
            theirs = lake.values(first)
            small = min(len(mine), len(theirs))
            if small >= CLONE_MIN and len(mine & theirs) >= CLONE_SHARE * small:
                c["clone_of"] = first
                break
        else:
            firsts[bare].append(c["name"])
    return found


def grouped(items: list[dict], cross: bool = False) -> list[dict]:
    """Columns of one table tied to the same words become one item: the words ask for a
    record of that table (several columns), so its alternatives are other tables. `cross`:
    the items are named db.table.column (a question across databases)."""
    def key(i: dict) -> tuple | None:
        return (split_item(i["item"], cross)[0], i["words"]) if i["words"] and i["role"] not in ("join", "table") else None

    by = defaultdict(list)
    for i in items:
        if key(i):
            by[key(i)].append(i)
    out, seen = [], set()
    for i in items:
        group = by.get(key(i), [])
        if len(group) < 2:
            out.append(i)
        elif key(i) not in seen:
            seen.add(key(i))
            out.append({"item": key(i)[0], "role": group[0]["role"], "words": key(i)[1], "note_only": False,
                        "columns": [split_item(g["item"], cross)[1] for g in group]})
    return out


def candidates(lake: Lake, row: dict, item: dict) -> dict:
    kind = "table" if item["role"] == "table" or "columns" in item else "column"
    names = lake.names(kind)
    gold = lake.case.get(full(row, item["item"]).lower(), full(row, item["item"]))
    shown = lake.shown[gold] if "columns" not in item else f"{item['item']} columns: " + ", ".join(item["columns"])
    ranked = lake.meaning(kind, item["words"], row["question"])
    signals = {
        "meaning": [names[i] for i in ranked[:TOP_MEANING]],
        "keyword": [names[i] for i in lake.bm25[kind].top(words(item["words"]), TOP)],
        "spelling": [names[i] for i in lake.spelling(kind, item["words"], TOP)],
    }
    literal = next((x["text"] for x in row["literals"] if x["column"] == item["item"]), None)
    if literal and kind == "column":
        held = lake.holding(literal)
        if len(held) > TOP_VALUE:
            rank = {names[i]: r for r, i in enumerate(ranked)}
            held = sorted(held, key=rank.__getitem__)[:TOP_VALUE]
        signals["value"] = held
    table = gold if kind == "table" else table_of(gold)
    copies = lake.copies(table) if table in lake.columns else []
    signals["copy"] = copies if kind == "table" else [
        f"{c}.{col}" for c in copies for col, _ in lake.columns[c] if col.lower() == column_of(gold).lower()]
    found = defaultdict(list)
    for signal, hits in signals.items():
        for name in hits:
            found[name].append(signal)
    if kind == "column" and not keylike(gold):
        found = defaultdict(list, {n: s for n, s in found.items() if n == gold or not keylike(n)})
    rng = random.Random(f"{row['id']}{item['item']}")
    bottom = [names[i] for i in ranked[len(ranked) // 2:] if names[i] not in found]
    return {**item, "kind": kind, "gold": gold, "gold_shown": shown, "literal": literal,
            "gold_found_by": found.pop(gold, []),
            "candidates": clones(lake, [{"name": n, "sources": s} for n, s in sorted(found.items())]) if kind == "column"
            else [{"name": n, "sources": s} for n, s in sorted(found.items())],
            "decoys": rng.sample(bottom, min(DECOYS, len(bottom)))}


def main() -> None:
    rows = {r["id"]: r for r in read("questions")}
    linked = [r for r in read("link") if r["items"]]
    lakes: dict[str, Lake] = {}
    lock = threading.Lock()

    def one(record: dict) -> dict:
        row = rows[record["id"]]
        with lock:
            if row["lake"] not in lakes:
                lakes[row["lake"]] = Lake(row["lake"])
                if len(lakes[row["lake"]].flat) > BATCH:  # as go.py: every gold value of the run in one pass
                    lakes[row["lake"]].hold([x["text"] for r in rows.values() if r["lake"] == row["lake"] for x in r["literals"]])
            lake = lakes[row["lake"]]
            cross = "db_ids" in row
            items = grouped(record["items"], cross)
            covered = {i["item"] if "columns" in i else split_item(i["item"], cross)[0]
                       for i in items if i["words"] and i["role"] not in ("join", "table")}
            items = [candidates(lake, row, i) if i["words"] and i["role"] != "join"
                     and not (i["role"] == "table" and i["item"] in covered)
                     else {**i, "candidates": [], **({"covered": True} if i["role"] == "table" and i["item"] in covered else {})}
                     for i in items]
        return {"id": record["id"], "items": items}

    def note() -> str:
        done = read("pool")
        named = [i for r in done for i in r["items"] if "gold_found_by" in i]
        found = sum(bool(i["gold_found_by"]) for i in named)
        size = sum(len(i["candidates"]) for i in named) / max(len(named), 1)
        return f"gold found by a signal {found}/{len(named)}  ~{size:.0f} candidates per item"

    linked.sort(key=lambda r: rows[r["id"]]["lake"])
    run("pool", linked, one, colour="blue", threads=1, note=note)


if __name__ == "__main__":
    main()
