# Spider 2.0-Lite multi-valid label (24 questions with a public gold SQL)

Made by score.py from runs/labeler/spider2_lite and the saved retrieval records. No LLM call.

## Label statistics

- databases: 30
- tables: 439
- columns: 3066
- questions in labeler: 135
### gold (all 135 questions)
- questions (retrieval): 135
- questions (SQL): 22
- tables per query: mean 2.82, median 2, max 8, min 1
- share single-table: 28.89
- databases per query: mean 1, median 1, max 1, min 1
### multi
- questions (retrieval): 24
- questions (SQL): 23
- valid queries per question: mean 6.38, median 5.50, max 16, min 1
- share with 2+ valid queries: 87.50
- table sets per question: mean 5.12, median 3.50, max 15, min 1
- share with 2+ table sets: 83.33
- tables per valid query: mean 3.26, median 3, max 9, min 1
- tables per table set: mean 3.17, median 3, max 9, min 1
- results per question (SQL questions): mean 3.57, median 2, max 13, min 1
- share with 2+ results (SQL questions): 73.91
- results, total (SQL questions): 82
- share with a table set in another database: 50.00
- results out of reach of the oracle (one SQL per label table set): 3
- share of results out of reach of the oracle: 3.66
### labeler
- labels: 24
- gold status: ok 22, slow 2
- accepted alternatives: 330
- accepted per question: 13.75
- kind: other database 205, copy 52, other table 63, same table 10
- rewritten by: llm 327, code 3
- outcome: not answerable 133, different rows 73, empty 17, same rows 99, failed 8
- checks: decoys_accepted 0, decoys 94, unsure 0, no_vote 0, revoted 432, asked 2490, calls 765, gold_items_found 69, gold_items 94
- distinct results in the gold database (2+): 45.83
- distinct results in the lake (2+): 70.83
- underspecified: items not asked: 16.67
- underspecified: note only: 0.00
- underspecified: value form: 8.33
- underspecified: computation: 100.00

### alternative queries of the final label by kind

- questions: 24
- alternative queries by kind: copy 18, new tables all share a name with an original table 8, other database 53, other table 50, same table 8
- share with 2+ valid queries: 87.50
- share with 2+ valid queries, both left out: 87.50

## Retrieval, single-valid label, all 135 questions

| method | R | CR | P | CR= | sets | n |
|---|---|---|---|---|---|---|
| Dense k3 | 45.3 | 31.5 | 31.1 | 2.2 | 1.00 | 135 |
| MURRE k3 | 47.8 | 31.5 | 36.0 | 4.4 | 1.00 | 135 |
| CORE-T | 68.7 | 48.1 | 49.9 | 15.6 | 1.00 | 135 |
| Route+SQL | 51.3 | 41.1 | 53.9 | 34.4 | 0.95 | 135 |
| AMIGO top-1 | 59.0 | 40.7 | 62.9 | 31.1 | 0.99 | 135 |
| AMIGO | 71.4 | 53.7 | 71.3 | 40.7 | 3.30 | 135 |

## Retrieval, single-valid label, the 24 questions of the multi-valid label

| method | R | CR | P | CR= | sets | n |
|---|---|---|---|---|---|---|
| Dense k3 | 51.7 | 31.2 | 38.9 | 4.2 | 1.00 | 24 |
| MURRE k3 | 47.5 | 27.1 | 38.9 | 0.0 | 1.00 | 24 |
| CORE-T | 71.4 | 50.0 | 51.3 | 16.7 | 1.00 | 24 |
| Route+SQL | 68.1 | 60.4 | 61.6 | 39.6 | 0.96 | 24 |
| AMIGO top-1 | 48.9 | 29.2 | 54.3 | 29.2 | 1.00 | 24 |
| AMIGO | 66.0 | 47.9 | 63.2 | 37.5 | 5.42 | 24 |

## Retrieval, multi-valid label, 24 questions

