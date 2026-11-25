# SQL (stage 2 of docs/eval_protocol.md), writer qwen

EX: a target (one distinct result of the label) counts when some SQL of the method returns its rows; mean over the question's targets, then over questions. Single / multi: targets whose smallest valid query reads one table / two or more. found / missed: targets whose tables some returned set holds / none does. result P (multi-valid label): distinct results that are a target, over distinct results (empty ones included, failed SQLs left out). SQLs: one per distinct returned set. failed: share of SQLs with no result (error, a table outside the set, too slow, no SQL). The oracle writes from the label's own table sets. AMIGO with hints writes AMIGO's plain prompt per table set, plus, when several interpretations share the set, one line per part whose place differs between them (one SQL per distinct prompt).

## gold label

| lake | method | EX | single EX | multi EX | EX found | EX missed | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 51.9 | 61.4 | 49.0 | 51.9 | nan | 1.00 | 1.2% | 1527 |
| BIRD | Dense k3 | 36.9 | 55.1 | 31.3 | 50.9 | 6.3 | 1.00 | 13.4% | 1527 |
| BIRD | MURRE k3 | 42.2 | 55.4 | 38.1 | 51.1 | 9.3 | 1.00 | 6.7% | 1527 |
| BIRD | CORE-T | 47.3 | 58.4 | 43.8 | 49.9 | 12.8 | 1.00 | 3.6% | 1527 |
| BIRD | Route+SQL | 46.9 | 55.1 | 44.3 | 54.6 | 12.8 | 0.99 | 1.5% | 1527 |
| BIRD | AMIGO top-1 | 47.1 | 59.2 | 43.3 | 53.2 | 11.6 | 1.00 | 1.5% | 1527 |
| BIRD | AMIGO | 49.2 | 60.1 | 45.8 | 52.9 | 10.4 | 1.50 | 2.2% | 1527 |
| BIRD | AMIGO with hints | 51.3 | 60.9 | 48.3 | 55.0 | 12.6 | 3.54 | 2.4% | 1527 |
| Spider | Gold-table oracle | 80.0 | 84.5 | 74.1 | 80.0 | nan | 1.00 | 0.7% | 985 |
| Spider | Dense k3 | 54.9 | 61.5 | 46.4 | 80.0 | 8.1 | 1.00 | 7.0% | 985 |
| Spider | MURRE k3 | 64.4 | 69.8 | 57.3 | 77.6 | 11.2 | 1.00 | 2.3% | 985 |
| Spider | CORE-T | 68.6 | 74.1 | 61.5 | 78.1 | 13.2 | 1.00 | 2.1% | 985 |
| Spider | Route+SQL | 58.0 | 52.9 | 64.6 | 81.8 | 4.6 | 1.00 | 4.6% | 985 |
| Spider | AMIGO top-1 | 70.5 | 73.4 | 66.7 | 80.4 | 8.8 | 1.00 | 1.3% | 985 |
| Spider | AMIGO | 76.1 | 81.3 | 69.5 | 80.1 | 3.9 | 1.66 | 2.0% | 985 |
| Spider | AMIGO with hints | 76.9 | 81.3 | 71.1 | 80.8 | 3.9 | 2.60 | 1.7% | 985 |
| MMQA | Gold-table oracle | 73.8 | 66.7 | 73.8 | 73.8 | nan | 1.00 | 0.4% | 965 |
| MMQA | Dense k3 | 25.1 | 33.3 | 25.1 | 68.9 | 5.1 | 1.00 | 12.4% | 965 |
| MMQA | MURRE k3 | 31.2 | 66.7 | 31.1 | 67.3 | 6.3 | 1.00 | 6.5% | 965 |
| MMQA | CORE-T | 50.2 | 33.3 | 50.2 | 67.1 | 8.3 | 1.00 | 3.9% | 965 |
| MMQA | AMIGO top-1 | 53.8 | 33.3 | 53.8 | 74.7 | 9.9 | 1.00 | 1.7% | 965 |
| MMQA | AMIGO | 66.1 | 66.7 | 66.1 | 76.0 | 13.7 | 8.79 | 2.3% | 965 |
| MMQA | AMIGO with hints | 66.0 | 66.7 | 66.0 | 75.5 | 15.7 | 15.95 | 2.5% | 965 |
| mean | Gold-table oracle | 68.6 | 70.9 | 65.6 | 68.6 | nan |
| mean | Dense k3 | 39.0 | 50.0 | 34.2 | 66.6 | 6.5 |
| mean | MURRE k3 | 45.9 | 63.9 | 42.2 | 65.3 | 8.9 |
| mean | CORE-T | 55.4 | 55.3 | 51.9 | 65.1 | 11.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 57.1 | 55.3 | 54.6 | 69.4 | 10.1 |
| mean | AMIGO | 63.8 | 69.3 | 60.5 | 69.7 | 9.3 |
| mean | AMIGO with hints | 64.7 | 69.6 | 61.8 | 70.5 | 10.7 |
| worst | Gold-table oracle | 51.9 | 61.4 | 49.0 | 51.9 | nan |
| worst | Dense k3 | 25.1 | 33.3 | 25.1 | 50.9 | 5.1 |
| worst | MURRE k3 | 31.2 | 55.4 | 31.1 | 51.1 | 6.3 |
| worst | CORE-T | 47.3 | 33.3 | 43.8 | 49.9 | 8.3 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 47.1 | 33.3 | 43.3 | 53.2 | 8.8 |
| worst | AMIGO | 49.2 | 60.1 | 45.8 | 52.9 | 3.9 |
| worst | AMIGO with hints | 51.3 | 60.9 | 48.3 | 55.0 | 3.9 |

