# Baselines

Single-answer table retrievers, re-implemented on AMIGO's lakes so every method reads the
same tables, columns and vectors and is scored by the same code
(`experiments/eval_lakes.py`). No method reads the gold. Each module's docstring gives its
paper and every departure from it.

| module | method | answer |
|---|---|---|
| `dense.py` | dense retrieval over the lake's table vectors | top k tables |
| `bm25.py` | BM25 over each table's database, name, description and column names (SQLite FTS5) | top k tables |
| `hybrid.py` | BM25 and dense rankings fused by reciprocal rank fusion (Cormack et al. 2009) | top k tables |
| `jar.py` | JAR (Chen et al. 2024): sub-queries, then a mixed-integer program picks k joinable tables | k tables |
| `greedy_jar.py` | Greedy JAR (arXiv 2511.13418): JAR's sub-queries and pool, k tables picked one at a time by coverage, joins and closeness | top k tables |
| `crush4sql.py` | CRUSH4SQL (Kothyari et al. 2023): an LLM writes a made-up schema, the closest real columns are picked | tables of b columns |
| `murre.py` | MURRE (Zhang et al. 2025): beam search over up to 3 hops, an LLM writes what is still missing | top k tables |
| `core_t.py` | CORE-T (Soliman et al. 2026): an LLM forms groups of joinable tables and keeps one | one table set |
| `full_schema.py` | every table of the lake in one prompt; one LLM call names the tables (no size cap: a lake that does not fit fails) | the tables it names |
| `route_sql.py` | the database of the closest table, then one LLM call writes SQL over it | the tables the SQL reads |
| `sql.py` | `sql=1` on any method: one LLM call writes SQL over its tables | the tables the SQL reads |

Run one (records go to `runs/eval/bl_<tag>/records.json`; `EVAL_RUNS` and `EVAL_QUESTIONS`
pick another folder and question file):

```bash
.venv/bin/python -m baselines.run dense k=10
.venv/bin/python -m baselines.run jar k=3
.venv/bin/python -m baselines.run crush4sql b=100
.venv/bin/python -m baselines.run murre k=10
.venv/bin/python -m baselines.run core_t
.venv/bin/python -m baselines.run route_sql
.venv/bin/python -m baselines.run dense k=3 sql=1
```

Smaller sizes are cut from a larger run where the smaller answer is always the start of
the larger one (`cut.py`): dense and MURRE k=1, 3, 5 from k=10; CRUSH4SQL's first 1, 3, 5,
10 tables from b=100. JAR picks its k tables as a whole, so it runs at each k.

```bash
.venv/bin/python -m baselines.cut bl_dense_k10 3
.venv/bin/python -m baselines.cut bl_crush4sql_b100 10 tables
```

`experiments/run_benchmark.sh LAKE` runs all of them, AMIGO and the scores for one
benchmark. The paper's results: see "Results" in the top README.
