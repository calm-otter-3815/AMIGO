# SQL (stage 2 of docs/eval_protocol.md), writer gemma

EX: a target (one distinct result of the label) counts when some SQL of the method returns its rows; mean over the question's targets, then over questions. Single / multi: targets whose smallest valid query reads one table / two or more. found / missed: targets whose tables some returned set holds / none does. result P (multi-valid label): distinct results that are a target, over distinct results (empty ones included, failed SQLs left out). SQLs: one per distinct returned set. failed: share of SQLs with no result (error, a table outside the set, too slow, no SQL). The oracle writes from the label's own table sets. AMIGO with hints writes AMIGO's plain prompt per table set, plus, when several interpretations share the set, one line per part whose place differs between them (one SQL per distinct prompt).

## gold label

| lake | method | EX | single EX | multi EX | EX found | EX missed | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 45.6 | 56.7 | 42.2 | 45.6 | nan | 1.00 | 8.6% | 1527 |
| BIRD | Dense k3 | 28.5 | 47.4 | 22.6 | 39.8 | 3.6 | 1.00 | 17.0% | 1527 |
| BIRD | MURRE k3 | 34.3 | 47.1 | 30.2 | 41.7 | 6.5 | 1.00 | 13.9% | 1527 |
| BIRD | CORE-T | 39.0 | 51.5 | 35.1 | 41.5 | 5.5 | 1.00 | 11.1% | 1527 |
| BIRD | Route+SQL | 41.3 | 51.0 | 38.2 | 48.2 | 10.6 | 0.99 | 9.5% | 1527 |
| BIRD | AMIGO top-1 | 41.2 | 52.3 | 37.7 | 46.4 | 11.2 | 1.00 | 9.2% | 1527 |
| BIRD | AMIGO | 43.4 | 54.3 | 39.9 | 46.5 | 11.1 | 1.50 | 10.9% | 1527 |
| BIRD | AMIGO with hints | 45.5 | 55.4 | 42.4 | 48.9 | 10.4 | 3.54 | 13.9% | 1527 |
| Spider | Gold-table oracle | 75.0 | 83.5 | 64.1 | 75.0 | nan | 1.00 | 2.0% | 985 |
| Spider | Dense k3 | 48.7 | 57.2 | 37.8 | 71.5 | 6.4 | 1.00 | 9.8% | 985 |
| Spider | MURRE k3 | 56.1 | 62.8 | 47.6 | 67.9 | 8.7 | 1.00 | 5.0% | 985 |
| Spider | CORE-T | 61.6 | 70.7 | 49.9 | 69.7 | 14.6 | 1.00 | 3.6% | 985 |
| Spider | Route+SQL | 53.6 | 51.4 | 56.4 | 75.5 | 4.6 | 1.00 | 6.5% | 985 |
| Spider | AMIGO top-1 | 65.3 | 70.3 | 58.7 | 74.8 | 6.6 | 1.00 | 2.3% | 985 |
| Spider | AMIGO | 70.7 | 78.4 | 60.6 | 74.4 | 2.0 | 1.66 | 2.9% | 985 |
| Spider | AMIGO with hints | 71.1 | 78.2 | 61.8 | 74.8 | 2.0 | 2.60 | 3.1% | 985 |
| MMQA | Gold-table oracle | 70.9 | 33.3 | 71.0 | 70.9 | nan | 1.00 | 2.4% | 965 |
| MMQA | Dense k3 | 22.9 | 0.0 | 23.0 | 65.6 | 3.5 | 1.00 | 13.4% | 965 |
| MMQA | MURRE k3 | 30.5 | 66.7 | 30.4 | 66.8 | 5.4 | 1.00 | 8.7% | 965 |
| MMQA | CORE-T | 46.5 | 33.3 | 46.6 | 63.3 | 5.0 | 1.00 | 7.0% | 965 |
| MMQA | AMIGO top-1 | 51.4 | 33.3 | 51.5 | 72.0 | 8.3 | 1.00 | 4.3% | 965 |
| MMQA | AMIGO | 63.2 | 33.3 | 63.3 | 72.7 | 13.1 | 8.79 | 6.1% | 965 |
| MMQA | AMIGO with hints | 63.8 | 33.3 | 63.9 | 73.6 | 11.8 | 15.95 | 6.4% | 965 |
| mean | Gold-table oracle | 63.9 | 57.8 | 59.1 | 63.9 | nan |
| mean | Dense k3 | 33.4 | 34.9 | 27.8 | 58.9 | 4.5 |
| mean | MURRE k3 | 40.3 | 58.8 | 36.0 | 58.8 | 6.9 |
| mean | CORE-T | 49.0 | 51.8 | 43.8 | 58.2 | 8.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 52.6 | 52.0 | 49.3 | 64.4 | 8.7 |
| mean | AMIGO | 59.1 | 55.3 | 54.6 | 64.5 | 8.7 |
| mean | AMIGO with hints | 60.1 | 55.6 | 56.0 | 65.8 | 8.0 |
| worst | Gold-table oracle | 45.6 | 33.3 | 42.2 | 45.6 | nan |
| worst | Dense k3 | 22.9 | 0.0 | 22.6 | 39.8 | 3.5 |
| worst | MURRE k3 | 30.5 | 47.1 | 30.2 | 41.7 | 5.4 |
| worst | CORE-T | 39.0 | 33.3 | 35.1 | 41.5 | 5.0 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 41.2 | 33.3 | 37.7 | 46.4 | 6.6 |
| worst | AMIGO | 43.4 | 33.3 | 39.9 | 46.5 | 2.0 |
| worst | AMIGO with hints | 45.5 | 33.3 | 42.4 | 48.9 | 2.0 |

