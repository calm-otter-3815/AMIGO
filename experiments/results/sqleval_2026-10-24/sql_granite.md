# SQL (stage 2 of docs/eval_protocol.md), writer granite

EX: a target (one distinct result of the label) counts when some SQL of the method returns its rows; mean over the question's targets, then over questions. Single / multi: targets whose smallest valid query reads one table / two or more. found / missed: targets whose tables some returned set holds / none does. result P (multi-valid label): distinct results that are a target, over distinct results (empty ones included, failed SQLs left out). SQLs: one per distinct returned set. failed: share of SQLs with no result (error, a table outside the set, too slow, no SQL). The oracle writes from the label's own table sets. AMIGO with hints writes AMIGO's plain prompt per table set, plus, when several interpretations share the set, one line per part whose place differs between them (one SQL per distinct prompt).

## gold label

| lake | method | EX | single EX | multi EX | EX found | EX missed | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 32.6 | 44.6 | 28.9 | 32.6 | nan | 1.00 | 16.8% | 1527 |
| BIRD | Dense k3 | 22.3 | 37.7 | 17.4 | 30.4 | 4.4 | 1.00 | 22.5% | 1527 |
| BIRD | MURRE k3 | 24.8 | 38.3 | 20.5 | 29.9 | 5.6 | 1.00 | 21.3% | 1527 |
| BIRD | CORE-T | 27.2 | 39.7 | 23.3 | 28.7 | 7.3 | 1.00 | 20.5% | 1527 |
| BIRD | Route+SQL | 29.8 | 40.2 | 26.5 | 34.6 | 8.5 | 0.99 | 17.1% | 1527 |
| BIRD | AMIGO top-1 | 29.5 | 42.7 | 25.4 | 33.0 | 9.4 | 1.00 | 17.3% | 1527 |
| BIRD | AMIGO | 31.8 | 44.1 | 27.9 | 33.9 | 9.6 | 1.50 | 18.2% | 1527 |
| BIRD | AMIGO with hints | 34.8 | 45.5 | 31.5 | 37.3 | 9.6 | 3.54 | 21.5% | 1527 |
| Spider | Gold-table oracle | 71.6 | 79.1 | 61.8 | 71.6 | nan | 1.00 | 3.8% | 985 |
| Spider | Dense k3 | 42.3 | 47.7 | 35.4 | 61.8 | 6.1 | 1.00 | 16.6% | 985 |
| Spider | MURRE k3 | 50.1 | 53.2 | 45.9 | 60.7 | 7.1 | 1.00 | 10.4% | 985 |
| Spider | CORE-T | 55.0 | 61.9 | 46.2 | 62.5 | 11.1 | 1.00 | 8.9% | 985 |
| Spider | Route+SQL | 50.9 | 49.3 | 52.9 | 72.0 | 3.6 | 1.00 | 9.1% | 985 |
| Spider | AMIGO top-1 | 62.5 | 67.4 | 56.2 | 71.2 | 8.8 | 1.00 | 4.7% | 985 |
| Spider | AMIGO | 67.9 | 75.0 | 58.7 | 71.4 | 3.9 | 1.66 | 6.1% | 985 |
| Spider | AMIGO with hints | 69.0 | 75.7 | 60.4 | 72.7 | 2.0 | 2.60 | 6.6% | 985 |
| MMQA | Gold-table oracle | 59.4 | 33.3 | 59.5 | 59.4 | nan | 1.00 | 6.6% | 965 |
| MMQA | Dense k3 | 18.3 | 0.0 | 18.4 | 50.0 | 3.9 | 1.00 | 17.2% | 965 |
| MMQA | MURRE k3 | 24.2 | 33.3 | 24.2 | 51.3 | 5.6 | 1.00 | 15.5% | 965 |
| MMQA | CORE-T | 37.3 | 33.3 | 37.3 | 50.2 | 5.4 | 1.00 | 12.8% | 965 |
| MMQA | AMIGO top-1 | 42.5 | 33.3 | 42.5 | 59.1 | 7.7 | 1.00 | 8.9% | 965 |
| MMQA | AMIGO | 54.1 | 33.3 | 54.2 | 62.2 | 11.1 | 8.79 | 13.0% | 965 |
| MMQA | AMIGO with hints | 57.0 | 33.3 | 57.1 | 65.3 | 13.1 | 15.95 | 12.9% | 965 |
| mean | Gold-table oracle | 54.5 | 52.4 | 50.0 | 54.5 | nan |
| mean | Dense k3 | 27.6 | 28.5 | 23.8 | 47.4 | 4.8 |
| mean | MURRE k3 | 33.0 | 41.6 | 30.2 | 47.3 | 6.1 |
| mean | CORE-T | 39.8 | 45.0 | 35.6 | 47.2 | 7.9 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 44.9 | 47.8 | 41.4 | 54.4 | 8.6 |
| mean | AMIGO | 51.3 | 50.8 | 46.9 | 55.8 | 8.2 |
| mean | AMIGO with hints | 53.6 | 51.5 | 49.7 | 58.4 | 8.2 |
| worst | Gold-table oracle | 32.6 | 33.3 | 28.9 | 32.6 | nan |
| worst | Dense k3 | 18.3 | 0.0 | 17.4 | 30.4 | 3.9 |
| worst | MURRE k3 | 24.2 | 33.3 | 20.5 | 29.9 | 5.6 |
| worst | CORE-T | 27.2 | 33.3 | 23.3 | 28.7 | 5.4 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 29.5 | 33.3 | 25.4 | 33.0 | 7.7 |
| worst | AMIGO | 31.8 | 33.3 | 27.9 | 33.9 | 3.9 |
| worst | AMIGO with hints | 34.8 | 33.3 | 31.5 | 37.3 | 2.0 |

