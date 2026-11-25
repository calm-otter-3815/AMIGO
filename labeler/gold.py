"""Step 1: what the gold SQL reads, and whether each gold literal is found by code.

A literal is a quoted string ('...' or a "..." that is not a name) in the gold SQL compared with = , LIKE or IN. Strings after
< , > or BETWEEN are thresholds, not stored values, and are skipped. A literal is found
when some column the gold reads holds it, trying in order:
  exact     the stored value equals the literal;
  nocase    equal after lower case and trimming;
  contains  a stored value contains the literal with its % signs removed (LIKE patterns,
            dates matched by year, 'Alameda' inside 'Alameda County').
"""

import hashlib
import json
import re
import sqlite3
from contextlib import closing

# a quoted string and the few characters before it, to see what it is compared with
LITERAL = re.compile(r"(<=|>=|<>|!=|<|>|=|\blike\b|\bin\b|\bbetween\b|\band\b|,|\()\s*(?:'((?:[^']|'')*)'|\"((?:[^\"]|\"\")*)\")", re.I)
FORMAT = re.compile(r"(%[a-zA-Z][-/: ]?)+")
THRESHOLD = {"<", ">", "<=", ">=", "between", "and"}
# what may sit before the "(" that holds a compared list: IN (...), or an operator and a function name (= lower(...))
LISTED = re.compile(r"(?:\bin|(?:<>|!=|=|\blike\b)\s*\w*)\s*$", re.I)


def ident(name: str) -> str:
    """`name` quoted for SQLite (a few taco_us column names hold a double quote)."""
    return '"' + name.replace('"', '""') + '"'


def connect(path) -> sqlite3.Connection:
    """Read-only. `path` is one database, or a dict name -> path for a question across
    databases: each is then attached under its name, its tables read as "name"."table"."""
    if isinstance(path, dict):
        conn = sqlite3.connect("file::memory:", uri=True)
        for name, one in path.items():
            conn.execute(f"ATTACH DATABASE ? AS {ident(name)}", (f"file:{one}?mode=ro",))
    else:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    # some benchmark databases store text that is not valid UTF-8
    conn.text_factory = lambda b: b.decode(errors="replace")
    return conn


def reads(conn: sqlite3.Connection, sql: str) -> tuple[set[str], set[tuple[str, str]]]:
    """The tables and (table, column) pairs SQLite reads when it prepares `sql`."""
    tables: set[str] = set()
    columns: set[tuple[str, str]] = set()

    def authorize(action, table, column, *_):
        if action == sqlite3.SQLITE_READ and table and not table.startswith("sqlite_"):
            tables.add(table)
            if column:
                columns.add((table, column))
        return sqlite3.SQLITE_OK

    conn.set_authorizer(authorize)
    try:
        conn.execute("EXPLAIN " + sql)
    finally:
        conn.set_authorizer(None)
    return tables, columns


def opened(sql: str, end: int) -> int:
    """Index of the nearest "(" before `end` that is still open there, or -1."""
    depth = 0
    for i in range(end - 1, -1, -1):
        if sql[i] == ")":
            depth += 1
        elif sql[i] == "(":
            if depth == 0:
                return i
            depth -= 1
    return -1


def literals(sql: str, names=frozenset()) -> list[str]:
    """The quoted strings the gold compares a column with, thresholds left out. A string after , or ( counts
    only inside IN (...) or op func(...). A
    double-quoted string counts only when it is not one of `names` (lower-case table and column names the query reads)."""
    found = []
    for m in LITERAL.finditer(sql):
        single = m.group(2) is not None
        text = m.group(2) if single else m.group(3)
        # strftime('%Y', ...) formats are not stored values
        if m.group(1).lower() in THRESHOLD or FORMAT.fullmatch(text) or (not single and text.lower() in names):
            continue
        if m.group(1) in {",", "("}:
            p = opened(sql, m.end(1))
            if p < 0 or not LISTED.search(sql[:p]):
                continue
        found.append(text.replace("''", "'") if single else text.replace('""', '"'))
    return found


def compared(sql: str, text: str, columns) -> list[set[tuple[str, str]]]:
    """Per place that compares `text`, the read (table, column) pairs named last before its operator (County in
    T2.County = 'Monterey', OpenDate in strftime('%Y', T1.OpenDate) = '1980'); an alias maps to its table."""
    quoted = "(?:'" + re.escape(text.replace("'", "''")) + "'|\"" + re.escape(text.replace('"', '""')) + '")'
    tables = {}
    for name, alias in re.findall(r"(?:FROM|JOIN)\s+[\"`]?(\w+)[\"`]?(?:\s+(?:AS\s+)?(\w+))?", sql, re.I):
        tables[name.lower()] = name.lower()
        if alias and alias.lower() not in {"on", "where", "join", "inner", "left", "group", "order", "limit"}:
            tables[alias.lower()] = name.lower()
    found = []
    for m in re.finditer(r"(?:<>|!=|=|\blike\b|\bin\s*\()\s*" + quoted, sql, re.I):
        before = re.sub(r"'(?:[^']|'')*'", "''", sql[:m.start()])
        idents = [(q.lower(), next(g for g in rest if g).lower())
                  for q, *rest in re.findall(r"(?:(\w+)\.)?(?:`([^`]+)`|\"([^\"]+)\"|\[([^\]]+)\]|(\w+))", before)]
        named = next(((q, i) for q, i in reversed(idents) if any(c.lower() == i for _, c in columns)), None)
        if named:
            q, i = named
            same = {(t, c) for t, c in columns if c.lower() == i}
            found.append({p for p in same if p[0].lower() == tables.get(q)} or same)
    return found


