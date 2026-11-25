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
| BIRD | AMIGO top-1 | 25.1 | 42.4 | 19.8 | 30.9 | 5.3 | 1.00 | 18.5% | 1527 |
| BIRD | AMIGO | 31.6 | 44.6 | 27.5 | 33.9 | 9.6 | 1.44 | 19.8% | 1527 |
| BIRD | AMIGO with hints | 33.2 | 45.5 | 29.4 | 35.6 | 10.3 | 2.18 | 21.8% | 1527 |
| Spider | Gold-table oracle | 71.6 | 79.1 | 61.8 | 71.6 | nan | 1.00 | 3.8% | 985 |
| Spider | Dense k3 | 42.3 | 47.7 | 35.4 | 61.8 | 6.1 | 1.00 | 16.6% | 985 |
| Spider | MURRE k3 | 50.1 | 53.2 | 45.9 | 60.7 | 7.1 | 1.00 | 10.4% | 985 |
| Spider | CORE-T | 55.0 | 61.9 | 46.2 | 62.5 | 11.1 | 1.00 | 8.9% | 985 |
| Spider | Route+SQL | 50.9 | 49.3 | 52.9 | 72.0 | 3.6 | 1.00 | 9.1% | 985 |
| Spider | AMIGO top-1 | 61.5 | 68.2 | 52.9 | 70.2 | 11.1 | 1.00 | 5.0% | 985 |
| Spider | AMIGO | 68.4 | 75.5 | 59.2 | 71.5 | 2.3 | 1.66 | 6.8% | 985 |
| Spider | AMIGO with hints | 69.1 | 75.9 | 60.4 | 72.3 | 2.3 | 2.08 | 6.8% | 985 |
| MMQA | Gold-table oracle | 59.4 | 33.3 | 59.5 | 59.4 | nan | 1.00 | 6.6% | 965 |
| MMQA | Dense k3 | 18.3 | 0.0 | 18.4 | 50.0 | 3.9 | 1.00 | 17.2% | 965 |
| MMQA | MURRE k3 | 24.2 | 33.3 | 24.2 | 51.3 | 5.6 | 1.00 | 15.5% | 965 |
| MMQA | CORE-T | 37.3 | 33.3 | 37.3 | 50.2 | 5.4 | 1.00 | 12.8% | 965 |
| MMQA | AMIGO top-1 | 39.6 | 33.3 | 39.6 | 58.8 | 6.2 | 1.00 | 11.6% | 965 |
| MMQA | AMIGO | 48.5 | 33.3 | 48.5 | 60.3 | 7.0 | 4.18 | 15.0% | 965 |
| MMQA | AMIGO with hints | 49.7 | 33.3 | 49.8 | 61.9 | 7.0 | 7.02 | 14.1% | 965 |
| mean | Gold-table oracle | 54.5 | 52.4 | 50.0 | 54.5 | nan |
| mean | Dense k3 | 27.6 | 28.5 | 23.8 | 47.4 | 4.8 |
| mean | MURRE k3 | 33.0 | 41.6 | 30.2 | 47.3 | 6.1 |
| mean | CORE-T | 39.8 | 45.0 | 35.6 | 47.2 | 7.9 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 42.1 | 48.0 | 37.4 | 53.3 | 7.5 |
| mean | AMIGO | 49.5 | 51.2 | 45.1 | 55.2 | 6.3 |
| mean | AMIGO with hints | 50.7 | 51.6 | 46.5 | 56.6 | 6.5 |
| worst | Gold-table oracle | 32.6 | 33.3 | 28.9 | 32.6 | nan |
| worst | Dense k3 | 18.3 | 0.0 | 17.4 | 30.4 | 3.9 |
| worst | MURRE k3 | 24.2 | 33.3 | 20.5 | 29.9 | 5.6 |
| worst | CORE-T | 27.2 | 33.3 | 23.3 | 28.7 | 5.4 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 25.1 | 33.3 | 19.8 | 30.9 | 5.3 |
| worst | AMIGO | 31.6 | 33.3 | 27.5 | 33.9 | 2.3 |
| worst | AMIGO with hints | 33.2 | 33.3 | 29.4 | 35.6 | 2.3 |

## multi-valid label

| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 29.6 | 44.1 | 24.9 | 29.6 | nan | 41.6 | 1.88 | 15.7% | 1533 |
| BIRD | Dense k3 | 18.6 | 31.5 | 13.9 | 27.6 | 2.4 | 33.5 | 1.00 | 22.5% | 1533 |
| BIRD | MURRE k3 | 19.9 | 31.6 | 15.5 | 25.5 | 2.8 | 36.4 | 1.00 | 21.3% | 1533 |
| BIRD | CORE-T | 21.5 | 30.9 | 17.7 | 24.6 | 2.2 | 38.1 | 1.00 | 20.5% | 1533 |
| BIRD | Route+SQL | 23.7 | 34.1 | 19.8 | 31.5 | 3.4 | 41.1 | 0.99 | 17.1% | 1533 |
| BIRD | AMIGO top-1 | 20.3 | 35.1 | 14.9 | 28.6 | 2.3 | 35.8 | 1.00 | 18.5% | 1533 |
| BIRD | AMIGO | 25.7 | 38.0 | 21.1 | 31.1 | 3.0 | 37.5 | 1.44 | 19.7% | 1533 |
| BIRD | AMIGO with hints | 27.2 | 38.9 | 22.9 | 32.8 | 3.6 | 37.3 | 2.19 | 21.6% | 1533 |
| Spider | Gold-table oracle | 63.7 | 72.3 | 47.4 | 63.7 | nan | 69.9 | 2.39 | 7.0% | 1000 |
| Spider | Dense k3 | 31.3 | 36.0 | 20.2 | 53.7 | 2.6 | 54.7 | 1.00 | 16.8% | 1000 |
| Spider | MURRE k3 | 37.6 | 41.0 | 26.7 | 53.1 | 1.5 | 60.4 | 1.00 | 10.4% | 1000 |
| Spider | CORE-T | 40.9 | 45.5 | 27.9 | 56.8 | 2.7 | 65.0 | 1.00 | 9.1% | 1000 |
| Spider | Route+SQL | 39.3 | 38.1 | 33.4 | 68.4 | 0.8 | 62.1 | 1.00 | 8.9% | 1000 |
| Spider | AMIGO top-1 | 46.1 | 50.9 | 32.1 | 67.7 | 1.2 | 70.5 | 1.00 | 5.2% | 1000 |
| Spider | AMIGO | 51.8 | 57.2 | 36.2 | 67.4 | 1.2 | 69.9 | 1.67 | 6.9% | 1000 |
| Spider | AMIGO with hints | 52.3 | 57.5 | 36.9 | 68.1 | 1.2 | 69.4 | 2.12 | 7.3% | 1000 |
| MMQA | Gold-table oracle | 53.6 | 59.0 | 52.9 | 53.6 | nan | 63.4 | 3.59 | 8.9% | 993 |
| MMQA | Dense k3 | 16.4 | 20.0 | 15.9 | 45.0 | 5.1 | 33.4 | 1.00 | 17.3% | 993 |
| MMQA | MURRE k3 | 20.9 | 23.8 | 20.2 | 46.8 | 6.1 | 40.2 | 1.00 | 15.5% | 993 |
| MMQA | CORE-T | 28.3 | 15.1 | 28.5 | 44.3 | 4.1 | 50.4 | 1.00 | 12.9% | 993 |
| MMQA | AMIGO top-1 | 30.0 | 23.3 | 29.9 | 55.6 | 4.5 | 53.2 | 1.00 | 11.3% | 993 |
| MMQA | AMIGO | 37.6 | 32.9 | 37.5 | 56.1 | 5.3 | 51.0 | 4.16 | 15.1% | 993 |
| MMQA | AMIGO with hints | 38.9 | 34.1 | 38.8 | 57.7 | 5.8 | 49.5 | 6.97 | 14.1% | 993 |
| mean | Gold-table oracle | 49.0 | 58.5 | 41.7 | 49.0 | nan | 58.3 |
| mean | Dense k3 | 22.1 | 29.1 | 16.7 | 42.1 | 3.4 | 40.5 |
| mean | MURRE k3 | 26.1 | 32.1 | 20.8 | 41.8 | 3.5 | 45.6 |
| mean | CORE-T | 30.3 | 30.5 | 24.7 | 41.9 | 3.0 | 51.2 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 32.1 | 36.4 | 25.6 | 50.6 | 2.7 | 53.2 |
| mean | AMIGO | 38.4 | 42.7 | 31.6 | 51.5 | 3.2 | 52.8 |
| mean | AMIGO with hints | 39.5 | 43.5 | 32.9 | 52.8 | 3.5 | 52.1 |
| worst | Gold-table oracle | 29.6 | 44.1 | 24.9 | 29.6 | nan | 41.6 |
| worst | Dense k3 | 16.4 | 20.0 | 13.9 | 27.6 | 2.4 | 33.4 |
| worst | MURRE k3 | 19.9 | 23.8 | 15.5 | 25.5 | 1.5 | 36.4 |
| worst | CORE-T | 21.5 | 15.1 | 17.7 | 24.6 | 2.2 | 38.1 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 20.3 | 23.3 | 14.9 | 28.6 | 1.2 | 35.8 |
| worst | AMIGO | 25.7 | 32.9 | 21.1 | 31.1 | 1.2 | 37.5 |
| worst | AMIGO with hints | 27.2 | 34.1 | 22.9 | 32.8 | 1.2 | 37.3 |

