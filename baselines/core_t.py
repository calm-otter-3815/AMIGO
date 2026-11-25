"""CORE-T (soliman2026core): the dense top-10 tables (name, an LLM-written purpose and the
first 5 rows), then one LLM call forms groups of joinable tables and keeps one, told how
well each pair joins (a unique column that holds the other column's values, scored by value
overlap and name likeness). The kept group then takes each member's best join partner and
grows greedily while joinability and relevance gain. One table set per question.

Departures from the paper:
1. granite-embedding-english-r2 replaces UAE-Large-V1, for table retrieval and for the
   column-name term of the join score; the embedded texts are the paper's, but granite reads up
   to 8192 tokens of a table's text where UAE reads 512. [medium]
2. AMIGO's default LLM and reasoning effort replace Llama-3.1-8B / Qwen-2.5-7B, for the
   purposes and the selection; temperature cannot be set (paper: greedy, 0). [medium]
3. Replies are JSON by a strict schema: the purpose is one field (the string None means no
   purpose), the selection keeps the paper's own JSON keys; one re-ask on a reply off the
   schema replaces the code's JSON repair; one user message, not the code's system message. [small]
4. Prompts: the paper's few-shot example (campaigns) is replaced by an invented beekeeping one
   of the same shape; an output-format line is added to the purpose prompt and both end with
   "Return an answer only in this exact Output Format."; dashes are written plain. [small]
5. Where paper and code differ, the code is followed: the first 5 rows (paper: 5 random rows);
   a retrieval similarity and a purpose line per table and the code's pair lines in the
   selection prompt; equal declared column types needed for a join pair; a column with a NULL
   is never unique; min-max scaled retrieval scores and a 0.01 edge floor in the greedy step. [small]
6. Column values are read with the code's SQL path, so only SQL NULL is null; the code's default
   CSV path also counts the strings '', null, none, nan and nat as NULL. [small]
"""

import json
import os
import string
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from itertools import combinations
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from amigo import config, embed, index, llm
from amigo.profile import quote

from .lake import lap, record

K = 10
ROWS = 5
TAU = 0.5  # a seed's best partner joins the group above this compatibility
EDGE_MIN = 0.01  # the greedy step only considers tables this joinable with the group
W_COH = W_REL = 0.5
WORKERS = 16  # purpose calls at the first use of a lake
# BL_CACHE_DIR moves the index caches: they are keyed by lake name only, so a rebuilt lake needs its own
CACHE = Path(os.environ.get("BL_CACHE_DIR", config.ROOT / "runs" / "eval" / "bl_cache")) / "core_t"

PURPOSE = string.Template("""Given the following table, describe the purpose of this table in layman's terms in one paragraph. If you do not think the text is semantically meaningful, output None.
$table

Output Format: a JSON object with exactly the key "purpose", whose value is the one paragraph as a string, or the string "None".
Return an answer only in this exact Output Format.""")

