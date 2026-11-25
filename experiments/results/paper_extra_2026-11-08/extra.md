# Extra tables for the paper (stage 1 of docs/eval_protocol.md, no LLM call)

Scored with experiments/protocol.py on existing outputs. R, CR, P: per target from the returned set with the best recall (then precision), averaged per question, then over questions.

## Ablations of AMIGO (join-choice run), gold label

| lake | method | R | CR | P | CR= | sets | tables | empty | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | AMIGO (place judge + join choice) | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 2.17 | 0 | 1534 |
| BIRD | place judge only (no join choice) | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 2.17 | 0 | 1534 |
| BIRD | place judge + whole judge (AMIGO-WJ) | 94.9 | 89.0 | 92.6 | 77.3 | 1.11 | 2.08 | 0 | 1534 |
| BIRD | no judge at all | 94.6 | 89.7 | 95.5 | 84.5 | 4.48 | 3.70 | 0 | 1534 |
| Spider | AMIGO (place judge + join choice) | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 2.18 | 2 | 1034 |
| Spider | place judge only (no join choice) | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 2.18 | 2 | 1034 |
| Spider | place judge + whole judge (AMIGO-WJ) | 95.1 | 94.0 | 93.6 | 88.8 | 1.43 | 2.04 | 2 | 1034 |
| Spider | no judge at all | 93.4 | 92.6 | 93.2 | 91.0 | 6.64 | 6.39 | 0 | 1034 |
| MMQA | AMIGO (place judge + join choice) | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 5.29 | 0 | 1049 |
| MMQA | place judge only (no join choice) | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 5.35 | 0 | 1049 |
| MMQA | place judge + whole judge (AMIGO-WJ) | 86.1 | 74.1 | 81.1 | 60.2 | 2.45 | 4.04 | 0 | 1049 |
| MMQA | no judge at all | 85.3 | 74.7 | 88.4 | 67.2 | 7.61 | 7.08 | 0 | 1049 |
| mean | AMIGO (place judge + join choice) | 93.2 | 87.4 | 90.7 | 78.1 |
| mean | place judge only (no join choice) | 93.2 | 87.4 | 90.7 | 78.1 |
| mean | place judge + whole judge (AMIGO-WJ) | 92.0 | 85.7 | 89.1 | 75.4 |
| mean | no judge at all | 91.1 | 85.7 | 92.4 | 80.9 |
| worst | AMIGO (place judge + join choice) | 87.9 | 76.7 | 83.0 | 62.5 |
| worst | place judge only (no join choice) | 87.9 | 76.7 | 83.0 | 62.5 |
| worst | place judge + whole judge (AMIGO-WJ) | 86.1 | 74.1 | 81.1 | 60.2 |
| worst | no judge at all | 85.3 | 74.7 | 88.4 | 67.2 |

## Ablations of AMIGO (join-choice run), gold label: first row minus each other row (points, 95% interval, Holm)

| lake | method | metric | difference |
|---|---|---|---|
| BIRD | place judge only (no join choice) | R | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | CR | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | P | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | CR= | +0.0 [+0.0, +0.0] |
| BIRD | place judge + whole judge (AMIGO-WJ) | R | +0.8 [+0.5, +1.1]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | CR | +1.4 [+0.9, +2.1]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | P | +1.1 [+0.8, +1.5]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | CR= | +2.7 [+2.0, +3.6]* |
| BIRD | no judge at all | R | +1.1 [+0.1, +2.0] |
| BIRD | no judge at all | CR | +0.7 [-0.8, +2.3] |
| BIRD | no judge at all | P | -1.7 [-2.7, -0.8]* |
| BIRD | no judge at all | CR= | -4.4 [-6.3, -2.5]* |
| Spider | place judge only (no join choice) | R | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | CR | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | P | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | CR= | +0.0 [+0.0, +0.0] |
| Spider | place judge + whole judge (AMIGO-WJ) | R | +1.0 [+0.4, +1.6]* |
| Spider | place judge + whole judge (AMIGO-WJ) | CR | +1.1 [+0.5, +1.7]* |
| Spider | place judge + whole judge (AMIGO-WJ) | P | +1.7 [+1.0, +2.4]* |
| Spider | place judge + whole judge (AMIGO-WJ) | CR= | +2.9 [+1.9, +4.0]* |
| Spider | no judge at all | R | +2.7 [+1.4, +4.0]* |
| Spider | no judge at all | CR | +2.4 [+1.1, +3.9]* |
| Spider | no judge at all | P | +2.2 [+0.8, +3.6]* |
| Spider | no judge at all | CR= | +0.7 [-1.0, +2.3] |
| MMQA | place judge only (no join choice) | R | +0.0 [+0.0, +0.0] |
| MMQA | place judge only (no join choice) | CR | +0.0 [+0.0, +0.0] |
| MMQA | place judge only (no join choice) | P | +0.0 [+0.0, +0.0] |
| MMQA | place judge only (no join choice) | CR= | +0.0 [+0.0, +0.0] |
| MMQA | place judge + whole judge (AMIGO-WJ) | R | +1.8 [+1.3, +2.5]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | CR | +2.7 [+1.7, +3.7]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | P | +1.8 [+1.3, +2.5]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | CR= | +2.4 [+1.5, +3.3]* |
| MMQA | no judge at all | R | +2.6 [+1.1, +4.1]* |
| MMQA | no judge at all | CR | +2.0 [-0.4, +4.4] |
| MMQA | no judge at all | P | -5.5 [-7.3, -3.6]* |
| MMQA | no judge at all | CR= | -4.7 [-7.0, -2.4]* |

## Ablations of AMIGO (join-choice run), multi-valid label

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | sets | tables | empty | n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | AMIGO (place judge + join choice) | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 2.17 | 0 | 1534 |
| BIRD | place judge only (no join choice) | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 2.17 | 0 | 1534 |
| BIRD | place judge + whole judge (AMIGO-WJ) | 69.3 | 52.2 | 91.3 | 64.6 | 48.2 | 85.1 | 1.11 | 2.08 | 0 | 1534 |
| BIRD | no judge at all | 80.6 | 69.1 | 39.2 | 76.2 | 63.3 | 37.3 | 4.48 | 3.70 | 0 | 1534 |
| Spider | AMIGO (place judge + join choice) | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 2.18 | 2 | 1034 |
| Spider | place judge only (no join choice) | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 2.18 | 2 | 1034 |
| Spider | place judge + whole judge (AMIGO-WJ) | 67.6 | 46.1 | 93.6 | 66.4 | 45.6 | 91.1 | 1.43 | 2.04 | 2 | 1034 |
| Spider | no judge at all | 78.2 | 60.6 | 33.5 | 76.1 | 57.8 | 32.4 | 6.64 | 6.39 | 0 | 1034 |
| MMQA | AMIGO (place judge + join choice) | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 5.29 | 0 | 1049 |
| MMQA | place judge only (no join choice) | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 5.35 | 0 | 1049 |
| MMQA | place judge + whole judge (AMIGO-WJ) | 48.1 | 29.7 | 73.8 | 40.7 | 25.5 | 62.1 | 2.45 | 4.04 | 0 | 1049 |
| MMQA | no judge at all | 56.3 | 38.2 | 29.3 | 50.7 | 34.2 | 26.4 | 7.61 | 7.08 | 0 | 1049 |
| mean | AMIGO (place judge + join choice) | 65.7 | 47.3 | 79.5 | 60.6 | 43.8 | 73.1 |
| mean | place judge only (no join choice) | 65.7 | 47.3 | 79.4 | 60.6 | 43.8 | 73.1 |
| mean | place judge + whole judge (AMIGO-WJ) | 61.6 | 42.7 | 86.2 | 57.2 | 39.8 | 79.5 |
| mean | no judge at all | 71.7 | 56.0 | 34.0 | 67.6 | 51.8 | 32.0 |
| worst | AMIGO (place judge + join choice) | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 |
| worst | place judge only (no join choice) | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 |
| worst | place judge + whole judge (AMIGO-WJ) | 48.1 | 29.7 | 73.8 | 40.7 | 25.5 | 62.1 |
| worst | no judge at all | 56.3 | 38.2 | 29.3 | 50.7 | 34.2 | 26.4 |

## Ablations of AMIGO (join-choice run), multi-valid label: first row minus each other row (points, 95% interval, Holm)