## multi-valid label

| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 29.6 | 44.1 | 24.9 | 29.6 | nan | 41.6 | 1.88 | 15.7% | 1533 |
| BIRD | Dense k3 | 18.6 | 31.5 | 13.9 | 27.6 | 2.4 | 33.5 | 1.00 | 22.5% | 1533 |
| BIRD | MURRE k3 | 19.9 | 31.6 | 15.5 | 25.5 | 2.8 | 36.4 | 1.00 | 21.3% | 1533 |
| BIRD | CORE-T | 21.5 | 30.9 | 17.7 | 24.6 | 2.2 | 38.1 | 1.00 | 20.5% | 1533 |
| BIRD | Route+SQL | 23.7 | 34.1 | 19.8 | 31.5 | 3.4 | 41.1 | 0.99 | 17.1% | 1533 |
| BIRD | AMIGO top-1 | 23.7 | 35.0 | 19.1 | 30.2 | 3.2 | 40.9 | 1.00 | 17.2% | 1533 |
| BIRD | AMIGO | 25.7 | 37.4 | 21.2 | 30.1 | 3.1 | 40.3 | 1.50 | 18.2% | 1533 |
| BIRD | AMIGO with hints | 28.7 | 38.8 | 24.5 | 33.6 | 3.8 | 38.7 | 3.55 | 21.4% | 1533 |
| Spider | Gold-table oracle | 63.7 | 72.3 | 47.4 | 63.7 | nan | 69.9 | 2.39 | 7.0% | 1000 |
| Spider | Dense k3 | 31.3 | 36.0 | 20.2 | 53.7 | 2.6 | 54.7 | 1.00 | 16.8% | 1000 |
| Spider | MURRE k3 | 37.6 | 41.0 | 26.7 | 53.1 | 1.5 | 60.4 | 1.00 | 10.4% | 1000 |
| Spider | CORE-T | 40.9 | 45.5 | 27.9 | 56.8 | 2.7 | 65.0 | 1.00 | 9.1% | 1000 |
| Spider | Route+SQL | 39.3 | 38.1 | 33.4 | 68.4 | 0.8 | 62.1 | 1.00 | 8.9% | 1000 |
| Spider | AMIGO top-1 | 46.2 | 49.6 | 34.3 | 68.5 | 0.8 | 70.6 | 1.00 | 4.6% | 1000 |
| Spider | AMIGO | 50.9 | 55.8 | 36.3 | 66.6 | 1.2 | 69.9 | 1.66 | 6.1% | 1000 |
| Spider | AMIGO with hints | 51.7 | 56.5 | 37.5 | 67.9 | 1.0 | 68.9 | 2.62 | 6.7% | 1000 |
| MMQA | Gold-table oracle | 53.6 | 59.0 | 52.9 | 53.6 | nan | 63.4 | 3.59 | 8.9% | 993 |
| MMQA | Dense k3 | 16.4 | 20.0 | 15.9 | 45.0 | 5.1 | 33.4 | 1.00 | 17.3% | 993 |
| MMQA | MURRE k3 | 20.9 | 23.8 | 20.2 | 46.8 | 6.1 | 40.2 | 1.00 | 15.5% | 993 |
| MMQA | CORE-T | 28.3 | 15.1 | 28.5 | 44.3 | 4.1 | 50.4 | 1.00 | 12.9% | 993 |
| MMQA | AMIGO top-1 | 31.8 | 18.1 | 32.1 | 55.0 | 4.3 | 54.4 | 1.00 | 8.9% | 993 |
| MMQA | AMIGO | 42.0 | 29.8 | 42.1 | 56.8 | 6.8 | 49.7 | 8.82 | 12.9% | 993 |
| MMQA | AMIGO with hints | 44.6 | 35.0 | 44.8 | 60.3 | 7.8 | 46.4 | 16.10 | 12.8% | 993 |
| mean | Gold-table oracle | 49.0 | 58.5 | 41.7 | 49.0 | nan | 58.3 |
| mean | Dense k3 | 22.1 | 29.1 | 16.7 | 42.1 | 3.4 | 40.5 |
| mean | MURRE k3 | 26.1 | 32.1 | 20.8 | 41.8 | 3.5 | 45.6 |
| mean | CORE-T | 30.3 | 30.5 | 24.7 | 41.9 | 3.0 | 51.2 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 33.9 | 34.2 | 28.5 | 51.2 | 2.8 | 55.3 |
| mean | AMIGO | 39.5 | 41.0 | 33.2 | 51.1 | 3.7 | 53.3 |
| mean | AMIGO with hints | 41.7 | 43.4 | 35.6 | 53.9 | 4.2 | 51.3 |
| worst | Gold-table oracle | 29.6 | 44.1 | 24.9 | 29.6 | nan | 41.6 |
| worst | Dense k3 | 16.4 | 20.0 | 13.9 | 27.6 | 2.4 | 33.4 |
| worst | MURRE k3 | 19.9 | 23.8 | 15.5 | 25.5 | 1.5 | 36.4 |
| worst | CORE-T | 21.5 | 15.1 | 17.7 | 24.6 | 2.2 | 38.1 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 23.7 | 18.1 | 19.1 | 30.2 | 0.8 | 40.9 |
| worst | AMIGO | 25.7 | 29.8 | 21.2 | 30.1 | 1.2 | 40.3 |
| worst | AMIGO with hints | 28.7 | 35.0 | 24.5 | 33.6 | 1.0 | 38.7 |