SELECT = string.Template("""You are a SQL schema analyst.
Your task: From a set of retrieved tables, identify a comprehensive set of tables that are BOTH:
(1) Relevant to the given query, and
(2) Compatible (joinable) with each other to answer the query.

IMPORTANT:
- Do NOT aggressively eliminate tables.
- If there is a reasonable probability that a table is relevant and compatible, keep it.
- When uncertain, prefer to keep the table rather than remove it; it is better to have slightly more tables than to risk removing a necessary one.
- Only remove a table if it is clearly irrelevant or incompatible.

---

### Information Provided:
- **Query**: $query
- **Tables**: $tables
  Each table includes:
  - Table name
  - Table header and sample content in markdown format (5 rows)
- **Compatibility analysis (restricted to valid key-foreign key pairs)**: $compat
  For each pair of tables, compatibility scores are included **only if** at least one column of the first table is completely unique and at least one column of the second table is a subset of it.
  If no such relationship exists, that pair is omitted (since all scores would be zero).

  For included pairs, the following metrics are provided:
    - `overall_compatibility`: Highest weighted score between all possible column pairs that satisfy the constraint: one column is unique, the other is a subset of it.
    - `best_join_columns`: The specific column pair with the highest overall compatibility score.

---

### Step-by-step reasoning policy (YOU MUST FOLLOW THIS ORDER):

**Step 1 - Understand the query**
- Identify the core entities and relationships.
- Determine what type of data is required to answer it.

**Step 2 - Evaluate individual table relevance**
- Use table name, column names, and sample data to decide if each table is relevant.
- When unsure, treat the table as potentially relevant.

**Step 3 - Evaluate pairwise compatibility**
For each pair of retrieved tables:
- Interpret the compatibility scores.
- Cross-check with table semantics from names, sample values.
- When in doubt about compatibility, keep the pair as potentially relevant.

**Step 4 - Group formation**
- Form one or more groups of tables where all members are mutually joinable.
- Groups must form connected join graphs (no isolated tables).
- Prefer forming larger groups when there is uncertainty rather than splitting unnecessarily.

**Step 5 - Group selection**
- Select the single most relevant and compatible group for the query.
- High recall is as important as precision in this step; include tables that are possibly relevant to ensure coverage.

---

### Output Format:
Return the output as valid JSON in the following format:

{
  "overall_reasoning": "Your general approach and observations about the tables and query",
  "group_formation": {
    "reasoning": "How groups were formed based on provided quantitative and qualitative information",
    "groups_formed": [
      {
        "group_index": 0,
        "table_indices": [0, 1, 2],
        "group_description": "Description of what this group represents"
      }
    ]
  },
  "group_selection": {
    "selected_group_index": 0,
    "reasoning": "Detailed explanation of why this group was selected for the query",
    "group_analysis": [
      {
        "group_index": 0,
        "reasoning": "Why this group is/isn't suitable for the query"
      }
    ]
  }
}

---

### Few-shot Example

**Example Input**:
Query:
"In apiaries with exactly 2 inspections, how many of the inspections counted 0 queen cells?"

Tables:
Table 0:
Table name: apiaries
Example table content:
| apiary_id | keeper_id | name            | founded_at           | inspection_count |
|----------:|----------:|-----------------|----------------------|-----------------:|
| 10        | 1         | Clover Ridge    | 2024-01-05 10:00:00  | 2                |
| 11        | 2         | Heather Hollow  | 2024-02-10 09:30:00  | 1                |
| 12        | 1         | Linden Row      | 2024-03-01 12:15:00  | 2                |

Table 1:
Table name: hive_inspections
Example table content:
| inspection_id | apiary_id | hive_code | queen_cells | frames_brood | inspected_at         |
|--------------:|----------:|-----------|------------:|-------------:|----------------------|
| 100           | 10        | H-A       | 0           | 5            | 2024-04-05 10:05:00  |
| 101           | 10        | H-B       | 3           | 7            | 2024-04-05 10:40:00  |
| 102           | 11        | H-A       | 1           | 4            | 2024-04-10 09:35:00  |
| 103           | 12        | H-C       | 0           | 6            | 2024-04-11 12:20:00  |
| 104           | 12        | H-D       | 2           | 8            | 2024-04-11 12:51:00  |

Table 2:
Table name: glaciers
Example table content:
| glacier_id | name           | range        | area_km2 |
|-----------:|----------------|--------------|---------:|
| 1          | Silverhorn     | North Massif | 15.2     |
| 2          | Kaltfirn       | Gray Ridge   | 78.0     |
| 3          | Brenngletscher | Ash Valley   | 16.6     |

Compatibility analysis:
Pair (Table 0 <-> Table 1):
  overall_compatibility: 0.96
  best_join_columns: "apiary_id ↔ apiary_id"

**Example Output**:
{
  "overall_reasoning": "The query is about apiaries and their inspections. The 'apiaries' table holds apiary-level data including inspection_count, while 'hive_inspections' holds per-inspection data including queen_cells and apiary_id for linking. The 'glaciers' table is unrelated to the query and has no compatible join key with the other tables.",
  "group_formation": {
    "reasoning": "Formed one group with 'apiaries' and 'hive_inspections' because they are both relevant to the query and strongly joinable via apiary_id ↔ apiary_id. 'glaciers' is excluded due to lack of relevance and join compatibility.",
    "groups_formed": [
      {
        "group_index": 0,
        "table_indices": [0, 1],
        "group_description": "Apiaries and their hive inspections, enabling filtering by inspection_count and counting inspections with queen_cells = 0."
      }
    ]
  },
  "group_selection": {
    "selected_group_index": 0,
    "reasoning": "This group contains all and only the tables needed to answer the query: apiaries to identify those with exactly 2 inspections, and hive_inspections to count inspections with queen_cells equal to 0.",
    "group_analysis": [
      {
        "group_index": 0,
        "reasoning": "Fully suitable and sufficient for the query; no other table contributes necessary information."
      }
    ]
  }
}

Return an answer only in this exact Output Format.""")


class Purpose(BaseModel):
    purpose: str


