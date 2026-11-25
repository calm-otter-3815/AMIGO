"""Step 5: answer the question with each accepted candidate, and run it (one LLM call each).

  .venv/bin/python -m labeler.swap

For each option the judge accepted (decoys aside), code first tries the plain swaps:
another column of the same table (when a filter value is stored the same way in it), or
a same-named table of the same database (a copy). Otherwise the LLM rewrites the gold SQL
so the words are read as that option, inside the option's own database (a lake is many separate
databases): same database, it changes only what it must; another database, it writes the
query over that database's tables, or says the question cannot be answered there. Code
runs the query. A query that fails is sent back once with the SQLite error. The result
hash is compared with the gold's: same rows, different rows, empty or failed.
Writes runs/labeler/swap.jsonl.
"""

import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

from labeler import dbs, full, llm, read, run, split_item, table_of
from labeler.gold import connect, ident, result
from labeler.link import note
from labeler.pool import Lake

TABLES = 30  # most tables shown from another database
SCHEMA_CHARS = 30_000  # longest table list shown (taco_us has tables of 1000+ columns; the lakes before stay under 23,000)

SCHEMA = {"type": "object", "required": ["sql"], "additionalProperties": False,
          "properties": {"sql": {"type": ["string", "null"]}}}

PROMPT = """You rewrite a SQL query so that it answers the same question with a different reading of some of its words.

A question was asked to a data lake (many separate SQLite databases). The reference SQL reads the words "{words}" as {gold}. Another reading takes these words to mean {option}. Write the SQLite query that answers the question under this other reading.

Rules:
- The query runs on the database "{db}" only. Use only the tables and columns listed below.
- Keep everything else the question asks for. When the reference SQL uses the same database, change only what the other reading needs (and the joins it needs).
- When a filter value is stored differently in the new column (a code, another spelling, another format), use the form the new column stores, as its values show.
- When this database cannot answer the question under this reading (a part of the question has no place here), give null.

Example
Question: "Which ferries leave from Brest?"
Reference SQL (database "harbor"): SELECT f.name FROM ferries f JOIN port_calls p ON p.ferry_id = f.id WHERE p.departure_port = 'Brest'
Words: "leave from Brest", reference reading: port_calls.departure_port
Other reading: ferries.home_port (TEXT) values: BRS, PLY, SAN
Tables of database "harbor":
ferries(id INTEGER, name TEXT, home_port TEXT)
port_calls(ferry_id INTEGER, departure_port TEXT, arrival_port TEXT, day TEXT)
Output Format:
{{"sql": "SELECT name FROM ferries WHERE home_port = 'BRS'"}}

Now this one.
Question: "{question}"
Reference SQL (database "{gold_db}"): {gold_sql}
Words: "{words}", reference reading: {gold}
Other reading: {option}
Tables of database "{db}":
{tables}

Output Format: a JSON object with exactly the key "sql", whose value is one SQLite query as a string, or null. No other text.
Return an answer only in this exact Output Format."""

CROSS = """You rewrite a SQL query so that it answers the same question with a different reading of some of its words.

A question was asked to a data lake (many separate SQLite databases); its reference SQL reads several databases at once. The reference SQL reads the words "{words}" as {gold} (database "{gold_db}"). Another reading takes these words to mean {option} (database "{db}"). Write the SQLite query that answers the question under this other reading.

Rules:
- The query runs on the databases {within} attached together. Name every table with its database, as database.table, and use only the tables and columns listed below.
- Keep everything else the question asks for: change only what the other reading needs (and the joins it needs).
- When a filter value is stored differently in the new column (a code, another spelling, another format), use the form the new column stores, as its values show.
- When these databases cannot answer the question under this reading (a part of the question has no place here), give null.

Example
Question: "Which ferries arrived on stormy days?"
Reference SQL (databases "harbor", "weather"): SELECT f.name FROM harbor.ferries f JOIN harbor.port_calls p ON p.ferry_id = f.id JOIN weather.daily d ON d.day = p.day WHERE d.storm = 1
Words: "stormy days", reference reading: daily.storm (INTEGER) values: 0, 1 (database "weather")
Other reading: alerts.kind (TEXT) values: STORM, FOG, HEAT (database "weather")
Tables of databases "harbor", "weather":
harbor.ferries(id INTEGER, name TEXT, home_port TEXT)
harbor.port_calls(ferry_id INTEGER, arrival_port TEXT, day TEXT)
weather.daily(day TEXT, storm INTEGER, rain_mm REAL)
weather.alerts(day TEXT, kind TEXT, region TEXT)
Output Format:
{{"sql": "SELECT DISTINCT f.name FROM harbor.ferries f JOIN harbor.port_calls p ON p.ferry_id = f.id JOIN weather.alerts a ON a.day = p.day WHERE a.kind = 'STORM'"}}

Now this one.
Question: "{question}"
Reference SQL (databases {gold_dbs}): {gold_sql}
Words: "{words}", reference reading: {gold} (database "{gold_db}")
Other reading: {option} (database "{db}")
Tables of databases {within}:
{tables}

Output Format: a JSON object with exactly the key "sql", whose value is one SQLite query as a string, or null. No other text.
Return an answer only in this exact Output Format."""