## AMIGO minus each method, EX

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | Dense k3 | +9.5 [+7.6, +11.4]* |
| gold label | BIRD | MURRE k3 | +7.0 [+5.3, +8.8]* |
| gold label | BIRD | CORE-T | +4.6 [+3.0, +6.2]* |
| gold label | BIRD | Route+SQL | +2.0 [+0.7, +3.2]* |
| gold label | BIRD | AMIGO top-1 | +2.2 [+1.5, +3.0]* |
| gold label | BIRD | AMIGO with hints | -3.1 [-4.4, -1.8]* |
| gold label | Spider | Dense k3 | +25.6 [+22.3, +28.7]* |
| gold label | Spider | MURRE k3 | +17.9 [+15.0, +20.7]* |
| gold label | Spider | CORE-T | +12.9 [+10.4, +15.4]* |
| gold label | Spider | Route+SQL | +17.1 [+14.4, +19.7]* |
| gold label | Spider | AMIGO top-1 | +5.4 [+4.0, +6.8]* |
| gold label | Spider | AMIGO with hints | -1.1 [-2.1, -0.1]* |
| gold label | MMQA | Dense k3 | +35.8 [+32.4, +39.2]* |
| gold label | MMQA | MURRE k3 | +29.8 [+26.5, +33.2]* |
| gold label | MMQA | CORE-T | +16.8 [+13.8, +19.7]* |
| gold label | MMQA | AMIGO top-1 | +11.6 [+9.6, +13.7]* |
| gold label | MMQA | AMIGO with hints | -2.9 [-4.6, -1.3]* |
| multi-valid label | BIRD | Dense k3 | +7.0 [+5.5, +8.6]* |
| multi-valid label | BIRD | MURRE k3 | +5.8 [+4.3, +7.3]* |
| multi-valid label | BIRD | CORE-T | +4.1 [+2.9, +5.4]* |
| multi-valid label | BIRD | Route+SQL | +2.0 [+1.0, +2.9]* |
| multi-valid label | BIRD | AMIGO top-1 | +2.0 [+1.4, +2.5]* |
| multi-valid label | BIRD | AMIGO with hints | -3.0 [-4.0, -2.0]* |
| multi-valid label | Spider | Dense k3 | +19.7 [+17.3, +22.1]* |
| multi-valid label | Spider | MURRE k3 | +13.3 [+11.3, +15.4]* |
| multi-valid label | Spider | CORE-T | +10.0 [+8.2, +11.9]* |
| multi-valid label | Spider | Route+SQL | +11.6 [+9.8, +13.7]* |
| multi-valid label | Spider | AMIGO top-1 | +4.7 [+3.8, +5.8]* |
| multi-valid label | Spider | AMIGO with hints | -0.7 [-1.5, -0.0]* |
| multi-valid label | MMQA | Dense k3 | +25.5 [+22.9, +28.2]* |
| multi-valid label | MMQA | MURRE k3 | +21.1 [+18.6, +23.6]* |
| multi-valid label | MMQA | CORE-T | +13.7 [+11.5, +15.9]* |
| multi-valid label | MMQA | AMIGO top-1 | +10.2 [+8.7, +11.7]* |
| multi-valid label | MMQA | AMIGO with hints | -2.7 [-3.9, -1.5]* |