| lake | method | metric | difference |
|---|---|---|---|
| BIRD | place judge only (no join choice) | IR | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | ICR | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | IP | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | IR= | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | ICR= | +0.0 [+0.0, +0.0] |
| BIRD | place judge only (no join choice) | IP= | +0.0 [+0.0, +0.0] |
| BIRD | place judge + whole judge (AMIGO-WJ) | IR | +3.8 [+3.1, +4.5]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | ICR | +5.3 [+4.2, +6.5]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | IP | -8.1 [-9.1, -7.1]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | IR= | +3.7 [+3.0, +4.4]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | ICR= | +5.0 [+3.9, +6.1]* |
| BIRD | place judge + whole judge (AMIGO-WJ) | IP= | -7.5 [-8.5, -6.5]* |
| BIRD | no judge at all | IR | -7.5 [-9.1, -6.0]* |
| BIRD | no judge at all | ICR | -11.7 [-13.9, -9.5]* |
| BIRD | no judge at all | IP | +44.0 [+42.4, +45.6]* |
| BIRD | no judge at all | IR= | -7.9 [-9.5, -6.3]* |
| BIRD | no judge at all | ICR= | -10.2 [-12.3, -8.1]* |
| BIRD | no judge at all | IP= | +40.4 [+38.6, +42.2]* |
| Spider | place judge only (no join choice) | IR | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | ICR | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | IP | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | IR= | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | ICR= | +0.0 [+0.0, +0.0] |
| Spider | place judge only (no join choice) | IP= | +0.0 [+0.0, +0.0] |
| Spider | place judge + whole judge (AMIGO-WJ) | IR | +3.2 [+2.5, +3.9]* |
| Spider | place judge + whole judge (AMIGO-WJ) | ICR | +3.9 [+2.7, +5.1]* |
| Spider | place judge + whole judge (AMIGO-WJ) | IP | -4.1 [-4.9, -3.2]* |
| Spider | place judge + whole judge (AMIGO-WJ) | IR= | +3.1 [+2.4, +3.8]* |
| Spider | place judge + whole judge (AMIGO-WJ) | ICR= | +3.4 [+2.3, +4.5]* |
| Spider | place judge + whole judge (AMIGO-WJ) | IP= | -3.6 [-4.4, -2.7]* |
| Spider | no judge at all | IR | -7.5 [-9.3, -5.7]* |
| Spider | no judge at all | ICR | -10.6 [-13.1, -8.1]* |
| Spider | no judge at all | IP | +56.1 [+54.3, +57.9]* |
| Spider | no judge at all | IR= | -6.6 [-8.3, -5.0]* |
| Spider | no judge at all | ICR= | -8.8 [-11.1, -6.6]* |
| Spider | no judge at all | IP= | +55.2 [+53.3, +57.1]* |
| MMQA | place judge only (no join choice) | IR | -0.0 [-0.0, +0.0] |
| MMQA | place judge only (no join choice) | ICR | +0.0 [+0.0, +0.0] |
| MMQA | place judge only (no join choice) | IP | +0.1 [+0.0, +0.2]* |
| MMQA | place judge only (no join choice) | IR= | +0.0 [+0.0, +0.0] |
| MMQA | place judge only (no join choice) | ICR= | +0.0 [+0.0, +0.0] |
| MMQA | place judge only (no join choice) | IP= | +0.1 [+0.0, +0.2]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | IR | +5.2 [+4.3, +6.2]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | ICR | +4.8 [+3.5, +6.1]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | IP | -8.2 [-9.5, -7.0]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | IR= | +3.2 [+2.5, +4.0]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | ICR= | +3.8 [+2.7, +5.1]* |
| MMQA | place judge + whole judge (AMIGO-WJ) | IP= | -8.1 [-9.4, -6.9]* |
| MMQA | no judge at all | IR | -3.0 [-4.9, -1.1]* |
| MMQA | no judge at all | ICR | -3.7 [-5.9, -1.5]* |
| MMQA | no judge at all | IP | +36.3 [+34.1, +38.6]* |
| MMQA | no judge at all | IR= | -6.7 [-8.4, -5.1]* |
| MMQA | no judge at all | ICR= | -4.9 [-6.8, -3.0]* |
| MMQA | no judge at all | IP= | +27.6 [+25.2, +30.0]* |

## Ablations of the AMIGO-WJ (with the whole judge), gold label

| lake | method | R | CR | P | CR= | sets | tables | empty | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | AMIGO-WJ (place judge + whole judge) | 94.9 | 89.0 | 92.6 | 77.3 | 1.11 | 2.08 | 0 | 1534 |
| BIRD |   without the relaxed fallback | 84.1 | 79.5 | 81.5 | 68.8 | 0.95 | 1.83 | 183 | 1534 |
| BIRD |   without LLM-judged links | 94.8 | 88.9 | 92.6 | 77.2 | 1.10 | 2.08 | 0 | 1534 |
| BIRD |   without the place judge (BIRD only) | 91.5 | 84.0 | 91.3 | 75.4 | 1.25 | 2.10 | 0 | 1534 |
| Spider | AMIGO-WJ (place judge + whole judge) | 95.1 | 94.0 | 93.6 | 88.8 | 1.43 | 2.04 | 2 | 1034 |
| Spider |   without the relaxed fallback | 89.3 | 88.7 | 87.4 | 83.7 | 1.29 | 1.87 | 72 | 1034 |
| Spider |   without LLM-judged links | 93.7 | 91.5 | 93.2 | 86.3 | 1.44 | 2.02 | 2 | 1034 |
| MMQA | AMIGO-WJ (place judge + whole judge) | 86.1 | 74.1 | 81.1 | 60.2 | 2.45 | 4.04 | 0 | 1049 |
| MMQA |   without the relaxed fallback | 78.1 | 69.4 | 71.7 | 56.6 | 2.19 | 3.65 | 120 | 1049 |
| MMQA |   without LLM-judged links | 82.1 | 67.2 | 83.0 | 55.9 | 2.39 | 4.25 | 0 | 1049 |
| mean | AMIGO-WJ (place judge + whole judge) | 92.0 | 85.7 | 89.1 | 75.4 |
| mean |   without the relaxed fallback | 83.9 | 79.2 | 80.2 | 69.7 |
| mean |   without LLM-judged links | 90.2 | 82.5 | 89.6 | 73.1 |
| mean |   without the place judge (BIRD only) | ran on 1 of 3 lakes |
| worst | AMIGO-WJ (place judge + whole judge) | 86.1 | 74.1 | 81.1 | 60.2 |
| worst |   without the relaxed fallback | 78.1 | 69.4 | 71.7 | 56.6 |
| worst |   without LLM-judged links | 82.1 | 67.2 | 83.0 | 55.9 |
| worst |   without the place judge (BIRD only) | ran on 1 of 3 lakes |

## Ablations of the AMIGO-WJ (with the whole judge), gold label: first row minus each other row (points, 95% interval, Holm)

| lake | method | metric | difference |
|---|---|---|---|
| BIRD |   without the relaxed fallback | R | +10.7 [+9.2, +12.3]* |
| BIRD |   without the relaxed fallback | CR | +9.5 [+8.0, +11.0]* |
| BIRD |   without the relaxed fallback | P | +11.1 [+9.6, +12.6]* |
| BIRD |   without the relaxed fallback | CR= | +8.5 [+7.2, +10.0]* |
| BIRD |   without LLM-judged links | R | +0.1 [+0.0, +0.2] |
| BIRD |   without LLM-judged links | CR | +0.1 [+0.0, +0.2] |
| BIRD |   without LLM-judged links | P | +0.1 [+0.0, +0.1] |
| BIRD |   without LLM-judged links | CR= | +0.1 [+0.0, +0.2] |
| BIRD |   without the place judge (BIRD only) | R | +3.4 [+2.5, +4.3]* |
| BIRD |   without the place judge (BIRD only) | CR | +5.0 [+3.4, +6.6]* |
| BIRD |   without the place judge (BIRD only) | P | +1.3 [+0.4, +2.3]* |
| BIRD |   without the place judge (BIRD only) | CR= | +1.9 [+0.0, +3.7] |
| Spider |   without the relaxed fallback | R | +5.8 [+4.5, +7.3]* |
| Spider |   without the relaxed fallback | CR | +5.3 [+4.0, +6.8]* |
| Spider |   without the relaxed fallback | P | +6.3 [+4.8, +7.8]* |
| Spider |   without the relaxed fallback | CR= | +5.1 [+3.9, +6.5]* |
| Spider |   without LLM-judged links | R | +1.4 [+0.9, +2.0]* |
| Spider |   without LLM-judged links | CR | +2.5 [+1.6, +3.6]* |
| Spider |   without LLM-judged links | P | +0.5 [+0.1, +0.9]* |
| Spider |   without LLM-judged links | CR= | +2.5 [+1.5, +3.5]* |
| MMQA |   without the relaxed fallback | R | +7.9 [+6.5, +9.4]* |
| MMQA |   without the relaxed fallback | CR | +4.7 [+3.4, +6.0]* |
| MMQA |   without the relaxed fallback | P | +9.4 [+7.7, +11.1]* |
| MMQA |   without the relaxed fallback | CR= | +3.5 [+2.5, +4.7]* |
| MMQA |   without LLM-judged links | R | +3.9 [+3.0, +4.9]* |
| MMQA |   without LLM-judged links | CR | +6.9 [+5.1, +8.7]* |
| MMQA |   without LLM-judged links | P | -1.9 [-2.9, -0.8]* |
| MMQA |   without LLM-judged links | CR= | +4.3 [+2.9, +5.8]* |

