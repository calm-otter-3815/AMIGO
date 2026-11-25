"""The probe protocol from PLAN.md section 5: the parts Stage 1 needs."""

import logging
from contextlib import closing
from itertools import combinations, product

import numpy as np

from . import config, cutoff, embed, index, layer

log = logging.getLogger(__name__)

# the longest list of stored values word_values keeps, in characters: a word found all over
# a free-text column gives megabytes of text, and a run over a whole benchmark asks for some
# 10,000 (column, words) pairs, so the kept lists stay near 100 MB at most
WORDS_KEPT_CHARS = 10_000


def _norm(value) -> str | None:
    """The SQL `norm` function. Its argument arrives as bytes, from CAST(... AS BLOB):
    SQLite hands a text argument over as strict UTF-8, and one spider row is not."""
    return None if value is None else index.normalise(value.decode("utf-8", "replace"))


class Probe:
    """One opened lake: cards, links and the column embedding matrix, loaded once."""

    def __init__(self, lake_name: str) -> None:
        self.lake_name = lake_name
        self.conn = layer.open_layer(lake_name)
        # the table vectors serve the baselines (baselines/lake.py); AMIGO searches columns only
        _, self.matrix = layer.load_embeddings(lake_name)
        built = layer._meta(self.conn, "embedding_revision")
        if built != config.EMBEDDING_REVISION:
            raise ValueError(
                f"probe: lake {lake_name!r} was embedded with model revision {built}, and"
                f" questions are embedded with {config.EMBEDDING_REVISION}: rebuild its embed step"
            )
        self.meanings = layer.load_meanings(lake_name)
        self.tables = {
            row["id"]: row
            for row in self.conn.execute(
                "SELECT t.*, d.name AS database, d.readable AS database_readable,"
                " d.path AS database_path"
                " FROM tables t JOIN databases d ON d.id = t.database_id ORDER BY t.id"
            )
        }
        self.columns = {
            row["id"]: row for row in self.conn.execute("SELECT * FROM columns ORDER BY id")
        }
        self.links = [dict(row) for row in self.conn.execute("SELECT * FROM links ORDER BY id")]
        self.blooms = {
            row["column_id"]: index.Bloom.from_bytes(row["bits"])
            for row in self.conn.execute("SELECT column_id, bits FROM blooms")
        }
        # row k of the matrix is the column with id k + 1, so the ids must be 1..n
        if sorted(self.columns) != list(range(1, len(self.matrix) + 1)):
            raise ValueError(
                f"probe: lake {lake_name!r} has {len(self.columns)} column cards but"
                f" {len(self.matrix)} column vectors with ids"
                f" {min(self.columns, default=0)}..{max(self.columns, default=0)}"
            )
        # row k: whether the column with id k + 1 sits in a table with no rows
        self.in_empty_table = np.array(
            [self.tables[c["table_id"]]["row_count"] == 0 for c in self.columns.values()],
            dtype=bool,
        )
        # role cards: the column a link points at, named by the link's words
        self.roles = [dict(row) for row in self.conn.execute("SELECT * FROM roles ORDER BY id")]
        self.role_matrix = layer.load_roles(lake_name)
        if len(self.roles) != len(self.role_matrix):
            raise ValueError(
                f"probe: lake {lake_name!r} has {len(self.roles)} role cards but"
                f" {len(self.role_matrix)} role vectors: rebuild its embed step"
            )
        self.role_columns = np.array([role["column_id"] - 1 for role in self.roles], dtype=int)
        self.table_ids = {self.path("table", t): t for t in self.tables}
        self.column_ids = {self.path("column", c): c for c in self.columns}
        # the answers of word_values so far: the lake never changes, so the same scan runs once
        self._words: dict[tuple[int, str], list[str]] = {}

    def path(self, kind: str, card_id: int) -> str:
        """Where a card lives, in original names: database.table[.column]."""
        if kind == "table":
            table = self.tables[card_id]
            return f"{table['database']}.{table['name']}"
        column = self.columns[card_id]
        table = self.tables[column["table_id"]]
        return f"{table['database']}.{table['name']}.{column['name']}"

    def find(self, name: str) -> tuple[str, int]:
        """The card at a path, the inverse of `path`."""
        if name in self.table_ids:
            return "table", self.table_ids[name]
        if name in self.column_ids:
            return "column", self.column_ids[name]
        raise KeyError(f"probe: no table or column named {name!r}")

    def peek(self, column_id: int, n: int, text_only: bool = False) -> list[str]:
        """`n` distinct non-null values, read from the source database itself; with
        `text_only`, only the ones stored as text."""
        column = self.columns[column_id]
        table = self.tables[column["table_id"]]
        name, table_name = index._quote(column["name"]), index._quote(table["name"])
        where = f"WHERE {name} IS NOT NULL"
        if text_only:
            where += f" AND typeof({name}) = 'text' AND trim({name}) <> ''"
        with closing(index.open_source(table["database_path"])) as source:
            return [
                str(row[0])
                for row in source.execute(
                    f"SELECT DISTINCT {name} FROM {table_name} {where} LIMIT ?", (n,)
                )
            ]

    def _stored_exact(self, column_id: int, text: str) -> list[str]:
        """The stored spellings of one value, read from the source database itself."""
        column = self.columns[column_id]
        table = self.tables[column["table_id"]]
        name = index._quote(column["name"])
        table_name = index._quote(table["name"])
        with closing(index.open_source(table["database_path"])) as source:
            # cheap path first: an exact, case-insensitive match needs no per-row scan
            exact = [
                str(row[0])
                for row in source.execute(
                    f"SELECT DISTINCT {name} FROM {table_name} WHERE lower({name}) = lower(?)",
                    (text,),
                )
            ]
            if exact:
                return exact
            # the Bloom filter matches on the normalised form, so the lookup behind it
            # must too, or "St Louis" would miss the stored "St. Louis"
            source.create_function("norm", 1, _norm, deterministic=True)
            return [
                str(row[0])
                for row in source.execute(
                    f"SELECT DISTINCT {name} FROM {table_name}"
                    f" WHERE norm(CAST({name} AS BLOB)) = ?",
                    (index.normalise(text),),
                )
            ]

    def stored_values(self, column_id: int, text: str) -> list[str]:
        """The values a text column really holds for `text`, as they are stored.

        Three levels, the first one that matches wins: the value itself, then the
        value with its last word in the other number ("saving" for "savings") or with
        words trimmed off, then containment either way in whole words
        (index.word_pattern one way), or a stored code that starts a one-word value ("F"
        for "female"; "Mary Smith" is a name, not an "M"). Letters inside a word do not
        count: "Hamilton" does not hold "M". No fuzzy matching. A column with a Bloom
        filter, too many values to list, gets the word pattern alone at the third level.
        """
        column = self.columns[column_id]
        wanted = index.normalise(text)
        if column["kind"] != "text" or not wanted:
            return []
        tried = [text, *index.inflections(text), *index.variants(text)]
        if column_id in self.blooms:
            # too many values to list, so the Bloom filter says which ones to ask for
            bloom = self.blooms[column_id]
            for one in tried:
                if index.normalise(one) not in bloom:
                    continue
                # a Bloom filter can say yes to a value that is not there, and it
                # matches on the normalised form, which the exact lookup does not
                hits = self._stored_exact(column_id, one)
                if hits:
                    return hits
            return self.word_values(column_id, text)
        # no Bloom filter means at most EXACT_VALUE_LIMIT distinct text values, whatever
        # the profile's count of every type says
        stored = [
            (index.normalise(v), v)
            for v in self.peek(column_id, config.EXACT_VALUE_LIMIT, text_only=True)
        ]
        for one in tried:
            asked = index.normalise(one)
            hits = [value for norm, value in stored if norm == asked]
            if hits:
                return hits
        words = wanted.split()
        pattern = index.word_pattern(text)
        return [
            value
            for norm, value in stored
            if norm
            and (
                (pattern is not None and pattern.search(value.lower()))
                or f" {norm} " in f" {wanted} "
                or (len(words) == 1 and words[0].startswith(norm))
            )
        ]

    def split_value(
        self, text: str, table_id: int | None = None
    ) -> list[list[tuple[int, str]]]:
        """A value stored over several columns of one row: "Lewis Hamilton" in two name columns.

        The words are cut into 2 parts, then 3, keeping their order. Each part must be
        stored whole in its own text column of one table, and one row must hold every
        part, or a Lewis and a Hamilton from two different rows would pass. A group is
        (column id, stored value) per part, in the value's order; the first number of
        parts that finds a group wins. `table_id` looks in that table only.
        """
        words = text.split()
        where: dict[str, list[int]] = {}
        for size in range(2, min(len(words), config.SPLIT_PARTS) + 1):
            groups = []
            for cuts in combinations(range(1, len(words)), size - 1):
                ends = list(zip((0, *cuts), (*cuts, len(words))))
                parts = [" ".join(words[start:end]) for start, end in ends]
                for part in parts:
                    if part not in where:
                        where[part] = [
                            c
                            for c in self.lookup_value(part)
                            if table_id in (None, self.columns[c]["table_id"])
                        ]
                for columns in product(*(where[part] for part in parts)):
                    tables = {self.columns[c]["table_id"] for c in columns}
                    if len(set(columns)) < size or len(tables) > 1:
                        continue
                    row = self._one_row(columns, parts)
                    if row is not None:
                        groups.append(list(zip(columns, row)))
            if groups:
                return groups
        return []

    def _one_row(self, columns: tuple[int, ...], parts: list[str]) -> tuple[str, ...] | None:
        """The stored values of the first row that holds each part in its own column."""
        table = self.tables[self.columns[columns[0]]["table_id"]]
        names = [index._quote(self.columns[c]["name"]) for c in columns]
        where = " AND ".join(f"norm(CAST({name} AS BLOB)) = ?" for name in names)
        with closing(index.open_source(table["database_path"])) as source:
            source.create_function("norm", 1, _norm, deterministic=True)
            row = source.execute(
                f"SELECT {', '.join(names)} FROM {index._quote(table['name'])}"
                f" WHERE {where} LIMIT 1",
                [index.normalise(part) for part in parts],
            ).fetchone()
        return None if row is None else tuple(str(value) for value in row)

    def neighbours(self, table_id: int) -> list[dict]:
        """The links from this table to a different one, in either direction."""
        found = []
        for link in self.links:
            ends = (link["from_column"], link["to_column"])
            a, b = (self.columns[column_id]["table_id"] for column_id in ends)
            if a == b or table_id not in (a, b):
                continue
            found.append(
                {
                    "table_id": b if a == table_id else a,
                    "from_column": link["from_column"],
                    "to_column": link["to_column"],
                    "kind": link["kind"],
                    "score": link["score"],
                }
            )
        return found

    def search_cards(self, text: str) -> tuple[list[dict], np.ndarray]:
        """The top-k columns by cosine to `text`, best first, and every cosine.

        Columns of empty tables have their own few slots after the main list: they hold
        no values to check, and a lake with many of them would crowd out the columns
        that do. A column scores the best of its full text, its meaning alone and its role
        cards: long example values can drown the meaning, short ones help name a coded
        column, and a link's name ("winner") can say what the column's own text does not.
        """
        vector = embed.embed([text])[0]
        scores = np.maximum(self.matrix @ vector, self.meanings @ vector)
        if len(self.roles):
            np.maximum.at(scores, self.role_columns, self.role_matrix @ vector)
        main = np.flatnonzero(~self.in_empty_table)
        empty = np.flatnonzero(self.in_empty_table)
        picked = np.concatenate([
            main[cutoff.top(scores[main], config.TOP_COLUMNS)],
            empty[cutoff.top(scores[empty], config.TOP_EMPTY_COLUMNS)],
        ]).astype(int)
        kept = [{**dict(self.columns[i + 1]), "score": float(scores[i])} for i in picked]
        return kept, scores

    def lookup_words(self, text: str, skip: frozenset[str] = frozenset()) -> dict[int, list[str]]:
        """Per text column whose values hold `text` as a run of whole words, those stored
        values, read from the source database itself (index.word_pattern). No column of
        the databases in `skip` is read: reading one is a scan of its whole table."""
        wanted = sorted(set(index.words(text)))
        if not wanted:
            return {}
        marks = ", ".join("?" * len(wanted))
        columns = [
            column_id
            for (column_id,) in self.conn.execute(
                f"SELECT column_id FROM value_words WHERE word IN ({marks})"
                " GROUP BY column_id HAVING count(*) = ? ORDER BY column_id",
                (*wanted, len(wanted)),
            )
            if self.tables[self.columns[column_id]["table_id"]]["database"] not in skip
        ]
        found = {c: self.word_values(c, text) for c in columns}
        return {c: values for c, values in found.items() if values}

    def stores(self, column_id: int, number: float) -> bool:
        """Whether one row of the column holds `number`; a text column holds 3541 as "3541"."""
        column = self.columns[column_id]
        table = self.tables[column["table_id"]]
        name, table_name = index._quote(column["name"]), index._quote(table["name"])
        value = int(number) if float(number).is_integer() else number
        with closing(index.open_source(table["database_path"])) as source:
            return source.execute(
                f"SELECT 1 FROM {table_name} WHERE {name} = ? LIMIT 1", (value,)
            ).fetchone() is not None

    def word_values(self, column_id: int, text: str) -> list[str]:
        """The stored values of one column that hold `text` as a run of whole words."""
        pattern = index.word_pattern(text)
        if pattern is None:
            return []
        key = (column_id, pattern.pattern)
        if key in self._words:
            return self._words[key]
        column = self.columns[column_id]
        table = self.tables[column["table_id"]]
        name, table_name = index._quote(column["name"]), index._quote(table["name"])
        # the longest word narrows the scan; the pattern decides
        longest = max(index.words(text), key=len)
        with closing(index.open_source(table["database_path"])) as source:
            found = [
                value
                for (value,) in source.execute(
                    f"SELECT DISTINCT {name} FROM {table_name}"
                    f" WHERE typeof({name}) = 'text' AND lower({name}) LIKE ?",
                    (f"%{longest}%",),
                )
                if pattern.search(value.lower())
            ]
        if sum(map(len, found)) <= WORDS_KEPT_CHARS:
            self._words[key] = found
        return found

    def lookup_value(self, text: str) -> list[int]:
        value = index.normalise(text)
        exact = {
            row[0]
            for row in self.conn.execute(
                "SELECT DISTINCT column_id FROM text_values WHERE value = ?", (value,)
            )
        }
        return sorted(exact | {c for c, bloom in self.blooms.items() if value in bloom})

