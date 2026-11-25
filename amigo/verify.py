"""The verification report from PLAN.md section 2.5."""

import random
import sqlite3
from contextlib import closing
from itertools import groupby

import numpy as np
from tqdm import tqdm

from . import embed, index, layer, links, names, profile

VALUE_SAMPLE = 20
RANDOM_STRINGS = 2000
RANDOM_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
MAX_FALSE_POSITIVE = 0.03
NEIGHBOURS = 5


def run(lake_name: str) -> bool:
    conn = layer.open_layer(lake_name)
    table_vectors, column_vectors = layer.load_embeddings(lake_name)
    rng = random.Random(0)

    results = [_structure(conn, table_vectors, column_vectors), _names()]
    results += _value_index(conn, rng)
    results.append(_link_graph(conn))
    _dates(conn)
    _neighbours(conn, column_vectors)
    conn.close()

    failed = results.count(False)
    print(f"verify {lake_name}: " + ("PASS" if not failed else f"FAIL ({failed} checks failed)"))
    return not failed


def _line(ok: bool, text: str, details: list[str]) -> bool:
    print(f"{'PASS' if ok else 'FAIL'} {text}")
    for detail in details:
        print(f"  {detail}")
    return ok


def _distinct_text(source: sqlite3.Connection, table: str, column: str) -> list[str]:
    c = profile.quote(column)
    return [
        value
        for (value,) in source.execute(
            f"SELECT DISTINCT {c} FROM {profile.quote(table)} "
            f"WHERE typeof({c}) = 'text' AND trim({c}) <> ''"
        )
    ]


def _value_set(source: sqlite3.Connection, table: str, column: str) -> set[str]:
    # the links step's own reading of a value, so an id written "12.0" is the id 12
    return links._normalised(set(_distinct_text(source, table, column)))


def _labels(conn: sqlite3.Connection, where: str = "") -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT c.id, c.name, t.name AS table_name, d.name AS database, d.path,"
        " c.date_format, c.date_min, c.date_max, c.date_failures"
        " FROM columns c JOIN tables t ON t.id = c.table_id"
        f" JOIN databases d ON d.id = t.database_id {where} ORDER BY c.id"
    ).fetchall()


def _structure(conn: sqlite3.Connection, table_vectors, column_vectors) -> bool:
    problems = []
    for database in conn.execute("SELECT id, name, path FROM databases ORDER BY id").fetchall():
        layer_tables = {
            row["name"]: row["id"]
            for row in conn.execute(
                "SELECT id, name FROM tables WHERE database_id = ? ORDER BY id",
                (database["id"],),
            )
        }
        with closing(index.open_source(database["path"])) as source:
            source_tables = set(profile.list_tables(source))
            if source_tables != set(layer_tables):
                problems.append(
                    f"{database['name']}: tables only in the source "
                    f"{sorted(source_tables - set(layer_tables))}, only in the layer "
                    f"{sorted(set(layer_tables) - source_tables)}"
                )
            for table, table_id in layer_tables.items():
                if table not in source_tables:
                    continue
                source_columns = {name for name, _, _ in profile.table_info(source, table)}
                layer_columns = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM columns WHERE table_id = ?", (table_id,)
                    )
                }
                if source_columns != layer_columns:
                    problems.append(
                        f"{database['name']}.{table}: columns only in the source "
                        f"{sorted(source_columns - layer_columns)}, only in the layer "
                        f"{sorted(layer_columns - source_columns)}"
                    )

    n_databases = conn.execute("SELECT count(*) FROM databases").fetchone()[0]
    n_tables = conn.execute("SELECT count(*) FROM tables").fetchone()[0]
    n_columns = conn.execute("SELECT count(*) FROM columns").fetchone()[0]

    missing = 0
    for card, sql in (
        (
            "table",
            "SELECT d.name AS database, t.name AS name FROM tables t"
            " JOIN databases d ON d.id = t.database_id"
            " WHERE t.description IS NULL OR trim(t.description) = '' ORDER BY t.id",
        ),
        (
            "column",
            "SELECT d.name AS database, t.name || '.' || c.name AS name FROM columns c"
            " JOIN tables t ON t.id = c.table_id JOIN databases d ON d.id = t.database_id"
            " WHERE c.description IS NULL OR trim(c.description) = '' ORDER BY c.id",
        ),
    ):
        rows = conn.execute(sql).fetchall()
        missing += len(rows)
        problems += [f"{card} without a description: {r['database']}.{r['name']}" for r in rows]

    for name, matrix, expected in (
        ("tables", table_vectors, n_tables),
        ("columns", column_vectors, n_columns),
    ):
        if matrix.shape != (expected, embed.DIM):
            problems.append(
                f"the {name} matrix is {matrix.shape}, expected ({expected}, {embed.DIM})"
            )
            continue
        n_nan = int(np.isnan(matrix).any(axis=1).sum())
        off = int((np.abs(np.linalg.norm(matrix, axis=1) - 1.0) > 1e-3).sum())
        if n_nan:
            problems.append(f"the {name} matrix has {n_nan} rows containing NaN")
        if off:
            problems.append(f"the {name} matrix has {off} rows whose L2 norm is not 1")

    return _line(
        not problems,
        f"structure: {n_databases} databases, {n_tables} tables, {n_columns} columns,"
        f" {missing} cards without a description,"
        f" embeddings {table_vectors.shape[0]}x{table_vectors.shape[1]}"
        f" and {column_vectors.shape[0]}x{column_vectors.shape[1]},"
        f" {len(problems)} problems",
        problems,
    )