class Group(BaseModel):
    group_index: int
    table_indices: list[int]
    group_description: str


class Formation(BaseModel):
    reasoning: str
    groups_formed: list[Group]


class GroupNote(BaseModel):
    group_index: int
    reasoning: str


class Choice(BaseModel):
    selected_group_index: int
    reasoning: str
    group_analysis: list[GroupNote]


class Selection(BaseModel):
    overall_reasoning: str
    group_formation: Formation
    group_selection: Choice


def _card(lake, table, log_path) -> dict:
    """The table's first rows as the code's Markdown, and its purpose from that Markdown."""
    with closing(index.open_source(lake.paths[table.database])) as conn:
        cursor = conn.execute(f"SELECT * FROM {quote(table.name)} LIMIT {ROWS}")
        names = [d[0] for d in cursor.description]
        rows = cursor.fetchall() or [[None] * len(names)]
    markdown = "\n".join([f"Table name: {table.name}", "Example table content:",
                          "| " + " | ".join(names) + " |", "|" + "|".join("-------:" for _ in names) + "|",
                          *("| " + " | ".join("" if v is None else str(v) for v in row) + " |" for row in rows)])
    reply = llm.call(PURPOSE.substitute(table=markdown), Purpose, log_path, f"core_t purpose {table.path}")
    purpose = reply.purpose.strip()
    return {"path": table.path, "markdown": markdown, "purpose": None if purpose.lower() == "none" else purpose}


def _words(text: str) -> set[str]:
    return set(text.replace("_", " ").replace(".", " ").lower().split())