## multi-valid label

| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 43.6 | 53.4 | 39.2 | 43.6 | nan | 55.8 | 1.88 | 2.1% | 1533 |
| BIRD | Dense k3 | 29.0 | 43.9 | 23.0 | 42.8 | 3.0 | 47.6 | 1.00 | 13.4% | 1533 |
| BIRD | MURRE k3 | 33.3 | 43.6 | 28.4 | 42.6 | 4.7 | 51.2 | 1.00 | 6.8% | 1533 |
| BIRD | CORE-T | 37.6 | 45.9 | 32.8 | 42.4 | 3.1 | 54.7 | 1.00 | 3.6% | 1533 |
| BIRD | Route+SQL | 36.7 | 42.9 | 33.1 | 48.8 | 3.5 | 53.2 | 0.99 | 1.6% | 1533 |
| BIRD | AMIGO top-1 | 37.4 | 46.3 | 32.7 | 47.6 | 2.9 | 53.5 | 1.00 | 1.6% | 1533 |
| BIRD | AMIGO | 39.1 | 47.5 | 34.6 | 46.0 | 2.1 | 53.0 | 1.50 | 2.6% | 1533 |
| BIRD | AMIGO with hints | 42.9 | 49.6 | 39.2 | 50.1 | 3.4 | 48.5 | 3.55 | 2.6% | 1533 |
| Spider | Gold-table oracle | 71.1 | 77.9 | 56.8 | 71.1 | nan | 77.5 | 2.39 | 1.4% | 1000 |
| Spider | Dense k3 | 40.6 | 45.6 | 26.8 | 68.6 | 3.2 | 64.0 | 1.00 | 7.1% | 1000 |
| Spider | MURRE k3 | 48.3 | 52.3 | 34.9 | 68.2 | 1.5 | 72.3 | 1.00 | 2.3% | 1000 |
| Spider | CORE-T | 50.0 | 53.2 | 36.9 | 68.7 | 3.9 | 75.4 | 1.00 | 2.1% | 1000 |
| Spider | Route+SQL | 44.0 | 40.8 | 40.2 | 76.7 | 0.9 | 68.1 | 1.00 | 4.5% | 1000 |
| Spider | AMIGO top-1 | 51.6 | 53.9 | 40.0 | 76.4 | 0.7 | 77.4 | 1.00 | 1.3% | 1000 |
| Spider | AMIGO | 56.5 | 60.1 | 42.9 | 74.2 | 0.9 | 76.3 | 1.66 | 1.9% | 1000 |
| Spider | AMIGO with hints | 57.8 | 60.6 | 45.1 | 75.9 | 0.9 | 74.2 | 2.62 | 1.6% | 1000 |
| MMQA | Gold-table oracle | 60.9 | 61.9 | 60.4 | 60.9 | nan | 73.3 | 3.59 | 0.7% | 993 |
| MMQA | Dense k3 | 21.1 | 22.4 | 20.4 | 59.0 | 6.1 | 39.4 | 1.00 | 12.5% | 993 |
| MMQA | MURRE k3 | 25.6 | 23.2 | 25.1 | 59.3 | 6.5 | 44.5 | 1.00 | 6.3% | 993 |
| MMQA | CORE-T | 36.7 | 19.8 | 37.3 | 58.7 | 4.1 | 61.5 | 1.00 | 4.0% | 993 |
| MMQA | AMIGO top-1 | 38.9 | 20.0 | 39.5 | 68.4 | 4.9 | 63.2 | 1.00 | 1.6% | 993 |
| MMQA | AMIGO | 48.4 | 31.0 | 48.7 | 66.3 | 6.7 | 60.9 | 8.82 | 2.2% | 993 |
| MMQA | AMIGO with hints | 51.0 | 43.6 | 50.9 | 69.2 | 8.2 | 50.9 | 16.10 | 2.4% | 993 |
| mean | Gold-table oracle | 58.5 | 64.4 | 52.1 | 58.5 | nan | 68.9 |
| mean | Dense k3 | 30.2 | 37.3 | 23.4 | 56.8 | 4.1 | 50.3 |
| mean | MURRE k3 | 35.7 | 39.7 | 29.5 | 56.7 | 4.2 | 56.0 |
| mean | CORE-T | 41.4 | 39.7 | 35.7 | 56.6 | 3.7 | 63.9 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 42.6 | 40.1 | 37.4 | 64.1 | 2.8 | 64.7 |
| mean | AMIGO | 48.0 | 46.2 | 42.1 | 62.2 | 3.2 | 63.4 |
| mean | AMIGO with hints | 50.6 | 51.3 | 45.1 | 65.1 | 4.1 | 57.8 |
| worst | Gold-table oracle | 43.6 | 53.4 | 39.2 | 43.6 | nan | 55.8 |
| worst | Dense k3 | 21.1 | 22.4 | 20.4 | 42.8 | 3.0 | 39.4 |
| worst | MURRE k3 | 25.6 | 23.2 | 25.1 | 42.6 | 1.5 | 44.5 |
| worst | CORE-T | 36.7 | 19.8 | 32.8 | 42.4 | 3.1 | 54.7 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 37.4 | 20.0 | 32.7 | 47.6 | 0.7 | 53.5 |
| worst | AMIGO | 39.1 | 31.0 | 34.6 | 46.0 | 0.9 | 53.0 |
| worst | AMIGO with hints | 42.9 | 43.6 | 39.2 | 50.1 | 0.9 | 48.5 |