def find(conn: sqlite3.Connection, columns: set[tuple[str, str]], literal: str, first=frozenset()) -> tuple[str, str] | None:
    """The first route and column that finds `literal`, or None. The (table, column) pairs in `first` go first."""
    bare = literal.strip("%").strip()
    tries = [
        ("exact", "{c} = ?", literal),
        ("nocase", "lower(trim({c})) = lower(?)", bare),
        ("contains", "instr(lower({c}), lower(?)) > 0", bare),
    ]
    for group in (first, columns - first):
        for route, test, value in tries:
            if not value:
                continue
            for table, column in sorted(group):
                sql = f"SELECT 1 FROM {ident(table)} WHERE {test.format(c=ident(column))} LIMIT 1"
                if conn.execute(sql, (value,)).fetchone():
                    return route, f"{table}.{column}"
    return None


def anchor(path, sql: str) -> dict:
    """Gold tables, gold columns and each literal's route for one question."""
    if isinstance(path, dict):
        return anchor_many(path, sql)
    with closing(connect(path)) as conn:
        tables, columns = reads(conn, sql)
        names = {t.lower() for t in tables} | {c.lower() for _, c in columns}
        found = {}
        for text in literals(sql, names):
            for first in compared(sql, text, columns) or [frozenset()]:
                r = find(conn, columns, text, first)
                found[text, r and r[1]] = r
    return {
        "tables": sorted(tables),
        "columns": sorted(f"{t}.{c}" for t, c in columns),
        "literals": [{"text": t, "route": r and r[0], "column": r and r[1]} for (t, _), r in found.items()],
    }


def anchor_many(paths: dict, sql: str) -> dict:
    """anchor() for a question across databases (`paths`: name -> path; its SQL reads
    "name"."table"): tables come back as db.table, columns and literal columns as
    db.table.column. A literal is looked up in each database on its own, the databases of
    the columns it is compared with first."""
    tables: set[str] = set()
    columns: set[tuple[str, str]] = set()
    with closing(connect(paths)) as conn:
        home = {}  # a table read for no column comes with no database name: find its own
        for db in paths:
            for (name,) in conn.execute(f"SELECT name FROM {ident(db)}.sqlite_master WHERE type IN ('table','view')"):
                home.setdefault(name.lower(), db)

        def authorize(action, table, column, db, *_):
            if action == sqlite3.SQLITE_READ and table and not table.startswith("sqlite_"):
                full = f"{db if db in paths else home.get(table.lower(), db)}.{table}"
                tables.add(full)
                if column:
                    columns.add((full, column))
            return sqlite3.SQLITE_OK

        conn.set_authorizer(authorize)
        try:
            conn.execute("EXPLAIN " + sql)
        finally:
            conn.set_authorizer(None)
    names = {d.lower() for d in paths} | {t.split(".", 1)[1].lower() for t in tables} | {c.lower() for _, c in columns}
    found = {}
    for text in literals(sql, names):
        for first in compared(sql, text, columns) or [frozenset()]:
            r = None
            for db in sorted(paths, key=lambda d: not any(t.split(".", 1)[0] == d for t, _ in first)):
                def local(pairs):
                    return {(t.split(".", 1)[1], c) for t, c in pairs if t.split(".", 1)[0] == db}
                with closing(connect(paths[db])) as one:
                    r = find(one, local(columns), text, local(first))
                if r:
                    r = (r[0], f"{db}.{r[1]}")
                    break
            found[text, r and r[1]] = r
    return {
        "tables": sorted(tables),
        "columns": sorted(f"{t}.{c}" for t, c in columns),
        "literals": [{"text": t, "route": r and r[0], "column": r and r[1]} for (t, _), r in found.items()],
    }


STEPS = 50_000_000  # SQLite steps before a query counts as too slow


def _cell(v):
    """One result value as compared: text trimmed, numbers by value (5 and 5.0 alike),
    rounded to 6 decimals."""
    if isinstance(v, float):
        v = round(v, 6)
        return int(v) if v.is_integer() else v
    return v.strip() if isinstance(v, str) else v


def result(path, sql: str) -> dict:
    """Run `sql` read-only. status is ok, empty, error or slow; `hash` names the result
    rows as a multiset (order ignored, column order kept, text trimmed, numbers by value
    and rounded) so two queries with the same answer get the same hash; `sample` keeps
    the first rows to show."""
    steps = 0

    def tick():
        nonlocal steps
        steps += 1000
        return steps > STEPS

    with closing(connect(path)) as conn:
        conn.set_progress_handler(tick, 1000)
        try:
            rows = conn.execute(sql).fetchall()
        except sqlite3.Error as error:
            return {"status": "slow" if steps > STEPS else "error", "error": str(error)[:200], "rows": 0}
    norm = sorted(json.dumps([_cell(v) for v in row]) for row in rows)
    return {"status": "ok" if rows else "empty", "rows": len(rows),
            "hash": hashlib.sha256("\n".join(norm).encode()).hexdigest()[:16],
            "sample": [list(map(str, r))[:6] for r in rows[:3]]}
