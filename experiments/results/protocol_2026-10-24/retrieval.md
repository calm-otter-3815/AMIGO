# Retrieval (stage 1 of docs/eval_protocol.md)

Per target R, CR, P from the returned set with the highest recall (then precision); mean over the question's targets, then over questions. Pooled P: every returned table against every table of a valid query (multi-valid label only). sets: distinct table sets returned per question; tables: distinct tables returned per question. empty: questions with no table returned (a failed run counts here, scored as returning nothing). AMIGO is the join-choice version; AMIGO top-1 keeps its first interpretation.

## gold label, every target

| lake | method | R | CR | P | sets | tables | empty | n |
|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 83.1 | 68.6 | 51.8 | 1.00 | 3.00 | 0 | 1534 |
| BIRD | MURRE k3 | 89.0 | 78.7 | 56.1 | 1.00 | 3.00 | 0 | 1534 |
| BIRD | CORE-T | 96.5 | 92.9 | 62.8 | 1.00 | 3.19 | 0 | 1534 |
| BIRD | Route+SQL | 88.7 | 81.5 | 90.7 | 0.99 | 1.87 | 9 | 1534 |
| BIRD | AMIGO top-1 | 92.7 | 85.2 | 91.3 | 1.00 | 1.99 | 0 | 1534 |
| BIRD | AMIGO | 95.7 | 91.1 | 92.5 | 1.50 | 2.38 | 0 | 1534 |
| Spider | Dense k3 | 73.5 | 63.9 | 37.1 | 1.00 | 3.00 | 0 | 1034 |
| Spider | MURRE k3 | 85.1 | 79.3 | 42.3 | 1.00 | 3.00 | 0 | 1034 |
| Spider | CORE-T | 89.3 | 84.9 | 57.4 | 1.00 | 2.68 | 0 | 1034 |
| Spider | Route+SQL | 68.1 | 67.4 | 68.0 | 1.00 | 1.60 | 4 | 1034 |
| Spider | AMIGO top-1 | 86.9 | 85.4 | 85.0 | 1.00 | 1.56 | 1 | 1034 |
| Spider | AMIGO | 95.3 | 94.3 | 93.3 | 1.67 | 2.29 | 1 | 1034 |
| MMQA | Dense k3 | 59.0 | 31.4 | 42.8 | 1.00 | 3.00 | 0 | 1049 |
| MMQA | MURRE k3 | 62.6 | 41.3 | 45.2 | 1.00 | 3.00 | 0 | 1049 |
| MMQA | CORE-T | 84.1 | 70.6 | 58.1 | 1.00 | 3.78 | 0 | 1049 |
| MMQA | AMIGO top-1 | 80.1 | 66.7 | 75.8 | 1.00 | 2.63 | 1 | 1049 |
| MMQA | AMIGO | 90.9 | 83.0 | 84.8 | 8.91 | 8.36 | 1 | 1049 |
| mean | Dense k3 | 71.9 | 54.6 | 43.9 |
| mean | MURRE k3 | 78.9 | 66.4 | 47.9 |
| mean | CORE-T | 89.9 | 82.8 | 59.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 86.6 | 79.1 | 84.0 |
| mean | AMIGO | 94.0 | 89.5 | 90.2 |
| worst | Dense k3 | 59.0 | 31.4 | 37.1 |
| worst | MURRE k3 | 62.6 | 41.3 | 42.3 |
| worst | CORE-T | 84.1 | 70.6 | 57.4 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 80.1 | 66.7 | 75.8 |
| worst | AMIGO | 90.9 | 83.0 | 84.8 |

## gold label, single-table targets