RETRY = """

Your previous query failed in SQLite:
{sql}
Error: {error}
Write a corrected query."""


def schema_text(lake: Lake, db: str | list[str], first: list[str]) -> str:
    """CREATE-style lines for the `first` tables, then the database's other tables, up to TABLES
    tables and SCHEMA_CHARS characters (each `first` table always shown once). A list of
    databases (a question across databases) shows their tables named db.table."""
    within = db if isinstance(db, list) else [db]
    tables = [t for t in lake.tables if t.split(".", 1)[0] in within]
    ordered = [t for t in first if t in tables] + [t for t in tables if t not in first]
    lines, size = [], 0
    for t in ordered[:TABLES]:
        line = f"{t if isinstance(db, list) else t.split('.', 1)[1]}({', '.join(f'{c} {k}'.strip() for c, k in lake.columns[t])})"
        if size + len(line) <= SCHEMA_CHARS or (t in first and line not in lines):
            lines.append(line)
            size += len(line) + 1
    return "\n".join(lines)


CLAUSE = r"(?:FROM|JOIN)\s+[\"`]?{t}[\"`]?(?:\s+(?:AS\s+)?(?!(?:ON|WHERE|JOIN|INNER|LEFT|RIGHT|CROSS|GROUP|ORDER|LIMIT|USING)\b)(\w+))?"


def family(kind: str) -> str:
    """number, text or '' (unknown) for a declared SQLite column type."""
    kind = kind.upper()
    if any(t in kind for t in ("INT", "REAL", "NUM", "DOUB", "FLOA", "DEC", "BOOL")):
        return "number"
    return "text" if any(t in kind for t in ("CHAR", "TEXT", "CLOB")) else ""


def named(text: str, column: str, names: str) -> bool:
    """The column is mentioned bare or qualified by one of the item table's aliases (`names`)."""
    return bool(re.search(rf"(?<![\w.])(?:(?:{names})\.)?[\"`\[]?{re.escape(column)}[\"`\]]?(?!\w)", text, re.I))


def code_swap(lake: Lake, row: dict, item: dict, name: str) -> str | None:
    """The gold SQL with the gold column (or table, only by its copy) replaced by `name`, when
    that is a plain textual swap; None when it needs the LLM."""
    sql, db = row["gold_sql"], name.split(".", 1)[0]
    if db != row["db_id"]:
        return None
    if "copy" in item.get("sources", []):
        old, new = item["item"].split(".", 1)[0], name.split(".")[1]
        swapped, n = re.subn(rf"\b(FROM|JOIN)\s+[\"`]?{re.escape(old)}[\"`]?(?=\s|$|,|\))", lambda m: f"{m[1]} {ident(new)}", sql, flags=re.I)
        # quoted "table".column prefixes follow the table (taco_us); bare ones stay as before
        swapped = re.sub(rf"([\"`]){re.escape(old)}\1\.", lambda m: f"{ident(new)}.", swapped, flags=re.I)
        return swapped if n else None
    if item["kind"] == "table":  # a table that is not a copy has other columns and rows: the LLM writes it
        return None
    table, column = split_item(item["item"])
    _, new_table, new_column = name.split(".", 2)
    if new_table.lower() != table.lower():
        return None
    aliases = {a for a in re.findall(CLAUSE.format(t=re.escape(table)), sql, re.I) if a} | {table}
    names = "|".join(re.escape(a) for a in aliases)
    # join keys, subqueries, an answer column also used elsewhere: a textual swap cannot tell which mentions to change
    on = " ".join(re.findall(r"\bON\b(.*?)(?=\b(?:JOIN|INNER|LEFT|RIGHT|CROSS|WHERE|GROUP|ORDER|HAVING|LIMIT)\b|$)", sql, re.I | re.S))
    head = re.search(r"\bSELECT\b(.*?)\bFROM\b", sql, re.I | re.S)
    if (len(re.findall(r"\bSELECT\b", sql, re.I)) > 1 or named(on, column, names)
            or item["role"] == "answer" and named(sql[head.end(1):] if head else sql, column, names)):
        return None
    if item["role"] != "answer":  # a filter or sort keeps its comparison: only safe on the same kind of value
        kinds = {c.lower(): k for c, k in lake.columns.get(lake.case.get(f"{db}.{table}".lower(), ""), [])}
        old_kind, new_kind = family(kinds.get(column.lower(), "")), family(kinds.get(new_column.lower(), ""))
        if old_kind != new_kind or not old_kind:
            return None
    if item.get("literal"):
        with closing(connect(lake.paths[db])) as conn:
            try:
                if not conn.execute(f"SELECT 1 FROM {ident(table)} WHERE {ident(new_column)} = ? LIMIT 1", (item["literal"],)).fetchone():
                    return None
            except sqlite3.Error:
                return None
    swapped, n = re.subn(rf"([\"`]?)\b({names})\1\.[\"`]?{re.escape(column)}[\"`]?(?!\w)",
                         lambda m: f"{m[1]}{m[2]}{m[1]}.{ident(new_column)}", sql, flags=re.I)
    if not n and len(re.findall(r"\b(?:FROM|JOIN)\b", sql, re.I)) == 1:
        swapped, n = re.subn(rf"(?<![\w.])[\"`]?{re.escape(column)}[\"`]?(?!\w)", lambda m: ident(new_column), sql, flags=re.I)
    return swapped if n else None


