# SQL (stage 2 of docs/eval_protocol.md), writer gemma

EX: a target (one distinct result of the label) counts when some SQL of the method returns its rows; mean over the question's targets, then over questions. Single / multi: targets whose smallest valid query reads one table / two or more. found / missed: targets whose tables some returned set holds / none does. result P (multi-valid label): distinct results that are a target, over distinct results (empty ones included, failed SQLs left out). SQLs: one per distinct returned set. failed: share of SQLs with no result (error, a table outside the set, too slow, no SQL). The oracle writes from the label's own table sets. AMIGO with hints writes AMIGO's plain prompt per table set, plus, when several interpretations share the set, one line per part whose place differs between them (one SQL per distinct prompt).

## gold label

| lake | method | EX | single EX | multi EX | EX found | EX missed | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 45.6 | 56.7 | 42.2 | 45.6 | nan | 1.00 | 8.6% | 1527 |
| BIRD | Dense k3 | 28.6 | 47.4 | 22.7 | 39.9 | 3.6 | 1.00 | 17.0% | 1527 |
| BIRD | MURRE k3 | 34.3 | 47.1 | 30.3 | 41.8 | 6.5 | 1.00 | 13.9% | 1527 |
| BIRD | CORE-T | 39.0 | 51.5 | 35.1 | 41.6 | 5.5 | 1.00 | 11.1% | 1527 |
| BIRD | Route+SQL | 41.3 | 51.0 | 38.2 | 48.2 | 10.6 | 0.99 | 9.5% | 1527 |
| BIRD | AMIGO top-1 | 37.0 | 52.6 | 32.1 | 45.4 | 7.6 | 1.00 | 10.9% | 1527 |
| BIRD | AMIGO | 43.6 | 53.2 | 40.6 | 47.2 | 9.6 | 1.44 | 13.9% | 1527 |
| BIRD | AMIGO with hints | 44.7 | 53.7 | 41.9 | 48.4 | 10.3 | 2.18 | 15.7% | 1527 |
| Spider | Gold-table oracle | 75.0 | 83.5 | 64.1 | 75.0 | nan | 1.00 | 2.0% | 985 |
| Spider | Dense k3 | 48.7 | 57.2 | 37.8 | 71.5 | 6.4 | 1.00 | 9.8% | 985 |
| Spider | MURRE k3 | 56.1 | 62.8 | 47.6 | 67.9 | 8.7 | 1.00 | 5.0% | 985 |
| Spider | CORE-T | 61.6 | 70.7 | 49.9 | 69.7 | 14.6 | 1.00 | 3.6% | 985 |
| Spider | Route+SQL | 53.6 | 51.4 | 56.4 | 75.5 | 4.6 | 1.00 | 6.5% | 985 |
| Spider | AMIGO top-1 | 65.1 | 71.8 | 56.4 | 74.6 | 9.7 | 1.00 | 3.0% | 985 |
| Spider | AMIGO | 72.2 | 79.9 | 62.2 | 75.2 | 6.8 | 1.66 | 3.4% | 985 |
| Spider | AMIGO with hints | 72.5 | 80.0 | 62.7 | 75.6 | 6.8 | 2.08 | 3.7% | 985 |
| MMQA | Gold-table oracle | 70.9 | 33.3 | 71.0 | 70.9 | nan | 1.00 | 2.4% | 965 |
| MMQA | Dense k3 | 22.9 | 0.0 | 23.0 | 65.6 | 3.5 | 1.00 | 13.4% | 965 |
| MMQA | MURRE k3 | 30.5 | 66.7 | 30.4 | 66.8 | 5.4 | 1.00 | 8.7% | 965 |
| MMQA | CORE-T | 46.5 | 33.3 | 46.6 | 63.3 | 5.0 | 1.00 | 7.0% | 965 |
| MMQA | AMIGO top-1 | 48.1 | 33.3 | 48.1 | 71.6 | 7.4 | 1.00 | 7.3% | 965 |
| MMQA | AMIGO | 57.3 | 33.3 | 57.4 | 71.4 | 7.9 | 4.18 | 8.9% | 965 |
| MMQA | AMIGO with hints | 58.0 | 33.3 | 58.1 | 72.2 | 8.4 | 7.02 | 8.0% | 965 |
| mean | Gold-table oracle | 63.9 | 57.8 | 59.1 | 63.9 | nan |
| mean | Dense k3 | 33.4 | 34.9 | 27.8 | 59.0 | 4.5 |
| mean | MURRE k3 | 40.3 | 58.8 | 36.1 | 58.8 | 6.9 |
| mean | CORE-T | 49.1 | 51.8 | 43.9 | 58.2 | 8.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 50.1 | 52.6 | 45.6 | 63.9 | 8.2 |
| mean | AMIGO | 57.7 | 55.5 | 53.4 | 64.6 | 8.1 |
| mean | AMIGO with hints | 58.4 | 55.7 | 54.2 | 65.4 | 8.5 |
| worst | Gold-table oracle | 45.6 | 33.3 | 42.2 | 45.6 | nan |
| worst | Dense k3 | 22.9 | 0.0 | 22.7 | 39.9 | 3.5 |
| worst | MURRE k3 | 30.5 | 47.1 | 30.3 | 41.8 | 5.4 |
| worst | CORE-T | 39.0 | 33.3 | 35.1 | 41.6 | 5.0 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 37.0 | 33.3 | 32.1 | 45.4 | 7.4 |
| worst | AMIGO | 43.6 | 33.3 | 40.6 | 47.2 | 6.8 |
| worst | AMIGO with hints | 44.7 | 33.3 | 41.9 | 48.4 | 6.8 |