| method | IR | ICR | IP | IR= | ICR= | IP= | sets | n |
|---|---|---|---|---|---|---|---|---|
| Dense k3 | 18.1 | 8.3 | 37.5 | 4.2 | 4.2 | 4.2 | 1.00 | 24 |
| MURRE k3 | 15.6 | 4.2 | 45.8 | 1.6 | 0.0 | 8.3 | 1.00 | 24 |
| CORE-T | 22.0 | 8.3 | 54.2 | 12.5 | 8.3 | 16.7 | 1.00 | 24 |
| Route+SQL | 26.5 | 8.3 | 70.8 | 22.6 | 8.3 | 54.2 | 0.96 | 24 |
| AMIGO top-1 | 17.9 | 8.3 | 45.8 | 17.2 | 8.3 | 37.5 | 1.00 | 24 |
| AMIGO | 31.1 | 12.5 | 50.4 | 23.7 | 12.5 | 39.4 | 5.42 | 24 |

## AMIGO minus each method

Mean difference in points, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one label (every method and score); * when below 0.05.

### single-valid label, all 135 questions

| method | R | CR | P | CR= |
|---|---|---|---|---|
| Dense k3 | +26.1 [+18.2, +34.3]* | +22.2 [+13.3, +31.1]* | +40.2 [+33.4, +46.5]* | +38.5 [+30.4, +46.7]* |
| MURRE k3 | +23.6 [+15.8, +31.5]* | +22.2 [+13.3, +31.9]* | +35.2 [+27.9, +42.4]* | +36.3 [+27.4, +45.2]* |
| CORE-T | +2.7 [-4.8, +10.1] | +5.6 [-4.4, +15.6] | +21.4 [+14.8, +27.8]* | +25.2 [+17.0, +33.3]* |
| Route+SQL | +20.1 [+10.8, +29.6]* | +12.6 [+2.2, +23.0] | +17.4 [+8.3, +26.6]* | +6.3 [-4.1, +16.7] |
| AMIGO top-1 | +12.4 [+7.9, +17.2]* | +13.0 [+7.8, +18.5]* | +8.4 [+4.6, +12.7]* | +9.6 [+5.2, +14.8]* |

### single-valid label, the 24 questions of the multi-valid label

| method | R | CR | P | CR= |
|---|---|---|---|---|
| Dense k3 | +14.2 [-3.9, +31.9] | +16.7 [+0.0, +37.5] | +24.3 [+8.3, +38.9]* | +33.3 [+16.7, +54.2]* |
| MURRE k3 | +18.4 [+0.2, +35.5] | +20.8 [+0.0, +41.7] | +24.3 [+7.6, +41.0] | +37.5 [+20.8, +58.3]* |
| CORE-T | -5.4 [-23.8, +12.4] | -2.1 [-27.1, +22.9] | +11.9 [-1.1, +24.8] | +20.8 [+0.0, +41.7] |
| Route+SQL | -2.1 [-26.1, +21.6] | -12.5 [-37.5, +12.5] | +1.6 [-18.6, +21.9] | -2.1 [-22.9, +18.8] |
| AMIGO top-1 | +17.1 [+5.6, +30.8]* | +18.8 [+4.2, +35.4] | +8.9 [+0.7, +19.2] | +8.3 [+0.0, +20.8] |

### multi-valid label, 24 questions

| method | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|
| Dense k3 | +12.9 [+5.7, +22.9]* | +4.2 [+0.0, +12.5] | +12.9 [-4.8, +31.7] | +19.5 [+8.7, +32.4]* | +8.3 [+0.0, +20.8] | +35.2 [+18.8, +53.8]* |
| MURRE k3 | +15.4 [+5.2, +28.4]* | +8.3 [+0.0, +20.8] | +4.6 [-14.1, +23.5] | +22.2 [+9.6, +37.1]* | +12.5 [+0.0, +29.2] | +31.0 [+15.4, +48.8]* |
| CORE-T | +9.1 [-6.9, +25.0] | +4.2 [-8.3, +20.8] | -3.7 [-27.4, +19.6] | +11.2 [-3.4, +26.0] | +4.2 [-8.3, +16.7] | +22.7 [+2.7, +43.5] |
| Route+SQL | +4.6 [-5.7, +15.9] | +4.2 [+0.0, +12.5] | -20.4 [-43.9, +4.8] | +1.1 [-9.0, +13.1] | +4.2 [+0.0, +12.5] | -14.8 [-40.0, +11.2] |
| AMIGO top-1 | +13.1 [+4.9, +23.6]* | +4.2 [+0.0, +12.5] | +4.6 [-2.4, +11.2] | +6.5 [+0.0, +16.9] | +4.2 [+0.0, +12.5] | +1.9 [-7.3, +10.0] |
