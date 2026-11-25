"""One SQLite query for a question over chosen tables of one database, written by an
LLM call; what the query reads is the method's one interpretation."""

import sqlite3
import string
from collections import Counter
from contextlib import closing

from pydantic import BaseModel

from amigo import index, llm

from .lake import Lake, Table, lap, record

PROMPT = string.Template('''You write one SQLite query that answers a question over the database below.

Database (CREATE TABLE statements; the comment after a column says what it holds and shows stored values):
$schema

Example, over a made-up database that is not the one above:
CREATE TABLE "harbor" (
  "harbor_id" INTEGER PRIMARY KEY,  -- The harbor's number. Examples: 1, 2, 3.
  "name" TEXT,  -- The harbor's name. Examples: Port Lyra, Saltmere.
);
CREATE TABLE "vessel" (
  "vessel_id" INTEGER PRIMARY KEY,  -- The vessel's number. Examples: 10, 11.
  "home_harbor" INTEGER,  -- The harbor the vessel is based in. Examples: 1, 2.
  "tonnage" REAL,  -- The vessel's weight in tonnes. Examples: 320.5, 910.0.
  FOREIGN KEY ("home_harbor") REFERENCES "harbor"("harbor_id"),
);
Question: How many vessels of more than 500 tonnes are based in Saltmere?
Answer: {"sql": "SELECT COUNT(*) FROM vessel JOIN harbor ON vessel.home_harbor = harbor.harbor_id WHERE harbor.name = 'Saltmere' AND vessel.tonnage > 500"}

Rules:
- SQLite dialect, one SELECT statement.
- Use only the tables and columns of the database above.
- Never write the database name in the SQL.
- Double-quote any name that holds a space or a character other than a letter, a digit or an underscore.

Question: $question

Output Format: a JSON object with exactly the key "sql", whose value is one SQLite SELECT statement as a string. No other text.
Return an answer only in this exact Output Format.''')


class Query(BaseModel):
    sql: str


def write(lake: Lake, database: str, tables: list[Table], question: str, log_path) -> str:
    def runs(reply: Query) -> None:
        try:
            with closing(index.open_source(lake.paths[database])) as conn:
                conn.execute("EXPLAIN " + reply.sql)
        except sqlite3.Error as err:
            raise llm.ModelError(f"the query does not run on SQLite: {err}") from err

    prompt = PROMPT.substitute(schema=lake.schema_text(tables, qualified=False), question=question)
    return llm.call(prompt, Query, log_path, f"baseline sql {question[:50]}", check=runs).sql


def answer(lake: Lake, database: str, tables: list[Table], question: str, log_path) -> dict:
    """The record of a method that writes SQL: the tables and columns its query reads."""
    sql = write(lake, database, tables, question, log_path)
    lap("llm sql")
    read_tables, read_columns = lake.reads(database, sql)
    lap("read sql")
    return record(read_tables, read_columns, levels=("columns", "tables", "interpretation"),
                  database=database, sql=sql)


def after(lake: Lake, retrieved: dict, question: str, log_path) -> dict:
    """SQL over what a table retriever returned. A query runs on one database: the one
    holding most of the returned tables, ties to the one of the best-ranked table."""
    order = [lake.table[path] for path in retrieved["order"]]
    if not order:
        return retrieved | {"error": "the retriever returned no table"}
    counts = Counter(t.database for t in order)
    database = max(counts, key=lambda d: (counts[d], -[t.database for t in order].index(d)))
    got = answer(lake, database, [t for t in order if t.database == database], question, log_path)
    return got | {"retrieved": retrieved["order"]}