## Ablations of the AMIGO-WJ (with the whole judge), multi-valid label

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | sets | tables | empty | n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | AMIGO-WJ (place judge + whole judge) | 69.3 | 52.2 | 91.3 | 64.6 | 48.2 | 85.1 | 1.11 | 2.08 | 0 | 1534 |
| BIRD |   without the relaxed fallback | 61.2 | 45.7 | 82.1 | 57.1 | 42.2 | 76.7 | 0.95 | 1.83 | 183 | 1534 |
| BIRD |   without LLM-judged links | 69.3 | 52.1 | 91.3 | 64.5 | 48.0 | 85.1 | 1.10 | 2.08 | 0 | 1534 |
| BIRD |   without the place judge (BIRD only) | 66.3 | 50.3 | 84.3 | 62.2 | 46.9 | 79.5 | 1.25 | 2.10 | 0 | 1534 |
| Spider | AMIGO-WJ (place judge + whole judge) | 67.6 | 46.1 | 93.6 | 66.4 | 45.6 | 91.1 | 1.43 | 2.04 | 2 | 1034 |
| Spider |   without the relaxed fallback | 63.5 | 43.1 | 89.0 | 62.5 | 42.7 | 86.7 | 1.29 | 1.87 | 72 | 1034 |
| Spider |   without LLM-judged links | 66.6 | 45.5 | 92.5 | 65.4 | 45.0 | 89.9 | 1.44 | 2.02 | 2 | 1034 |
| MMQA | AMIGO-WJ (place judge + whole judge) | 48.1 | 29.7 | 73.8 | 40.7 | 25.5 | 62.1 | 2.45 | 4.04 | 0 | 1049 |
| MMQA |   without the relaxed fallback | 44.8 | 27.5 | 69.8 | 37.9 | 23.5 | 58.8 | 2.19 | 3.65 | 120 | 1049 |
| MMQA |   without LLM-judged links | 43.5 | 26.5 | 67.6 | 37.2 | 22.9 | 57.8 | 2.39 | 4.25 | 0 | 1049 |
| mean | AMIGO-WJ (place judge + whole judge) | 61.6 | 42.7 | 86.2 | 57.2 | 39.8 | 79.5 |
| mean |   without the relaxed fallback | 56.5 | 38.8 | 80.3 | 52.5 | 36.1 | 74.0 |
| mean |   without LLM-judged links | 59.8 | 41.3 | 83.8 | 55.7 | 38.6 | 77.6 |
| mean |   without the place judge (BIRD only) | ran on 1 of 3 lakes |
| worst | AMIGO-WJ (place judge + whole judge) | 48.1 | 29.7 | 73.8 | 40.7 | 25.5 | 62.1 |
| worst |   without the relaxed fallback | 44.8 | 27.5 | 69.8 | 37.9 | 23.5 | 58.8 |
| worst |   without LLM-judged links | 43.5 | 26.5 | 67.6 | 37.2 | 22.9 | 57.8 |
| worst |   without the place judge (BIRD only) | ran on 1 of 3 lakes |

## Ablations of the AMIGO-WJ (with the whole judge), multi-valid label: first row minus each other row (points, 95% interval, Holm)

| lake | method | metric | difference |
|---|---|---|---|
| BIRD |   without the relaxed fallback | IR | +8.1 [+6.8, +9.4]* |
| BIRD |   without the relaxed fallback | ICR | +6.5 [+5.3, +7.7]* |
| BIRD |   without the relaxed fallback | IP | +9.2 [+7.8, +10.6]* |
| BIRD |   without the relaxed fallback | IR= | +7.5 [+6.3, +8.8]* |
| BIRD |   without the relaxed fallback | ICR= | +5.9 [+4.8, +7.2]* |
| BIRD |   without the relaxed fallback | IP= | +8.5 [+7.2, +9.9]* |
| BIRD |   without LLM-judged links | IR | +0.1 [+0.0, +0.1] |
| BIRD |   without LLM-judged links | ICR | +0.1 [+0.0, +0.2] |
| BIRD |   without LLM-judged links | IP | +0.0 [-0.1, +0.1] |
| BIRD |   without LLM-judged links | IR= | +0.1 [+0.0, +0.2] |
| BIRD |   without LLM-judged links | ICR= | +0.1 [+0.0, +0.3] |
| BIRD |   without LLM-judged links | IP= | +0.0 [-0.0, +0.2] |
| BIRD |   without the place judge (BIRD only) | IR | +3.0 [+1.8, +4.2]* |
| BIRD |   without the place judge (BIRD only) | ICR | +1.9 [+0.5, +3.3]* |
| BIRD |   without the place judge (BIRD only) | IP | +6.9 [+5.5, +8.4]* |
| BIRD |   without the place judge (BIRD only) | IR= | +2.4 [+1.0, +3.7]* |
| BIRD |   without the place judge (BIRD only) | ICR= | +1.2 [-0.2, +2.7] |
| BIRD |   without the place judge (BIRD only) | IP= | +5.7 [+4.1, +7.3]* |
| Spider |   without the relaxed fallback | IR | +4.0 [+3.0, +5.2]* |
| Spider |   without the relaxed fallback | ICR | +3.0 [+2.0, +4.1]* |
| Spider |   without the relaxed fallback | IP | +4.7 [+3.4, +6.0]* |
| Spider |   without the relaxed fallback | IR= | +3.9 [+2.9, +5.1]* |
| Spider |   without the relaxed fallback | ICR= | +2.9 [+1.9, +4.0]* |
| Spider |   without the relaxed fallback | IP= | +4.5 [+3.3, +5.7]* |
| Spider |   without LLM-judged links | IR | +0.9 [+0.5, +1.5]* |
| Spider |   without LLM-judged links | ICR | +0.7 [+0.2, +1.3]* |
| Spider |   without LLM-judged links | IP | +1.1 [+0.6, +1.7]* |
| Spider |   without LLM-judged links | IR= | +1.0 [+0.5, +1.5]* |
| Spider |   without LLM-judged links | ICR= | +0.7 [+0.2, +1.3]* |
| Spider |   without LLM-judged links | IP= | +1.2 [+0.7, +1.8]* |
| MMQA |   without the relaxed fallback | IR | +3.3 [+2.3, +4.3]* |
| MMQA |   without the relaxed fallback | ICR | +2.3 [+1.4, +3.2]* |
| MMQA |   without the relaxed fallback | IP | +4.0 [+2.9, +5.1]* |
| MMQA |   without the relaxed fallback | IR= | +2.8 [+1.9, +3.8]* |
| MMQA |   without the relaxed fallback | ICR= | +2.1 [+1.2, +3.0]* |
| MMQA |   without the relaxed fallback | IP= | +3.3 [+2.4, +4.4]* |
| MMQA |   without LLM-judged links | IR | +4.5 [+3.3, +5.9]* |
| MMQA |   without LLM-judged links | ICR | +3.2 [+2.1, +4.5]* |
| MMQA |   without LLM-judged links | IP | +6.2 [+4.5, +7.9]* |
| MMQA |   without LLM-judged links | IR= | +3.5 [+2.4, +4.7]* |
| MMQA |   without LLM-judged links | ICR= | +2.7 [+1.7, +3.7]* |
| MMQA |   without LLM-judged links | IP= | +4.3 [+2.8, +5.9]* |

## Every baseline at every k, gold label