class _State:
    """One lake's cards, table vectors and pair compatibilities, built once and kept on disk."""

    def __init__(self, lake, log_path):
        self.lake, self.lock, self.profiles = lake, threading.Lock(), {}
        self.folder = CACHE / config.LLM_MODEL / lake.name  # the purposes are this model's
        meta, npy = self.folder / "tables.json", self.folder / "tables.npy"
        cards = json.loads(meta.read_text()) if meta.exists() and npy.exists() else None
        if cards is None or [c["path"] for c in cards] != [t.path for t in lake.tables]:
            with ThreadPoolExecutor(WORKERS) as pool:
                cards = list(pool.map(lambda t: _card(lake, t, log_path), lake.tables))
            vectors = embed.embed([f"Table name: {t.name.lower()}\nTable purpose: {c['purpose'] or ''}\n"
                                   f"Table content: {c['markdown']}" for t, c in zip(lake.tables, cards)])
            self.folder.mkdir(parents=True, exist_ok=True)
            np.save(npy, vectors)
            meta.write_text(json.dumps(cards, ensure_ascii=False))
        self.cards = {c["path"]: c for c in cards}
        self.vectors = np.load(npy)
        self.compat = {}
        pairs = self.folder / "compat.jsonl"
        if pairs.exists():
            for line in filter(None, pairs.read_text().split("\n")):
                a, b, score, ca, cb = json.loads(line)
                self.compat[a, b] = (score, ca, cb)

    def profile(self, table) -> list:
        """Per column: name, declared type, unique (no NULL, all distinct), distinct values as
        text, and the vector of 'table column' (the code's SQL path)."""
        if table.path not in self.profiles:
            out = []
            with closing(index.open_source(self.lake.paths[table.database])) as conn:
                name = quote(table.name)
                counts = conn.execute("SELECT COUNT(*)" + "".join(f", COUNT({quote(c.name)})" for c in table.columns)
                                      + f" FROM {name}").fetchone()
                heads = embed.embed([f"{table.name} {c.name}".replace("_", " ").lower().strip() for c in table.columns])
                for c, filled, head in zip(table.columns, counts[1:], heads):
                    col = quote(c.name)
                    values = [v for (v,) in conn.execute(f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL")]
                    unique = filled == counts[0] and 0 < filled == len(values)
                    out.append((c.name, c.type, unique, {str(v) for v in values}, head))
            self.profiles[table.path] = out
        return self.profiles[table.path]

    def pair(self, a, b) -> tuple[float, str, str]:
        """CS(a, b): the best score of a valid column pair (one column unique and holding the
        other's values, same declared type), with that pair's columns of a and of b."""
        key = (a.path, b.path) if a.path < b.path else (b.path, a.path)
        if key not in self.compat:
            x, y = (a, b) if key[0] == a.path else (b, a)
            best = (0.0, "", "")
            for cx, kx, ux, vx, ex in self.profile(x):
                for cy, ky, uy, vy, ey in self.profile(y):
                    if kx != ky or not (ux or uy) or not vx or not vy or not (vx <= vy or vy <= vx):
                        continue
                    jaccard = min(len(vx), len(vy)) / max(len(vx), len(vy))  # one set holds the other
                    wx, wy = _words(f"{x.name} {cx}"), _words(f"{y.name} {cy}")
                    exact = len(wx & wy) / min(len(wx), len(wy)) if wx and wy else 0.0
                    score = 0.5 * jaccard + 0.5 * (0.5 * float(ex @ ey) + 0.5 * exact)
                    if score > best[0]:
                        best = (score, cx, cy)
            self.compat[key] = best
            with (self.folder / "compat.jsonl").open("a") as handle:
                handle.write(json.dumps([*key, *best], ensure_ascii=False) + "\n")
        score, cx, cy = self.compat[key]
        return (score, cx, cy) if key[0] == a.path else (score, cy, cx)


_STATES: dict[str, _State] = {}
_LOCK = threading.Lock()


def run(lake, question, log_path):
    with _LOCK:
        if lake.name not in _STATES:
            _STATES[lake.name] = _State(lake, log_path)
        state = _STATES[lake.name]
    lap("setup")
    question = question.strip()
    scores = state.vectors @ embed.embed([question])[0]
    top = [int(i) for i in np.argsort(-scores, kind="stable")[:K]]
    tables, rs = [lake.tables[i] for i in top], [float(scores[i]) for i in top]
    k = len(tables)
    lap("search")
    with state.lock:
        pairs = {(i, j): state.pair(tables[i], tables[j]) for i, j in combinations(range(k), 2)}
    cs = [[0.0] * k for _ in range(k)]
    for (i, j), (score, _, _) in pairs.items():
        cs[i][j] = cs[j][i] = score
    lap("compat")

    blocks = [f"Table {i} (Retrieval similarity={rs[i]:.3f}):\n{state.cards[t.path]['markdown']}\n"
              f"Purpose: {state.cards[t.path]['purpose']}\n" for i, t in enumerate(tables)]
    lines = [f"Pair (Table {i}: {tables[i].name.lower()} <-> Table {j}: {tables[j].name.lower()}):\n"
             f"  Overall Compatibility: {score:.3f}\n  Best Join Columns: {ci} ↔ {cj}"
             for (i, j), (score, ci, cj) in pairs.items() if score != 0]
    prompt = SELECT.substitute(query=question, tables="\n".join(blocks), compat="\n".join(lines))
    # a failed call (a flex 429 after the retries) fails the question, so a later pass redoes it
    reply = llm.call(prompt, Selection, log_path, f"core_t select {question[:50]}")
    groups = [[i for i in g.table_indices if 0 <= i < k] for g in reply.group_formation.groups_formed]
    groups = [g for g in groups if g]
    chosen = reply.group_selection.selected_group_index
    fallback = None
    if not groups:
        picked, fallback = list(range(k)), f"no valid group, all top-{k} kept"
    else:
        picked = groups[chosen if 0 <= chosen < len(groups) else 0]

    lap("llm select")
    # adjustment 1: each seed's best partner in the top-k, when it joins above TAU
    seeds = list(dict.fromkeys(picked))
    group = list(seeds)
    for s in seeds:
        partner = max((j for j in range(k) if j != s), key=lambda j: (cs[s][j], -j), default=None)
        if partner is not None and cs[s][partner] > TAU and partner not in group:
            group.append(partner)
    group = seeds + sorted(group[len(seeds):], key=lambda j: -rs[j])

    # adjustment 2: greedy growth while mean joinability and mean scaled relevance gain
    low, high = min(rs), max(rs)
    rel = [(r - low) / ((high - low) or 1.0) for r in rs]

    def coherence(g):
        links = [cs[i][j] for i, j in combinations(g, 2)]
        return sum(links) / len(links) if links else 0.0

    def relevance(g):
        return sum(rel[i] for i in g) / len(g)

    while len(group) < k:
        best, gain = None, -1e9
        for t in range(k):
            if t in group or max(cs[t][g] for g in group) < EDGE_MIN:
                continue
            new = group + [t]
            delta = (W_COH * (coherence(new) - coherence(group))
                     + W_REL * (relevance(new) - relevance(group)))
            if delta > gain:
                best, gain = t, delta
        if best is None or gain <= 0:
            break
        group.append(best)
    lap("adjust")
    return record([tables[i].path for i in group], **({"fallback": fallback} if fallback else {}))
