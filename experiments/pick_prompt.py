"""What a BIRD gold query reads, for experiments/sample_bird100.py.

This was the script that compared two renderings of the pick prompt; the new one won
and became prompts/pick.txt (experiments/results/pick_prompt_20260913-181530.md, removed; in git history at acf8b59), and
its run loop is gone. experiments/test_pick_gold.py checks `gold_columns`.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from amigo.probe import Probe  # noqa: E402

# SQL words that are never a column name; everything else bare is resolved against
# the tables of the FROM/JOIN clauses.
KEYWORDS = set(
    """select distinct from where group by having order limit offset as on join inner
    left right full outer cross union all except intersect and or not in is null like
    between exists case when then else end asc desc count sum avg min max cast real
    integer text numeric int date datetime strftime substr replace iif coalesce nullif
    round abs length lower upper trim julianday true false with values""".split()
)


def _bare(name: str) -> str:
    return name.strip().strip("`\"[]")


def gold_columns(sql: str, schema: dict[str, list[str]]) -> tuple[set[str], set[str]]:
    """The tables and `table.column` pairs a BIRD query reads.

    `schema` maps table name to its column names, both in the database's own spelling.
    A regex, not a parser: BIRD dev queries are single statements with `T1.col`,
    `table.col`, backticked names and bare names.
    """
    by_table = {t.lower(): {c.lower(): c for c in cols} for t, cols in schema.items()}
    real = {t.lower(): t for t in schema}
    text = re.sub(r"'[^']*'", " ", sql)

    aliases: dict[str, str] = {}
    for target, alias in re.findall(
        r"(?:FROM|JOIN)\s+(`[^`]+`|\[[^\]]+\]|\"[^\"]+\"|\w+)"
        r"(?:\s+(?:AS\s+)?(`[^`]+`|\w+))?",
        text,
        re.IGNORECASE,
    ):
        table = _bare(target).lower()
        if table not in by_table:
            continue
        aliases[table] = table
        if alias and _bare(alias).lower() not in KEYWORDS:
            aliases[_bare(alias).lower()] = table

    tables = set(aliases.values())
    found: set[str] = set()
    for qualifier, column in re.findall(r"(`[^`]+`|\w+)\s*\.\s*(`[^`]+`|\w+)", text):
        table = aliases.get(_bare(qualifier).lower())
        name = by_table.get(table, {}).get(_bare(column).lower()) if table else None
        if name:
            found.add(f"{real[table]}.{name}")

    rest = re.sub(r"(`[^`]+`|\w+)\s*\.\s*(`[^`]+`|\w+)", " ", text)
    for token in re.findall(r"`[^`]+`|\b[A-Za-z_]\w*\b", rest):
        word = _bare(token).lower()
        if word in KEYWORDS or word in aliases:
            continue
        for table in tables:
            if word in by_table[table]:
                found.add(f"{real[table]}.{by_table[table][word]}")
    return {real[t] for t in tables}, found


def schema_of(probe: Probe, db_id: str) -> dict[str, list[str]]:
    tables = {t["id"]: t["name"] for t in probe.tables.values() if t["database"] == db_id}
    schema: dict[str, list[str]] = {name: [] for name in tables.values()}
    for column in probe.columns.values():
        if column["table_id"] in tables:
            schema[tables[column["table_id"]]].append(column["name"])
    return schema