| lake | method | R | CR | P | CR= | tables | empty | n |
|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k1 | 44.6 | 16.7 | 77.2 | 16.7 | 1.00 | 0 | 1534 |
| BIRD | Dense k3 | 83.1 | 68.6 | 51.8 | 3.9 | 3.00 | 0 | 1534 |
| BIRD | Dense k5 | 91.5 | 83.4 | 34.9 | 0.1 | 5.00 | 0 | 1534 |
| BIRD | BM25 k1 | 38.5 | 12.6 | 68.4 | 12.6 | 1.00 | 0 | 1534 |
| BIRD | BM25 k3 | 68.5 | 48.4 | 42.5 | 1.6 | 3.00 | 0 | 1534 |
| BIRD | BM25 k5 | 79.2 | 64.1 | 30.0 | 0.0 | 5.00 | 0 | 1534 |
| BIRD | Hybrid k1 | 46.3 | 16.9 | 80.4 | 16.9 | 1.00 | 0 | 1534 |
| BIRD | Hybrid k3 | 82.2 | 67.0 | 51.4 | 3.5 | 3.00 | 0 | 1534 |
| BIRD | Hybrid k5 | 90.0 | 80.1 | 34.2 | 0.0 | 5.00 | 0 | 1534 |
| BIRD | JAR k1 | 53.0 | 21.2 | 89.8 | 21.2 | 1.00 | 0 | 1534 |
| BIRD | JAR k3 | 87.0 | 76.1 | 54.7 | 5.9 | 3.00 | 0 | 1534 |
| BIRD | JAR k5 | 89.8 | 81.7 | 34.4 | 0.0 | 5.00 | 0 | 1534 |
| BIRD | Greedy JAR k1 | 53.5 | 21.3 | 90.7 | 21.3 | 1.00 | 0 | 1534 |
| BIRD | Greedy JAR k3 | 88.0 | 75.7 | 55.1 | 4.6 | 3.00 | 0 | 1534 |
| BIRD | Greedy JAR k5 | 93.4 | 86.8 | 35.7 | 0.0 | 5.00 | 0 | 1534 |
| BIRD | MURRE k1 | 50.8 | 20.3 | 86.2 | 20.3 | 1.00 | 0 | 1534 |
| BIRD | MURRE k3 | 89.0 | 78.7 | 56.1 | 6.6 | 3.00 | 0 | 1534 |
| BIRD | MURRE k5 | 94.3 | 88.7 | 36.2 | 0.1 | 5.00 | 0 | 1534 |
| BIRD | CRUSH4SQL 1 tables | 47.9 | 17.5 | 83.6 | 17.5 | 1.00 | 0 | 1534 |
| BIRD | CRUSH4SQL 3 tables | 85.6 | 71.8 | 53.8 | 5.3 | 3.00 | 0 | 1534 |
| BIRD | CRUSH4SQL 5 tables | 91.7 | 82.9 | 35.2 | 0.0 | 4.99 | 0 | 1534 |
| BIRD | CORE-T | 96.5 | 92.9 | 62.8 | 21.6 | 3.19 | 0 | 1534 |
| BIRD | Route+SQL | 88.7 | 81.5 | 90.7 | 78.0 | 1.87 | 9 | 1534 |
| BIRD | Full schema | 94.2 | 87.4 | 92.4 | 76.7 | 2.00 | 0 | 1534 |
| Spider | Dense k1 | 40.8 | 25.7 | 57.7 | 25.7 | 1.00 | 0 | 1034 |
| Spider | Dense k3 | 73.5 | 63.9 | 37.1 | 2.2 | 3.00 | 0 | 1034 |
| Spider | Dense k5 | 82.8 | 77.6 | 25.4 | 0.0 | 5.00 | 0 | 1034 |
| Spider | BM25 k1 | 48.5 | 33.1 | 65.7 | 33.1 | 1.00 | 0 | 1034 |
| Spider | BM25 k3 | 74.6 | 66.0 | 37.0 | 2.0 | 3.00 | 0 | 1034 |
| Spider | BM25 k5 | 81.2 | 74.7 | 24.3 | 0.0 | 5.00 | 0 | 1034 |
| Spider | Hybrid k1 | 48.1 | 31.9 | 66.3 | 31.9 | 1.00 | 0 | 1034 |
| Spider | Hybrid k3 | 79.3 | 71.0 | 39.6 | 2.4 | 3.00 | 0 | 1034 |
| Spider | Hybrid k5 | 86.9 | 81.7 | 26.2 | 0.0 | 5.00 | 0 | 1034 |
| Spider | JAR k1 | 60.5 | 43.6 | 79.0 | 43.6 | 1.00 | 0 | 1034 |
| Spider | JAR k3 | 78.8 | 72.7 | 39.0 | 2.4 | 3.00 | 0 | 1034 |
| Spider | JAR k5 | 84.4 | 79.9 | 25.6 | 0.0 | 5.00 | 0 | 1034 |
| Spider | Greedy JAR k1 | 60.6 | 44.6 | 78.1 | 44.6 | 1.00 | 0 | 1034 |
| Spider | Greedy JAR k3 | 79.9 | 75.7 | 39.0 | 2.3 | 3.00 | 0 | 1034 |
| Spider | Greedy JAR k5 | 83.0 | 79.6 | 24.5 | 0.0 | 5.00 | 0 | 1034 |
| Spider | MURRE k1 | 56.7 | 39.4 | 75.8 | 39.4 | 1.00 | 0 | 1034 |
| Spider | MURRE k3 | 85.1 | 79.3 | 42.3 | 3.0 | 3.00 | 0 | 1034 |
| Spider | MURRE k5 | 90.8 | 87.4 | 27.4 | 0.0 | 5.00 | 0 | 1034 |
| Spider | CRUSH4SQL 1 tables | 49.4 | 36.4 | 63.8 | 36.4 | 1.00 | 0 | 1034 |
| Spider | CRUSH4SQL 3 tables | 79.2 | 70.2 | 37.9 | 1.5 | 3.00 | 0 | 1034 |
| Spider | CRUSH4SQL 5 tables | 87.5 | 82.5 | 25.8 | 0.0 | 5.00 | 0 | 1034 |
| Spider | CORE-T | 89.3 | 84.9 | 57.4 | 25.4 | 2.68 | 0 | 1034 |
| Spider | Route+SQL | 68.1 | 67.4 | 68.0 | 65.8 | 1.60 | 4 | 1034 |
| Spider | Full schema | 0.0 | 0.0 | 0.0 | 0.0 | 0.00 | 1034 | 1034 |
| MMQA | Dense k1 | 31.9 | 0.3 | 68.2 | 0.3 | 1.00 | 0 | 1049 |
| MMQA | Dense k3 | 59.0 | 31.4 | 42.8 | 2.8 | 3.00 | 0 | 1049 |
| MMQA | Dense k5 | 70.9 | 46.5 | 31.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | BM25 k1 | 34.7 | 0.2 | 74.4 | 0.2 | 1.00 | 0 | 1049 |
| MMQA | BM25 k3 | 58.6 | 28.2 | 42.3 | 1.2 | 3.00 | 0 | 1049 |
| MMQA | BM25 k5 | 66.1 | 38.8 | 28.8 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | Hybrid k1 | 35.6 | 0.3 | 76.4 | 0.3 | 1.00 | 0 | 1049 |
| MMQA | Hybrid k3 | 66.1 | 38.0 | 48.0 | 3.2 | 3.00 | 0 | 1049 |
| MMQA | Hybrid k5 | 75.1 | 53.3 | 32.8 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | JAR k1 | 33.9 | 0.4 | 72.2 | 0.4 | 1.00 | 0 | 1049 |
| MMQA | JAR k3 | 62.0 | 41.5 | 44.7 | 4.4 | 3.00 | 0 | 1049 |
| MMQA | JAR k5 | 68.4 | 49.5 | 29.7 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | Greedy JAR k1 | 34.3 | 0.4 | 72.8 | 0.4 | 1.00 | 0 | 1049 |
| MMQA | Greedy JAR k3 | 61.9 | 41.5 | 44.6 | 4.2 | 3.00 | 0 | 1049 |
| MMQA | Greedy JAR k5 | 66.1 | 48.2 | 28.7 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | MURRE k1 | 29.8 | 0.2 | 63.9 | 0.2 | 1.00 | 0 | 1049 |
| MMQA | MURRE k3 | 62.6 | 41.3 | 45.2 | 4.5 | 3.00 | 0 | 1049 |
| MMQA | MURRE k5 | 71.4 | 52.5 | 31.2 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | CRUSH4SQL 1 tables | 26.8 | 0.3 | 57.4 | 0.3 | 1.00 | 0 | 1049 |
| MMQA | CRUSH4SQL 3 tables | 59.6 | 35.6 | 43.0 | 2.5 | 3.00 | 0 | 1049 |
| MMQA | CRUSH4SQL 5 tables | 71.4 | 49.3 | 31.1 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | CORE-T | 84.1 | 70.6 | 58.1 | 21.7 | 3.78 | 0 | 1049 |
| MMQA | Full schema | 0.0 | 0.0 | 0.0 | 0.0 | 0.00 | 1049 | 1049 |
| mean | Dense k1 | 39.1 | 14.2 | 67.7 | 14.2 |
| mean | Dense k3 | 71.9 | 54.6 | 43.9 | 3.0 |
| mean | Dense k5 | 81.7 | 69.2 | 30.4 | 0.0 |
| mean | BM25 k1 | 40.6 | 15.3 | 69.5 | 15.3 |
| mean | BM25 k3 | 67.2 | 47.5 | 40.6 | 1.6 |
| mean | BM25 k5 | 75.5 | 59.2 | 27.7 | 0.0 |
| mean | Hybrid k1 | 43.3 | 16.4 | 74.4 | 16.4 |
| mean | Hybrid k3 | 75.9 | 58.7 | 46.3 | 3.1 |
| mean | Hybrid k5 | 84.0 | 71.7 | 31.1 | 0.0 |
| mean | JAR k1 | 49.1 | 21.7 | 80.3 | 21.7 |
| mean | JAR k3 | 75.9 | 63.4 | 46.1 | 4.2 |
| mean | JAR k5 | 80.9 | 70.3 | 29.9 | 0.0 |
| mean | Greedy JAR k1 | 49.4 | 22.1 | 80.6 | 22.1 |
| mean | Greedy JAR k3 | 76.6 | 64.3 | 46.2 | 3.7 |
| mean | Greedy JAR k5 | 80.8 | 71.5 | 29.6 | 0.0 |
| mean | MURRE k1 | 45.8 | 19.9 | 75.3 | 19.9 |
| mean | MURRE k3 | 78.9 | 66.4 | 47.9 | 4.7 |
| mean | MURRE k5 | 85.5 | 76.2 | 31.6 | 0.0 |
| mean | CRUSH4SQL 1 tables | 41.4 | 18.0 | 68.3 | 18.0 |
| mean | CRUSH4SQL 3 tables | 74.8 | 59.2 | 44.9 | 3.1 |
| mean | CRUSH4SQL 5 tables | 83.6 | 71.5 | 30.7 | 0.0 |
| mean | CORE-T | 89.9 | 82.8 | 59.4 | 22.9 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | Full schema | 31.4 | 29.1 | 30.8 | 25.6 |
| worst | Dense k1 | 31.9 | 0.3 | 57.7 | 0.3 |
| worst | Dense k3 | 59.0 | 31.4 | 37.1 | 2.2 |
| worst | Dense k5 | 70.9 | 46.5 | 25.4 | 0.0 |
| worst | BM25 k1 | 34.7 | 0.2 | 65.7 | 0.2 |
| worst | BM25 k3 | 58.6 | 28.2 | 37.0 | 1.2 |
| worst | BM25 k5 | 66.1 | 38.8 | 24.3 | 0.0 |
| worst | Hybrid k1 | 35.6 | 0.3 | 66.3 | 0.3 |
| worst | Hybrid k3 | 66.1 | 38.0 | 39.6 | 2.4 |
| worst | Hybrid k5 | 75.1 | 53.3 | 26.2 | 0.0 |
| worst | JAR k1 | 33.9 | 0.4 | 72.2 | 0.4 |
| worst | JAR k3 | 62.0 | 41.5 | 39.0 | 2.4 |
| worst | JAR k5 | 68.4 | 49.5 | 25.6 | 0.0 |
| worst | Greedy JAR k1 | 34.3 | 0.4 | 72.8 | 0.4 |
| worst | Greedy JAR k3 | 61.9 | 41.5 | 39.0 | 2.3 |
| worst | Greedy JAR k5 | 66.1 | 48.2 | 24.5 | 0.0 |
| worst | MURRE k1 | 29.8 | 0.2 | 63.9 | 0.2 |
| worst | MURRE k3 | 62.6 | 41.3 | 42.3 | 3.0 |
| worst | MURRE k5 | 71.4 | 52.5 | 27.4 | 0.0 |
| worst | CRUSH4SQL 1 tables | 26.8 | 0.3 | 57.4 | 0.3 |
| worst | CRUSH4SQL 3 tables | 59.6 | 35.6 | 37.9 | 1.5 |
| worst | CRUSH4SQL 5 tables | 71.4 | 49.3 | 25.8 | 0.0 |
| worst | CORE-T | 84.1 | 70.6 | 57.4 | 21.6 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | Full schema | 0.0 | 0.0 | 0.0 | 0.0 |

