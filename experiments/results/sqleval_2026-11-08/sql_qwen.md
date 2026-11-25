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
| BIRD | AMIGO top-1 | 42.6 | 59.5 | 37.3 | 51.8 | 10.6 | 1.00 | 4.8% | 1527 |
| BIRD | AMIGO | 49.2 | 59.8 | 46.0 | 53.4 | 9.6 | 1.44 | 6.6% | 1527 |
| BIRD | AMIGO with hints | 50.2 | 60.3 | 47.0 | 54.3 | 11.0 | 2.18 | 5.7% | 1527 |
| Spider | Gold-table oracle | 80.0 | 84.5 | 74.1 | 80.0 | nan | 1.00 | 0.7% | 985 |
| Spider | Dense k3 | 54.9 | 61.5 | 46.4 | 80.0 | 8.1 | 1.00 | 7.0% | 985 |
| Spider | MURRE k3 | 64.4 | 69.8 | 57.3 | 77.6 | 11.2 | 1.00 | 2.3% | 985 |
| Spider | CORE-T | 68.6 | 74.1 | 61.5 | 78.1 | 13.2 | 1.00 | 2.1% | 985 |
| Spider | Route+SQL | 58.0 | 52.9 | 64.6 | 81.8 | 4.6 | 1.00 | 4.6% | 985 |
| Spider | AMIGO top-1 | 69.6 | 73.9 | 64.1 | 79.7 | 11.1 | 1.00 | 1.4% | 985 |
| Spider | AMIGO | 76.5 | 81.8 | 69.7 | 79.9 | 4.5 | 1.66 | 2.1% | 985 |
| Spider | AMIGO with hints | 76.6 | 81.8 | 69.9 | 80.0 | 4.5 | 2.08 | 2.2% | 985 |
| MMQA | Gold-table oracle | 73.8 | 66.7 | 73.8 | 73.8 | nan | 1.00 | 0.4% | 965 |
| MMQA | Dense k3 | 25.1 | 33.3 | 25.1 | 68.9 | 5.1 | 1.00 | 12.4% | 965 |
| MMQA | MURRE k3 | 31.2 | 66.7 | 31.1 | 67.3 | 6.3 | 1.00 | 6.5% | 965 |
| MMQA | CORE-T | 50.2 | 33.3 | 50.2 | 67.1 | 8.3 | 1.00 | 3.9% | 965 |
| MMQA | AMIGO top-1 | 49.4 | 66.7 | 49.4 | 73.9 | 7.1 | 1.00 | 3.4% | 965 |
| MMQA | AMIGO | 59.4 | 66.7 | 59.4 | 73.8 | 8.9 | 4.18 | 3.2% | 965 |
| MMQA | AMIGO with hints | 59.6 | 66.7 | 59.6 | 73.9 | 9.3 | 7.02 | 3.1% | 965 |
| mean | Gold-table oracle | 68.6 | 70.9 | 65.6 | 68.6 | nan |
| mean | Dense k3 | 39.0 | 50.0 | 34.2 | 66.6 | 6.5 |
| mean | MURRE k3 | 45.9 | 63.9 | 42.2 | 65.3 | 8.9 |
| mean | CORE-T | 55.4 | 55.3 | 51.9 | 65.1 | 11.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 53.9 | 66.7 | 50.3 | 68.4 | 9.6 |
| mean | AMIGO | 61.7 | 69.4 | 58.3 | 69.0 | 7.7 |
| mean | AMIGO with hints | 62.1 | 69.6 | 58.8 | 69.4 | 8.3 |
| worst | Gold-table oracle | 51.9 | 61.4 | 49.0 | 51.9 | nan |
| worst | Dense k3 | 25.1 | 33.3 | 25.1 | 50.9 | 5.1 |
| worst | MURRE k3 | 31.2 | 55.4 | 31.1 | 51.1 | 6.3 |
| worst | CORE-T | 47.3 | 33.3 | 43.8 | 49.9 | 8.3 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 42.6 | 59.5 | 37.3 | 51.8 | 7.1 |
| worst | AMIGO | 49.2 | 59.8 | 46.0 | 53.4 | 4.5 |
| worst | AMIGO with hints | 50.2 | 60.3 | 47.0 | 54.3 | 4.5 |

## multi-valid label

| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Gold-table oracle | 43.6 | 53.4 | 39.2 | 43.6 | nan | 55.8 | 1.88 | 2.1% | 1533 |
| BIRD | Dense k3 | 29.0 | 43.9 | 23.0 | 42.8 | 3.0 | 47.6 | 1.00 | 13.4% | 1533 |
| BIRD | MURRE k3 | 33.3 | 43.6 | 28.4 | 42.6 | 4.7 | 51.2 | 1.00 | 6.8% | 1533 |
| BIRD | CORE-T | 37.6 | 45.9 | 32.8 | 42.4 | 3.1 | 54.7 | 1.00 | 3.6% | 1533 |
| BIRD | Route+SQL | 36.7 | 42.9 | 33.1 | 48.8 | 3.5 | 53.2 | 0.99 | 1.6% | 1533 |
| BIRD | AMIGO top-1 | 33.6 | 46.1 | 28.1 | 46.0 | 4.1 | 50.5 | 1.00 | 4.9% | 1533 |
| BIRD | AMIGO | 38.9 | 47.8 | 34.4 | 46.9 | 3.5 | 51.3 | 1.44 | 6.7% | 1533 |
| BIRD | AMIGO with hints | 40.3 | 48.5 | 36.1 | 48.3 | 4.7 | 49.9 | 2.19 | 5.7% | 1533 |
| Spider | Gold-table oracle | 71.1 | 77.9 | 56.8 | 71.1 | nan | 77.5 | 2.39 | 1.4% | 1000 |
| Spider | Dense k3 | 40.6 | 45.6 | 26.8 | 68.6 | 3.2 | 64.0 | 1.00 | 7.1% | 1000 |
| Spider | MURRE k3 | 48.3 | 52.3 | 34.9 | 68.2 | 1.5 | 72.3 | 1.00 | 2.3% | 1000 |
| Spider | CORE-T | 50.0 | 53.2 | 36.9 | 68.7 | 3.9 | 75.4 | 1.00 | 2.1% | 1000 |
| Spider | Route+SQL | 44.0 | 40.8 | 40.2 | 76.7 | 0.9 | 68.1 | 1.00 | 4.5% | 1000 |
| Spider | AMIGO top-1 | 51.5 | 55.1 | 38.1 | 76.1 | 0.9 | 77.3 | 1.00 | 1.4% | 1000 |
| Spider | AMIGO | 57.1 | 61.0 | 42.4 | 74.5 | 1.1 | 76.6 | 1.67 | 2.0% | 1000 |
| Spider | AMIGO with hints | 57.5 | 61.3 | 43.2 | 75.1 | 1.3 | 75.3 | 2.12 | 2.1% | 1000 |
| MMQA | Gold-table oracle | 60.9 | 61.9 | 60.4 | 60.9 | nan | 73.3 | 3.59 | 0.7% | 993 |
| MMQA | Dense k3 | 21.1 | 22.4 | 20.4 | 59.0 | 6.1 | 39.4 | 1.00 | 12.5% | 993 |
| MMQA | MURRE k3 | 25.6 | 23.2 | 25.1 | 59.3 | 6.5 | 44.5 | 1.00 | 6.3% | 993 |
| MMQA | CORE-T | 36.7 | 19.8 | 37.3 | 58.7 | 4.1 | 61.5 | 1.00 | 4.0% | 993 |
| MMQA | AMIGO top-1 | 36.5 | 23.6 | 36.5 | 67.6 | 5.0 | 59.6 | 1.00 | 3.5% | 993 |
| MMQA | AMIGO | 44.1 | 33.4 | 44.2 | 66.4 | 5.7 | 58.5 | 4.16 | 3.3% | 993 |
| MMQA | AMIGO with hints | 44.9 | 37.1 | 45.0 | 67.4 | 6.5 | 55.0 | 6.97 | 3.1% | 993 |
| mean | Gold-table oracle | 58.5 | 64.4 | 52.1 | 58.5 | nan | 68.9 |
| mean | Dense k3 | 30.2 | 37.3 | 23.4 | 56.8 | 4.1 | 50.3 |
| mean | MURRE k3 | 35.7 | 39.7 | 29.5 | 56.7 | 4.2 | 56.0 |
| mean | CORE-T | 41.4 | 39.7 | 35.7 | 56.6 | 3.7 | 63.9 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 40.5 | 41.6 | 34.3 | 63.2 | 3.3 | 62.5 |
| mean | AMIGO | 46.7 | 47.4 | 40.4 | 62.6 | 3.4 | 62.1 |
| mean | AMIGO with hints | 47.6 | 48.9 | 41.4 | 63.6 | 4.1 | 60.1 |
| worst | Gold-table oracle | 43.6 | 53.4 | 39.2 | 43.6 | nan | 55.8 |
| worst | Dense k3 | 21.1 | 22.4 | 20.4 | 42.8 | 3.0 | 39.4 |
| worst | MURRE k3 | 25.6 | 23.2 | 25.1 | 42.6 | 1.5 | 44.5 |
| worst | CORE-T | 36.7 | 19.8 | 32.8 | 42.4 | 3.1 | 54.7 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 33.6 | 23.6 | 28.1 | 46.0 | 0.9 | 50.5 |
| worst | AMIGO | 38.9 | 33.4 | 34.4 | 46.9 | 1.1 | 51.3 |
| worst | AMIGO with hints | 40.3 | 37.1 | 36.1 | 48.3 | 1.3 | 49.9 |