| lake | method | R | CR | P | n |
|---|---|---|---|---|---|
| BIRD | Dense k3 | 93.7 | 93.7 | 31.2 | 363 |
| BIRD | MURRE k3 | 96.7 | 96.7 | 32.2 | 363 |
| BIRD | CORE-T | 99.7 | 99.7 | 44.1 | 363 |
| BIRD | Route+SQL | 91.7 | 91.7 | 88.9 | 363 |
| BIRD | AMIGO top-1 | 97.5 | 97.5 | 86.2 | 363 |
| BIRD | AMIGO | 98.6 | 98.6 | 87.7 | 363 |
| Spider | Dense k3 | 72.7 | 72.7 | 24.2 | 575 |
| Spider | MURRE k3 | 87.0 | 87.0 | 29.0 | 575 |
| Spider | CORE-T | 90.1 | 90.1 | 49.4 | 575 |
| Spider | Route+SQL | 57.2 | 57.2 | 56.8 | 575 |
| Spider | AMIGO top-1 | 83.8 | 83.8 | 79.2 | 575 |
| Spider | AMIGO | 94.6 | 94.6 | 90.7 | 575 |
| MMQA | Dense k3 | 75.0 | 75.0 | 25.0 | 4 |
| MMQA | MURRE k3 | 100.0 | 100.0 | 33.3 | 4 |
| MMQA | CORE-T | 100.0 | 100.0 | 45.8 | 4 |
| MMQA | AMIGO top-1 | 75.0 | 75.0 | 75.0 | 4 |
| MMQA | AMIGO | 100.0 | 100.0 | 100.0 | 4 |
| mean | Dense k3 | 80.5 | 80.5 | 26.8 |
| mean | MURRE k3 | 94.6 | 94.6 | 31.5 |
| mean | CORE-T | 96.6 | 96.6 | 46.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 85.4 | 85.4 | 80.2 |
| mean | AMIGO | 97.7 | 97.7 | 92.8 |
| worst | Dense k3 | 72.7 | 72.7 | 24.2 |
| worst | MURRE k3 | 87.0 | 87.0 | 29.0 |
| worst | CORE-T | 90.1 | 90.1 | 44.1 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 75.0 | 75.0 | 75.0 |
| worst | AMIGO | 94.6 | 94.6 | 87.7 |

## gold label, multi-table targets

| lake | method | R | CR | P | n |
|---|---|---|---|---|---|
| BIRD | Dense k3 | 79.8 | 60.8 | 58.1 | 1171 |
| BIRD | MURRE k3 | 86.7 | 73.1 | 63.6 | 1171 |
| BIRD | CORE-T | 95.4 | 90.8 | 68.6 | 1171 |
| BIRD | Route+SQL | 87.8 | 78.3 | 91.3 | 1171 |
| BIRD | AMIGO top-1 | 91.2 | 81.4 | 92.8 | 1171 |
| BIRD | AMIGO | 94.8 | 88.7 | 94.0 | 1171 |
| Spider | Dense k3 | 74.4 | 52.9 | 53.3 | 459 |
| Spider | MURRE k3 | 82.7 | 69.7 | 58.9 | 459 |
| Spider | CORE-T | 88.3 | 78.4 | 67.4 | 459 |
| Spider | Route+SQL | 81.7 | 80.2 | 82.2 | 459 |
| Spider | AMIGO top-1 | 90.8 | 87.4 | 92.3 | 459 |
| Spider | AMIGO | 96.1 | 93.9 | 96.5 | 459 |
| MMQA | Dense k3 | 58.9 | 31.2 | 42.9 | 1045 |
| MMQA | MURRE k3 | 62.4 | 41.1 | 45.2 | 1045 |
| MMQA | CORE-T | 84.0 | 70.5 | 58.1 | 1045 |
| MMQA | AMIGO top-1 | 80.2 | 66.7 | 75.8 | 1045 |
| MMQA | AMIGO | 90.8 | 83.0 | 84.8 | 1045 |
| mean | Dense k3 | 71.1 | 48.3 | 51.4 |
| mean | MURRE k3 | 77.3 | 61.3 | 55.9 |
| mean | CORE-T | 89.2 | 79.9 | 64.7 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 87.4 | 78.5 | 87.0 |
| mean | AMIGO | 93.9 | 88.5 | 91.8 |
| worst | Dense k3 | 58.9 | 31.2 | 42.9 |
| worst | MURRE k3 | 62.4 | 41.1 | 45.2 |
| worst | CORE-T | 84.0 | 70.5 | 58.1 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 80.2 | 66.7 | 75.8 |
| worst | AMIGO | 90.8 | 83.0 | 84.8 |

## multi-valid label, every target