## Every baseline at every k, multi-valid label

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | tables | empty | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k1 | 12.5 | 7.6 | 19.8 | 12.5 | 7.6 | 19.8 | 1.00 | 0 | 1534 |
| BIRD | Dense k3 | 50.9 | 36.2 | 72.0 | 6.3 | 2.3 | 12.4 | 3.00 | 0 | 1534 |
| BIRD | Dense k5 | 61.1 | 44.1 | 85.9 | 0.0 | 0.0 | 0.1 | 5.00 | 0 | 1534 |
| BIRD | BM25 k1 | 9.5 | 5.7 | 15.3 | 9.5 | 5.7 | 15.3 | 1.00 | 0 | 1534 |
| BIRD | BM25 k3 | 36.4 | 25.5 | 52.3 | 3.3 | 1.0 | 7.0 | 3.00 | 0 | 1534 |
| BIRD | BM25 k5 | 46.9 | 33.1 | 66.8 | 0.0 | 0.0 | 0.1 | 5.00 | 0 | 1534 |
| BIRD | Hybrid k1 | 12.8 | 7.9 | 20.1 | 12.8 | 7.9 | 20.1 | 1.00 | 0 | 1534 |
| BIRD | Hybrid k3 | 50.2 | 35.8 | 70.6 | 5.9 | 2.3 | 11.3 | 3.00 | 0 | 1534 |
| BIRD | Hybrid k5 | 59.2 | 42.4 | 83.2 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1534 |
| BIRD | JAR k1 | 17.2 | 10.9 | 26.3 | 17.2 | 10.9 | 26.3 | 1.00 | 0 | 1534 |
| BIRD | JAR k3 | 56.8 | 40.9 | 79.9 | 8.5 | 3.4 | 16.6 | 3.00 | 0 | 1534 |
| BIRD | JAR k5 | 59.4 | 42.1 | 84.8 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1534 |
| BIRD | Greedy JAR k1 | 17.2 | 10.8 | 26.5 | 17.2 | 10.8 | 26.5 | 1.00 | 0 | 1534 |
| BIRD | Greedy JAR k3 | 57.6 | 41.9 | 80.1 | 7.7 | 3.1 | 15.2 | 3.00 | 0 | 1534 |
| BIRD | Greedy JAR k5 | 63.9 | 46.2 | 89.4 | 0.0 | 0.0 | 0.1 | 5.00 | 0 | 1534 |
| BIRD | MURRE k1 | 16.0 | 10.2 | 24.4 | 16.0 | 10.2 | 24.4 | 1.00 | 0 | 1534 |
| BIRD | MURRE k3 | 58.5 | 41.9 | 82.7 | 8.9 | 4.0 | 17.1 | 3.00 | 0 | 1534 |
| BIRD | MURRE k5 | 64.8 | 46.9 | 90.9 | 0.0 | 0.0 | 0.1 | 5.00 | 0 | 1534 |
| BIRD | CRUSH4SQL 1 tables | 14.3 | 9.3 | 21.4 | 14.3 | 9.3 | 21.4 | 1.00 | 0 | 1534 |
| BIRD | CRUSH4SQL 3 tables | 54.4 | 39.5 | 76.3 | 7.5 | 2.9 | 14.4 | 3.00 | 0 | 1534 |
| BIRD | CRUSH4SQL 5 tables | 61.6 | 44.8 | 86.4 | 0.0 | 0.0 | 0.0 | 4.99 | 0 | 1534 |
| BIRD | CORE-T | 68.1 | 49.7 | 94.9 | 22.6 | 16.3 | 31.3 | 3.19 | 0 | 1534 |
| BIRD | Route+SQL | 62.6 | 45.3 | 88.1 | 60.9 | 44.1 | 85.7 | 1.87 | 9 | 1534 |
| BIRD | Full schema | 66.9 | 49.0 | 93.2 | 63.3 | 46.4 | 87.9 | 2.00 | 0 | 1534 |
| Spider | Dense k1 | 19.6 | 13.0 | 31.0 | 19.6 | 13.0 | 31.0 | 1.00 | 0 | 1034 |
| Spider | Dense k3 | 43.9 | 28.2 | 69.8 | 2.5 | 1.0 | 5.0 | 3.00 | 0 | 1034 |
| Spider | Dense k5 | 52.3 | 34.0 | 82.7 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | BM25 k1 | 24.6 | 16.1 | 37.9 | 24.6 | 16.1 | 37.9 | 1.00 | 0 | 1034 |
| Spider | BM25 k3 | 44.9 | 28.4 | 71.2 | 2.7 | 0.9 | 5.5 | 3.00 | 0 | 1034 |
| Spider | BM25 k5 | 49.3 | 31.0 | 79.3 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | Hybrid k1 | 24.6 | 16.2 | 38.5 | 24.6 | 16.2 | 38.5 | 1.00 | 0 | 1034 |
| Spider | Hybrid k3 | 48.7 | 31.1 | 77.9 | 3.0 | 0.9 | 6.4 | 3.00 | 0 | 1034 |
| Spider | Hybrid k5 | 55.0 | 35.2 | 88.6 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | JAR k1 | 33.3 | 22.7 | 51.3 | 33.3 | 22.7 | 51.3 | 1.00 | 0 | 1034 |
| Spider | JAR k3 | 52.6 | 34.5 | 83.3 | 2.9 | 1.2 | 5.7 | 3.00 | 0 | 1034 |
| Spider | JAR k5 | 55.9 | 36.4 | 89.0 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | Greedy JAR k1 | 34.1 | 22.7 | 53.9 | 34.1 | 22.7 | 53.9 | 1.00 | 0 | 1034 |
| Spider | Greedy JAR k3 | 54.2 | 35.6 | 85.4 | 2.7 | 1.2 | 4.9 | 3.00 | 0 | 1034 |
| Spider | Greedy JAR k5 | 55.9 | 36.7 | 88.4 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | MURRE k1 | 30.3 | 20.9 | 45.4 | 30.3 | 20.9 | 45.4 | 1.00 | 0 | 1034 |
| Spider | MURRE k3 | 55.4 | 37.1 | 85.8 | 3.7 | 1.7 | 6.5 | 3.00 | 0 | 1034 |
| Spider | MURRE k5 | 59.0 | 39.3 | 92.4 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | CRUSH4SQL 1 tables | 28.9 | 20.0 | 44.7 | 28.9 | 20.0 | 44.7 | 1.00 | 0 | 1034 |
| Spider | CRUSH4SQL 3 tables | 48.4 | 31.7 | 76.5 | 1.6 | 0.6 | 3.1 | 3.00 | 0 | 1034 |
| Spider | CRUSH4SQL 5 tables | 55.1 | 36.4 | 87.1 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1034 |
| Spider | CORE-T | 57.5 | 37.7 | 90.2 | 21.3 | 13.0 | 33.5 | 2.68 | 0 | 1034 |
| Spider | Route+SQL | 48.2 | 31.2 | 76.0 | 47.8 | 31.2 | 75.0 | 1.60 | 4 | 1034 |
| Spider | Full schema | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.00 | 1034 | 1034 |
| MMQA | Dense k1 | 1.2 | 0.1 | 4.3 | 1.2 | 0.1 | 4.3 | 1.00 | 0 | 1049 |
| MMQA | Dense k3 | 20.9 | 12.2 | 39.1 | 3.1 | 1.0 | 7.1 | 3.00 | 0 | 1049 |
| MMQA | Dense k5 | 29.2 | 17.1 | 55.4 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | BM25 k1 | 1.3 | 0.1 | 4.6 | 1.3 | 0.1 | 4.6 | 1.00 | 0 | 1049 |
| MMQA | BM25 k3 | 19.8 | 11.8 | 37.3 | 2.1 | 0.6 | 5.1 | 3.00 | 0 | 1049 |
| MMQA | BM25 k5 | 25.8 | 15.2 | 48.5 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | Hybrid k1 | 1.4 | 0.1 | 4.7 | 1.4 | 0.1 | 4.7 | 1.00 | 0 | 1049 |
| MMQA | Hybrid k3 | 25.6 | 15.4 | 47.8 | 4.2 | 1.4 | 9.2 | 3.00 | 0 | 1049 |
| MMQA | Hybrid k5 | 33.8 | 20.5 | 62.7 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | JAR k1 | 1.5 | 0.1 | 5.6 | 1.5 | 0.1 | 5.6 | 1.00 | 0 | 1049 |
| MMQA | JAR k3 | 27.1 | 16.0 | 50.4 | 5.2 | 1.6 | 11.9 | 3.00 | 0 | 1049 |
| MMQA | JAR k5 | 30.6 | 17.9 | 58.6 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | Greedy JAR k1 | 1.6 | 0.1 | 5.9 | 1.6 | 0.1 | 5.9 | 1.00 | 0 | 1049 |
| MMQA | Greedy JAR k3 | 27.3 | 16.0 | 51.3 | 4.8 | 1.6 | 11.1 | 3.00 | 0 | 1049 |
| MMQA | Greedy JAR k5 | 30.5 | 18.3 | 57.2 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | MURRE k1 | 1.2 | 0.0 | 4.2 | 1.2 | 0.0 | 4.2 | 1.00 | 0 | 1049 |
| MMQA | MURRE k3 | 27.3 | 16.3 | 49.8 | 4.5 | 1.9 | 9.4 | 3.00 | 0 | 1049 |
| MMQA | MURRE k5 | 32.8 | 19.8 | 59.9 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | CRUSH4SQL 1 tables | 1.0 | 0.0 | 3.8 | 1.0 | 0.0 | 3.8 | 1.00 | 0 | 1049 |
| MMQA | CRUSH4SQL 3 tables | 23.6 | 13.5 | 44.3 | 3.7 | 0.9 | 9.2 | 3.00 | 0 | 1049 |
| MMQA | CRUSH4SQL 5 tables | 30.8 | 17.7 | 59.3 | 0.0 | 0.0 | 0.0 | 5.00 | 0 | 1049 |
| MMQA | CORE-T | 42.8 | 26.4 | 78.6 | 16.5 | 10.1 | 28.0 | 3.78 | 0 | 1049 |
| MMQA | Full schema | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.00 | 1049 | 1049 |
| mean | Dense k1 | 11.1 | 6.9 | 18.4 | 11.1 | 6.9 | 18.4 |
| mean | Dense k3 | 38.5 | 25.6 | 60.3 | 4.0 | 1.4 | 8.2 |
| mean | Dense k5 | 47.6 | 31.7 | 74.7 | 0.0 | 0.0 | 0.0 |
| mean | BM25 k1 | 11.8 | 7.3 | 19.2 | 11.8 | 7.3 | 19.2 |
| mean | BM25 k3 | 33.7 | 21.9 | 53.6 | 2.7 | 0.8 | 5.9 |
| mean | BM25 k5 | 40.6 | 26.4 | 64.9 | 0.0 | 0.0 | 0.0 |
| mean | Hybrid k1 | 12.9 | 8.0 | 21.1 | 12.9 | 8.0 | 21.1 |
| mean | Hybrid k3 | 41.5 | 27.5 | 65.4 | 4.3 | 1.5 | 9.0 |
| mean | Hybrid k5 | 49.3 | 32.7 | 78.2 | 0.0 | 0.0 | 0.0 |
| mean | JAR k1 | 17.3 | 11.2 | 27.7 | 17.3 | 11.2 | 27.7 |
| mean | JAR k3 | 45.5 | 30.5 | 71.2 | 5.5 | 2.1 | 11.4 |
| mean | JAR k5 | 48.6 | 32.1 | 77.5 | 0.0 | 0.0 | 0.0 |
| mean | Greedy JAR k1 | 17.6 | 11.2 | 28.7 | 17.6 | 11.2 | 28.7 |
| mean | Greedy JAR k3 | 46.3 | 31.2 | 72.3 | 5.1 | 1.9 | 10.4 |
| mean | Greedy JAR k5 | 50.1 | 33.7 | 78.3 | 0.0 | 0.0 | 0.0 |
| mean | MURRE k1 | 15.8 | 10.4 | 24.6 | 15.8 | 10.4 | 24.6 |
| mean | MURRE k3 | 47.1 | 31.8 | 72.8 | 5.7 | 2.5 | 11.0 |
| mean | MURRE k5 | 52.2 | 35.3 | 81.1 | 0.0 | 0.0 | 0.0 |
| mean | CRUSH4SQL 1 tables | 14.7 | 9.8 | 23.3 | 14.7 | 9.8 | 23.3 |
| mean | CRUSH4SQL 3 tables | 42.1 | 28.3 | 65.7 | 4.2 | 1.5 | 8.9 |
| mean | CRUSH4SQL 5 tables | 49.2 | 33.0 | 77.6 | 0.0 | 0.0 | 0.0 |
| mean | CORE-T | 56.1 | 37.9 | 87.9 | 20.1 | 13.1 | 30.9 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | Full schema | 22.3 | 16.3 | 31.1 | 21.1 | 15.5 | 29.3 |
| worst | Dense k1 | 1.2 | 0.1 | 4.3 | 1.2 | 0.1 | 4.3 |
| worst | Dense k3 | 20.9 | 12.2 | 39.1 | 2.5 | 1.0 | 5.0 |
| worst | Dense k5 | 29.2 | 17.1 | 55.4 | 0.0 | 0.0 | 0.0 |
| worst | BM25 k1 | 1.3 | 0.1 | 4.6 | 1.3 | 0.1 | 4.6 |
| worst | BM25 k3 | 19.8 | 11.8 | 37.3 | 2.1 | 0.6 | 5.1 |
| worst | BM25 k5 | 25.8 | 15.2 | 48.5 | 0.0 | 0.0 | 0.0 |
| worst | Hybrid k1 | 1.4 | 0.1 | 4.7 | 1.4 | 0.1 | 4.7 |
| worst | Hybrid k3 | 25.6 | 15.4 | 47.8 | 3.0 | 0.9 | 6.4 |
| worst | Hybrid k5 | 33.8 | 20.5 | 62.7 | 0.0 | 0.0 | 0.0 |
| worst | JAR k1 | 1.5 | 0.1 | 5.6 | 1.5 | 0.1 | 5.6 |
| worst | JAR k3 | 27.1 | 16.0 | 50.4 | 2.9 | 1.2 | 5.7 |
| worst | JAR k5 | 30.6 | 17.9 | 58.6 | 0.0 | 0.0 | 0.0 |
| worst | Greedy JAR k1 | 1.6 | 0.1 | 5.9 | 1.6 | 0.1 | 5.9 |
| worst | Greedy JAR k3 | 27.3 | 16.0 | 51.3 | 2.7 | 1.2 | 4.9 |
| worst | Greedy JAR k5 | 30.5 | 18.3 | 57.2 | 0.0 | 0.0 | 0.0 |
| worst | MURRE k1 | 1.2 | 0.0 | 4.2 | 1.2 | 0.0 | 4.2 |
| worst | MURRE k3 | 27.3 | 16.3 | 49.8 | 3.7 | 1.7 | 6.5 |
| worst | MURRE k5 | 32.8 | 19.8 | 59.9 | 0.0 | 0.0 | 0.0 |
| worst | CRUSH4SQL 1 tables | 1.0 | 0.0 | 3.8 | 1.0 | 0.0 | 3.8 |
| worst | CRUSH4SQL 3 tables | 23.6 | 13.5 | 44.3 | 1.6 | 0.6 | 3.1 |
| worst | CRUSH4SQL 5 tables | 30.8 | 17.7 | 59.3 | 0.0 | 0.0 | 0.0 |
| worst | CORE-T | 42.8 | 26.4 | 78.6 | 16.5 | 10.1 | 28.0 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | Full schema | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Multi-valid label, ambiguous questions only (two or more retrieval targets)

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | sets | tables | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 31.0 | 0.0 | 75.7 | 8.5 | 0.0 | 21.2 | 1.00 | 3.00 | 725 |
| BIRD | MURRE k3 | 35.1 | 0.0 | 86.3 | 10.5 | 0.0 | 27.9 | 1.00 | 3.00 | 725 |
| BIRD | CORE-T | 39.0 | 0.0 | 95.7 | 13.4 | 0.0 | 31.7 | 1.00 | 3.52 | 725 |
| BIRD | Route+SQL | 36.7 | 0.0 | 90.5 | 35.7 | 0.0 | 88.1 | 1.00 | 1.84 | 725 |
| BIRD | AMIGO top-1 | 34.9 | 0.0 | 85.2 | 33.1 | 0.0 | 80.7 | 1.00 | 1.91 | 725 |
| BIRD | AMIGO | 48.9 | 15.7 | 85.4 | 45.6 | 13.4 | 79.8 | 1.54 | 2.30 | 725 |
| Spider | Dense k3 | 27.3 | 0.0 | 72.6 | 2.7 | 0.0 | 7.1 | 1.00 | 3.00 | 592 |
| Spider | MURRE k3 | 32.0 | 0.0 | 85.0 | 3.4 | 0.0 | 8.3 | 1.00 | 3.00 | 592 |
| Spider | CORE-T | 34.6 | 0.0 | 91.7 | 14.6 | 0.0 | 35.8 | 1.00 | 2.86 | 592 |
| Spider | Route+SQL | 29.5 | 0.0 | 78.2 | 28.9 | 0.0 | 76.4 | 1.00 | 1.62 | 592 |
| Spider | AMIGO top-1 | 34.7 | 0.0 | 92.4 | 33.4 | 0.0 | 89.4 | 1.00 | 1.52 | 592 |
| Spider | AMIGO | 50.9 | 14.7 | 89.0 | 49.1 | 13.5 | 85.8 | 2.03 | 2.55 | 592 |
| MMQA | Dense k3 | 12.9 | 0.0 | 39.9 | 3.3 | 0.0 | 9.2 | 1.00 | 3.00 | 706 |
| MMQA | MURRE k3 | 16.3 | 0.0 | 49.7 | 3.9 | 0.0 | 11.2 | 1.00 | 3.00 | 706 |
| MMQA | CORE-T | 24.4 | 0.0 | 77.5 | 9.5 | 0.0 | 26.6 | 1.00 | 3.97 | 706 |
| MMQA | AMIGO top-1 | 22.5 | 0.0 | 70.7 | 19.3 | 0.0 | 58.4 | 1.00 | 2.73 | 706 |
| MMQA | AMIGO | 39.0 | 11.0 | 64.9 | 30.0 | 8.4 | 51.0 | 4.76 | 5.69 | 706 |
| mean | Dense k3 | 23.7 | 0.0 | 62.8 | 4.8 | 0.0 | 12.5 |
| mean | MURRE k3 | 27.8 | 0.0 | 73.7 | 5.9 | 0.0 | 15.8 |
| mean | CORE-T | 32.7 | 0.0 | 88.3 | 12.5 | 0.0 | 31.4 |
| mean | Route+SQL | ran on 2 of 3 lakes |
| mean | AMIGO top-1 | 30.7 | 0.0 | 82.8 | 28.6 | 0.0 | 76.1 |
| mean | AMIGO | 46.3 | 13.8 | 79.8 | 41.6 | 11.7 | 72.2 |
| worst | Dense k3 | 12.9 | 0.0 | 39.9 | 2.7 | 0.0 | 7.1 |
| worst | MURRE k3 | 16.3 | 0.0 | 49.7 | 3.4 | 0.0 | 8.3 |
| worst | CORE-T | 24.4 | 0.0 | 77.5 | 9.5 | 0.0 | 26.6 |
| worst | Route+SQL | ran on 2 of 3 lakes |
| worst | AMIGO top-1 | 22.5 | 0.0 | 70.7 | 19.3 | 0.0 | 58.4 |
| worst | AMIGO | 39.0 | 11.0 | 64.9 | 30.0 | 8.4 | 51.0 |