## multi-valid label

| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 38.3 | 50.4 | 33.4 | 38.3 | nan | 52.0 | 1.88 | 9.0% | 1533 |
| BIRD | Dense k3 | 22.5 | 37.8 | 16.8 | 34.5 | 1.5 | 39.2 | 1.00 | 17.0% | 1533 |
| BIRD | MURRE k3 | 27.1 | 38.4 | 22.5 | 35.3 | 3.3 | 45.2 | 1.00 | 13.9% | 1533 |
| BIRD | CORE-T | 30.9 | 40.5 | 26.4 | 35.4 | 2.0 | 49.0 | 1.00 | 11.2% | 1533 |
| BIRD | Route+SQL | 32.4 | 40.2 | 28.6 | 43.2 | 3.2 | 51.0 | 0.99 | 9.5% | 1533 |
| BIRD | AMIGO top-1 | 32.8 | 42.0 | 28.5 | 42.0 | 3.0 | 51.0 | 1.00 | 9.3% | 1533 |
| BIRD | AMIGO | 34.7 | 43.6 | 30.5 | 40.9 | 3.5 | 50.6 | 1.50 | 10.9% | 1533 |
| BIRD | AMIGO with hints | 36.4 | 44.6 | 32.5 | 43.2 | 3.0 | 50.0 | 3.55 | 14.0% | 1533 |
| Spider | Gold-table oracle | 67.1 | 75.2 | 50.9 | 67.1 | nan | 73.1 | 2.39 | 2.9% | 1000 |
| Spider | Dense k3 | 37.3 | 43.2 | 22.8 | 62.6 | 2.7 | 58.9 | 1.00 | 9.9% | 1000 |
| Spider | MURRE k3 | 43.0 | 48.4 | 28.1 | 60.1 | 1.6 | 64.6 | 1.00 | 5.2% | 1000 |
| Spider | CORE-T | 45.8 | 51.6 | 30.3 | 63.0 | 3.1 | 68.2 | 1.00 | 3.7% | 1000 |
| Spider | Route+SQL | 41.2 | 39.8 | 35.3 | 71.1 | 0.8 | 63.9 | 1.00 | 6.4% | 1000 |
| Spider | AMIGO top-1 | 48.4 | 52.0 | 35.3 | 71.3 | 0.5 | 72.6 | 1.00 | 2.5% | 1000 |
| Spider | AMIGO | 53.3 | 58.4 | 37.6 | 69.9 | 0.8 | 72.1 | 1.66 | 3.1% | 1000 |
| Spider | AMIGO with hints | 53.4 | 58.2 | 37.8 | 70.1 | 0.8 | 71.4 | 2.62 | 3.2% | 1000 |
| MMQA | Gold-table oracle | 59.3 | 60.9 | 58.9 | 59.3 | nan | 71.2 | 3.59 | 2.9% | 993 |
| MMQA | Dense k3 | 19.5 | 15.7 | 19.3 | 55.6 | 5.1 | 37.5 | 1.00 | 13.3% | 993 |
| MMQA | MURRE k3 | 25.3 | 22.4 | 25.0 | 57.8 | 6.0 | 44.3 | 1.00 | 8.6% | 993 |
| MMQA | CORE-T | 34.6 | 17.1 | 35.2 | 55.3 | 3.1 | 58.2 | 1.00 | 7.3% | 993 |
| MMQA | AMIGO top-1 | 37.7 | 22.4 | 38.1 | 66.0 | 4.2 | 62.0 | 1.00 | 4.3% | 993 |
| MMQA | AMIGO | 46.8 | 31.8 | 47.1 | 63.5 | 6.6 | 57.8 | 8.82 | 6.0% | 993 |
| MMQA | AMIGO with hints | 48.0 | 33.1 | 48.4 | 65.2 | 7.2 | 56.0 | 16.10 | 6.2% | 993 |
| mean | Gold-table oracle | 54.9 | 62.2 | 47.7 | 54.9 | nan | 65.5 |
| mean | Dense k3 | 26.5 | 32.3 | 19.7 | 50.9 | 3.1 | 45.2 |
| mean | MURRE k3 | 31.8 | 36.4 | 25.2 | 51.1 | 3.6 | 51.4 |
| mean | CORE-T | 37.1 | 36.4 | 30.6 | 51.3 | 2.7 | 58.5 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 39.6 | 38.8 | 33.9 | 59.8 | 2.6 | 61.9 |
| mean | AMIGO | 44.9 | 44.6 | 38.4 | 58.1 | 3.6 | 60.1 |
| mean | AMIGO with hints | 45.9 | 45.3 | 39.6 | 59.5 | 3.7 | 59.1 |
| worst | Gold-table oracle | 38.3 | 50.4 | 33.4 | 38.3 | nan | 52.0 |
| worst | Dense k3 | 19.5 | 15.7 | 16.8 | 34.5 | 1.5 | 37.5 |
| worst | MURRE k3 | 25.3 | 22.4 | 22.5 | 35.3 | 1.6 | 44.3 |
| worst | CORE-T | 30.9 | 17.1 | 26.4 | 35.4 | 2.0 | 49.0 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 32.8 | 22.4 | 28.5 | 42.0 | 0.5 | 51.0 |
| worst | AMIGO | 34.7 | 31.8 | 30.5 | 40.9 | 0.8 | 50.6 |
| worst | AMIGO with hints | 36.4 | 33.1 | 32.5 | 43.2 | 0.8 | 50.0 |

