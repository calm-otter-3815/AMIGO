"""What a baseline may read: the lake's tables, columns, declared keys and vectors.

Names follow the scorer: database.table and database.table.column, as stored.
"""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field

import numpy as np

from amigo import embed, index, layer
from amigo.clock import CLOCK, Clock, lap  # noqa: F401 - the baselines import them from here


@dataclass
class Column:
    path: str  # database.table.column
    table: str  # database.table
    name: str
    type: str
    description: str
    samples: list
    is_pk: bool


@dataclass
class Table:
    path: str  # database.table
    database: str
    name: str
    description: str
    row_count: int
    columns: list[Column] = field(default_factory=list)


class Lake:
    def __init__(self, name: str):
        self.name = name
        with closing(layer.open_layer(name)) as conn:
            self.paths = {r["name"]: r["path"] for r in conn.execute("SELECT name, path FROM databases")}
            rows = conn.execute(
                "SELECT t.id, d.name AS db, t.name, t.description, t.row_count FROM tables t"
                " JOIN databases d ON d.id = t.database_id ORDER BY t.id").fetchall()
            self.tables = [Table(f"{r['db']}.{r['name']}", r["db"], r["name"], r["description"] or "",
                                 r["row_count"]) for r in rows]
            by_id = {r["id"]: t for r, t in zip(rows, self.tables)}
            self.column_list: list[Column] = []
            column_of = {}
            for r in conn.execute(
                    "SELECT id, table_id, name, type, description, samples, is_pk FROM columns ORDER BY id"):
                t = by_id[r["table_id"]]
                c = Column(f"{t.path}.{r['name']}", t.path, r["name"], r["type"], r["description"] or "",
                           json.loads(r["samples"] or "[]"), bool(r["is_pk"]))
                t.columns.append(c)
                self.column_list.append(c)
                column_of[r["id"]] = c
            # the benchmark's own foreign keys only: the inferred links are AMIGO's
            self.keys: list[tuple[Column, Column]] = [
                (column_of[r["from_column"]], column_of[r["to_column"]])
                for r in conn.execute("SELECT from_column, to_column FROM links WHERE kind = 'declared'")
            ]
        self.table = {t.path: t for t in self.tables}
        self.column = {c.path: c for c in self.column_list}
        # the layer's vectors, row order = id order, as built by amigo.layer._embed
        self.table_vectors, self.column_vectors = layer.load_embeddings(name)

    def databases(self) -> list[str]:
        return list(self.paths)

    def in_database(self, database: str) -> list[Table]:
        return [t for t in self.tables if t.database == database]

    def rank_tables(self, text: str, among: list[Table] | None = None) -> list[tuple[Table, float]]:
        """Tables by cosine with `text`, best first."""
        vector = embed.embed([text])[0]
        scores = self.table_vectors @ vector
        pool = range(len(self.tables)) if among is None else [self.tables.index(t) for t in among]
        return sorted(((self.tables[i], float(scores[i])) for i in pool), key=lambda p: -p[1])

    def rank_columns(self, text: str) -> list[tuple[Column, float]]:
        vector = embed.embed([text])[0]
        scores = self.column_vectors @ vector
        return sorted(((self.column_list[i], float(scores[i])) for i in range(len(scores))), key=lambda p: -p[1])

    def schema_text(self, tables: list[Table], samples: int = 3, qualified: bool = True) -> str:
        """CREATE TABLE text with each column's type, description and a few stored values,
        and the declared foreign keys among `tables`. `qualified` names a table
        database.table; a prompt that writes SQL over one database names it bare."""

        def name(t: Table) -> str:
            return t.path if qualified else f'"{t.name}"'

        out = []
        for t in tables:
            lines = [f"-- {t.description}" if t.description else None, f"CREATE TABLE {name(t)} ("]
            for c in t.columns:
                values = ", ".join(str(v)[:40] for v in c.samples[:samples])
                note = " ".join(x for x in (c.description, f"Examples: {values}." if values else "") if x)
                lines.append(f'  "{c.name}" {c.type}{" PRIMARY KEY" if c.is_pk else ""},  -- {note}')
            for a, b in self.keys:
                target = self.table[b.table]
                if a.table == t.path and target in tables:
                    lines.append(f'  FOREIGN KEY ("{a.name}") REFERENCES {name(target)}("{b.name}"),')
            lines.append(");")
            out.append("\n".join(x for x in lines if x))
        return "\n\n".join(out)

    def reads(self, database: str, sql: str) -> tuple[list[str], list[str]]:
        """The tables and columns SQLite reads for `sql`, as lake paths (as the scorer reads gold)."""
        tables, columns = set(), set()

        def authorize(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and table:
                tables.add(table.lower())
                if column:
                    columns.add((table.lower(), column.lower()))
            return sqlite3.SQLITE_OK

        with closing(index.open_source(self.paths[database])) as conn:
            conn.set_authorizer(authorize)
            conn.execute("EXPLAIN " + sql)
        named = {t.name.lower(): t for t in self.in_database(database)}
        got_t = sorted(named[t].path for t in tables if t in named)
        got_c = sorted(c.path for t, col in columns if t in named
                       for c in named[t].columns if c.name.lower() == col)
        return got_t, got_c


def record(tables: list[str], columns: list[str] = (), levels=("tables",), **extra) -> dict:
    """One result in the scorer's format: one interpretation. A table retriever fills
    `tables` only, best first, and is scored at the table level; a method that writes SQL
    gives the columns its query reads and is scored at all three levels."""
    return {
        "picked": sorted(columns),
        "interpretations": [{"tables": sorted(tables), "bound": sorted(columns), "joins": []}],
        "levels": list(levels),
        "order": list(tables),
        **extra,
    }


def unit(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12)