## Pooled P on the gold label (a lower bound)

| lake | method | pooled P | n |
|---|---|---|---|
| BIRD | Dense k3 | 51.8 | 1534 |
| BIRD | MURRE k3 | 56.1 | 1534 |
| BIRD | CORE-T | 62.8 | 1534 |
| BIRD | Route+SQL | 90.7 | 1534 |
| BIRD | AMIGO top-1 | 92.1 | 1534 |
| BIRD | AMIGO | 88.4 | 1534 |
| Spider | Dense k3 | 37.1 | 1034 |
| Spider | MURRE k3 | 42.3 | 1034 |
| Spider | CORE-T | 57.4 | 1034 |
| Spider | Route+SQL | 68.0 | 1034 |
| Spider | AMIGO top-1 | 87.2 | 1034 |
| Spider | AMIGO | 82.1 | 1034 |
| MMQA | Dense k3 | 42.8 | 1049 |
| MMQA | MURRE k3 | 45.2 | 1049 |
| MMQA | CORE-T | 58.1 | 1049 |
| MMQA | AMIGO top-1 | 78.2 | 1049 |
| MMQA | AMIGO | 68.2 | 1049 |

## Run-to-run check, 150 BIRD questions (gold: R, CR, P, CR=; multi-valid: IR, ICR, IP, IR=, ICR=, IP=)

