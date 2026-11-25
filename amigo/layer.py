"""The two files per lake: layer.sqlite and embeddings.npz (PLAN.md 2.3 and 2.4)."""

import json
import logging
import re
import sqlite3
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from itertools import groupby
from pathlib import Path

import numpy as np
from tqdm import tqdm

from . import config, embed, index, links, llm, names, profile

log = logging.getLogger(__name__)

# glued name pieces per model call; also the most columns one describe call is shown
NAMES_PER_CALL = 100
# describe calls in flight: with 48 eval workers, under vLLM's 128 sequences
DESCRIBE_WORKERS = 32
# column names of a table the link judge is shown, and its calls in flight
JUDGE_NAMES = 25
JUDGE_WORKERS = 8
# role words come from links at least this good to join on
ROLE_QUALITY = 0.8
# words of key column names that name no role
KEY_WORDS = frozenset({"id", "key", "fk", "ref", "code", "no", "num"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS databases(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    readable TEXT NOT NULL, path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tables(id INTEGER PRIMARY KEY,
    database_id INTEGER NOT NULL REFERENCES databases(id),
    name TEXT NOT NULL, readable TEXT NOT NULL, description TEXT, description_source TEXT,
    row_count INTEGER NOT NULL, primary_key TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS columns(id INTEGER PRIMARY KEY,
    table_id INTEGER NOT NULL REFERENCES tables(id),
    name TEXT NOT NULL, readable TEXT NOT NULL, type TEXT NOT NULL, is_pk INTEGER NOT NULL,
    kind TEXT, description TEXT, description_source TEXT, value_description TEXT,
    distinct_count INTEGER, empty_share REAL, samples TEXT, is_unique INTEGER,
    min, max, date_format TEXT, date_min TEXT, date_max TEXT, date_failures INTEGER);
CREATE TABLE IF NOT EXISTS links(id INTEGER PRIMARY KEY,
    from_column INTEGER NOT NULL REFERENCES columns(id),
    to_column INTEGER NOT NULL REFERENCES columns(id), kind TEXT NOT NULL, score REAL NOT NULL,
    grp INTEGER);
CREATE TABLE IF NOT EXISTS text_values(column_id INTEGER NOT NULL REFERENCES columns(id),
    value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS text_values_value ON text_values(value);
CREATE TABLE IF NOT EXISTS blooms(column_id INTEGER PRIMARY KEY REFERENCES columns(id),
    bits BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS value_words(word TEXT NOT NULL,
    column_id INTEGER NOT NULL REFERENCES columns(id), PRIMARY KEY(word, column_id)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS roles(id INTEGER PRIMARY KEY,
    column_id INTEGER NOT NULL REFERENCES columns(id), link_id INTEGER NOT NULL REFERENCES links(id),
    words TEXT NOT NULL, via TEXT NOT NULL);
"""


def paths(lake_name: str) -> tuple[Path, Path]:
    folder = config.LAKES_DIR / lake_name
    return folder / "layer.sqlite", folder / "embeddings.npz"


def load_roles(lake_name: str) -> np.ndarray:
    """The role card vectors."""
    _, npz_path = paths(lake_name)
    with np.load(npz_path) as data:
        return data["roles"]


def open_layer(lake_name: str) -> sqlite3.Connection:
    layer_path, _ = paths(lake_name)
    if not layer_path.exists():
        raise FileNotFoundError(f"lake {lake_name!r} is not built: no {layer_path}")
    # the serve command reads the layer from a worker thread; the layer is read-only once built
    conn = sqlite3.connect(layer_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def load_meanings(lake_name: str) -> np.ndarray:
    """The column vectors from the name and descriptions alone, without the examples."""
    _, npz_path = paths(lake_name)
    with np.load(npz_path) as data:
        if "meanings" not in data:
            raise ValueError(f"lake {lake_name!r} has no meaning vectors: rebuild its embed step")
        return data["meanings"]


def load_embeddings(lake_name: str) -> tuple[np.ndarray, np.ndarray]:
    _, npz_path = paths(lake_name)
    if not npz_path.exists():
        raise FileNotFoundError(f"lake {lake_name!r} is not built: no {npz_path}")
    with np.load(npz_path) as data:
        return data["tables"], data["columns"]


def build(lake_name: str) -> None:
    lake = config.lake(lake_name)
    layer_path, _ = paths(lake_name)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    # the serve command reads the layer from a worker thread; the layer is read-only once built
    conn = sqlite3.connect(layer_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    for name, step in (
        ("schema", _schema),
        ("profile", _profile),
        ("describe", _describe),
        ("names", _names),
        ("index", _index),
        ("words", _words),
        ("links", _links),
        ("more_links", _more_links),
        ("judged_links", _judged_links),
        ("roles", _roles),
        ("embed", _embed),
    ):
        done = _meta(conn, f"step_{name}")
        if done:
            log.info("step %s: done at %s, skipping", name, done)
            continue
        started = time.monotonic()
        step(conn, lake)
        _set_meta(conn, f"step_{name}", _now())
        # a step that crashed and resumed keeps only its last sitting
        _set_meta(conn, f"seconds_{name}", f"{time.monotonic() - started:.1f}")
        conn.commit()
    _finish(conn, lake)
    conn.close()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value))


def _count(conn: sqlite3.Connection, sql: str, *args) -> int:
    return conn.execute(sql, args).fetchone()[0]


def _schema(conn: sqlite3.Connection, lake: dict) -> None:
    for path in tqdm(lake["databases"], desc="schema"):
        name = path.stem
        database_id = conn.execute(
            "INSERT INTO databases(name, readable, path) VALUES (?, ?, ?)",
            (name, names.readable(name), str(path)),
        ).lastrowid
        with closing(index.open_source(str(path))) as source:
            for table in profile.list_tables(source):
                info = profile.table_info(source, table)
                table_id = conn.execute(
                    "INSERT INTO tables(database_id, name, readable, row_count, primary_key)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        database_id,
                        table,
                        names.readable(table),
                        profile.row_count(source, table),
                        json.dumps([c for c, _, is_pk in info if is_pk]),
                    ),
                ).lastrowid
                conn.executemany(
                    "INSERT INTO columns(table_id, name, readable, type, is_pk)"
                    " VALUES (?, ?, ?, ?, ?)",
                    [
                        (table_id, c, names.readable(c), c_type, int(is_pk))
                        for c, c_type, is_pk in info
                    ],
                )
    log.info(
        "schema: %d databases, %d tables, %d columns",
        _count(conn, "SELECT count(*) FROM databases"),
        _count(conn, "SELECT count(*) FROM tables"),
        _count(conn, "SELECT count(*) FROM columns"),
    )


def _profile(conn: sqlite3.Connection, lake: dict) -> None:
    rows = conn.execute(
        "SELECT c.id, c.name, t.name AS table_name, t.row_count, d.path"
        " FROM columns c JOIN tables t ON t.id = c.table_id"
        " JOIN databases d ON d.id = t.database_id ORDER BY d.id, c.id"
    ).fetchall()
    for path, group in groupby(tqdm(rows, desc="profile"), key=lambda row: row["path"]):
        with closing(index.open_source(path)) as source:
            for row in group:
                card = profile.profile_column(
                    source, row["table_name"], row["name"], row["row_count"]
                )
                conn.execute(
                    "UPDATE columns SET kind = ?, distinct_count = ?, empty_share = ?,"
                    " samples = ?, is_unique = ?, min = ?, max = ?, date_format = ?,"
                    " date_min = ?, date_max = ?, date_failures = ? WHERE id = ?",
                    (
                        card["kind"],
                        card["distinct_count"],
                        card["empty_share"],
                        json.dumps(card["samples"], ensure_ascii=False),
                        int(card["is_unique"]),
                        card["min"],
                        card["max"],
                        card["date_format"],
                        card["date_min"],
                        card["date_max"],
                        card["date_failures"],
                        row["id"],
                    ),
                )
    log.info(
        "profile: %d columns, %d text, %d date",
        len(rows),
        _count(conn, "SELECT count(*) FROM columns WHERE kind = 'text'"),
        _count(conn, "SELECT count(*) FROM columns WHERE kind = 'date'"),
    )


def _describe(conn: sqlite3.Connection, lake: dict) -> None:
    """One description per table and column. Calls run in parallel; the writes stay in this
    thread, a table at a time, so the step resumes per table. A table wider than
    NAMES_PER_CALL columns is described in parts; its own description comes from the first.
    A table that still fails is left with empty descriptions and listed in
    describe_failed.txt next to the layer."""
    log_path = config.RUNS_DIR / f"build_{lake['name']}.jsonl"
    tables = conn.execute(
        "SELECT t.id, t.name, t.row_count, d.name AS database FROM tables t"
        " JOIN databases d ON d.id = t.database_id WHERE t.description IS NULL ORDER BY t.id"
    ).fetchall()
    columns_of = {
        table["id"]: conn.execute(
            "SELECT id, name, type, distinct_count, samples FROM columns"
            " WHERE table_id = ? ORDER BY id",
            (table["id"],),
        ).fetchall()
        for table in tables
    }

    def describe(table: sqlite3.Row):
        cards = [
            {
                "name": column["name"],
                "type": column["type"],
                "distinct_count": column["distinct_count"],
                "samples": json.loads(column["samples"]),
            }
            for column in columns_of[table["id"]]
        ]
        parts = [
            llm.describe_table(
                table["database"], table["name"], table["row_count"],
                cards[start : start + NAMES_PER_CALL], log_path,
            )
            for start in range(0, len(cards), NAMES_PER_CALL)
        ]
        by_name = {column.name: column.description for part in parts for column in part.columns}
        return parts[0].table_description, by_name

    def guarded(table: sqlite3.Row):
        try:
            return describe(table)
        except llm.ModelError as err:
            log.warning("describe %s.%s failed: %s", table["database"], table["name"], err)
            return None

    failed = []
    with ThreadPoolExecutor(max_workers=DESCRIBE_WORKERS) as pool:
        for table, got in zip(tables, tqdm(pool.map(guarded, tables), total=len(tables), desc="describe")):
            if got is None:
                failed.append(f"{table['database']}.{table['name']}")
                got, source = ("", {}), "failed"
            else:
                source = "model"
            description, by_name = got
            conn.execute(
                "UPDATE tables SET description = ?, description_source = ? WHERE id = ?",
                (description, source, table["id"]),
            )
            for column in columns_of[table["id"]]:
                conn.execute(
                    "UPDATE columns SET description = ?, description_source = ? WHERE id = ?",
                    (by_name.get(column["name"], ""), source, column["id"]),
                )
            conn.commit()
    if failed:
        with (paths(lake["name"])[0].parent / "describe_failed.txt").open("a") as handle:
            handle.write("".join(f"{name}\n" for name in failed))
    log.info("describe: %d tables described, %d failed", len(tables) - len(failed), len(failed))


def _names(conn: sqlite3.Connection, lake: dict) -> None:
    """Readable names for glued ones: HASLASTTRADEDVALUE reads "has last traded value".
    A piece is glued when it is no known word but known words spell it; known words are
    the embedding tokenizer's and those of this lake's descriptions. The model splits
    it: a word list lacks words (bootable is not "boot able")."""
    vocab = embed.whole_words()
    described = " ".join(
        text
        for (text,) in conn.execute("SELECT description FROM tables UNION ALL SELECT description FROM columns")
        if text
    )
    rank = {word.lower(): len(vocab) for word in re.findall(r"[A-Za-z]+", described)} | vocab
    rows = [
        (kind, row["id"], row["readable"])
        for kind in ("tables", "columns")
        for row in conn.execute(f"SELECT id, readable FROM {kind}")
    ]
    glued = sorted({
        piece
        for *_, readable in rows
        for piece in readable.lower().split()
        if len(piece) >= names.GLUED_MIN and piece.isalpha() and piece not in rank
        and names.split_glued(piece, rank)
    })
    log_path = config.RUNS_DIR / f"build_{lake['name']}.jsonl"
    splits: dict[str, str] = {}
    for start in range(0, len(glued), NAMES_PER_CALL):
        splits |= llm.split_names(glued[start : start + NAMES_PER_CALL], log_path)
    # a piece the model gives back whole keeps its case
    splits = {piece: words for piece, words in splits.items() if " " in words}
    changed = 0
    for kind, row_id, readable in rows:
        new = " ".join(splits.get(piece.lower(), piece) for piece in readable.split())
        if new != readable:
            conn.execute(f"UPDATE {kind} SET readable = ? WHERE id = ?", (new, row_id))
            changed += 1
    if changed:
        # the embeddings read the names
        conn.execute("DELETE FROM meta WHERE key = 'step_embed'")
    log.info("names: %d glued pieces, %d names changed", len(glued), changed)


def _index(conn: sqlite3.Connection, lake: dict) -> None:
    rows = conn.execute(
        "SELECT c.id, c.name, t.name AS table_name, d.path FROM columns c"
        " JOIN tables t ON t.id = c.table_id JOIN databases d ON d.id = t.database_id"
        " WHERE c.kind = 'text' ORDER BY d.id, c.id"
    ).fetchall()
    for path, group in groupby(tqdm(rows, desc="index"), key=lambda row: row["path"]):
        with closing(index.open_source(path)) as source:
            for row in group:
                built = index.column_index(source, row["table_name"], row["name"])
                if isinstance(built, index.Bloom):
                    conn.execute(
                        "INSERT INTO blooms(column_id, bits) VALUES (?, ?)",
                        (row["id"], built.to_bytes()),
                    )
                else:
                    conn.executemany(
                        "INSERT INTO text_values(column_id, value) VALUES (?, ?)",
                        [(row["id"], value) for value in built],
                    )
    log.info(
        "index: %d text columns, %d values stored exactly, %d Bloom filters",
        len(rows),
        _count(conn, "SELECT count(*) FROM text_values"),
        _count(conn, "SELECT count(*) FROM blooms"),
    )


def _words(conn: sqlite3.Connection, lake: dict) -> None:
    """Which text columns hold each word inside their values, so a value the question
    names in part ("Alphabet" for "Alphabet Inc.") finds its columns. A value of one
    word is left out: the exact index already finds it whole."""
    rows = conn.execute(
        "SELECT c.id, c.name, t.name AS table_name, d.path FROM columns c"
        " JOIN tables t ON t.id = c.table_id JOIN databases d ON d.id = t.database_id"
        " WHERE c.kind = 'text' ORDER BY d.id, c.id"
    ).fetchall()
    conn.execute("DELETE FROM value_words")
    for path, group in groupby(tqdm(rows, desc="words"), key=lambda row: row["path"]):
        with closing(index.open_source(path)) as source:
            for row in group:
                c = profile.quote(row["name"])
                found = {
                    word
                    for (value,) in source.execute(
                        f"SELECT DISTINCT {c} FROM {profile.quote(row['table_name'])}"
                        f" WHERE typeof({c}) = 'text'"
                    )
                    if len(split := index.words(value)) > 1
                    for word in split
                }
                conn.executemany(
                    "INSERT INTO value_words(word, column_id) VALUES (?, ?)",
                    [(word, row["id"]) for word in found],
                )
    log.info("words: %d (word, column) pairs", _count(conn, "SELECT count(*) FROM value_words"))


def _column_id(known: dict, database: str, table: str, column: str) -> int:
    # SQLite identifiers are case-insensitive, so a foreign key may spell a column
    # differently from PRAGMA table_info.
    found = known.get((table.lower(), column.lower()))
    if found is None:
        raise ValueError(f"links: {database}.{table}.{column} is not a column of the layer")
    return found


def link_cards(rows: list[sqlite3.Row]) -> list[dict]:
    """The column cards `links.inferred` reads, from rows of one database's columns."""
    return [
        {
            "id": row["id"],
            "table": row["table_name"],
            "name": row["name"],
            "kind": row["kind"],
            "is_unique": bool(row["is_unique"]),
            "is_pk": bool(row["is_pk"]),
        }
        for row in rows
    ]


def _database_cards(conn: sqlite3.Connection, database_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT c.id, c.name, c.kind, c.is_unique, c.is_pk, c.distinct_count,"
        " t.name AS table_name, t.row_count FROM columns c"
        " JOIN tables t ON t.id = c.table_id WHERE t.database_id = ? ORDER BY c.id",
        (database_id,),
    ).fetchall()
    return [
        {**card, "distinct_count": row["distinct_count"], "rows": row["row_count"]}
        for card, row in zip(link_cards(rows), rows)
    ]


def _database_links(
    conn: sqlite3.Connection, database_id: int, kinds: tuple[str, ...]
) -> dict[tuple[int, int], sqlite3.Row]:
    return {
        (row["from_column"], row["to_column"]): row
        for row in conn.execute(
            "SELECT l.from_column, l.to_column, l.kind, l.score FROM links l JOIN columns c"
            " ON c.id = l.from_column JOIN tables t ON t.id = c.table_id"
            f" WHERE l.kind IN ({', '.join('?' * len(kinds))}) AND t.database_id = ?",
            (*kinds, database_id),
        )
    }


def _more_links(conn: sqlite3.Connection, lake: dict) -> None:
    """The semantic design's links, for joins only: by values alone, by names and values
    agreeing, and by name onto or out of empty tables, which no values can check. A name
    link scores the least a join takes, so any link checked on values beats it."""
    conn.execute("DELETE FROM links WHERE kind IN ('values', 'name')")
    # the judge reads which columns these links settle
    conn.execute("DELETE FROM meta WHERE key = 'step_judged_links'")
    for database in tqdm(
        conn.execute("SELECT id, path FROM databases ORDER BY id").fetchall(), desc="more links"
    ):
        cards = _database_cards(conn, database["id"])
        linked = _database_links(conn, database["id"], ("declared", "inferred"))
        declared = {pair for pair, link in linked.items() if link["kind"] == "declared"}
        card_of = {card["id"]: card for card in cards}
        with closing(index.open_source(database["path"])) as source:
            found = links.contained(source, cards, declared)
            found += links.small_links(source, cards, declared, set(linked))
            sure = {
                (a, b) for (a, b), link in linked.items()
                if links.quality(link, card_of[a], card_of[b]) >= config.MIN_EDGE_QUALITY
            } | {(a, b) for a, b, score in found if score >= config.MIN_EDGE_QUALITY}
            seen = {(a, b) for a, b, _ in found}
            found += [
                link for link in links.agreeing(source, cards, declared, sure) if link[:2] not in seen
            ]
        conn.executemany(
            "INSERT INTO links(from_column, to_column, kind, score) VALUES (?, ?, 'values', ?)",
            found,
        )
        conn.executemany(
            "INSERT INTO links(from_column, to_column, kind, score) VALUES (?, ?, 'name', ?)",
            [(a, b, config.MIN_EDGE_QUALITY) for a, b in links.named(cards, declared)],
        )
    log.info(
        "more links: %d by values, %d by name",
        _count(conn, "SELECT count(*) FROM links WHERE kind = 'values'"),
        _count(conn, "SELECT count(*) FROM links WHERE kind = 'name'"),
    )


def _judged_links(conn: sqlite3.Connection, lake: dict) -> None:
    """Links the model reads off the descriptions, for joins only: a column whose values
    sit in keys of other tables that no rule settles gets one call naming the keys it
    points to, or none. A link scores the share of values its key holds."""
    conn.execute("DELETE FROM links WHERE kind = 'judged'")
    log_path = config.RUNS_DIR / f"build_{lake['name']}.jsonl"
    for database in conn.execute("SELECT id, name, path FROM databases ORDER BY id").fetchall():
        cards = _database_cards(conn, database["id"])
        card_of = {card["id"]: card for card in cards}
        linked = _database_links(conn, database["id"], ("declared", "inferred", "values", "name"))
        declared = {pair for pair, link in linked.items() if link["kind"] == "declared"}
        sure = {
            pair for pair, link in linked.items()
            if links.quality(link, card_of[pair[0]], card_of[pair[1]]) >= config.MIN_EDGE_QUALITY
        }
        with closing(index.open_source(database["path"])) as source:
            found = links.candidates(source, cards, declared, sure)
        if not found:
            continue
        rows = conn.execute(
            "SELECT c.id, c.name, c.description, c.distinct_count, c.samples, t.id AS table_id,"
            " t.name AS table_name, t.description AS table_description, t.row_count"
            " FROM columns c JOIN tables t ON t.id = c.table_id WHERE t.database_id = ? ORDER BY c.id",
            (database["id"],),
        ).fetchall()
        row_of = {row["id"]: row for row in rows}
        names = defaultdict(list)
        for row in rows:
            names[row["table_id"]].append(row["name"])

        def judge(item: tuple[int, list[tuple[int, float]]]) -> list[int]:
            column, keys = item
            own = row_of[column]
            text = (
                f"{own['table_name']}.{own['name']} in table {own['table_name']}"
                f" ({own['row_count']} rows): {own['table_description']}\n"
                f"  Other columns of the table: {', '.join(names[own['table_id']][:JUDGE_NAMES])}\n"
                f"  Description: {own['description']} {own['distinct_count']} values:"
                f" {', '.join(map(str, json.loads(own['samples'])[:5]))}"
            )
            shown = []
            for key, share in keys:
                row = row_of[key]
                shown.append(
                    f"Table {row['table_name']} ({row['row_count']} rows): {row['table_description']}\n"
                    f"   Other columns: {', '.join(names[row['table_id']][:JUDGE_NAMES])}\n"
                    f"   Column {row['table_name']}.{row['name']}: {row['description']}"
                    f" {row['distinct_count']} values, different on"
                    f" {min(1.0, row['distinct_count'] / row['row_count']):.0%} of rows."
                    f" Samples: {', '.join(map(str, json.loads(row['samples'])[:5]))}\n"
                    f"   Holds {round(share * own['distinct_count'])} of {own['distinct_count']} values."
                )
            return llm.judge_link(database["name"], text, shown, log_path)

        with ThreadPoolExecutor(max_workers=JUDGE_WORKERS) as pool:
            chosen = list(tqdm(pool.map(judge, found.items()), total=len(found), desc="judge"))
        judged = [
            (column, keys[n - 1][0], keys[n - 1][1])
            for (column, keys), picked in zip(found.items(), chosen)
            for n in picked
            if (column, keys[n - 1][0]) not in sure
        ]
        conn.executemany(
            "INSERT INTO links(from_column, to_column, kind, score) VALUES (?, ?, 'judged', ?)", judged
        )
    log.info("judged links: %d", _count(conn, "SELECT count(*) FROM links WHERE kind = 'judged'"))


def _roles(conn: sqlite3.Connection, lake: dict) -> None:
    """Role cards: the words of a link column's name, put on the columns of the table it
    points to. LISTEDSECURITY.HASLASTTRADEDVALUE points at MONETARYAMOUNT, so "last traded
    value" lands on its amount; a subtype's key (REVENUE.REVENUEID) points at its parent's
    key, so "revenue" lands on the parent's columns. Words in more than a third of the
    lake's column names (has), key words, and words the target table's own name says are
    left out."""
    columns = {row["id"]: row for row in conn.execute("SELECT * FROM columns")}
    tables = {row["id"]: row for row in conn.execute("SELECT id, name, readable FROM tables")}
    good, joinable = [], set()
    for link in conn.execute("SELECT * FROM links"):
        source, target = columns[link["from_column"]], columns[link["to_column"]]
        if source["table_id"] == target["table_id"]:
            continue
        quality = links.quality(link, source, target)
        if quality >= config.MIN_EDGE_QUALITY:
            joinable.add(source["id"])
        if quality >= ROLE_QUALITY:
            good.append(link)
    counts = Counter(word for c in columns.values() for word in set(c["readable"].lower().split()))
    stop = KEY_WORDS | {word for word, n in counts.items() if n > len(columns) / 3}
    content = defaultdict(list)
    for column in columns.values():
        if not column["is_pk"] and column["id"] not in joinable:
            content[column["table_id"]].append(column["id"])
    conn.execute("DELETE FROM roles")
    made = 0
    for link in good:
        source, target = columns[link["from_column"]], columns[link["to_column"]]
        words = [word for word in source["readable"].lower().split() if word not in stop]
        own = {names.stem(word) for word in tables[target["table_id"]]["readable"].lower().split()}
        if all(names.stem(word) in own for word in words):
            continue
        via = f"{tables[source['table_id']]['name']}.{source['name']}"
        for column_id in content[target["table_id"]]:
            if column_id != target["id"]:
                conn.execute(
                    "INSERT INTO roles(column_id, link_id, words, via) VALUES (?, ?, ?, ?)",
                    (column_id, link["id"], " ".join(words), via),
                )
                made += 1
    if made:
        # the embeddings hold the role cards
        conn.execute("DELETE FROM meta WHERE key = 'step_embed'")
    log.info("roles: %d role cards from %d links, stop words %s", made, len(good), sorted(stop - KEY_WORDS))


def _links(conn: sqlite3.Connection, lake: dict) -> None:
    # a rerun of this step alone replaces its links, it does not add a second copy
    conn.execute("DELETE FROM links WHERE kind IN ('declared', 'inferred')")
    groups = 0
    for database in tqdm(
        conn.execute("SELECT id, name, path FROM databases ORDER BY id").fetchall(),
        desc="links",
    ):
        cards = conn.execute(
            "SELECT c.id, c.name, c.kind, c.is_unique, c.is_pk, t.name AS table_name"
            " FROM columns c"
            " JOIN tables t ON t.id = c.table_id WHERE t.database_id = ? ORDER BY c.id",
            (database["id"],),
        ).fetchall()
        known = {(row["table_name"].lower(), row["name"].lower()): row["id"] for row in cards}
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM tables WHERE database_id = ? ORDER BY id", (database["id"],)
            )
        ]
        pairs: dict[tuple[int, int], int | None] = {}
        with closing(index.open_source(database["path"])) as source:
            for table in tables:
                found = links.declared(source, table, tables)
                sizes = Counter(constraint for constraint, *_ in found)
                numbers: dict[int, int] = {}
                for constraint, from_column, to_table, to_column in found:
                    if sizes[constraint] > 1 and constraint not in numbers:
                        groups += 1
                        numbers[constraint] = groups
                    pair = (
                        _column_id(known, database["name"], table, from_column),
                        _column_id(known, database["name"], to_table, to_column),
                    )
                    pairs.setdefault(pair, numbers.get(constraint))
            inferred = links.inferred(source, link_cards(cards), set(pairs))
        conn.executemany(
            "INSERT INTO links(from_column, to_column, kind, score, grp)"
            " VALUES (?, ?, 'declared', 1.0, ?)",
            sorted((a, b, grp) for (a, b), grp in pairs.items()),
        )
        conn.executemany(
            "INSERT INTO links(from_column, to_column, kind, score) VALUES (?, ?, 'inferred', ?)",
            inferred,
        )
    log.info(
        "links: %d declared, %d inferred",
        _count(conn, "SELECT count(*) FROM links WHERE kind = 'declared'"),
        _count(conn, "SELECT count(*) FROM links WHERE kind = 'inferred'"),
    )


def _embed(conn: sqlite3.Connection, lake: dict) -> None:
    tables = conn.execute(
        "SELECT d.readable AS database_readable, t.readable, t.description FROM tables t"
        " JOIN databases d ON d.id = t.database_id ORDER BY t.id"
    ).fetchall()
    columns = conn.execute(
        "SELECT t.readable AS table_readable, c.readable, c.type, c.description,"
        " c.value_description, c.samples FROM columns c JOIN tables t ON t.id = c.table_id"
        " ORDER BY c.id"
    ).fetchall()
    roles = conn.execute(
        "SELECT r.words, st.readable AS source_table, t.readable AS table_readable, c.readable,"
        " c.type, c.description, c.value_description, c.samples FROM roles r"
        " JOIN links l ON l.id = r.link_id JOIN columns sc ON sc.id = l.from_column"
        " JOIN tables st ON st.id = sc.table_id JOIN columns c ON c.id = r.column_id"
        " JOIN tables t ON t.id = c.table_id ORDER BY r.id"
    ).fetchall()
    matrices = {
        "tables": embed.embed([embed.table_text(dict(row)) for row in tables]),
        "columns": embed.embed(
            [
                embed.column_text({**dict(row), "samples": json.loads(row["samples"])})
                for row in columns
            ]
        ),
        # the same without the examples: long example texts can drown what the column means
        "meanings": embed.embed(
            [embed.column_text({**dict(row), "samples": []}) for row in columns]
        ),
        "roles": embed.embed(
            [embed.role_text({**dict(row), "samples": json.loads(row["samples"])}) for row in roles]
        ),
    }
    for name, matrix in matrices.items():
        if np.isnan(matrix).any():
            raise ValueError(f"embed: the {name} matrix contains NaN")
    _, npz_path = paths(lake["name"])
    np.savez(npz_path, **matrices)
    _set_meta(conn, "embedding_revision", config.EMBEDDING_REVISION)
    log.info(
        "embed: %d table vectors, %d column vectors written to %s",
        len(tables),
        len(columns),
        npz_path,
    )


def _finish(conn: sqlite3.Connection, lake: dict) -> None:
    log.info(
        "built %s: %d databases, %d tables, %d columns, %d text values, %d Bloom filters,"
        " %d declared and %d inferred links",
        lake["name"],
        _count(conn, "SELECT count(*) FROM databases"),
        _count(conn, "SELECT count(*) FROM tables"),
        _count(conn, "SELECT count(*) FROM columns"),
        _count(conn, "SELECT count(*) FROM text_values"),
        _count(conn, "SELECT count(*) FROM blooms"),
        _count(conn, "SELECT count(*) FROM links WHERE kind = 'declared'"),
        _count(conn, "SELECT count(*) FROM links WHERE kind = 'inferred'"),
    )