## multi-valid label

| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 38.3 | 50.4 | 33.4 | 38.3 | nan | 52.0 | 1.88 | 9.0% | 1533 |
| BIRD | Dense k3 | 22.6 | 37.8 | 16.9 | 34.6 | 1.5 | 39.3 | 1.00 | 17.0% | 1533 |
| BIRD | MURRE k3 | 27.1 | 38.4 | 22.5 | 35.3 | 3.3 | 45.3 | 1.00 | 13.9% | 1533 |
| BIRD | CORE-T | 30.9 | 40.5 | 26.4 | 35.5 | 2.0 | 49.0 | 1.00 | 11.2% | 1533 |
| BIRD | Route+SQL | 32.4 | 40.2 | 28.6 | 43.2 | 3.2 | 51.0 | 0.99 | 9.5% | 1533 |
| BIRD | AMIGO top-1 | 29.4 | 41.9 | 24.2 | 40.9 | 3.2 | 47.2 | 1.00 | 11.0% | 1533 |
| BIRD | AMIGO | 34.8 | 43.5 | 30.8 | 42.1 | 4.1 | 48.1 | 1.44 | 13.9% | 1533 |
| BIRD | AMIGO with hints | 35.9 | 44.3 | 32.0 | 43.5 | 4.0 | 48.2 | 2.19 | 15.6% | 1533 |
| Spider | Gold-table oracle | 67.1 | 75.2 | 50.9 | 67.1 | nan | 73.1 | 2.39 | 2.9% | 1000 |
| Spider | Dense k3 | 37.3 | 43.2 | 22.8 | 62.6 | 2.7 | 58.9 | 1.00 | 9.9% | 1000 |
| Spider | MURRE k3 | 43.0 | 48.4 | 28.1 | 60.1 | 1.6 | 64.6 | 1.00 | 5.2% | 1000 |
| Spider | CORE-T | 45.8 | 51.6 | 30.3 | 63.0 | 3.1 | 68.2 | 1.00 | 3.7% | 1000 |
| Spider | Route+SQL | 41.2 | 39.8 | 35.3 | 71.1 | 0.8 | 63.9 | 1.00 | 6.4% | 1000 |
| Spider | AMIGO top-1 | 48.5 | 53.5 | 33.8 | 71.4 | 0.8 | 73.5 | 1.00 | 3.3% | 1000 |
| Spider | AMIGO | 54.2 | 59.6 | 37.9 | 70.8 | 0.6 | 73.0 | 1.67 | 3.5% | 1000 |
| Spider | AMIGO with hints | 54.4 | 59.7 | 38.3 | 71.1 | 0.6 | 72.7 | 2.12 | 3.8% | 1000 |
| MMQA | Gold-table oracle | 59.3 | 60.9 | 58.9 | 59.3 | nan | 71.2 | 3.59 | 2.9% | 993 |
| MMQA | Dense k3 | 19.5 | 15.7 | 19.3 | 55.6 | 5.1 | 37.5 | 1.00 | 13.3% | 993 |
| MMQA | MURRE k3 | 25.3 | 22.4 | 25.0 | 57.8 | 6.0 | 44.3 | 1.00 | 8.6% | 993 |
| MMQA | CORE-T | 34.6 | 17.1 | 35.2 | 55.3 | 3.1 | 58.2 | 1.00 | 7.3% | 993 |
| MMQA | AMIGO top-1 | 35.3 | 22.9 | 35.7 | 65.7 | 4.2 | 59.9 | 1.00 | 7.2% | 993 |
| MMQA | AMIGO | 42.8 | 32.5 | 43.3 | 64.6 | 4.7 | 57.1 | 4.16 | 8.9% | 993 |
| MMQA | AMIGO with hints | 43.6 | 32.5 | 44.1 | 65.6 | 5.4 | 56.7 | 6.97 | 8.0% | 993 |
| mean | Gold-table oracle | 54.9 | 62.2 | 47.7 | 54.9 | nan | 65.5 |
| mean | Dense k3 | 26.5 | 32.3 | 19.7 | 50.9 | 3.1 | 45.3 |
| mean | MURRE k3 | 31.8 | 36.4 | 25.2 | 51.1 | 3.6 | 51.4 |
| mean | CORE-T | 37.1 | 36.4 | 30.6 | 51.3 | 2.7 | 58.5 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 37.7 | 39.4 | 31.2 | 59.3 | 2.7 | 60.2 |
| mean | AMIGO | 44.0 | 45.2 | 37.3 | 59.2 | 3.2 | 59.4 |
| mean | AMIGO with hints | 44.7 | 45.5 | 38.1 | 60.0 | 3.4 | 59.2 |
| worst | Gold-table oracle | 38.3 | 50.4 | 33.4 | 38.3 | nan | 52.0 |
| worst | Dense k3 | 19.5 | 15.7 | 16.9 | 34.6 | 1.5 | 37.5 |
| worst | MURRE k3 | 25.3 | 22.4 | 22.5 | 35.3 | 1.6 | 44.3 |
| worst | CORE-T | 30.9 | 17.1 | 26.4 | 35.5 | 2.0 | 49.0 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 29.4 | 22.9 | 24.2 | 40.9 | 0.8 | 47.2 |
| worst | AMIGO | 34.8 | 32.5 | 30.8 | 42.1 | 0.6 | 48.1 |
| worst | AMIGO with hints | 35.9 | 32.5 | 32.0 | 43.5 | 0.6 | 48.2 |