| label | run | scores | sets | tables | n |
|---|---|---|---|---|---|
| gold label | AMIGO-WJ, first run | 95.7 / 91.3 / 91.5 / 76.7 | 1.11 | 2.09 | 150 |
| gold label | AMIGO-WJ, second run (empty cache) | 96.4 / 92.7 / 91.1 / 76.0 | 1.10 | 2.11 | 150 |
| multi-valid label | AMIGO-WJ, first run | 71.9 / 55.3 / 93.2 / 66.2 / 50.7 / 86.5 | 1.11 | 2.09 | 150 |
| multi-valid label | AMIGO-WJ, second run (empty cache) | 71.8 / 54.0 / 94.3 / 66.2 / 49.3 / 87.3 | 1.10 | 2.11 | 150 |

Same table sets in the same order: 125 of 150; same table sets in any order: 125 of 150.

## Time per question (idle GPU) and LLM calls per question

| lake | timed | split s | lookups s | place judge s | search s | join choice s | total mean s | total median s | questions | with a join choice call | LLM calls per question |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | 30 | 9.9 | 5.8 | 30.6 | 0.0 | 0.3 | 46.6 | 41.4 | 1534 | 214 | 2.2 |
| Spider | 30 | 6.9 | 1.6 | 32.4 | 0.0 | 0.5 | 41.5 | 40.9 | 1034 | 82 | 2.1 |
| MMQA | 30 | 9.7 | 1.9 | 47.3 | 0.5 | 1.3 | 60.7 | 49.3 | 1105 | 166 | 2.3 |