def _names() -> bool:
    wrong = [
        f"{name!r} -> {names.readable(name)!r}, expected {want!r}"
        for name, want in names.EXAMPLES
        if names.readable(name) != want
    ]
    return _line(
        not wrong,
        f"readable names: {len(names.EXAMPLES) - len(wrong)}/{len(names.EXAMPLES)} examples match",
        wrong,
    )


def _value_index(conn: sqlite3.Connection, rng: random.Random) -> list[bool]:
    rows = conn.execute(
        "SELECT c.id, c.name, t.name AS table_name, d.name AS database, d.path,"
        " EXISTS(SELECT 1 FROM blooms b WHERE b.column_id = c.id) AS has_bloom"
        " FROM columns c JOIN tables t ON t.id = c.table_id"
        " JOIN databases d ON d.id = t.database_id"
        " WHERE EXISTS(SELECT 1 FROM blooms b WHERE b.column_id = c.id)"
        " OR EXISTS(SELECT 1 FROM text_values v WHERE v.column_id = c.id)"
        " ORDER BY d.id, c.id"
    ).fetchall()

    misses = []
    checked = 0
    for path, group in groupby(
        tqdm(rows, desc="values", leave=False), key=lambda row: row["path"]
    ):
        with closing(index.open_source(path)) as source:
            for row in group:
                bloom = None
                if row["has_bloom"]:
                    bits = conn.execute(
                        "SELECT bits FROM blooms WHERE column_id = ?", (row["id"],)
                    ).fetchone()["bits"]
                    bloom = index.Bloom.from_bytes(bits)
                values = _distinct_text(source, row["table_name"], row["name"])
                for value in rng.sample(values, min(VALUE_SAMPLE, len(values))):
                    text = index.normalise(value)
                    if not text:
                        continue
                    checked += 1
                    if bloom is not None:
                        found = text in bloom
                    else:
                        found = (
                            conn.execute(
                                "SELECT 1 FROM text_values WHERE column_id = ? AND value = ?",
                                (row["id"], text),
                            ).fetchone()
                            is not None
                        )
                    if not found:
                        misses.append(
                            f"{row['database']}.{row['table_name']}.{row['name']}:"
                            f" {value!r} is not in its own index"
                        )

    sample_ok = _line(
        not misses,
        f"value index: {checked} values checked over {len(rows)} indexed columns,"
        f" {len(misses)} not found",
        misses,
    )
    return [sample_ok, _false_positives(conn, rng)]


def _false_positives(conn: sqlite3.Connection, rng: random.Random) -> bool:
    blooms = [
        index.Bloom.from_bytes(row["bits"])
        for row in conn.execute("SELECT bits FROM blooms ORDER BY column_id")
    ]
    if not blooms:
        print(f"INFO bloom false positives: 0 filters in this lake, {RANDOM_STRINGS} strings unused")
        return True
    hits = 0
    for _ in tqdm(range(RANDOM_STRINGS), desc="bloom", leave=False):
        text = "".join(rng.choices(RANDOM_ALPHABET, k=12))
        hits += sum(text in bloom for bloom in blooms)
    share = hits / (RANDOM_STRINGS * len(blooms))
    ok = share <= MAX_FALSE_POSITIVE
    print(
        f"{'INFO' if ok else 'FAIL'} bloom false positives: {share:.4f} over"
        f" {RANDOM_STRINGS} strings x {len(blooms)} filters"
        f" (expect about 0.0001, limit {MAX_FALSE_POSITIVE})"
    )
    return ok