## AMIGO minus each method, EX

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | Dense k3 | +14.9 [+12.9, +16.9]* |
| gold label | BIRD | MURRE k3 | +9.1 [+7.3, +10.9]* |
| gold label | BIRD | CORE-T | +4.4 [+2.8, +6.0]* |
| gold label | BIRD | Route+SQL | +2.1 [+0.8, +3.5]* |
| gold label | BIRD | AMIGO top-1 | +2.2 [+1.4, +2.9]* |
| gold label | BIRD | AMIGO with hints | -2.2 [-3.1, -1.3]* |
| gold label | Spider | Dense k3 | +21.9 [+19.1, +24.9]* |
| gold label | Spider | MURRE k3 | +14.5 [+11.9, +17.2]* |
| gold label | Spider | CORE-T | +9.0 [+6.7, +11.4]* |
| gold label | Spider | Route+SQL | +17.1 [+14.3, +19.8]* |
| gold label | Spider | AMIGO top-1 | +5.4 [+4.1, +6.8]* |
| gold label | Spider | AMIGO with hints | -0.4 [-1.3, +0.5] |
| gold label | MMQA | Dense k3 | +40.3 [+36.9, +43.7]* |
| gold label | MMQA | MURRE k3 | +32.7 [+29.4, +36.0]* |
| gold label | MMQA | CORE-T | +16.7 [+13.7, +19.8]* |
| gold label | MMQA | AMIGO top-1 | +11.8 [+9.8, +13.9]* |
| gold label | MMQA | AMIGO with hints | -0.6 [-1.7, +0.3] |
| multi-valid label | BIRD | Dense k3 | +12.2 [+10.5, +13.9]* |
| multi-valid label | BIRD | MURRE k3 | +7.6 [+6.2, +9.2]* |
| multi-valid label | BIRD | CORE-T | +3.8 [+2.5, +5.1]* |
| multi-valid label | BIRD | Route+SQL | +2.3 [+1.3, +3.4]* |
| multi-valid label | BIRD | AMIGO top-1 | +1.9 [+1.3, +2.5]* |
| multi-valid label | BIRD | AMIGO with hints | -1.7 [-2.4, -1.0]* |
| multi-valid label | Spider | Dense k3 | +15.9 [+13.8, +18.2]* |
| multi-valid label | Spider | MURRE k3 | +10.3 [+8.4, +12.3]* |
| multi-valid label | Spider | CORE-T | +7.5 [+5.9, +9.2]* |
| multi-valid label | Spider | Route+SQL | +12.1 [+10.1, +14.2]* |
| multi-valid label | Spider | AMIGO top-1 | +4.9 [+3.9, +6.0]* |
| multi-valid label | Spider | AMIGO with hints | -0.1 [-0.8, +0.6] |
| multi-valid label | MMQA | Dense k3 | +27.3 [+24.7, +29.8]* |
| multi-valid label | MMQA | MURRE k3 | +21.5 [+19.0, +23.9]* |
| multi-valid label | MMQA | CORE-T | +12.2 [+10.0, +14.3]* |
| multi-valid label | MMQA | AMIGO top-1 | +9.1 [+7.8, +10.6]* |
| multi-valid label | MMQA | AMIGO with hints | -1.2 [-1.9, -0.5]* |