## Stage 1 on all questions and on the questions stage 2 keeps

| lake | label | method | R all | R kept | CR all | CR kept | P all | P kept | n all | n kept |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | gold label | Dense k3 | 83.1 | 83.2 | 68.6 | 68.8 | 51.8 | 51.8 | 1534 | 1527 |
| BIRD | gold label | MURRE k3 | 89.0 | 89.1 | 78.7 | 78.8 | 56.1 | 56.1 | 1534 | 1527 |
| BIRD | gold label | CORE-T | 96.5 | 96.4 | 92.9 | 92.9 | 62.8 | 62.9 | 1534 | 1527 |
| BIRD | gold label | Route+SQL | 88.7 | 88.7 | 81.5 | 81.5 | 90.7 | 90.7 | 1534 | 1527 |
| BIRD | gold label | AMIGO top-1 | 89.1 | 89.1 | 77.6 | 77.7 | 92.1 | 92.1 | 1534 | 1527 |
| BIRD | gold label | AMIGO | 95.6 | 95.6 | 90.4 | 90.4 | 93.7 | 93.7 | 1534 | 1527 |
| BIRD | multi-valid label | Dense k3 | 80.1 | 80.1 | 61.9 | 62.0 | 53.6 | 53.6 | 1534 | 1533 |
| BIRD | multi-valid label | MURRE k3 | 85.6 | 85.6 | 70.8 | 70.7 | 57.7 | 57.7 | 1534 | 1533 |
| BIRD | multi-valid label | CORE-T | 93.0 | 93.0 | 85.3 | 85.3 | 64.3 | 64.3 | 1534 | 1533 |
| BIRD | multi-valid label | Route+SQL | 81.5 | 81.5 | 65.4 | 65.3 | 88.6 | 88.5 | 1534 | 1533 |
| BIRD | multi-valid label | AMIGO top-1 | 82.6 | 82.6 | 64.4 | 64.4 | 90.5 | 90.5 | 1534 | 1533 |
| BIRD | multi-valid label | AMIGO | 89.5 | 89.5 | 77.1 | 77.0 | 92.2 | 92.2 | 1534 | 1533 |
| Spider | gold label | Dense k3 | 73.5 | 74.0 | 63.9 | 65.1 | 37.1 | 37.2 | 1034 | 985 |
| Spider | gold label | MURRE k3 | 85.1 | 85.5 | 79.3 | 80.1 | 42.3 | 42.3 | 1034 | 985 |
| Spider | gold label | CORE-T | 89.3 | 89.7 | 84.9 | 85.4 | 57.4 | 57.2 | 1034 | 985 |
| Spider | gold label | Route+SQL | 68.1 | 69.8 | 67.4 | 69.1 | 68.0 | 69.8 | 1034 | 985 |
| Spider | gold label | AMIGO top-1 | 87.2 | 88.0 | 84.6 | 85.4 | 87.2 | 87.9 | 1034 | 985 |
| Spider | gold label | AMIGO | 96.1 | 96.5 | 95.1 | 95.5 | 95.3 | 95.7 | 1034 | 985 |
| Spider | multi-valid label | Dense k3 | 61.8 | 61.9 | 51.8 | 52.3 | 32.5 | 32.4 | 1034 | 1000 |
| Spider | multi-valid label | MURRE k3 | 72.5 | 72.4 | 65.4 | 65.2 | 37.4 | 37.2 | 1034 | 1000 |
| Spider | multi-valid label | CORE-T | 73.0 | 72.5 | 67.4 | 67.0 | 48.5 | 48.0 | 1034 | 1000 |
| Spider | multi-valid label | Route+SQL | 54.8 | 55.4 | 50.2 | 50.7 | 56.8 | 57.6 | 1034 | 1000 |
| Spider | multi-valid label | AMIGO top-1 | 68.1 | 67.7 | 62.4 | 61.9 | 70.3 | 70.0 | 1034 | 1000 |
| Spider | multi-valid label | AMIGO | 76.7 | 76.2 | 73.0 | 72.3 | 77.6 | 77.2 | 1034 | 1000 |
| MMQA | gold label | Dense k3 | 59.0 | 59.1 | 31.4 | 31.3 | 42.8 | 42.8 | 1049 | 965 |
| MMQA | gold label | MURRE k3 | 62.6 | 62.3 | 41.3 | 40.8 | 45.2 | 44.9 | 1049 | 965 |
| MMQA | gold label | CORE-T | 84.1 | 84.4 | 70.6 | 71.2 | 58.1 | 58.2 | 1049 | 965 |
| MMQA | gold label | AMIGO top-1 | 78.0 | 78.7 | 62.2 | 63.4 | 78.2 | 78.8 | 1049 | 965 |
| MMQA | gold label | AMIGO | 87.9 | 88.5 | 76.7 | 77.8 | 83.0 | 83.5 | 1049 | 965 |
| MMQA | multi-valid label | Dense k3 | 54.3 | 54.0 | 24.0 | 23.2 | 42.4 | 42.3 | 1049 | 993 |
| MMQA | multi-valid label | MURRE k3 | 58.0 | 57.6 | 31.6 | 30.7 | 44.8 | 44.8 | 1049 | 993 |
| MMQA | multi-valid label | CORE-T | 76.8 | 76.5 | 53.8 | 52.8 | 56.6 | 56.5 | 1049 | 993 |
| MMQA | multi-valid label | AMIGO top-1 | 68.9 | 68.6 | 42.0 | 41.3 | 74.2 | 74.4 | 1049 | 993 |
| MMQA | multi-valid label | AMIGO | 78.9 | 78.5 | 55.3 | 54.5 | 79.4 | 79.4 | 1049 | 993 |

Largest change of CR: 1.73 points.

## Building AMIGO's layer (baselines' preparation left out)

| lake | seconds | minutes | LLM calls | input tokens | output tokens | LLM calls by step |
|---|---|---|---|---|---|---|
| BIRD | 1603.0 | 26.7 | 258 | 321567 | 210969 | describe 75, names 1, index 1, judged_links 180, embed 1 |
| Spider | 1627.8 | 27.1 | 1079 | 628011 | 889816 | describe 872, names 1, index 1, judged_links 205 |
| MMQA | 2410.4 | 40.2 | 1602 | 1684993 | 1334557 | describe 709, names 1, index 1, judged_links 890, embed 1 |