## AMIGO with hints minus each method, EX

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | Dense k3 | +13.2 [+11.2, +15.3]* |
| gold label | BIRD | MURRE k3 | +7.9 [+6.2, +9.8]* |
| gold label | BIRD | CORE-T | +2.9 [+1.4, +4.4]* |
| gold label | BIRD | Route+SQL | +3.3 [+2.0, +4.6]* |
| gold label | BIRD | AMIGO top-1 | +7.6 [+6.2, +9.0]* |
| gold label | BIRD | AMIGO | +0.9 [+0.3, +1.6]* |
| gold label | Spider | Dense k3 | +21.7 [+18.9, +24.6]* |
| gold label | Spider | MURRE k3 | +12.3 [+9.8, +14.7]* |
| gold label | Spider | CORE-T | +8.0 [+5.7, +10.3]* |
| gold label | Spider | Route+SQL | +18.7 [+15.9, +21.4]* |
| gold label | Spider | AMIGO top-1 | +7.0 [+5.4, +8.7]* |
| gold label | Spider | AMIGO | +0.1 [-0.4, +0.6] |
| gold label | MMQA | Dense k3 | +34.5 [+31.2, +37.8]* |
| gold label | MMQA | MURRE k3 | +28.4 [+25.2, +31.6]* |
| gold label | MMQA | CORE-T | +9.4 [+6.6, +12.3]* |
| gold label | MMQA | AMIGO top-1 | +10.2 [+8.2, +12.2]* |
| gold label | MMQA | AMIGO | +0.2 [-0.7, +1.1] |
| multi-valid label | BIRD | Dense k3 | +11.3 [+9.6, +13.0]* |
| multi-valid label | BIRD | MURRE k3 | +7.0 [+5.5, +8.5]* |
| multi-valid label | BIRD | CORE-T | +2.7 [+1.5, +3.8]* |
| multi-valid label | BIRD | Route+SQL | +3.7 [+2.6, +4.8]* |
| multi-valid label | BIRD | AMIGO top-1 | +6.7 [+5.6, +7.9]* |
| multi-valid label | BIRD | AMIGO | +1.4 [+0.8, +2.0]* |
| multi-valid label | Spider | Dense k3 | +16.9 [+14.8, +19.2]* |
| multi-valid label | Spider | MURRE k3 | +9.2 [+7.5, +11.0]* |
| multi-valid label | Spider | CORE-T | +7.5 [+5.8, +9.2]* |
| multi-valid label | Spider | Route+SQL | +13.5 [+11.5, +15.5]* |
| multi-valid label | Spider | AMIGO top-1 | +6.0 [+5.0, +7.2]* |
| multi-valid label | Spider | AMIGO | +0.4 [+0.0, +0.8]* |
| multi-valid label | MMQA | Dense k3 | +23.8 [+21.4, +26.3]* |
| multi-valid label | MMQA | MURRE k3 | +19.3 [+16.9, +21.7]* |
| multi-valid label | MMQA | CORE-T | +8.2 [+6.2, +10.2]* |
| multi-valid label | MMQA | AMIGO top-1 | +8.4 [+6.9, +9.9]* |
| multi-valid label | MMQA | AMIGO | +0.8 [+0.1, +1.5]* |