## AMIGO minus each method, EX

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | Dense k3 | +12.2 [+10.2, +14.3]* |
| gold label | BIRD | MURRE k3 | +6.9 [+5.2, +8.7]* |
| gold label | BIRD | CORE-T | +1.9 [+0.5, +3.3]* |
| gold label | BIRD | Route+SQL | +2.3 [+1.0, +3.6]* |
| gold label | BIRD | AMIGO top-1 | +2.1 [+1.4, +2.8]* |
| gold label | BIRD | AMIGO with hints | -2.1 [-3.2, -1.0]* |
| gold label | Spider | Dense k3 | +21.2 [+18.5, +24.1]* |
| gold label | Spider | MURRE k3 | +11.8 [+9.3, +14.3]* |
| gold label | Spider | CORE-T | +7.5 [+5.3, +9.7]* |
| gold label | Spider | Route+SQL | +18.2 [+15.5, +20.9]* |
| gold label | Spider | AMIGO top-1 | +5.7 [+4.3, +7.2]* |
| gold label | Spider | AMIGO with hints | -0.7 [-1.6, +0.1] |
| gold label | MMQA | Dense k3 | +41.0 [+37.7, +44.4]* |
| gold label | MMQA | MURRE k3 | +34.9 [+31.8, +38.1]* |
| gold label | MMQA | CORE-T | +16.0 [+13.2, +18.9]* |
| gold label | MMQA | AMIGO top-1 | +12.3 [+10.4, +14.5]* |
| gold label | MMQA | AMIGO with hints | +0.1 [-1.1, +1.3] |
| multi-valid label | BIRD | Dense k3 | +10.1 [+8.4, +11.8]* |
| multi-valid label | BIRD | MURRE k3 | +5.8 [+4.4, +7.3]* |
| multi-valid label | BIRD | CORE-T | +1.5 [+0.4, +2.6]* |
| multi-valid label | BIRD | Route+SQL | +2.4 [+1.4, +3.5]* |
| multi-valid label | BIRD | AMIGO top-1 | +1.7 [+1.2, +2.3]* |
| multi-valid label | BIRD | AMIGO with hints | -3.8 [-4.7, -2.9]* |
| multi-valid label | Spider | Dense k3 | +15.9 [+13.8, +18.2]* |
| multi-valid label | Spider | MURRE k3 | +8.2 [+6.4, +10.0]* |
| multi-valid label | Spider | CORE-T | +6.5 [+4.9, +8.2]* |
| multi-valid label | Spider | Route+SQL | +12.5 [+10.6, +14.5]* |
| multi-valid label | Spider | AMIGO top-1 | +4.9 [+3.9, +6.0]* |
| multi-valid label | Spider | AMIGO with hints | -1.3 [-1.9, -0.7]* |
| multi-valid label | MMQA | Dense k3 | +27.3 [+24.8, +29.8]* |
| multi-valid label | MMQA | MURRE k3 | +22.8 [+20.5, +25.2]* |
| multi-valid label | MMQA | CORE-T | +11.7 [+9.7, +13.7]* |
| multi-valid label | MMQA | AMIGO top-1 | +9.5 [+8.1, +10.9]* |
| multi-valid label | MMQA | AMIGO with hints | -2.6 [-3.7, -1.6]* |
