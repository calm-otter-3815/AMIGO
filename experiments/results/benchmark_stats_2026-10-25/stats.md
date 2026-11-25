# Benchmark statistics (gold label and multi-valid label)

From runs/paper_2026-10-20/lakes/<lake>/layer.sqlite and runs/labeler/<lake>/labels.jsonl, read with paper_results.labels (stage 1 view: every valid query, queries with the same tables and columns once) and sqleval.targets (stage 2 view: distinct non-empty results). No LLM call.

## BIRD

- databases: 11
- tables: 75
- columns: 798
- questions in labeler: 1534
### gold
- questions (retrieval): 1534
- questions (SQL): 1527
- tables per query: mean 1.94, median 2.00, max 5, min 1
- share single-table: 23.66
- databases per query: mean 1, median 1.00, max 1, min 1
### multi
- questions (retrieval): 1534
- questions (SQL): 1533
- valid queries per question: mean 2.72, median 2.00, max 14, min 1
- share with 2+ valid queries: 64.47
- table sets per question: mean 1.88, median 1.00, max 10, min 1
- share with 2+ table sets: 47.26
- tables per valid query: mean 2.14, median 2, max 5, min 1
- tables per table set: mean 2.21, median 2.00, max 5, min 1
- results per question (SQL questions): mean 1.88, median 1, max 12, min 1
- share with 2+ results (SQL questions): 47.16
- results, total (SQL questions): 2888
- share with a table set in another database: 2.22
- results out of reach of the oracle (one SQL per label table set): 541
- share of results out of reach of the oracle: 18.73
### labeler
- labels: 1534
- gold status: ok 1527, slow 7
- accepted alternatives: 3854
- accepted per question: 2.51
- kind: other database 828, same table 927, other table 2099
- rewritten by: llm 3307, code 547
- outcome: not answerable 754, same rows 1275, empty 279, different rows 1530, failed 16
- checks: decoys_accepted 3, decoys 4262, unsure 21, no_vote 77, revoted 11351, asked 113287, calls 21570, gold_items_found 3803, gold_items 4262
- distinct results in the gold database (2+): 46.02
- distinct results in the lake (2+): 47.13
- underspecified: items not asked: 3.91
- underspecified: note only: 2.93
- underspecified: value form: 26.73
- underspecified: computation: 58.21

## Spider

- databases: 166
- tables: 873
- columns: 4497
- questions in labeler: 1034
### gold
- questions (retrieval): 1034
- questions (SQL): 985
- tables per query: mean 1.51, median 1.00, max 4, min 1
- share single-table: 55.61
- databases per query: mean 1, median 1.00, max 1, min 1
### multi
- questions (retrieval): 1034
- questions (SQL): 1000
- valid queries per question: mean 2.57, median 2.00, max 19, min 1
- share with 2+ valid queries: 61.22
- table sets per question: mean 2.35, median 2.00, max 19, min 1
- share with 2+ table sets: 57.25
- tables per valid query: mean 1.59, median 1, max 5, min 1
- tables per table set: mean 1.57, median 1, max 5, min 1
- results per question (SQL questions): mean 2.21, median 2.00, max 14, min 1
- share with 2+ results (SQL questions): 52.80
- results, total (SQL questions): 2214
- share with a table set in another database: 41.01
- results out of reach of the oracle (one SQL per label table set): 159
- share of results out of reach of the oracle: 7.18
### labeler
- labels: 1034
- gold status: ok 985, empty 49
- accepted alternatives: 6467
- accepted per question: 6.25
- kind: other database 5442, other table 554, copy 352, same table 119
- rewritten by: llm 6423, code 44
- outcome: same rows 374, different rows 1525, not answerable 4019, empty 541, failed 8
- checks: decoys_accepted 0, decoys 2220, unsure 88, no_vote 206, revoted 13254, asked 64402, calls 17369, gold_items_found 2105, gold_items 2220
- distinct results in the gold database (2+): 18.86
- distinct results in the lake (2+): 51.06
- underspecified: items not asked: 1.16
- underspecified: note only: 0.00
- underspecified: value form: 3.97
- underspecified: computation: 35.40

## MMQA

- databases: 1
- tables: 710
- columns: 3652
- questions in labeler: 1105
### gold
- questions (retrieval): 1049
- questions (SQL): 965
- tables per query: mean 2.21, median 2, max 4, min 1
- share single-table: 0.38
- databases per query: mean 1, median 1, max 1, min 1
### multi
- questions (retrieval): 1049
- questions (SQL): 993
- valid queries per question: mean 3.79, median 3, max 29, min 1
- share with 2+ valid queries: 70.54
- table sets per question: mean 3.48, median 2, max 29, min 1
- share with 2+ table sets: 67.30
- tables per valid query: mean 2.50, median 2, max 4, min 1
- tables per table set: mean 2.49, median 2, max 4, min 1
- results per question (SQL questions): mean 2.52, median 2, max 17, min 1
- share with 2+ results (SQL questions): 59.62
- results, total (SQL questions): 2498
- share with a table set in another database: 0.00
- results out of reach of the oracle (one SQL per label table set): 91
- share of results out of reach of the oracle: 3.64
### labeler
- labels: 1105
- gold status: empty 79, ok 965, error 61
- accepted alternatives: 7316
- accepted per question: 6.62
- kind: other table 7181, same table 135
- rewritten by: llm 7275, code 41
- outcome: empty 2290, not answerable 1928, different rows 2181, same rows 911, failed 6
- checks: decoys_accepted 2, decoys 3161, unsure 136, no_vote 222, revoted 15002, asked 93648, calls 22525, gold_items_found 2797, gold_items 3161
- distinct results in the gold database (2+): 53.57
- distinct results in the lake (2+): 53.57
- underspecified: items not asked: 2.62
- underspecified: note only: 0.00
- underspecified: value form: 10.41
- underspecified: computation: 49.95