| lake | method | R | CR | P | pooled P | sets | tables | empty | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 80.1 | 61.9 | 53.6 | 63.5 | 1.00 | 3.00 | 0 | 1534 |
| BIRD | MURRE k3 | 85.6 | 70.8 | 57.7 | 67.6 | 1.00 | 3.00 | 0 | 1534 |
| BIRD | CORE-T | 93.0 | 85.3 | 64.3 | 74.9 | 1.00 | 3.19 | 0 | 1534 |
| BIRD | Route+SQL | 81.5 | 65.4 | 88.6 | 93.8 | 0.99 | 1.87 | 9 | 1534 |
| BIRD | AMIGO top-1 | 86.3 | 71.2 | 90.1 | 97.3 | 1.00 | 1.99 | 0 | 1534 |
| BIRD | AMIGO | 90.9 | 80.4 | 91.4 | 93.9 | 1.50 | 2.38 | 0 | 1534 |
| Spider | Dense k3 | 61.8 | 51.8 | 32.5 | 49.3 | 1.00 | 3.00 | 0 | 1034 |
| Spider | MURRE k3 | 72.5 | 65.4 | 37.4 | 56.3 | 1.00 | 3.00 | 0 | 1034 |
| Spider | CORE-T | 73.0 | 67.4 | 48.5 | 69.4 | 1.00 | 2.68 | 0 | 1034 |
| Spider | Route+SQL | 54.8 | 50.2 | 56.8 | 77.2 | 1.00 | 1.60 | 4 | 1034 |
| Spider | AMIGO top-1 | 67.9 | 63.2 | 68.7 | 94.3 | 1.00 | 1.56 | 1 | 1034 |
| Spider | AMIGO | 76.8 | 73.7 | 76.4 | 91.2 | 1.67 | 2.29 | 1 | 1034 |
| MMQA | Dense k3 | 54.3 | 24.0 | 42.4 | 54.5 | 1.00 | 3.00 | 0 | 1049 |
| MMQA | MURRE k3 | 58.0 | 31.6 | 44.8 | 57.8 | 1.00 | 3.00 | 0 | 1049 |
| MMQA | CORE-T | 76.8 | 53.8 | 56.6 | 71.6 | 1.00 | 3.78 | 0 | 1049 |
| MMQA | AMIGO top-1 | 71.1 | 46.1 | 72.5 | 86.0 | 1.00 | 2.63 | 1 | 1049 |
| MMQA | AMIGO | 82.9 | 63.2 | 80.5 | 66.0 | 8.91 | 8.36 | 1 | 1049 |
| mean | Dense k3 | 65.4 | 45.9 | 42.8 | 55.7 |
| mean | MURRE k3 | 72.1 | 55.9 | 46.7 | 60.6 |
| mean | CORE-T | 80.9 | 68.8 | 56.5 | 72.0 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 75.1 | 60.2 | 77.1 | 92.6 |
| mean | AMIGO | 83.5 | 72.4 | 82.8 | 83.7 |
| worst | Dense k3 | 54.3 | 24.0 | 32.5 | 49.3 |
| worst | MURRE k3 | 58.0 | 31.6 | 37.4 | 56.3 |
| worst | CORE-T | 73.0 | 53.8 | 48.5 | 69.4 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 67.9 | 46.1 | 68.7 | 86.0 |
| worst | AMIGO | 76.8 | 63.2 | 76.4 | 66.0 |

## multi-valid label, single-table targets

| lake | method | R | CR | P | n |
|---|---|---|---|---|---|
| BIRD | Dense k3 | 89.0 | 89.0 | 29.7 | 473 |
| BIRD | MURRE k3 | 92.5 | 92.5 | 30.8 | 473 |
| BIRD | CORE-T | 96.0 | 96.0 | 40.5 | 473 |
| BIRD | Route+SQL | 87.9 | 87.9 | 79.9 | 473 |
| BIRD | AMIGO top-1 | 92.7 | 92.7 | 78.4 | 473 |
| BIRD | AMIGO | 94.3 | 94.3 | 80.7 | 473 |
| Spider | Dense k3 | 60.9 | 60.9 | 20.3 | 683 |
| Spider | MURRE k3 | 73.6 | 73.6 | 24.5 | 683 |
| Spider | CORE-T | 71.7 | 71.7 | 38.1 | 683 |
| Spider | Route+SQL | 46.0 | 46.0 | 44.3 | 683 |
| Spider | AMIGO top-1 | 65.1 | 65.1 | 59.9 | 683 |
| Spider | AMIGO | 74.7 | 74.7 | 69.9 | 683 |
| MMQA | Dense k3 | 60.5 | 60.5 | 20.2 | 106 |
| MMQA | MURRE k3 | 64.9 | 64.9 | 21.6 | 106 |
| MMQA | CORE-T | 67.0 | 67.0 | 22.3 | 106 |
| MMQA | AMIGO top-1 | 57.7 | 57.7 | 29.6 | 106 |
| MMQA | AMIGO | 78.1 | 78.1 | 41.1 | 106 |
| mean | Dense k3 | 70.2 | 70.2 | 23.4 |
| mean | MURRE k3 | 77.0 | 77.0 | 25.7 |
| mean | CORE-T | 78.2 | 78.2 | 33.6 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 71.8 | 71.8 | 55.9 |
| mean | AMIGO | 82.4 | 82.4 | 63.9 |
| worst | Dense k3 | 60.5 | 60.5 | 20.2 |
| worst | MURRE k3 | 64.9 | 64.9 | 21.6 |
| worst | CORE-T | 67.0 | 67.0 | 22.3 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 57.7 | 57.7 | 29.6 |
| worst | AMIGO | 74.7 | 74.7 | 41.1 |