def swap(lake: Lake, row: dict, item: dict, option: dict) -> dict:
    name = option["name"]
    gold_hash = row["gold"].get("hash")
    sql = code_swap(lake, row, {**item, "sources": option["sources"]}, name)
    if sql:
        res = result(lake.paths[name.split(".", 1)[0]], sql)
        if res["status"] not in ("error", "slow"):
            return {"name": name, "sql": sql, "result": res, "by": "code",
                    "answer": "empty" if res["status"] == "empty" else "same rows" if res["hash"] == gold_hash else "different rows"}
    db = name.split(".", 1)[0]
    table = name if item["kind"] == "table" else table_of(name)
    gold_tables = [full(row, t) for t in row["tables"]]
    paths = None  # one database: lake.paths[db]
    if "db_ids" in row:  # across databases: the gold's databases and the option's, attached together
        within = list(dict.fromkeys(dbs(row) + [db]))
        paths = {d: lake.paths[d] for d in within}
        prompt = CROSS.format(
            question=row["question"], words=item["words"], gold=item["gold_shown"], gold_db=item["gold"].split(".", 1)[0],
            option=lake.shown[name], db=db, within=", ".join(f'"{d}"' for d in within),
            gold_dbs=", ".join(f'"{d}"' for d in dbs(row)), gold_sql=row["gold_sql"],
            tables=schema_text(lake, within, [table, *gold_tables]))
    else:
        prompt = PROMPT.format(
            question=row["question"], words=item["words"], gold=item["gold_shown"], option=lake.shown[name],
            db=db, gold_db=row["db_id"], gold_sql=row["gold_sql"], tables=schema_text(lake, db, [table, *gold_tables]))
    out = {"name": name, "sql": None, "result": None, "by": "llm"}
    replied = False
    for seed in range(2):
        try:
            sql = llm.ask_json(prompt, seed, SCHEMA, tag=f"swap {row['id']} {name}")["sql"]
        except (ValueError, KeyError, TypeError):
            continue
        replied = True
        out["sql"] = sql
        if sql is None:
            break
        out["result"] = result(paths or lake.paths[db], sql)
        if out["result"]["status"] not in ("error", "slow"):
            break
        prompt += RETRY.format(sql=sql, error=out["result"].get("error", "too slow"))
    res = out["result"] or {}
    out["answer"] = ("not answerable" if replied and out["sql"] is None and res == {} else
                     "failed" if res.get("status") in (None, "error", "slow") else
                     "empty" if res["status"] == "empty" else
                     "same rows" if res["hash"] == gold_hash else "different rows")
    return out


def main() -> None:
    rows = {r["id"]: r for r in read("questions")}
    todo = read("judge")
    lakes = {name: Lake(name) for name in {rows[r["id"]]["lake"] for r in todo}}

    def one(record: dict) -> dict:
        row = rows[record["id"]]
        return swap_all(lakes[row["lake"]], row, record)

    run("swap", todo, one, colour="green", threads=48, note=note)


def swap_all(lake: Lake, row: dict, judged: dict) -> dict:
    """Every accepted option of one question, swapped and run, in parallel."""
    jobs = [(item, o) for item in judged["items"] for o in item.get("options", [])
            if o["verdict"] in ("yes", "copy") and not o["decoy"]]
    with ThreadPoolExecutor(max(len(jobs), 1)) as pool:
        done = list(pool.map(lambda job: swap(lake, row, *job), jobs))
    return {"id": judged["id"], "swaps": [{"item": item["item"], **d} for (item, _), d in zip(jobs, done)]}


if __name__ == "__main__":
    main()
