"""Data-derived profile of SQLite tables and columns.

Names, descriptions and ids are added elsewhere; this module only looks at
the SQLite files.
"""

import sqlite3
from datetime import datetime

# Bare %Y and time-only formats are deliberately absent: a four-digit text
# year stays text so an exact value lookup can hit it, and a time of day is
# not a date.
DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M",
    # the timestamp text DB2 writes: 2015-06-25-15.11.03.000000
    "%Y-%m-%d-%H.%M.%S.%f",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%y",
    "%Y%m%d",
    "%Y%m",
    "%b %d, %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%d %B %Y",
    "%d-%b-%y",
    "%d-%b-%Y",
    "%B %Y",
)

_KIND_OF_STORAGE = {
    "integer": "number",
    "real": "number",
    "text": "text",
    "blob": "blob",
}

SAMPLE_CHARS = 100
DATE_SAMPLE = 100
# a format holds when this share of the sampled values parse with it: one typo or
# placeholder among a hundred dates does not make the column text
DATE_SHARE = 0.95


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [name for (name,) in rows]


def table_info(conn: sqlite3.Connection, table: str) -> list[tuple[str, str, bool]]:
    rows = conn.execute(f"PRAGMA table_info({quote(table)})").fetchall()
    if not rows:
        raise ValueError(f"table_info: no such table {table!r}")
    return [(row[1], row[2], bool(row[5])) for row in rows]


def row_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM {quote(table)}").fetchone()[0]


def profile_column(
    conn: sqlite3.Connection, table: str, column: str, n_rows: int
) -> dict:
    t, c = quote(table), quote(column)
    empty = f"{c} IS NULL OR trim({c}) = ''"
    filled = f"NOT ({empty})"

    storage = conn.execute(
        f"SELECT typeof({c}) FROM {t} WHERE {filled} "
        f"GROUP BY 1 ORDER BY count(*) DESC LIMIT 1"
    ).fetchone()
    kind = _KIND_OF_STORAGE[storage[0]] if storage else "empty"

    distinct_count = conn.execute(
        f"SELECT count(DISTINCT {c}) FROM {t} WHERE {filled}"
    ).fetchone()[0]
    empty_count = conn.execute(f"SELECT count(*) FROM {t} WHERE {empty}").fetchone()[0]

    card = {
        "kind": kind,
        "distinct_count": distinct_count,
        "empty_share": empty_count / n_rows if n_rows else 0.0,
        "samples": [],
        "is_unique": n_rows > 0 and empty_count == 0 and distinct_count == n_rows,
        "min": None,
        "max": None,
        "date_format": None,
        "date_min": None,
        "date_max": None,
        "date_failures": None,
    }

    if kind in ("blob", "empty"):
        return card

    card["samples"] = [
        value[:SAMPLE_CHARS] if isinstance(value, str) else value
        for (value,) in conn.execute(
            f"SELECT {c} FROM {t} WHERE {filled} "
            f"GROUP BY {c} ORDER BY count(*) DESC, {c} LIMIT 5"
        )
    ]

    if kind == "number":
        card["min"], card["max"] = conn.execute(
            f"SELECT min({c}), max({c}) FROM {t} "
            f"WHERE typeof({c}) IN ('integer', 'real')"
        ).fetchone()
        return card

    dated = date_card(conn, t, c, filled)
    if dated:
        card.update(kind="date", **dated)
    return card


def date_card(conn: sqlite3.Connection, t: str, c: str, filled: str) -> dict | None:
    """The date format and range of a text column, or None when it holds no dates.

    The sample picks the format. A sample with a value that does not parse passes only
    if the whole column parses at the same share, or ids that happen to look like year
    and month (21206) would pass."""
    fmt, clean = _detect_date_format(conn, t, c, filled)
    if fmt is None:
        return None
    span = _date_range(conn, t, c, filled, fmt)
    parsed = span.pop("parsed")
    if not clean and parsed < DATE_SHARE * (parsed + span["date_failures"]):
        return None
    return {"date_format": fmt, **span}


def _detect_date_format(
    conn: sqlite3.Connection, t: str, c: str, filled: str
) -> tuple[str | None, bool]:
    """The first format enough of the sample parses with, and whether all of it does."""
    sample = [
        value
        for (value,) in conn.execute(
            f"SELECT DISTINCT {c} FROM {t} "
            f"WHERE typeof({c}) = 'text' AND {filled} LIMIT {DATE_SAMPLE}"
        )
    ]
    if not sample:
        return None, False
    for fmt in DATE_FORMATS:
        if all(_parses(value, fmt) for value in sample):
            return fmt, True
    for fmt in DATE_FORMATS:
        if sum(_parses(value, fmt) for value in sample) >= DATE_SHARE * len(sample):
            return fmt, False
    return None, False


def _date_range(
    conn: sqlite3.Connection, t: str, c: str, filled: str, fmt: str
) -> dict:
    failures = 0
    parsed = []
    for (value,) in conn.execute(
        f"SELECT DISTINCT {c} FROM {t} WHERE typeof({c}) = 'text' AND {filled}"
    ):
        try:
            parsed.append(datetime.strptime(value, fmt))
        except ValueError:
            failures += 1
    if not parsed:
        raise ValueError(f"_date_range: no value of {t}.{c} parses with {fmt!r}")
    as_text = (lambda d: d.isoformat()) if "%H" in fmt else (lambda d: d.date().isoformat())
    return {
        "parsed": len(parsed),
        "date_min": as_text(min(parsed)),
        "date_max": as_text(max(parsed)),
        "date_failures": failures,
    }


def _parses(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
    except ValueError:
        return False
    return True