## multi-valid label, multi-table targets

| lake | method | R | CR | P | n |
|---|---|---|---|---|---|
| BIRD | Dense k3 | 78.1 | 55.9 | 59.2 | 1345 |
| BIRD | MURRE k3 | 83.7 | 65.2 | 63.7 | 1345 |
| BIRD | CORE-T | 91.7 | 82.0 | 69.3 | 1345 |
| BIRD | Route+SQL | 78.0 | 56.5 | 90.3 | 1345 |
| BIRD | AMIGO top-1 | 82.7 | 62.7 | 91.8 | 1345 |
| BIRD | AMIGO | 88.6 | 74.8 | 92.8 | 1345 |
| Spider | Dense k3 | 59.9 | 39.5 | 43.7 | 624 |
| Spider | MURRE k3 | 67.4 | 51.7 | 49.0 | 624 |
| Spider | CORE-T | 70.0 | 58.6 | 56.2 | 624 |
| Spider | Route+SQL | 59.5 | 48.1 | 67.2 | 624 |
| Spider | AMIGO top-1 | 65.5 | 54.3 | 72.2 | 624 |
| Spider | AMIGO | 73.7 | 66.7 | 76.7 | 624 |
| MMQA | Dense k3 | 54.2 | 22.9 | 43.1 | 1048 |
| MMQA | MURRE k3 | 57.9 | 30.6 | 45.6 | 1048 |
| MMQA | CORE-T | 77.4 | 53.8 | 58.0 | 1048 |
| MMQA | AMIGO top-1 | 71.8 | 46.1 | 74.0 | 1048 |
| MMQA | AMIGO | 83.3 | 63.0 | 81.9 | 1048 |
| mean | Dense k3 | 64.1 | 39.4 | 48.7 |
| mean | MURRE k3 | 69.7 | 49.2 | 52.8 |
| mean | CORE-T | 79.7 | 64.8 | 61.2 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 73.3 | 54.4 | 79.4 |
| mean | AMIGO | 81.9 | 68.2 | 83.8 |
| worst | Dense k3 | 54.2 | 22.9 | 43.1 |
| worst | MURRE k3 | 57.9 | 30.6 | 45.6 |
| worst | CORE-T | 70.0 | 53.8 | 56.2 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 65.5 | 46.1 | 72.2 |
| worst | AMIGO | 73.7 | 63.0 | 76.7 |

## AMIGO minus each method (every target)

Mean difference in points over questions, 95% bootstrap interval (10,000 resamples of questions), Holm-corrected p over the comparisons of one lake and label; * when below 0.05.