def _link_graph(conn: sqlite3.Connection) -> bool:
    problems = []
    expected = set()
    # the inferred links the links step makes today: a layer built by an older rule set
    # misses some, and nothing else would say so
    remade = set()
    for database in conn.execute("SELECT id, name, path FROM databases ORDER BY id").fetchall():
        cards = conn.execute(
            "SELECT c.id, c.name, c.kind, c.is_unique, c.is_pk, t.name AS table_name"
            " FROM columns c"
            " JOIN tables t ON t.id = c.table_id WHERE t.database_id = ? ORDER BY c.id",
            (database["id"],),
        ).fetchall()
        known = {(row["table_name"].lower(), row["name"].lower()): row["id"] for row in cards}
        here = set()
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM tables WHERE database_id = ? ORDER BY id", (database["id"],)
            )
        ]
        with closing(index.open_source(database["path"])) as source:
            for table in tables:
                for _, from_column, to_table, to_column in links.declared(source, table, tables):
                    here.add(
                        (
                            layer._column_id(known, database["name"], table, from_column),
                            layer._column_id(known, database["name"], to_table, to_column),
                        )
                    )
            remade |= {(a, b) for a, b, _ in links.inferred(source, layer.link_cards(cards), here)}
        expected |= here

    stored = {
        (row["from_column"], row["to_column"])
        for row in conn.execute("SELECT from_column, to_column FROM links WHERE kind = 'declared'")
    }
    name_of = {
        row["id"]: f"{row['database']}.{row['table_name']}.{row['name']}" for row in _labels(conn)
    }
    problems += [
        f"declared foreign key missing from the layer: "
        f"{name_of[a]} -> {name_of[b]}"
        for a, b in sorted(expected - stored)
    ]
    problems += [
        f"declared link in the layer is not a foreign key: {name_of[a]} -> {name_of[b]}"
        for a, b in sorted(stored - expected)
    ]
    kept = {
        (row["from_column"], row["to_column"])
        for row in conn.execute("SELECT from_column, to_column FROM links WHERE kind = 'inferred'")
    }
    problems += [
        f"inferred link missing from the layer, rerun the links step: {name_of[a]} -> {name_of[b]}"
        for a, b in sorted(remade - kept)
    ]
    problems += [
        f"inferred link the links step no longer makes: {name_of[a]} -> {name_of[b]}"
        for a, b in sorted(kept - remade)
    ]

    inferred = conn.execute(
        "SELECT l.score, fc.kind AS from_kind,"
        " fd.name AS from_db, fd.path AS from_path, ft.name AS from_table,"
        " fc.name AS from_column, td.name AS to_db, td.path AS to_path, tt.name AS to_table,"
        " tc.name AS to_column FROM links l"
        " JOIN columns fc ON fc.id = l.from_column JOIN tables ft ON ft.id = fc.table_id"
        " JOIN databases fd ON fd.id = ft.database_id"
        " JOIN columns tc ON tc.id = l.to_column JOIN tables tt ON tt.id = tc.table_id"
        " JOIN databases td ON td.id = tt.database_id"
        " WHERE l.kind = 'inferred' ORDER BY l.id"
    ).fetchall()

    listing = []
    for row in tqdm(inferred, desc="inferred", leave=False):
        # The integer rule links number columns, which hold no text values.
        values_of = links._numbers if row["from_kind"] == "number" else _value_set
        with closing(index.open_source(row["from_path"])) as source:
            from_set = values_of(source, row["from_table"], row["from_column"])
        with closing(index.open_source(row["to_path"])) as source:
            to_set = values_of(source, row["to_table"], row["to_column"])
        left = f"{row['from_db']}.{row['from_table']}.{row['from_column']}"
        right = f"{row['to_db']}.{row['to_table']}.{row['to_column']}"
        if not from_set:
            problems.append(f"inferred link {left} -> {right}: the source column has no values")
            continue
        share = len(from_set & to_set) / len(from_set)
        if abs(share - row["score"]) > 1e-9:
            problems.append(
                f"inferred link {left} -> {right}: stored {row['score']:.6f},"
                f" recomputed {share:.6f}"
            )
        listing.append(f"{left} -> {right} {share:.3f}")

    return _line(
        not problems,
        f"links: {len(stored)} declared, {len(expected)} declared recomputed from the sources,"
        f" {len(inferred)} inferred rechecked, {len(problems)} problems",
        problems + listing,
    )


def _dates(conn: sqlite3.Connection) -> None:
    rows = _labels(conn, "WHERE c.kind = 'date'")
    print(f"INFO dates: {len(rows)} columns detected as dates")
    for row in rows:
        print(
            f"  {row['database']}.{row['table_name']}.{row['name']} {row['date_format']}"
            f" {row['date_min']}..{row['date_max']} failures={row['date_failures']}"
        )


def _neighbours(conn: sqlite3.Connection, column_vectors) -> None:
    rows = _labels(conn)
    n = min(len(rows), len(column_vectors))
    if n < 2:
        print(f"INFO neighbours: {n} column cards, nothing to compare")
        return
    picks = sorted({0, n // 4, n // 2, 3 * n // 4, n - 1})
    print(f"INFO neighbours: {len(picks)} of {n} columns sampled, {NEIGHBOURS} neighbours each")
    for i in picks:
        scores = column_vectors[:n] @ column_vectors[i]
        scores[i] = -np.inf
        row = rows[i]
        print(f"  {row['database']}.{row['table_name']}.{row['name']}")
        for j in np.argsort(-scores)[:NEIGHBOURS]:
            other = rows[j]
            print(
                f"    {other['database']}.{other['table_name']}.{other['name']}"
                f" {scores[j]:.3f}"
            )