## AMIGO with hints minus each method, EX

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | Dense k3 | +16.2 [+14.1, +18.3]* |
| gold label | BIRD | MURRE k3 | +10.4 [+8.6, +12.3]* |
| gold label | BIRD | CORE-T | +5.7 [+4.1, +7.3]* |
| gold label | BIRD | Route+SQL | +3.5 [+2.2, +4.8]* |
| gold label | BIRD | AMIGO top-1 | +7.7 [+6.4, +9.1]* |
| gold label | BIRD | AMIGO | +1.1 [+0.5, +1.8]* |
| gold label | Spider | Dense k3 | +23.8 [+20.9, +26.7]* |
| gold label | Spider | MURRE k3 | +16.3 [+13.8, +19.1]* |
| gold label | Spider | CORE-T | +10.9 [+8.4, +13.2]* |
| gold label | Spider | Route+SQL | +18.9 [+16.2, +21.5]* |
| gold label | Spider | AMIGO top-1 | +7.4 [+5.8, +9.1]* |
| gold label | Spider | AMIGO | +0.3 [-0.2, +0.8] |
| gold label | MMQA | Dense k3 | +35.1 [+31.8, +38.4]* |
| gold label | MMQA | MURRE k3 | +27.6 [+24.2, +30.7]* |
| gold label | MMQA | CORE-T | +11.5 [+8.6, +14.5]* |
| gold label | MMQA | AMIGO top-1 | +9.9 [+8.0, +12.0]* |
| gold label | MMQA | AMIGO | +0.7 [-0.1, +1.7] |
| multi-valid label | BIRD | Dense k3 | +13.4 [+11.7, +15.1]* |
| multi-valid label | BIRD | MURRE k3 | +8.9 [+7.3, +10.4]* |
| multi-valid label | BIRD | CORE-T | +5.0 [+3.7, +6.4]* |
| multi-valid label | BIRD | Route+SQL | +3.5 [+2.5, +4.6]* |
| multi-valid label | BIRD | AMIGO top-1 | +6.5 [+5.4, +7.7]* |
| multi-valid label | BIRD | AMIGO | +1.1 [+0.6, +1.6]* |
| multi-valid label | Spider | Dense k3 | +17.1 [+14.9, +19.3]* |
| multi-valid label | Spider | MURRE k3 | +11.5 [+9.6, +13.4]* |
| multi-valid label | Spider | CORE-T | +8.6 [+7.0, +10.4]* |
| multi-valid label | Spider | Route+SQL | +13.3 [+11.3, +15.3]* |
| multi-valid label | Spider | AMIGO top-1 | +5.9 [+4.8, +7.1]* |
| multi-valid label | Spider | AMIGO | +0.2 [-0.1, +0.5] |
| multi-valid label | MMQA | Dense k3 | +24.1 [+21.6, +26.6]* |
| multi-valid label | MMQA | MURRE k3 | +18.3 [+15.9, +20.7]* |
| multi-valid label | MMQA | CORE-T | +9.0 [+7.0, +11.0]* |
| multi-valid label | MMQA | AMIGO top-1 | +8.3 [+6.9, +9.8]* |
| multi-valid label | MMQA | AMIGO | +0.8 [+0.3, +1.3]* |