| label | lake | method | R | CR | P |
|---|---|---|---|---|---|
| gold label | BIRD | Dense k3 | +12.6 [+11.1, +14.1]* | +22.5 [+19.9, +24.9]* | +40.8 [+39.5, +42.0]* |
| gold label | BIRD | MURRE k3 | +6.7 [+5.4, +7.9]* | +12.4 [+10.2, +14.5]* | +36.4 [+35.1, +37.7]* |
| gold label | BIRD | CORE-T | -0.7 [-1.6, +0.1] | -1.8 [-3.5, -0.2] | +29.7 [+28.4, +31.0]* |
| gold label | BIRD | Route+SQL | +7.0 [+5.7, +8.4]* | +9.6 [+7.6, +11.6]* | +1.8 [+0.5, +3.2]* |
| gold label | BIRD | AMIGO top-1 | +3.0 [+2.4, +3.6]* | +5.9 [+4.8, +7.0]* | +1.3 [+0.9, +1.7]* |
| gold label | Spider | Dense k3 | +21.8 [+19.5, +24.2]* | +30.4 [+27.5, +33.4]* | +56.1 [+54.4, +57.8]* |
| gold label | Spider | MURRE k3 | +10.2 [+8.2, +12.3]* | +15.0 [+12.4, +17.6]* | +51.0 [+49.3, +52.7]* |
| gold label | Spider | CORE-T | +6.0 [+4.2, +7.8]* | +9.4 [+7.1, +11.8]* | +35.9 [+34.0, +37.9]* |
| gold label | Spider | Route+SQL | +27.2 [+24.4, +30.0]* | +26.9 [+24.0, +29.8]* | +25.2 [+22.4, +28.1]* |
| gold label | Spider | AMIGO top-1 | +8.3 [+6.8, +10.0]* | +8.9 [+7.2, +10.6]* | +8.2 [+6.6, +9.9]* |
| gold label | MMQA | Dense k3 | +31.9 [+29.6, +34.1]* | +51.7 [+48.2, +55.1]* | +42.0 [+40.0, +44.1]* |
| gold label | MMQA | MURRE k3 | +28.3 [+26.0, +30.7]* | +41.8 [+38.5, +45.1]* | +39.7 [+37.7, +41.7]* |
| gold label | MMQA | CORE-T | +6.8 [+5.0, +8.6]* | +12.4 [+9.2, +15.6]* | +26.8 [+24.6, +28.8]* |
| gold label | MMQA | AMIGO top-1 | +10.7 [+9.3, +12.2]* | +16.3 [+14.1, +18.6]* | +9.0 [+7.7, +10.4]* |
| multi-valid label | BIRD | Dense k3 | +10.8 [+9.4, +12.2]* | +18.5 [+16.1, +20.9]* | +37.8 [+36.6, +39.0]* |
| multi-valid label | BIRD | MURRE k3 | +5.3 [+4.1, +6.4]* | +9.6 [+7.6, +11.7]* | +33.6 [+32.4, +34.8]* |
| multi-valid label | BIRD | CORE-T | -2.1 [-3.0, -1.3]* | -4.9 [-6.6, -3.3]* | +27.0 [+25.9, +28.2]* |
| multi-valid label | BIRD | Route+SQL | +9.4 [+8.2, +10.7]* | +15.0 [+13.2, +16.8]* | +2.8 [+1.6, +4.1]* |
| multi-valid label | BIRD | AMIGO top-1 | +4.6 [+4.0, +5.2]* | +9.1 [+8.0, +10.3]* | +1.2 [+0.9, +1.6]* |
| multi-valid label | Spider | Dense k3 | +15.0 [+13.1, +17.0]* | +21.9 [+19.3, +24.4]* | +43.9 [+42.3, +45.6]* |
| multi-valid label | Spider | MURRE k3 | +4.2 [+2.6, +5.9]* | +8.3 [+6.1, +10.4]* | +39.0 [+37.4, +40.6]* |
| multi-valid label | Spider | CORE-T | +3.8 [+2.4, +5.2]* | +6.3 [+4.4, +8.3]* | +27.9 [+26.3, +29.5]* |
| multi-valid label | Spider | Route+SQL | +22.0 [+19.9, +24.2]* | +23.5 [+21.1, +25.8]* | +19.6 [+17.3, +21.8]* |
| multi-valid label | Spider | AMIGO top-1 | +8.9 [+7.6, +10.1]* | +10.5 [+9.1, +11.9]* | +7.7 [+6.5, +9.0]* |
| multi-valid label | MMQA | Dense k3 | +28.6 [+26.6, +30.6]* | +39.2 [+36.6, +41.9]* | +38.1 [+36.3, +40.0]* |
| multi-valid label | MMQA | MURRE k3 | +25.0 [+22.9, +27.0]* | +31.6 [+28.9, +34.2]* | +35.7 [+33.9, +37.5]* |
| multi-valid label | MMQA | CORE-T | +6.1 [+4.5, +7.7]* | +9.4 [+6.8, +12.0]* | +23.9 [+22.1, +25.8]* |
| multi-valid label | MMQA | AMIGO top-1 | +11.8 [+10.7, +13.0]* | +17.1 [+15.5, +18.8]* | +8.0 [+6.9, +9.1]* |
