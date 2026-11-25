"""Route, then write SQL: the database of the table closest to the question (the lake's
table vectors), then one LLM call writes SQL over that whole database. The plain
pipeline that open-domain text-to-SQL work (DBCopilot, CRUSH4SQL) improves on."""

from . import sql
from .lake import lap


def run(lake, question, log_path):
    best, _ = lake.rank_tables(question)[0]
    lap("route")
    return sql.answer(lake, best.database, lake.in_database(best.database), question, log_path)