## AMIGO with hints minus each method, EX

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | Dense k3 | +10.9 [+9.0, +12.9]* |
| gold label | BIRD | MURRE k3 | +8.4 [+6.6, +10.3]* |
| gold label | BIRD | CORE-T | +6.0 [+4.4, +7.7]* |
| gold label | BIRD | Route+SQL | +3.4 [+2.1, +4.7]* |
| gold label | BIRD | AMIGO top-1 | +8.1 [+6.7, +9.4]* |
| gold label | BIRD | AMIGO | +1.6 [+0.9, +2.4]* |
| gold label | Spider | Dense k3 | +26.8 [+23.6, +30.1]* |
| gold label | Spider | MURRE k3 | +19.1 [+16.2, +22.0]* |
| gold label | Spider | CORE-T | +14.1 [+11.5, +16.8]* |
| gold label | Spider | Route+SQL | +18.3 [+15.6, +21.0]* |
| gold label | Spider | AMIGO top-1 | +7.6 [+6.0, +9.3]* |
| gold label | Spider | AMIGO | +0.7 [+0.0, +1.4] |
| gold label | MMQA | Dense k3 | +31.4 [+28.1, +34.7]* |
| gold label | MMQA | MURRE k3 | +25.5 [+22.3, +28.7]* |
| gold label | MMQA | CORE-T | +12.4 [+9.4, +15.3]* |
| gold label | MMQA | AMIGO top-1 | +10.2 [+8.2, +12.1]* |
| gold label | MMQA | AMIGO | +1.2 [+0.2, +2.3]* |
| multi-valid label | BIRD | Dense k3 | +8.6 [+6.9, +10.2]* |
| multi-valid label | BIRD | MURRE k3 | +7.3 [+5.7, +8.9]* |
| multi-valid label | BIRD | CORE-T | +5.7 [+4.3, +7.1]* |
| multi-valid label | BIRD | Route+SQL | +3.5 [+2.4, +4.6]* |
| multi-valid label | BIRD | AMIGO top-1 | +6.9 [+5.7, +8.1]* |
| multi-valid label | BIRD | AMIGO | +1.5 [+0.9, +2.1]* |
| multi-valid label | Spider | Dense k3 | +21.0 [+18.7, +23.6]* |
| multi-valid label | Spider | MURRE k3 | +14.7 [+12.6, +16.9]* |
| multi-valid label | Spider | CORE-T | +11.4 [+9.5, +13.3]* |
| multi-valid label | Spider | Route+SQL | +13.0 [+11.1, +15.0]* |
| multi-valid label | Spider | AMIGO top-1 | +6.2 [+5.1, +7.4]* |
| multi-valid label | Spider | AMIGO | +0.5 [-0.0, +1.0] |
| multi-valid label | MMQA | Dense k3 | +22.4 [+19.8, +25.1]* |
| multi-valid label | MMQA | MURRE k3 | +18.0 [+15.5, +20.5]* |
| multi-valid label | MMQA | CORE-T | +10.6 [+8.5, +12.7]* |
| multi-valid label | MMQA | AMIGO top-1 | +8.9 [+7.3, +10.5]* |
| multi-valid label | MMQA | AMIGO | +1.2 [+0.4, +2.2]* |
