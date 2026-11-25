# Answers to review rounds 1 to 3 (stage 1 of docs/eval_protocol.md, no LLM call)

Scored with experiments/protocol.py on existing outputs. Gold label: R, CR, P, CR= per target against its matched set; multi-valid label: IR, ICR, IP and their strict forms IR=, ICR=, IP= from a one-to-one pairing (paper Section 4.1). Averaged per question, then over questions. size: mean tables per returned set, per question, then over the questions with a set.

## AMIGO cut to its first m table sets, gold label

| lake | cut | R | CR | P | CR= | sets | size |
|---|---|---|---|---|---|---|---|
| BIRD | first 1 | 89.1 | 77.6 | 92.1 | 66.9 | 1.00 | 1.88 |
| BIRD | first 2 | 94.9 | 88.5 | 93.6 | 78.1 | 1.33 | 1.95 |
| BIRD | first 3 | 95.4 | 89.8 | 93.7 | 79.4 | 1.39 | 1.95 |
| BIRD | first 5 | 95.6 | 90.4 | 93.7 | 79.9 | 1.43 | 1.96 |
| BIRD | first 10 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 |
| BIRD | all (AMIGO) | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 |
| Spider | first 1 | 87.2 | 84.6 | 87.2 | 80.3 | 1.00 | 1.50 |
| Spider | first 2 | 93.3 | 92.2 | 92.6 | 88.7 | 1.30 | 1.52 |
| Spider | first 3 | 94.5 | 93.5 | 93.8 | 90.1 | 1.44 | 1.54 |
| Spider | first 5 | 95.3 | 94.3 | 94.6 | 90.9 | 1.56 | 1.54 |
| Spider | first 10 | 95.9 | 94.9 | 95.1 | 91.5 | 1.65 | 1.54 |
| Spider | all (AMIGO) | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 |
| MMQA | first 1 | 78.0 | 62.2 | 78.2 | 51.5 | 1.00 | 2.62 |
| MMQA | first 2 | 83.6 | 71.2 | 80.3 | 59.1 | 1.45 | 2.78 |
| MMQA | first 3 | 84.8 | 72.3 | 81.1 | 60.1 | 1.69 | 2.85 |
| MMQA | first 5 | 86.0 | 73.8 | 82.0 | 61.1 | 2.06 | 2.92 |
| MMQA | first 10 | 87.0 | 75.6 | 82.6 | 62.2 | 2.71 | 3.01 |
| MMQA | all (AMIGO) | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 3.11 |
| mean | first 1 | 84.8 | 74.8 | 85.8 | 66.2 | 1.00 | 2.00 |
| mean | first 2 | 90.6 | 84.0 | 88.8 | 75.3 | 1.36 | 2.08 |
| mean | first 3 | 91.6 | 85.2 | 89.5 | 76.5 | 1.50 | 2.11 |
| mean | first 5 | 92.3 | 86.1 | 90.1 | 77.3 | 1.68 | 2.14 |
| mean | first 10 | 92.8 | 87.0 | 90.5 | 77.9 | 1.93 | 2.17 |
| mean | all (AMIGO) | 93.2 | 87.4 | 90.7 | 78.1 | 2.44 | 2.20 |
| worst | first 1 | 78.0 | 62.2 | 78.2 | 51.5 | 1.00 | 2.62 |
| worst | first 2 | 83.6 | 71.2 | 80.3 | 59.1 | 1.45 | 2.78 |
| worst | first 3 | 84.8 | 72.3 | 81.1 | 60.1 | 1.69 | 2.85 |
| worst | first 5 | 86.0 | 73.8 | 82.0 | 61.1 | 2.06 | 2.92 |
| worst | first 10 | 87.0 | 75.6 | 82.6 | 62.2 | 2.71 | 3.01 |
| worst | all (AMIGO) | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 3.11 |

## AMIGO cut to its first m table sets, multi-valid label

| lake | cut | IR | ICR | IP | IR= | ICR= | IP= | sets | size |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | first 1 | 60.0 | 43.5 | 83.8 | 56.0 | 40.4 | 78.6 | 1.00 | 1.88 |
| BIRD | first 2 | 71.3 | 55.4 | 83.5 | 66.6 | 51.2 | 78.0 | 1.33 | 1.95 |
| BIRD | first 3 | 72.5 | 56.6 | 83.4 | 67.6 | 52.3 | 77.8 | 1.39 | 1.95 |
| BIRD | first 5 | 73.0 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.43 | 1.96 |
| BIRD | first 10 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 |
| BIRD | all (AMIGO) | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 |
| Spider | first 1 | 59.6 | 39.7 | 92.6 | 58.7 | 39.6 | 90.7 | 1.00 | 1.50 |
| Spider | first 2 | 67.0 | 46.5 | 91.0 | 65.9 | 46.0 | 89.1 | 1.30 | 1.52 |
| Spider | first 3 | 68.9 | 48.5 | 90.0 | 67.6 | 47.7 | 88.1 | 1.44 | 1.54 |
| Spider | first 5 | 70.1 | 49.2 | 89.7 | 68.7 | 48.3 | 87.7 | 1.56 | 1.54 |
| Spider | first 10 | 70.6 | 50.0 | 89.6 | 69.3 | 49.0 | 87.6 | 1.65 | 1.54 |
| Spider | all (AMIGO) | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 |
| MMQA | first 1 | 38.9 | 23.7 | 71.3 | 34.1 | 21.2 | 60.4 | 1.00 | 2.62 |
| MMQA | first 2 | 47.6 | 30.7 | 70.3 | 40.7 | 26.6 | 58.0 | 1.45 | 2.78 |
| MMQA | first 3 | 49.4 | 32.7 | 68.9 | 41.8 | 27.6 | 56.5 | 1.69 | 2.85 |
| MMQA | first 5 | 50.9 | 33.3 | 67.4 | 42.8 | 28.5 | 55.3 | 2.06 | 2.92 |
| MMQA | first 10 | 52.3 | 34.2 | 66.3 | 43.7 | 29.3 | 54.5 | 2.71 | 3.01 |
| MMQA | all (AMIGO) | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 3.11 |
| mean | first 1 | 52.8 | 35.7 | 82.6 | 49.6 | 33.7 | 76.6 | 1.00 | 2.00 |
| mean | first 2 | 62.0 | 44.2 | 81.6 | 57.7 | 41.3 | 75.0 | 1.36 | 2.08 |
| mean | first 3 | 63.6 | 45.9 | 80.8 | 59.0 | 42.5 | 74.1 | 1.50 | 2.11 |
| mean | first 5 | 64.7 | 46.6 | 80.1 | 59.9 | 43.3 | 73.5 | 1.68 | 2.14 |
| mean | first 10 | 65.3 | 47.2 | 79.7 | 60.4 | 43.8 | 73.3 | 1.93 | 2.17 |
| mean | all (AMIGO) | 65.7 | 47.3 | 79.5 | 60.6 | 43.8 | 73.1 | 2.44 | 2.20 |
| worst | first 1 | 38.9 | 23.7 | 71.3 | 34.1 | 21.2 | 60.4 | 1.00 | 2.62 |
| worst | first 2 | 47.6 | 30.7 | 70.3 | 40.7 | 26.6 | 58.0 | 1.45 | 2.78 |
| worst | first 3 | 49.4 | 32.7 | 68.9 | 41.8 | 27.6 | 56.5 | 1.69 | 2.85 |
| worst | first 5 | 50.9 | 33.3 | 67.4 | 42.8 | 28.5 | 55.3 | 2.06 | 2.92 |
| worst | first 10 | 52.3 | 34.2 | 66.3 | 43.7 | 29.3 | 54.5 | 2.71 | 3.01 |
| worst | all (AMIGO) | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 3.11 |

## Judges at equal size: each variant cut per question to AMIGO's number of table sets, gold label

| lake | variant | R full | CR full | P full | CR= full | sets full | R cut | CR cut | P cut | CR= cut | sets cut | R AMIGO | CR AMIGO | P AMIGO | CR= AMIGO | sets AMIGO | AMIGO - cut CR | Holm p CR | AMIGO - cut P | Holm p P | AMIGO - cut CR= | Holm p CR= |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | no judge at all | 94.6 | 89.7 | 95.5 | 84.5 | 4.48 | 80.6 | 64.7 | 89.9 | 59.1 | 1.40 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 25.7 | 0.0000 | 3.8 | 0.0000 | 21.0 | 0.0000 |
| BIRD | place judge only (no join choice) | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 |
| Spider | no judge at all | 93.4 | 92.6 | 93.2 | 91.0 | 6.64 | 76.6 | 71.6 | 80.9 | 69.8 | 1.66 | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 23.5 | 0.0000 | 14.5 | 0.0000 | 21.9 | 0.0000 |
| Spider | place judge only (no join choice) | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 |
| MMQA | no judge at all | 85.3 | 74.7 | 88.4 | 67.2 | 7.61 | 71.3 | 52.9 | 80.8 | 47.2 | 2.92 | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 23.8 | 0.0000 | 2.2 | 0.1560 | 15.3 | 0.0000 |
| MMQA | place judge only (no join choice) | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 |

## Judges at equal size: each variant cut per question to AMIGO's number of table sets, multi-valid label

| lake | variant | IR full | ICR full | IP full | IR= full | ICR= full | IP= full | sets full | IR cut | ICR cut | IP cut | IR= cut | ICR= cut | IP= cut | sets cut | IR AMIGO | ICR AMIGO | IP AMIGO | IR= AMIGO | ICR= AMIGO | IP= AMIGO | sets AMIGO | AMIGO - cut ICR | Holm p ICR | AMIGO - cut IP | Holm p IP | AMIGO - cut IR= | Holm p IR= | AMIGO - cut ICR= | Holm p ICR= | AMIGO - cut IP= | Holm p IP= |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | no judge at all | 80.6 | 69.1 | 39.2 | 76.2 | 63.3 | 37.3 | 4.48 | 52.1 | 40.2 | 59.2 | 49.3 | 37.5 | 56.3 | 1.40 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 17.2 | 0.0000 | 24.0 | 0.0000 | 19.0 | 0.0000 | 15.6 | 0.0000 | 21.4 | 0.0000 |
| BIRD | place judge only (no join choice) | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 |
| Spider | no judge at all | 78.2 | 60.6 | 33.5 | 76.1 | 57.8 | 32.4 | 6.64 | 53.8 | 37.5 | 66.9 | 53.1 | 36.8 | 66.0 | 1.66 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 12.5 | 0.0000 | 22.7 | 0.0000 | 16.4 | 0.0000 | 12.2 | 0.0000 | 21.5 | 0.0000 |
| Spider | place judge only (no join choice) | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 |
| MMQA | no judge at all | 56.3 | 38.2 | 29.3 | 50.7 | 34.2 | 26.4 | 7.61 | 36.5 | 23.0 | 46.1 | 33.4 | 20.8 | 42.7 | 2.92 | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 11.5 | 0.0000 | 19.5 | 0.0000 | 10.5 | 0.0000 | 8.6 | 0.0000 | 11.3 | 0.0000 |
| MMQA | place judge only (no join choice) | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 | 0.0 | 1.0000 |

## Judges at equal size, mean and worst over the three benchmarks, gold label (R not tested)

| over | variant | R | CR | P | CR= |
|---|---|---|---|---|---|
| mean | AMIGO | 93.2 | 87.4 | 90.7 | 78.1 |
| worst | AMIGO | 87.9 | 76.7 | 83.0 | 62.5 |
| mean | no judge at all, cut | 76.2 | 63.0 | 83.9 | 58.7 |
| worst | no judge at all, cut | 71.3 | 52.9 | 80.8 | 47.2 |
| mean | place judge only (no join choice), cut | 93.2 | 87.4 | 90.7 | 78.1 |
| worst | place judge only (no join choice), cut | 87.9 | 76.7 | 83.0 | 62.5 |

## Judges at equal size, mean and worst over the three benchmarks, multi-valid label (IR not tested)

| over | variant | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|---|
| mean | AMIGO | 65.7 | 47.3 | 79.5 | 60.6 | 43.8 | 73.1 |
| worst | AMIGO | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 |
| mean | no judge at all, cut | 47.5 | 33.6 | 57.4 | 45.3 | 31.7 | 55.0 |
| worst | no judge at all, cut | 36.5 | 23.0 | 46.1 | 33.4 | 20.8 | 42.7 |
| mean | place judge only (no join choice), cut | 65.7 | 47.3 | 79.5 | 60.6 | 43.8 | 73.1 |
| worst | place judge only (no join choice), cut | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 |

## Relaxed candidates in AMIGO (place judge + join choice), gold label

| lake | questions | with relaxed | only relaxed | only relaxed, a target found | R | R without | CR | CR without | P | P without | CR= | CR= without | length mismatch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | 1534 | 183 | 183 | 146 | 95.6 | 84.9 | 90.4 | 80.9 | 93.7 | 82.7 | 80.1 | 71.5 | 0 |
| Spider | 1034 | 70 | 70 | 55 | 96.1 | 90.2 | 95.1 | 89.7 | 95.3 | 89.0 | 91.7 | 86.6 | 0 |
| MMQA | 1049 | 120 | 120 | 49 | 87.9 | 80.0 | 76.7 | 72.1 | 83.0 | 73.6 | 62.5 | 59.0 | 0 |

## Relaxed candidates in AMIGO (place judge + join choice), multi-valid label

| lake | questions | with relaxed | only relaxed | only relaxed, a target found | IR | IR without | ICR | ICR without | IP | IP without | IR= | IR= without | ICR= | ICR= without | IP= | IP= without | length mismatch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | 1534 | 183 | 183 | 157 | 73.1 | 65.1 | 57.4 | 51.0 | 83.2 | 74.0 | 68.3 | 60.8 | 53.1 | 47.2 | 77.7 | 69.2 | 0 |
| Spider | 1034 | 70 | 70 | 57 | 70.7 | 66.7 | 50.0 | 47.0 | 89.6 | 84.9 | 69.4 | 65.5 | 49.0 | 46.1 | 87.6 | 83.1 | 0 |
| MMQA | 1049 | 120 | 120 | 51 | 53.3 | 50.0 | 34.5 | 32.2 | 65.6 | 61.6 | 43.9 | 41.1 | 29.4 | 27.3 | 54.0 | 50.7 | 0 |

## Candidates that hold all tables of a labeled table set, by cost above the best candidate

| lake | label | cost above best | candidates | share holding a labeled table set (%) |
|---|---|---|---|---|
| BIRD | gold label | best (cost above best 0) | 1866 | 81.0 |
| BIRD | gold label | above best by (0, 1] bit | 602 | 64.3 |
| BIRD | gold label | by (1, 2] bits | 543 | 70.2 |
| BIRD | gold label | by (2, 4] bits | 633 | 71.4 |
| BIRD | gold label | by more than 4 bits | 238 | 82.8 |
| BIRD | multi-valid label | best (cost above best 0) | 1866 | 86.3 |
| BIRD | multi-valid label | above best by (0, 1] bit | 602 | 72.4 |
| BIRD | multi-valid label | by (1, 2] bits | 543 | 75.7 |
| BIRD | multi-valid label | by (2, 4] bits | 633 | 76.9 |
| BIRD | multi-valid label | by more than 4 bits | 238 | 87.4 |
| Spider | gold label | best (cost above best 0) | 1089 | 84.5 |
| Spider | gold label | above best by (0, 1] bit | 289 | 51.6 |
| Spider | gold label | by (1, 2] bits | 275 | 37.8 |
| Spider | gold label | by (2, 4] bits | 420 | 35.7 |
| Spider | gold label | by more than 4 bits | 221 | 34.4 |
| Spider | multi-valid label | best (cost above best 0) | 1089 | 92.6 |
| Spider | multi-valid label | above best by (0, 1] bit | 289 | 77.9 |
| Spider | multi-valid label | by (1, 2] bits | 275 | 68.0 |
| Spider | multi-valid label | by (2, 4] bits | 420 | 64.8 |
| Spider | multi-valid label | by more than 4 bits | 221 | 56.1 |
| MMQA | gold label | best (cost above best 0) | 1106 | 62.7 |
| MMQA | gold label | above best by (0, 1] bit | 483 | 42.7 |
| MMQA | gold label | by (1, 2] bits | 595 | 32.6 |
| MMQA | gold label | by (2, 4] bits | 1583 | 28.5 |
| MMQA | gold label | by more than 4 bits | 4166 | 29.4 |
| MMQA | multi-valid label | best (cost above best 0) | 1106 | 71.8 |
| MMQA | multi-valid label | above best by (0, 1] bit | 483 | 60.7 |
| MMQA | multi-valid label | by (1, 2] bits | 595 | 47.2 |
| MMQA | multi-valid label | by (2, 4] bits | 1583 | 44.9 |
| MMQA | multi-valid label | by more than 4 bits | 4166 | 44.5 |

## Multi-valid label: alternative queries by kind, and questions with two or more valid queries

| lake | questions | alternative queries | by kind | 2+ (%) | 2+ without copies (%) | 2+ without same-name tables (%) | 2+ without either (%) | 2+ without same-row alternatives (%) |
|---|---|---|---|---|---|---|---|---|
| BIRD | 1534 | 2631 | same table 863, new tables all share a name with an original table 0, other table 1726, other database 42 | 64.47 | 64.47 | 64.47 | 64.47 | 47.13 |
| Spider | 1034 | 1627 | other database 1129, new tables all share a name with an original table 199, other table 381, copy 16, same table 101 | 61.22 | 61.03 | 58.12 | 58.12 | 50.87 |
| MMQA | 1049 | 2922 | other table 2812, new tables all share a name with an original table 747, same table 110 | 70.54 | 70.54 | 64.82 | 64.82 | 57.96 |

## MMQA database as released (benchmarks/MMQA/databases/mmqa/mmqa.sqlite)

- tables: 710
- declared foreign keys: 0
- groups of tables sharing a base name: 76
- tables in those groups: 262
- largest groups: {'customers': 17, 'products': 11, 'people': 10, 'addresses': 10, 'department': 7}

## Output tokens per question over all questions (a measure of the size of each LLM step)

| lake | place judge output tokens | join choice output tokens |
|---|---|---|
| BIRD | 2273 | 59 |
| Spider | 2723 | 39 |
| MMQA | 3831 | 113 |

## AMIGO with hints minus AMIGO, EX (from sql_<writer>.md)

| writer | label | lake | difference |
|---|---|---|---|
| Qwen3.8-27B | gold label | BIRD | +0.9 [+0.3, +1.6]* |
| Qwen3.8-27B | gold label | Spider | +0.1 [-0.4, +0.6] |
| Qwen3.8-27B | gold label | MMQA | +0.2 [-0.7, +1.1] |
| Qwen3.8-27B | multi-valid label | BIRD | +1.4 [+0.8, +2.0]* |
| Qwen3.8-27B | multi-valid label | Spider | +0.4 [+0.0, +0.8]* |
| Qwen3.8-27B | multi-valid label | MMQA | +0.8 [+0.1, +1.5]* |
| Granite 4.2 8B | gold label | BIRD | +1.6 [+0.9, +2.4]* |
| Granite 4.2 8B | gold label | Spider | +0.7 [+0.0, +1.4] |
| Granite 4.2 8B | gold label | MMQA | +1.2 [+0.2, +2.3]* |
| Granite 4.2 8B | multi-valid label | BIRD | +1.5 [+0.9, +2.1]* |
| Granite 4.2 8B | multi-valid label | Spider | +0.5 [-0.0, +1.0] |
| Granite 4.2 8B | multi-valid label | MMQA | +1.2 [+0.4, +2.2]* |
| Gemma 4 E4B | gold label | BIRD | +1.1 [+0.5, +1.8]* |
| Gemma 4 E4B | gold label | Spider | +0.3 [-0.2, +0.8] |
| Gemma 4 E4B | gold label | MMQA | +0.7 [-0.1, +1.7] |
| Gemma 4 E4B | multi-valid label | BIRD | +1.1 [+0.6, +1.6]* |
| Gemma 4 E4B | multi-valid label | Spider | +0.2 [-0.1, +0.5] |
| Gemma 4 E4B | multi-valid label | MMQA | +0.8 [+0.3, +1.3]* |

Hints higher in 18 of 18; significant (*) in 11.

## Main writer: failed queries and questions in result P

| lake | label | method | failed | questions in result P | questions |
|---|---|---|---|---|---|
| BIRD | gold label | Gold-table oracle | 1.2% | -- | 1527 |
| BIRD | gold label | Dense k3 | 13.4% | -- | 1527 |
| BIRD | gold label | MURRE k3 | 6.7% | -- | 1527 |
| BIRD | gold label | CORE-T | 3.6% | -- | 1527 |
| BIRD | gold label | Route+SQL | 1.5% | -- | 1527 |
| BIRD | gold label | AMIGO top-1 | 4.8% | -- | 1527 |
| BIRD | gold label | AMIGO | 6.6% | -- | 1527 |
| BIRD | gold label | AMIGO with hints | 5.7% | -- | 1527 |
| Spider | gold label | Gold-table oracle | 0.7% | -- | 985 |
| Spider | gold label | Dense k3 | 7.0% | -- | 985 |
| Spider | gold label | MURRE k3 | 2.3% | -- | 985 |
| Spider | gold label | CORE-T | 2.1% | -- | 985 |
| Spider | gold label | Route+SQL | 4.6% | -- | 985 |
| Spider | gold label | AMIGO top-1 | 1.4% | -- | 985 |
| Spider | gold label | AMIGO | 2.1% | -- | 985 |
| Spider | gold label | AMIGO with hints | 2.2% | -- | 985 |
| MMQA | gold label | Gold-table oracle | 0.4% | -- | 965 |
| MMQA | gold label | Dense k3 | 12.4% | -- | 965 |
| MMQA | gold label | MURRE k3 | 6.5% | -- | 965 |
| MMQA | gold label | CORE-T | 3.9% | -- | 965 |
| MMQA | gold label | AMIGO top-1 | 3.4% | -- | 965 |
| MMQA | gold label | AMIGO | 3.2% | -- | 965 |
| MMQA | gold label | AMIGO with hints | 3.1% | -- | 965 |
| BIRD | multi-valid label | Gold-table oracle | 2.1% | 1519 | 1533 |
| BIRD | multi-valid label | Dense k3 | 13.4% | 1327 | 1533 |
| BIRD | multi-valid label | MURRE k3 | 6.8% | 1428 | 1533 |
| BIRD | multi-valid label | CORE-T | 3.6% | 1478 | 1533 |
| BIRD | multi-valid label | Route+SQL | 1.6% | 1500 | 1533 |
| BIRD | multi-valid label | AMIGO top-1 | 4.9% | 1458 | 1533 |
| BIRD | multi-valid label | AMIGO | 6.7% | 1510 | 1533 |
| BIRD | multi-valid label | AMIGO with hints | 5.7% | 1511 | 1533 |
| Spider | multi-valid label | Gold-table oracle | 1.4% | 996 | 1000 |
| Spider | multi-valid label | Dense k3 | 7.1% | 929 | 1000 |
| Spider | multi-valid label | MURRE k3 | 2.3% | 977 | 1000 |
| Spider | multi-valid label | CORE-T | 2.1% | 979 | 1000 |
| Spider | multi-valid label | Route+SQL | 4.5% | 951 | 1000 |
| Spider | multi-valid label | AMIGO top-1 | 1.4% | 984 | 1000 |
| Spider | multi-valid label | AMIGO | 2.0% | 991 | 1000 |
| Spider | multi-valid label | AMIGO with hints | 2.1% | 993 | 1000 |
| MMQA | multi-valid label | Gold-table oracle | 0.7% | 992 | 993 |
| MMQA | multi-valid label | Dense k3 | 12.5% | 869 | 993 |
| MMQA | multi-valid label | MURRE k3 | 6.3% | 930 | 993 |
| MMQA | multi-valid label | CORE-T | 4.0% | 953 | 993 |
| MMQA | multi-valid label | AMIGO top-1 | 3.5% | 958 | 993 |
| MMQA | multi-valid label | AMIGO | 3.3% | 981 | 993 |
| MMQA | multi-valid label | AMIGO with hints | 3.1% | 982 | 993 |

## Join choice outcomes and caps

| lake | questions | join choice: questions asked | join choice: joins asked | join choice: lists said no to entirely | join choice: questions with ways past the cap of 50 | join choice: ways past the cap | output: questions with 50 or more candidates | search: questions run again | search: same candidates as stored | search: questions with 50 or more candidates (cap of 50) | search: questions where the 3000-solve cap was reached | questions with more than 10 parts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | 1534 | 214 | 222 | 11 | 3 | 244 | 7 | 1534 | 1534 | 4 | 0 | 0 |
| Spider | 1034 | 82 | 92 | 3 | 0 | 0 | 0 | 1033 | 1033 | 0 | 0 | 0 |
| MMQA | 1105 | 166 | 218 | 49 | 22 | 459 | 89 | 1097 | 1097 | 78 | 0 | 0 |

## Labeled table sets by the first step that lost them (count, and % of the targets of all questions)

| lake | label | targets | found | empty output | a table not among the places listed for any part, nor reached by a join | the place judge said no to every place in a table | only relaxed candidates | no candidate holds all its tables | dropped by the join choice | labeled tables | labeled tables among the listed places |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | gold label | 1534 | 1387 (90.4) | 0 (0.0) | 17 (1.1) | 120 (7.8) | 2 (0.1) | 8 (0.5) | 0 (0.0) | 2978 | 2959 (99.4) |
| BIRD | multi-valid label | 2888 | 1802 (62.4) | 0 (0.0) | 46 (1.6) | 1018 (35.2) | 2 (0.1) | 20 (0.7) | 0 (0.0) | 6374 | 6322 (99.2) |
| Spider | gold label | 1034 | 983 (95.1) | 2 (0.2) | 13 (1.3) | 25 (2.4) | 2 (0.2) | 9 (0.9) | 0 (0.0) | 1565 | 1549 (99.0) |
| Spider | multi-valid label | 2435 | 1432 (58.8) | 9 (0.4) | 285 (11.7) | 616 (25.3) | 5 (0.2) | 88 (3.6) | 0 (0.0) | 3826 | 3458 (90.4) |
| MMQA | gold label | 1049 | 805 (76.7) | 0 (0.0) | 39 (3.7) | 152 (14.5) | 28 (2.7) | 25 (2.4) | 0 (0.0) | 2316 | 2248 (97.1) |
| MMQA | multi-valid label | 3649 | 1403 (38.4) | 0 (0.0) | 484 (13.3) | 1567 (42.9) | 45 (1.2) | 149 (4.1) | 1 (0.0) | 9104 | 8475 (93.1) |

## AMIGO's table sets on questions with one and with several table-set targets (multi-valid label)

| lake | questions | n | AMIGO returns two or more sets (%) | sets | sets, tables sharing a base name taken as one |
|---|---|---|---|---|---|
| BIRD | one table-set target | 809 | 27.07 | 1.35 | 1.35 |
| BIRD | two or more | 725 | 39.03 | 1.54 | 1.54 |
| Spider | one table-set target | 442 | 12.67 | 1.25 | 1.25 |
| Spider | two or more | 592 | 42.57 | 2.03 | 2.03 |
| MMQA | one table-set target | 343 | 31.49 | 3.01 | 2.21 |
| MMQA | two or more | 706 | 51.70 | 4.76 | 2.83 |

## Ambiguous questions (multi-valid label, two or more targets): AMIGO minus each method, points, 95% interval, Holm over the comparisons of one lake; * when below 0.05

| lake | method | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | +17.9 [+16.0, +19.9]* | +15.7 [+13.1, +18.5]* | +9.7 [+6.4, +12.9]* | +37.1 [+34.9, +39.3]* | +13.4 [+10.9, +15.9]* | +58.6 [+54.8, +62.3]* |
| BIRD | MURRE k3 | +13.8 [+12.0, +15.7]* | +15.7 [+13.1, +18.5]* | -1.0 [-3.6, +1.8] | +35.1 [+32.9, +37.3]* | +13.4 [+10.9, +15.9]* | +51.9 [+48.0, +55.9]* |
| BIRD | CORE-T | +9.9 [+8.4, +11.6]* | +15.7 [+13.1, +18.5]* | -10.3 [-12.5, -8.2]* | +32.1 [+29.9, +34.4]* | +13.4 [+10.9, +15.9]* | +48.1 [+44.1, +51.9]* |
| BIRD | Route+SQL | +12.3 [+10.6, +13.9]* | +15.7 [+13.1, +18.3]* | -5.1 [-7.4, -2.8]* | +9.9 [+8.1, +11.6]* | +13.4 [+11.0, +16.0]* | -8.3 [-11.1, -5.6]* |
| BIRD | AMIGO top-1 | +14.1 [+12.4, +15.7]* | +15.7 [+13.1, +18.3]* | +0.1 [-1.3, +1.6] | +12.5 [+10.9, +14.1]* | +13.4 [+10.9, +15.9]* | -0.9 [-2.5, +0.6] |
| Spider | Dense k3 | +23.6 [+21.3, +25.9]* | +14.7 [+11.8, +17.6]* | +16.3 [+12.7, +20.0]* | +46.4 [+44.2, +48.6]* | +13.5 [+10.8, +16.4]* | +78.7 [+75.7, +81.7]* |
| Spider | MURRE k3 | +19.0 [+16.8, +21.2]* | +14.7 [+11.8, +17.6]* | +4.0 [+0.9, +7.2]* | +45.7 [+43.5, +48.0]* | +13.5 [+10.8, +16.4]* | +77.5 [+74.2, +80.6]* |
| Spider | CORE-T | +16.3 [+14.3, +18.3]* | +14.7 [+12.0, +17.6]* | -2.7 [-5.2, -0.2]* | +34.5 [+32.1, +37.0]* | +13.5 [+10.8, +16.2]* | +50.0 [+45.7, +54.3]* |
| Spider | Route+SQL | +21.4 [+19.2, +23.7]* | +14.7 [+12.0, +17.6]* | +10.8 [+7.1, +14.4]* | +20.2 [+17.9, +22.5]* | +13.5 [+10.8, +16.4]* | +9.5 [+5.7, +13.2]* |
| Spider | AMIGO top-1 | +16.3 [+14.3, +18.3]* | +14.7 [+11.8, +17.6]* | -3.4 [-5.1, -1.8]* | +15.7 [+13.8, +17.6]* | +13.5 [+10.8, +16.4]* | -3.6 [-5.3, -1.9]* |
| MMQA | Dense k3 | +26.0 [+23.7, +28.3]* | +11.0 [+8.8, +13.5]* | +24.9 [+21.0, +28.9]* | +26.7 [+24.5, +29.0]* | +8.4 [+6.4, +10.5]* | +41.8 [+38.2, +45.3]* |
| MMQA | MURRE k3 | +22.6 [+20.4, +24.9]* | +11.0 [+8.8, +13.5]* | +15.2 [+11.3, +18.9]* | +26.1 [+23.9, +28.4]* | +8.4 [+6.4, +10.5]* | +39.8 [+36.2, +43.3]* |
| MMQA | CORE-T | +14.6 [+12.4, +16.7]* | +11.0 [+8.8, +13.5]* | -12.6 [-16.1, -9.1]* | +20.5 [+18.3, +22.8]* | +8.4 [+6.4, +10.5]* | +24.3 [+20.5, +28.2]* |
| MMQA | AMIGO top-1 | +16.5 [+14.6, +18.3]* | +11.0 [+8.8, +13.5]* | -5.8 [-7.9, -3.7]* | +10.7 [+9.1, +12.3]* | +8.4 [+6.4, +10.5]* | -7.4 [-9.6, -5.2]* |

## Place judge only (no join choice), search run again with a cap of 25, 50 and 100 candidates, gold label

| lake | cap | R | CR | P | CR= | sets | size |
|---|---|---|---|---|---|---|---|
| BIRD | 25 | 95.6 | 90.4 | 93.7 | 80.0 | 1.44 | 1.96 |
| BIRD | 50 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 |
| BIRD | 100 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 |
| Spider | 25 | 96.1 | 95.1 | 95.3 | 91.6 | 1.69 | 1.54 |
| Spider | 50 | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 |
| Spider | 100 | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 |
| MMQA | 25 | 87.6 | 76.3 | 82.8 | 62.3 | 3.30 | 3.05 |
| MMQA | 50 | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 3.12 |
| MMQA | 100 | 88.1 | 77.1 | 82.9 | 62.5 | 5.79 | 3.18 |
| mean | 25 | 93.1 | 87.2 | 90.6 | 78.0 |
| mean | 50 | 93.2 | 87.4 | 90.7 | 78.1 |
| mean | 100 | 93.3 | 87.5 | 90.7 | 78.1 |
| worst | 25 | 87.6 | 76.3 | 82.8 | 62.3 |
| worst | 50 | 87.9 | 76.7 | 83.0 | 62.5 |
| worst | 100 | 88.1 | 77.1 | 82.9 | 62.5 |

## Place judge only (no join choice), search run again with a cap of 25, 50 and 100 candidates, multi-valid label

| lake | cap | IR | ICR | IP | IR= | ICR= | IP= | sets | size |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | 25 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 |
| BIRD | 50 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 |
| BIRD | 100 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 |
| Spider | 25 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.5 | 1.69 | 1.54 |
| Spider | 50 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 |
| Spider | 100 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 |
| MMQA | 25 | 52.7 | 34.4 | 66.0 | 43.8 | 29.4 | 54.2 | 3.30 | 3.05 |
| MMQA | 50 | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 3.12 |
| MMQA | 100 | 53.6 | 34.5 | 65.3 | 44.0 | 29.4 | 53.8 | 5.79 | 3.18 |
| mean | 25 | 65.5 | 47.3 | 79.6 | 60.5 | 43.8 | 73.1 |
| mean | 50 | 65.7 | 47.3 | 79.4 | 60.6 | 43.8 | 73.1 |
| mean | 100 | 65.8 | 47.3 | 79.3 | 60.6 | 43.8 | 73.0 |
| worst | 25 | 52.7 | 34.4 | 66.0 | 43.8 | 29.4 | 54.2 |
| worst | 50 | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 |
| worst | 100 | 53.6 | 34.5 | 65.3 | 44.0 | 29.4 | 53.8 |

## The labeler's judge and AMIGO's place judge on the columns and tables both saw for one question

| lake | questions with a shared option | shared options | both yes | both no | labeler yes, place judge no | labeler no, place judge yes | agree (%) | place judge yes among labeler yes (%) | labeler yes among place judge yes (%) | Cohen's kappa | agreement on yes (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | 1531 | 24741 | 871 | 18679 | 2498 | 2693 | 79.0 | 25.9 | 24.4 | 0.13 | 25.1 |
| Spider | 984 | 16022 | 1051 | 10532 | 2994 | 1445 | 72.3 | 26.0 | 42.1 | 0.16 | 32.1 |
| MMQA | 1034 | 19109 | 1372 | 12174 | 3496 | 2067 | 70.9 | 28.2 | 39.9 | 0.15 | 33.0 |

## Multi-valid label without copies and without same-name alternatives (stage 1)

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | sets | size |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 50.9 | 36.2 | 72.0 | 6.3 | 2.3 | 12.4 | 1.00 | 3.00 |
| BIRD | MURRE k3 | 58.5 | 41.9 | 82.7 | 8.9 | 4.0 | 17.1 | 1.00 | 3.00 |
| BIRD | CORE-T | 68.1 | 49.7 | 94.9 | 22.6 | 16.3 | 31.3 | 1.00 | 3.19 |
| BIRD | Route+SQL | 62.6 | 45.3 | 88.1 | 60.9 | 44.1 | 85.7 | 0.99 | 1.88 |
| BIRD | AMIGO top-1 | 60.0 | 43.5 | 83.8 | 56.0 | 40.4 | 78.6 | 1.00 | 1.88 |
| BIRD | AMIGO | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 |
| Spider | Dense k3 | 45.6 | 30.8 | 69.1 | 2.7 | 1.1 | 5.0 | 1.00 | 3.00 |
| Spider | MURRE k3 | 57.1 | 39.7 | 83.9 | 3.8 | 1.7 | 6.5 | 1.00 | 3.00 |
| Spider | CORE-T | 59.4 | 40.4 | 89.1 | 22.2 | 14.3 | 33.4 | 1.00 | 2.68 |
| Spider | Route+SQL | 48.9 | 32.7 | 74.1 | 48.5 | 32.7 | 73.0 | 1.00 | 1.60 |
| Spider | AMIGO top-1 | 60.6 | 41.9 | 89.2 | 59.7 | 41.7 | 87.2 | 1.00 | 1.50 |
| Spider | AMIGO | 71.7 | 52.0 | 86.8 | 70.4 | 51.1 | 84.8 | 1.69 | 1.54 |
| MMQA | Dense k3 | 21.8 | 13.8 | 36.7 | 2.9 | 1.2 | 5.5 | 1.00 | 3.00 |
| MMQA | MURRE k3 | 28.8 | 18.8 | 47.4 | 4.4 | 2.4 | 7.9 | 1.00 | 3.00 |
| MMQA | CORE-T | 45.6 | 30.4 | 74.5 | 17.0 | 11.1 | 27.4 | 1.00 | 3.78 |
| MMQA | AMIGO top-1 | 41.0 | 27.0 | 67.8 | 35.8 | 24.2 | 57.4 | 1.00 | 2.62 |
| MMQA | AMIGO | 55.0 | 38.2 | 62.1 | 45.6 | 33.0 | 51.6 | 4.19 | 3.11 |
| mean | Dense k3 | 39.4 | 26.9 | 59.3 | 4.0 | 1.5 | 7.6 |
| mean | MURRE k3 | 48.1 | 33.5 | 71.3 | 5.7 | 2.7 | 10.5 |
| mean | CORE-T | 57.7 | 40.2 | 86.2 | 20.6 | 13.9 | 30.7 |
| mean | AMIGO top-1 | 53.9 | 37.5 | 80.3 | 50.5 | 35.4 | 74.4 |
| mean | AMIGO | 66.6 | 49.2 | 77.3 | 61.4 | 45.7 | 71.3 |
| worst | Dense k3 | 21.8 | 13.8 | 36.7 | 2.7 | 1.1 | 5.0 |
| worst | MURRE k3 | 28.8 | 18.8 | 47.4 | 3.8 | 1.7 | 6.5 |
| worst | CORE-T | 45.6 | 30.4 | 74.5 | 17.0 | 11.1 | 27.4 |
| worst | AMIGO top-1 | 41.0 | 27.0 | 67.8 | 35.8 | 24.2 | 57.4 |
| worst | AMIGO | 55.0 | 38.2 | 62.1 | 45.6 | 33.0 | 51.6 |

## One returned table set per labeled table set, gold label (stage 1)

| lake | method | set recall | set precision | set F1 |
|---|---|---|---|---|
| BIRD | Dense k3 | 68.6 | 68.6 | 68.6 |
| BIRD | MURRE k3 | 78.7 | 78.7 | 78.7 |
| BIRD | CORE-T | 92.9 | 92.9 | 92.9 |
| BIRD | Route+SQL | 81.5 | 81.5 | 81.5 |
| BIRD | AMIGO top-1 | 77.6 | 77.6 | 77.6 |
| BIRD | AMIGO | 90.4 | 74.1 | 79.0 |
| Spider | Dense k3 | 63.9 | 63.9 | 63.9 |
| Spider | MURRE k3 | 79.3 | 79.3 | 79.3 |
| Spider | CORE-T | 84.9 | 84.9 | 84.9 |
| Spider | Route+SQL | 67.4 | 67.4 | 67.4 |
| Spider | AMIGO top-1 | 84.6 | 84.6 | 84.6 |
| Spider | AMIGO | 95.1 | 78.2 | 82.5 |
| MMQA | Dense k3 | 31.4 | 31.4 | 31.4 |
| MMQA | MURRE k3 | 41.3 | 41.3 | 41.3 |
| MMQA | CORE-T | 70.6 | 70.6 | 70.6 |
| MMQA | AMIGO top-1 | 62.2 | 62.2 | 62.2 |
| MMQA | AMIGO | 76.7 | 53.7 | 58.0 |
| mean | Dense k3 | 54.6 | 54.6 | 54.6 |
| mean | MURRE k3 | 66.4 | 66.4 | 66.4 |
| mean | CORE-T | 82.8 | 82.8 | 82.8 |
| mean | AMIGO top-1 | 74.8 | 74.8 | 74.8 |
| mean | AMIGO | 87.4 | 68.6 | 73.2 |
| worst | Dense k3 | 31.4 | 31.4 | 31.4 |
| worst | MURRE k3 | 41.3 | 41.3 | 41.3 |
| worst | CORE-T | 70.6 | 70.6 | 70.6 |
| worst | AMIGO top-1 | 62.2 | 62.2 | 62.2 |
| worst | AMIGO | 76.7 | 53.7 | 58.0 |

## Set F1, AMIGO minus each method, gold label: points, 95% interval, Holm over the methods of one lake; * when below 0.05

| lake | method | AMIGO - method |
|---|---|---|
| BIRD | Dense k3 | +10.4 [+8.0, +12.9]* |
| BIRD | MURRE k3 | +0.3 [-1.8, +2.5] |
| BIRD | CORE-T | -13.9 [-15.6, -12.1]* |
| BIRD | Route+SQL | -2.5 [-4.4, -0.5]* |
| BIRD | AMIGO top-1 | +1.5 [+0.1, +2.8] |
| Spider | Dense k3 | +18.6 [+15.7, +21.5]* |
| Spider | MURRE k3 | +3.2 [+0.8, +5.7]* |
| Spider | CORE-T | -2.4 [-4.8, -0.0]* |
| Spider | Route+SQL | +15.1 [+12.1, +18.0]* |
| Spider | AMIGO top-1 | -2.1 [-3.7, -0.7]* |
| MMQA | Dense k3 | +26.7 [+23.6, +29.8]* |
| MMQA | MURRE k3 | +16.8 [+13.7, +19.8]* |
| MMQA | CORE-T | -12.6 [-15.5, -9.7]* |
| MMQA | AMIGO top-1 | -4.2 [-6.0, -2.4]* |

## One returned table set per labeled table set, multi-valid label (stage 1)

| lake | method | set recall | set precision | set F1 |
|---|---|---|---|---|
| BIRD | Dense k3 | 50.9 | 72.0 | 56.6 |
| BIRD | MURRE k3 | 58.5 | 82.7 | 65.0 |
| BIRD | CORE-T | 68.1 | 94.9 | 75.3 |
| BIRD | Route+SQL | 62.6 | 88.1 | 69.5 |
| BIRD | AMIGO top-1 | 60.0 | 83.8 | 66.5 |
| BIRD | AMIGO | 73.1 | 83.2 | 72.6 |
| Spider | Dense k3 | 43.9 | 69.8 | 50.3 |
| Spider | MURRE k3 | 55.4 | 85.8 | 63.0 |
| Spider | CORE-T | 57.5 | 90.2 | 65.7 |
| Spider | Route+SQL | 48.2 | 76.0 | 55.2 |
| Spider | AMIGO top-1 | 59.6 | 92.6 | 67.8 |
| Spider | AMIGO | 70.7 | 89.6 | 74.3 |
| MMQA | Dense k3 | 20.9 | 39.1 | 24.8 |
| MMQA | MURRE k3 | 27.3 | 49.8 | 32.2 |
| MMQA | CORE-T | 42.8 | 78.6 | 50.3 |
| MMQA | AMIGO top-1 | 38.9 | 71.3 | 45.7 |
| MMQA | AMIGO | 53.3 | 65.6 | 50.6 |
| mean | Dense k3 | 38.5 | 60.3 | 43.9 |
| mean | MURRE k3 | 47.1 | 72.8 | 53.4 |
| mean | CORE-T | 56.1 | 87.9 | 63.8 |
| mean | AMIGO top-1 | 52.8 | 82.6 | 60.0 |
| mean | AMIGO | 65.7 | 79.5 | 65.8 |
| worst | Dense k3 | 20.9 | 39.1 | 24.8 |
| worst | MURRE k3 | 27.3 | 49.8 | 32.2 |
| worst | CORE-T | 42.8 | 78.6 | 50.3 |
| worst | AMIGO top-1 | 38.9 | 71.3 | 45.7 |
| worst | AMIGO | 53.3 | 65.6 | 50.6 |

## Set F1, AMIGO minus each method, multi-valid label: points, 95% interval, Holm over the methods of one lake; * when below 0.05

| lake | method | AMIGO - method |
|---|---|---|
| BIRD | Dense k3 | +16.0 [+14.1, +18.0]* |
| BIRD | MURRE k3 | +7.6 [+5.9, +9.3]* |
| BIRD | CORE-T | -2.7 [-4.0, -1.4]* |
| BIRD | Route+SQL | +3.2 [+1.6, +4.8]* |
| BIRD | AMIGO top-1 | +6.2 [+5.1, +7.3]* |
| Spider | Dense k3 | +23.9 [+21.7, +26.2]* |
| Spider | MURRE k3 | +11.3 [+9.4, +13.1]* |
| Spider | CORE-T | +8.5 [+6.7, +10.4]* |
| Spider | Route+SQL | +19.1 [+16.9, +21.4]* |
| Spider | AMIGO top-1 | +6.5 [+5.2, +7.7]* |
| MMQA | Dense k3 | +25.8 [+23.4, +28.2]* |
| MMQA | MURRE k3 | +18.4 [+16.2, +20.6]* |
| MMQA | CORE-T | +0.3 [-1.9, +2.4] |
| MMQA | AMIGO top-1 | +4.8 [+3.5, +6.2]* |

## First hint prompt, main writer (sql_qwen.md at commit 009dcb6, AMIGO with hints rows)

### gold label
| lake | method | EX | single EX | multi EX | EX found | EX missed | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | AMIGO with hints | 47.8 | 53.2 | 46.1 | 51.4 | 11.1 | 4.35 | 5.4% | 1527 |
| Spider | AMIGO with hints | 74.8 | 78.8 | 69.7 | 78.7 | 3.9 | 2.69 | 2.8% | 985 |
| MMQA | AMIGO with hints | 57.3 | 66.7 | 57.3 | 66.3 | 9.8 | 20.43 | 2.5% | 965 |
| mean | AMIGO with hints | 60.0 | 66.2 | 57.7 | 65.4 | 8.3 |
| worst | AMIGO with hints | 47.8 | 53.2 | 46.1 | 51.4 | 3.9 |
### multi-valid label
| lake | method | EX | single EX | multi EX | EX found | EX missed | result P | SQLs | failed | n |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | AMIGO with hints | 40.3 | 44.9 | 37.6 | 47.3 | 3.7 | 46.9 | 4.38 | 5.5% | 1533 |
| Spider | AMIGO with hints | 56.7 | 58.6 | 45.3 | 74.5 | 1.2 | 72.8 | 2.71 | 2.8% | 1000 |
| MMQA | AMIGO with hints | 46.3 | 40.6 | 46.1 | 62.5 | 8.4 | 45.4 | 20.75 | 2.4% | 993 |
| mean | AMIGO with hints | 47.8 | 48.0 | 43.0 | 61.4 | 4.5 | 55.0 |
| worst | AMIGO with hints | 40.3 | 40.6 | 37.6 | 47.3 | 1.2 | 45.4 |
### AMIGO minus each method, EX
| label | lake | method | EX |
|---|---|---|---|
| gold label | BIRD | AMIGO with hints | +1.4 [-0.8, +3.6] |
| gold label | Spider | AMIGO with hints | +1.3 [-0.7, +3.5] |
| gold label | MMQA | AMIGO with hints | +8.8 [+6.5, +11.2]* |
| multi-valid label | BIRD | AMIGO with hints | -1.2 [-2.9, +0.6] |
| multi-valid label | Spider | AMIGO with hints | -0.2 [-1.7, +1.3] |
| multi-valid label | MMQA | AMIGO with hints | +2.1 [+0.3, +4.0]* |

## AMIGO without its fallback candidates, gold label (stage 1)

| lake | candidates kept | R | CR | P | CR= | sets | questions with such candidates |
|---|---|---|---|---|---|---|---|
| BIRD | all | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 0 |
| BIRD | without relaxed | 84.9 | 80.9 | 82.7 | 71.5 | 1.28 | 183 |
| BIRD | without judged no | 95.0 | 89.8 | 93.3 | 79.7 | 1.43 | 10 |
| BIRD | without either | 84.3 | 80.2 | 82.2 | 71.2 | 1.28 | 193 |
| Spider | all | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 0 |
| Spider | without relaxed | 90.2 | 89.7 | 89.0 | 86.6 | 1.55 | 70 |
| Spider | without judged no | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 3 |
| Spider | without either | 90.2 | 89.7 | 89.0 | 86.6 | 1.54 | 73 |
| MMQA | all | 87.9 | 76.7 | 83.0 | 62.5 | 4.19 | 0 |
| MMQA | without relaxed | 80.0 | 72.1 | 73.6 | 59.0 | 3.93 | 120 |
| MMQA | without judged no | 87.9 | 76.7 | 83.0 | 62.5 | 4.09 | 31 |
| MMQA | without either | 79.9 | 72.1 | 73.6 | 59.0 | 3.83 | 150 |
| mean | all | 93.2 | 87.4 | 90.7 | 78.1 |
| mean | without relaxed | 85.0 | 80.9 | 81.8 | 72.4 |
| mean | without judged no | 93.0 | 87.2 | 90.5 | 78.0 |
| mean | without either | 84.8 | 80.7 | 81.6 | 72.3 |
| worst | all | 87.9 | 76.7 | 83.0 | 62.5 |
| worst | without relaxed | 80.0 | 72.1 | 73.6 | 59.0 |
| worst | without judged no | 87.9 | 76.7 | 83.0 | 62.5 |
| worst | without either | 79.9 | 72.1 | 73.6 | 59.0 |

## AMIGO without either kind of fallback candidate, minus CORE-T, gold label: points, 95% interval, Holm over the 4 scores of one lake (mean row: stratified paired bootstrap over the three benchmarks); * when below 0.05

| lake | R | CR | P | CR= |
|---|---|---|---|---|
| BIRD | -12.2 [-13.9, -10.5]* | -12.6 [-14.7, -10.6]* | +19.4 [+17.4, +21.3]* | +49.6 [+46.8, +52.4]* |
| Spider | +1.0 [-1.2, +3.1] | +4.8 [+2.2, +7.5]* | +31.7 [+29.3, +34.0]* | +61.1 [+57.8, +64.3]* |
| MMQA | -4.1 [-6.5, -1.8]* | +1.4 [-1.9, +4.7] | +15.5 [+13.0, +17.9]* | +37.3 [+34.0, +40.7]* |
| mean (stratified) | -5.1 [-6.3, -3.9]* | -2.1 [-3.7, -0.6]* | +22.2 [+20.9, +23.5]* | +49.3 [+47.5, +51.1]* |

## AMIGO without its fallback candidates, multi-valid label (stage 1)

| lake | candidates kept | IR | ICR | IP | IR= | ICR= | IP= | sets | questions with such candidates |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | all | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 0 |
| BIRD | without relaxed | 65.1 | 51.0 | 74.0 | 60.8 | 47.2 | 69.2 | 1.28 | 183 |
| BIRD | without judged no | 72.5 | 56.8 | 82.5 | 68.0 | 52.9 | 77.4 | 1.43 | 10 |
| BIRD | without either | 64.4 | 50.4 | 73.4 | 60.5 | 46.9 | 68.9 | 1.28 | 193 |
| Spider | all | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 0 |
| Spider | without relaxed | 66.7 | 47.0 | 84.9 | 65.5 | 46.1 | 83.1 | 1.55 | 70 |
| Spider | without judged no | 70.7 | 50.0 | 89.7 | 69.4 | 49.0 | 87.7 | 1.69 | 3 |
| Spider | without either | 66.7 | 47.0 | 85.0 | 65.5 | 46.1 | 83.2 | 1.54 | 73 |
| MMQA | all | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 4.19 | 0 |
| MMQA | without relaxed | 50.0 | 32.2 | 61.6 | 41.1 | 27.3 | 50.7 | 3.93 | 120 |
| MMQA | without judged no | 53.2 | 34.4 | 65.7 | 43.9 | 29.3 | 54.2 | 4.09 | 31 |
| MMQA | without either | 50.0 | 32.1 | 61.7 | 41.1 | 27.2 | 50.8 | 3.83 | 150 |
| mean | all | 65.7 | 47.3 | 79.5 | 60.6 | 43.8 | 73.1 |
| mean | without relaxed | 60.6 | 43.4 | 73.5 | 55.8 | 40.2 | 67.7 |
| mean | without judged no | 65.5 | 47.1 | 79.3 | 60.5 | 43.7 | 73.1 |
| mean | without either | 60.4 | 43.2 | 73.4 | 55.7 | 40.1 | 67.7 |
| worst | all | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 |
| worst | without relaxed | 50.0 | 32.2 | 61.6 | 41.1 | 27.3 | 50.7 |
| worst | without judged no | 53.2 | 34.4 | 65.7 | 43.9 | 29.3 | 54.2 |
| worst | without either | 50.0 | 32.1 | 61.7 | 41.1 | 27.2 | 50.8 |

## AMIGO without either kind of fallback candidate, minus CORE-T, multi-valid label: points, 95% interval, Holm over the 6 scores of one lake (mean row: stratified paired bootstrap over the three benchmarks); * when below 0.05

| lake | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|
| BIRD | -3.7 [-5.4, -1.9]* | +0.7 [-1.3, +2.7] | -21.5 [-23.5, -19.5]* | +37.9 [+35.5, +40.3]* | +30.6 [+28.1, +33.2]* | +37.6 [+34.7, +40.6]* |
| Spider | +9.2 [+7.1, +11.2]* | +9.3 [+7.0, +11.6]* | -5.2 [-7.6, -2.8]* | +44.2 [+41.4, +46.8]* | +33.2 [+30.2, +36.2]* | +49.8 [+46.2, +53.2]* |
| MMQA | +7.2 [+4.9, +9.5]* | +5.7 [+3.3, +8.1]* | -16.8 [-19.8, -13.8]* | +24.6 [+22.2, +27.1]* | +17.1 [+14.7, +19.6]* | +22.8 [+19.5, +26.1]* |
| mean (stratified) | +4.2 [+3.0, +5.4]* | +5.2 [+3.9, +6.6]* | -14.5 [-15.9, -13.1]* | +35.6 [+34.1, +37.0]* | +27.0 [+25.4, +28.5]* | +36.7 [+34.9, +38.6]* |

## Reference queries of two or more tables whose joins the link graph holds (distinct queries)

| lake | label | queries | tables not in the layer | joined by some link (%) | joined by links on columns the query reads (%) | the same with dropped links put back (%) | links dropped by the declared-key rule |
|---|---|---|---|---|---|---|---|
| BIRD | gold label | 904 | 0 | 97.0 | 95.4 | 95.4 | 6 |
| BIRD | multi-valid label | 2612 | 0 | 91.5 | 88.4 | 88.4 | 6 |
| BIRD | multi-valid label, alternatives only | 1708 | 0 | 88.6 | 84.8 | 84.8 | 6 |
| Spider | gold label | 175 | 0 | 97.7 | 97.1 | 97.1 | 32 |
| Spider | multi-valid label | 572 | 0 | 90.2 | 87.9 | 88.1 | 32 |
| Spider | multi-valid label, alternatives only | 397 | 0 | 86.9 | 83.9 | 84.1 | 32 |
| MMQA | gold label | 847 | 0 | 82.1 | 80.5 | 80.5 | 0 |
| MMQA | multi-valid label | 3263 | 0 | 52.3 | 51.2 | 51.2 | 0 |
| MMQA | multi-valid label, alternatives only | 2416 | 0 | 41.9 | 40.9 | 40.9 | 0 |

## Returning two or more table sets as a test for a multi-valid label of two or more table sets

| lake | method | questions | label has 2+ table sets | returns 2+ sets | both | precision (%) | recall (%) |
|---|---|---|---|---|---|---|---|
| BIRD | AMIGO | 1534 | 725 | 502 | 283 | 56.4 | 39.0 |
| BIRD | place judge only (no join choice) | 1534 | 725 | 502 | 283 | 56.4 | 39.0 |
| Spider | AMIGO | 1034 | 592 | 308 | 252 | 81.8 | 42.6 |
| Spider | place judge only (no join choice) | 1034 | 592 | 308 | 252 | 81.8 | 42.6 |
| MMQA | AMIGO | 1049 | 706 | 473 | 365 | 77.2 | 51.7 |
| MMQA | place judge only (no join choice) | 1049 | 706 | 473 | 365 | 77.2 | 51.7 |

## The labeler's options (decoys left out) by votes

| lake | options | no after one vote | no after three votes | yes after three votes | other |
|---|---|---|---|---|---|
| BIRD | 111874 | 97670 | 7898 | 3437 | 2869 |
| Spider | 63700 | 48889 | 7377 | 5830 | 1604 |
| MMQA | 91607 | 75423 | 7747 | 7182 | 1255 |

## Alternative queries that return rows: same aggregates, grouping, order, limit and DISTINCT keywords as the original query

| lake | rewritten | queries | same keywords | share (%) |
|---|---|---|---|---|
| BIRD | with an LLM call | 2277 | 1910 | 83.9 |
| BIRD | without an LLM call | 528 | 524 | 99.2 |
| Spider | with an LLM call | 1861 | 1678 | 90.2 |
| Spider | without an LLM call | 38 | 38 | 100.0 |
| MMQA | with an LLM call | 3055 | 2929 | 95.9 |
| MMQA | without an LLM call | 37 | 37 | 100.0 |

## Worked example of the benchmark section (bird_dev-q78)

- question: What is the most common type of grade span served in the city of Adelanto?
- items: [{'item': 'schools', 'words': None, 'options': 0, 'decoys': []}, {'item': 'schools.City', 'words': 'in the city of Adelanto', 'options': 31, 'decoys': [('debit_card_specializing.transactions_1k.GasStationID', 'no')]}, {'item': 'schools.GSserved', 'words': 'type of grade span served', 'options': 33, 'decoys': [('card_games.cards.multiverseId', 'no')]}]
- accepted: [('schools.City', 'student_club.zip_code.city', 'llm', 'not answerable'), ('schools.City', 'california_schools.schools.MailCity', 'code', 'different rows'), ('schools.GSserved', 'california_schools.schools.EILName', 'llm', 'different rows'), ('schools.GSserved', 'california_schools.schools.GSoffered', 'llm', 'different rows')]
- groups: [['gold'], ['california_schools.schools.MailCity'], ['california_schools.schools.EILName'], ['california_schools.schools.GSoffered']]

## Output tokens and GPU-hour shares of the scored runs (eval_2026-10-20/runs.csv)

| lake | method | questions | LLM calls | output tokens | output tokens per question | GPU hours (share of busy time, by output tokens) | note |
|---|---|---|---|---|---|---|---|
| BIRD | MURRE (k=5) | 1534 | 5787 | 0 |  |  | replies taken from saved replies |
| BIRD | CORE-T | 1534 | 1534 | 2842245 | 1853 | 1.994 |  |
| BIRD | Route+SQL | 1534 | 1545 | 888479 | 579 | 0.623 |  |
| BIRD | Full schema | 1534 | 1534 | 576633 | 376 | 0.405 |  |
| BIRD | AMIGO-WJ (split, place judge, whole judge) | 1534 | 2865 | 9695315 | 6320 | 6.803 |  |
| Spider | MURRE (k=5) | 1034 | 2798 | 0 |  |  | replies taken from saved replies |
| Spider | CORE-T | 1034 | 1034 | 2453020 | 2372 | 1.721 |  |
| Spider | Route+SQL | 1034 | 1057 | 524779 | 508 | 0.368 |  |
| Spider | Full schema | 1034 | 0 | 0 |  |  | every question failed |
| Spider | AMIGO-WJ (split, place judge, whole judge) | 1034 | 1986 | 6703848 | 6483 | 4.704 |  |
| MMQA | MURRE (k=5) | 1105 | 5492 | 0 |  |  | replies taken from saved replies |
| MMQA | CORE-T | 1105 | 1105 | 2837108 | 2568 | 1.991 |  |
| MMQA | Full schema | 1105 | 0 | 0 |  |  | every question failed |
| MMQA | AMIGO-WJ (split, place judge, whole judge) | 1105 | 2128 | 13443938 | 12166 | 9.433 |  |

## AMIGO's logged place judge and join choice replies (cut prompts and repeated calls included)

| lake | questions | place judge replies | questions with a join choice call | join choice replies |
|---|---|---|---|---|
| BIRD | 1534 | 1572 | 214 | 214 |
| Spider | 1034 | 1096 | 82 | 82 |
| MMQA | 1105 | 1227 | 166 | 166 |

## Saved replies among AMIGO's logged judging replies (no status: given back from the saved replies, not a new call); LLM calls per question with one split call, with and without them

| lake | questions | judging replies | saved replies | calls per question | calls per question without saved replies |
|---|---|---|---|---|---|
| BIRD | 1534 | 1786 | 0 | 2.16 | 2.16 |
| Spider | 1034 | 1178 | 27 | 2.14 | 2.11 |
| MMQA | 1105 | 1393 | 26 | 2.26 | 2.24 |

## Spider multi-valid label: questions with a table set in another database

| questions | development databases | questions with a table set in another database | of them, in a development database | of them, in a training database | of them, in training databases only |
|---|---|---|---|---|---|
| 1034 | 20 | 424 | 84 | 394 | 340 |

## Multi-valid label, alternatives only: table-set targets other than the original query's table set, on the questions that have one (stage 1)

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | sets | size | questions |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 43.4 | 33.9 | 57.9 | 13.5 | 11.3 | 17.9 | 1.00 | 3.00 | 725 |
| BIRD | MURRE k3 | 47.9 | 36.4 | 66.5 | 14.8 | 11.2 | 22.2 | 1.00 | 3.00 | 725 |
| BIRD | CORE-T | 56.3 | 43.4 | 77.5 | 15.3 | 12.0 | 20.6 | 1.00 | 3.52 | 725 |
| BIRD | Route+SQL | 19.0 | 13.4 | 27.4 | 10.5 | 6.5 | 16.3 | 1.00 | 1.84 | 725 |
| BIRD | AMIGO top-1 | 24.5 | 17.9 | 35.0 | 16.3 | 11.0 | 24.6 | 1.00 | 1.91 | 725 |
| BIRD | AMIGO | 38.8 | 30.9 | 36.8 | 28.7 | 21.9 | 26.5 | 1.54 | 2.04 | 725 |
| Spider | Dense k3 | 26.4 | 17.9 | 42.4 | 3.7 | 3.0 | 4.9 | 1.00 | 3.00 | 592 |
| Spider | MURRE k3 | 31.9 | 22.3 | 52.0 | 4.8 | 4.1 | 6.1 | 1.00 | 3.00 | 592 |
| Spider | CORE-T | 29.7 | 19.9 | 48.8 | 9.9 | 7.4 | 14.0 | 1.00 | 2.86 | 592 |
| Spider | Route+SQL | 13.2 | 7.8 | 24.5 | 8.6 | 5.4 | 16.0 | 1.00 | 1.63 | 592 |
| Spider | AMIGO top-1 | 14.4 | 9.1 | 27.0 | 9.6 | 6.4 | 18.2 | 1.00 | 1.53 | 592 |
| Spider | AMIGO | 31.3 | 20.8 | 28.9 | 25.8 | 16.9 | 21.8 | 2.03 | 1.60 | 592 |
| MMQA | Dense k3 | 11.2 | 5.9 | 23.9 | 4.0 | 2.8 | 6.5 | 1.00 | 3.00 | 706 |
| MMQA | MURRE k3 | 13.4 | 6.9 | 28.8 | 4.1 | 2.7 | 7.4 | 1.00 | 3.00 | 706 |
| MMQA | CORE-T | 24.0 | 13.3 | 50.8 | 5.8 | 4.2 | 9.3 | 1.00 | 3.97 | 706 |
| MMQA | AMIGO top-1 | 11.7 | 6.2 | 26.6 | 6.3 | 3.4 | 13.3 | 1.00 | 2.73 | 706 |
| MMQA | AMIGO | 26.5 | 14.3 | 24.5 | 17.1 | 10.8 | 12.6 | 4.76 | 3.24 | 706 |
| mean | Dense k3 | 27.0 | 19.3 | 41.4 | 7.1 | 5.7 | 9.8 |
| mean | MURRE k3 | 31.1 | 21.9 | 49.1 | 7.9 | 6.0 | 11.9 |
| mean | CORE-T | 36.7 | 25.6 | 59.1 | 10.3 | 7.9 | 14.6 |
| mean | AMIGO top-1 | 16.9 | 11.1 | 29.6 | 10.7 | 7.0 | 18.7 |
| mean | AMIGO | 32.2 | 22.0 | 30.1 | 23.9 | 16.5 | 20.3 |
| worst | Dense k3 | 11.2 | 5.9 | 23.9 | 3.7 | 2.8 | 4.9 |
| worst | MURRE k3 | 13.4 | 6.9 | 28.8 | 4.1 | 2.7 | 6.1 |
| worst | CORE-T | 24.0 | 13.3 | 48.8 | 5.8 | 4.2 | 9.3 |
| worst | AMIGO top-1 | 11.7 | 6.2 | 26.6 | 6.3 | 3.4 | 13.3 |
| worst | AMIGO | 26.5 | 14.3 | 24.5 | 17.1 | 10.8 | 12.6 |

## Alternatives only: AMIGO minus each method, points, 95% interval, Holm over the comparisons of one lake; * when below 0.05

| lake | method | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | -4.6 [-8.1, -1.0] | -3.0 [-6.6, +0.4] | -21.1 [-25.1, -17.1]* | +15.2 [+11.7, +18.7]* | +10.6 [+7.2, +14.1]* | +8.6 [+4.8, +12.4]* |
| BIRD | MURRE k3 | -9.1 [-12.4, -5.7]* | -5.5 [-9.0, -2.1]* | -29.7 [-33.5, -25.9]* | +13.9 [+10.5, +17.2]* | +10.8 [+7.6, +13.9]* | +4.3 [+0.6, +8.0] |
| BIRD | CORE-T | -17.5 [-20.6, -14.5]* | -12.6 [-15.7, -9.5]* | -40.7 [-43.9, -37.5]* | +13.4 [+10.1, +16.7]* | +9.9 [+6.8, +13.2]* | +5.9 [+2.2, +9.8]* |
| BIRD | Route+SQL | +19.7 [+16.9, +22.7]* | +17.5 [+14.6, +20.4]* | +9.4 [+6.5, +12.3]* | +18.1 [+15.0, +21.3]* | +15.4 [+12.4, +18.5]* | +10.2 [+7.2, +13.2]* |
| BIRD | AMIGO top-1 | +14.2 [+11.9, +16.7]* | +13.0 [+10.5, +15.4]* | +1.8 [-0.0, +3.6] | +12.4 [+10.2, +14.7]* | +10.9 [+8.7, +13.2]* | +1.9 [+0.2, +3.6] |
| Spider | Dense k3 | +4.9 [+1.1, +8.7] | +2.9 [-0.7, +6.4] | -13.4 [-17.7, -9.2]* | +22.1 [+18.7, +25.6]* | +13.9 [+10.5, +17.2]* | +16.9 [+13.8, +20.1]* |
| Spider | MURRE k3 | -0.6 [-4.5, +3.2] | -1.5 [-5.2, +2.0] | -23.1 [-27.2, -18.9]* | +21.1 [+17.5, +24.4]* | +12.8 [+9.6, +16.2]* | +15.7 [+12.5, +19.0]* |
| Spider | CORE-T | +1.6 [-1.8, +4.9] | +0.8 [-2.4, +4.1] | -19.9 [-23.7, -16.2]* | +15.9 [+12.6, +19.3]* | +9.5 [+6.4, +12.5]* | +7.8 [+4.4, +11.1]* |
| Spider | Route+SQL | +18.1 [+14.8, +21.6]* | +13.0 [+9.8, +16.2]* | +4.5 [+1.0, +7.8] | +17.2 [+13.9, +20.6]* | +11.5 [+8.4, +14.7]* | +5.7 [+2.4, +9.1]* |
| Spider | AMIGO top-1 | +17.0 [+14.5, +19.6]* | +11.7 [+9.1, +14.4]* | +1.9 [-0.4, +4.3] | +16.2 [+13.7, +18.7]* | +10.5 [+8.1, +13.0]* | +3.5 [+1.3, +5.7]* |
| MMQA | Dense k3 | +15.3 [+12.5, +18.1]* | +8.4 [+5.8, +11.0]* | +0.6 [-2.7, +3.9] | +13.1 [+10.5, +15.7]* | +7.9 [+5.5, +10.3]* | +6.1 [+3.6, +8.6]* |
| MMQA | MURRE k3 | +13.0 [+10.1, +16.0]* | +7.4 [+4.7, +10.2]* | -4.3 [-7.7, -0.8] | +13.1 [+10.5, +15.7]* | +8.1 [+5.7, +10.6]* | +5.3 [+2.8, +7.8]* |
| MMQA | CORE-T | +2.4 [-0.5, +5.3] | +1.0 [-1.6, +3.7] | -26.4 [-30.0, -22.8]* | +11.3 [+8.7, +14.0]* | +6.5 [+4.1, +8.9]* | +3.3 [+0.6, +6.0] |
| MMQA | AMIGO top-1 | +14.7 [+12.6, +16.9]* | +8.1 [+6.1, +10.2]* | -2.1 [-4.2, -0.1] | +10.8 [+8.9, +12.9]* | +7.4 [+5.5, +9.3]* | -0.7 [-2.6, +1.1] |

## Stage 2, main writer: AMIGO cut to its first m table sets (queries already written, no LLM call)

| label | lake | method | EX | queries per question |
|---|---|---|---|---|
| gold label | BIRD | AMIGO, first 1 | 42.6 | 1.00 |
| gold label | BIRD | AMIGO, first 2 | 48.6 | 1.33 |
| gold label | BIRD | AMIGO, first 3 | 49.1 | 1.38 |
| gold label | BIRD | AMIGO, all sets | 49.2 | 1.44 |
| gold label | BIRD | CORE-T | 47.3 | 1.00 |
| gold label | Spider | AMIGO, first 1 | 69.6 | 1.00 |
| gold label | Spider | AMIGO, first 2 | 74.4 | 1.28 |
| gold label | Spider | AMIGO, first 3 | 75.6 | 1.41 |
| gold label | Spider | AMIGO, all sets | 76.5 | 1.66 |
| gold label | Spider | CORE-T | 68.6 | 1.00 |
| gold label | MMQA | AMIGO, first 1 | 49.4 | 1.00 |
| gold label | MMQA | AMIGO, first 2 | 55.3 | 1.45 |
| gold label | MMQA | AMIGO, first 3 | 56.7 | 1.69 |
| gold label | MMQA | AMIGO, all sets | 59.4 | 4.18 |
| gold label | MMQA | CORE-T | 50.2 | 1.00 |
| multi-valid label | BIRD | AMIGO, first 1 | 33.6 | 1.00 |
| multi-valid label | BIRD | AMIGO, first 2 | 38.4 | 1.33 |
| multi-valid label | BIRD | AMIGO, first 3 | 38.8 | 1.39 |
| multi-valid label | BIRD | AMIGO, all sets | 38.9 | 1.44 |
| multi-valid label | BIRD | CORE-T | 37.6 | 1.00 |
| multi-valid label | Spider | AMIGO, first 1 | 51.5 | 1.00 |
| multi-valid label | Spider | AMIGO, first 2 | 55.1 | 1.29 |
| multi-valid label | Spider | AMIGO, first 3 | 56.0 | 1.42 |
| multi-valid label | Spider | AMIGO, all sets | 57.1 | 1.67 |
| multi-valid label | Spider | CORE-T | 50.0 | 1.00 |
| multi-valid label | MMQA | AMIGO, first 1 | 36.5 | 1.00 |
| multi-valid label | MMQA | AMIGO, first 2 | 41.1 | 1.45 |
| multi-valid label | MMQA | AMIGO, first 3 | 42.2 | 1.69 |
| multi-valid label | MMQA | AMIGO, all sets | 44.1 | 4.16 |
| multi-valid label | MMQA | CORE-T | 36.7 | 1.00 |

## Stage 2: AMIGO cut minus CORE-T, EX points, 95% interval, Holm over the cuts of one lake and label; * when below 0.05

| label | lake | cut | EX |
|---|---|---|---|
| gold label | BIRD | AMIGO, first 1 | -4.7 [-6.4, -3.1]* |
| gold label | BIRD | AMIGO, first 2 | +1.3 [-0.1, +2.8] |
| gold label | BIRD | AMIGO, first 3 | +1.8 [+0.5, +3.2]* |
| gold label | BIRD | AMIGO, all sets | +2.0 [+0.7, +3.3]* |
| gold label | Spider | AMIGO, first 1 | +1.0 [-1.3, +3.4] |
| gold label | Spider | AMIGO, first 2 | +5.8 [+3.7, +8.0]* |
| gold label | Spider | AMIGO, first 3 | +7.0 [+4.8, +9.1]* |
| gold label | Spider | AMIGO, all sets | +7.9 [+5.7, +10.3]* |
| gold label | MMQA | AMIGO, first 1 | -0.7 [-3.4, +2.0] |
| gold label | MMQA | AMIGO, first 2 | +5.2 [+2.5, +7.9]* |
| gold label | MMQA | AMIGO, first 3 | +6.5 [+3.9, +9.2]* |
| gold label | MMQA | AMIGO, all sets | +9.2 [+6.4, +11.9]* |
| multi-valid label | BIRD | AMIGO, first 1 | -4.0 [-5.4, -2.7]* |
| multi-valid label | BIRD | AMIGO, first 2 | +0.7 [-0.4, +1.8] |
| multi-valid label | BIRD | AMIGO, first 3 | +1.2 [+0.1, +2.2] |
| multi-valid label | BIRD | AMIGO, all sets | +1.3 [+0.2, +2.3] |
| multi-valid label | Spider | AMIGO, first 1 | +1.5 [+0.0, +3.0]* |
| multi-valid label | Spider | AMIGO, first 2 | +5.1 [+3.6, +6.6]* |
| multi-valid label | Spider | AMIGO, first 3 | +6.0 [+4.5, +7.5]* |
| multi-valid label | Spider | AMIGO, all sets | +7.1 [+5.5, +8.8]* |
| multi-valid label | MMQA | AMIGO, first 1 | -0.2 [-1.9, +1.6] |
| multi-valid label | MMQA | AMIGO, first 2 | +4.4 [+2.6, +6.2]* |
| multi-valid label | MMQA | AMIGO, first 3 | +5.5 [+3.7, +7.4]* |
| multi-valid label | MMQA | AMIGO, all sets | +7.4 [+5.5, +9.3]* |

## Links of the "by few values" rule (recomputed, no LLM call) and those whose weight reaches the edge threshold of 1/2

| lake | links | of them in the layer | weight 1/2 or more |
|---|---|---|---|
| BIRD | 0 | 0 | 0 |
| Spider | 5 | 5 | 1 |
| MMQA | 15 | 15 | 9 |

## AMIGO's table sets in three orders, cut to the first m sets (stage 1), gold label

| lake | m | order | R | CR | P | CR= |
|---|---|---|---|---|---|---|
| BIRD | 1 | cost order (AMIGO) | 89.1 | 77.6 | 92.1 | 66.9 |
| BIRD | 1 | random order (mean of 20) | 90.3 | 79.8 | 90.5 | 65.2 |
| BIRD | 1 | fewest tables first | 85.6 | 71.1 | 92.7 | 62.5 |
| BIRD | 2 | cost order (AMIGO) | 94.9 | 88.5 | 93.6 | 78.1 |
| BIRD | 2 | random order (mean of 20) | 95.1 | 89.0 | 93.2 | 77.6 |
| BIRD | 2 | fewest tables first | 94.5 | 87.5 | 93.7 | 77.3 |
| BIRD | 3 | cost order (AMIGO) | 95.4 | 89.8 | 93.7 | 79.4 |
| BIRD | 3 | random order (mean of 20) | 95.5 | 89.9 | 93.5 | 79.1 |
| BIRD | 3 | fewest tables first | 95.1 | 88.7 | 93.7 | 78.3 |
| Spider | 1 | cost order (AMIGO) | 87.2 | 84.6 | 87.2 | 80.3 |
| Spider | 1 | random order (mean of 20) | 84.6 | 81.7 | 83.7 | 74.8 |
| Spider | 1 | fewest tables first | 84.7 | 80.1 | 87.1 | 77.2 |
| Spider | 2 | cost order (AMIGO) | 93.3 | 92.2 | 92.6 | 88.7 |
| Spider | 2 | random order (mean of 20) | 91.6 | 90.1 | 90.7 | 85.4 |
| Spider | 2 | fewest tables first | 92.3 | 90.0 | 92.6 | 86.7 |
| Spider | 3 | cost order (AMIGO) | 94.5 | 93.5 | 93.8 | 90.1 |
| Spider | 3 | random order (mean of 20) | 93.8 | 92.6 | 93.0 | 88.6 |
| Spider | 3 | fewest tables first | 94.2 | 92.7 | 93.8 | 89.4 |
| MMQA | 1 | cost order (AMIGO) | 78.0 | 62.2 | 78.2 | 51.5 |
| MMQA | 1 | random order (mean of 20) | 77.9 | 61.3 | 72.5 | 45.5 |
| MMQA | 1 | fewest tables first | 74.7 | 55.8 | 78.6 | 47.4 |
| MMQA | 2 | cost order (AMIGO) | 83.6 | 71.2 | 80.3 | 59.1 |
| MMQA | 2 | random order (mean of 20) | 83.4 | 69.9 | 76.8 | 54.0 |
| MMQA | 2 | fewest tables first | 82.8 | 70.0 | 80.5 | 58.7 |
| MMQA | 3 | cost order (AMIGO) | 84.8 | 72.3 | 81.1 | 60.1 |
| MMQA | 3 | random order (mean of 20) | 84.9 | 71.8 | 78.4 | 56.1 |
| MMQA | 3 | fewest tables first | 84.1 | 71.4 | 81.1 | 59.9 |

## AMIGO's table sets in three orders, mean and worst over the three benchmarks, gold label

| over | m | order | R | CR | P | CR= |
|---|---|---|---|---|---|---|
| mean | 1 | cost order (AMIGO) | 84.8 | 74.8 | 85.8 | 66.2 |
| worst | 1 | cost order (AMIGO) | 78.0 | 62.2 | 78.2 | 51.5 |
| mean | 1 | random order (mean of 20) | 84.3 | 74.2 | 82.2 | 61.8 |
| worst | 1 | random order (mean of 20) | 77.9 | 61.3 | 72.5 | 45.5 |
| mean | 1 | fewest tables first | 81.7 | 69.0 | 86.1 | 62.3 |
| worst | 1 | fewest tables first | 74.7 | 55.8 | 78.6 | 47.4 |
| mean | 2 | cost order (AMIGO) | 90.6 | 84.0 | 88.8 | 75.3 |
| worst | 2 | cost order (AMIGO) | 83.6 | 71.2 | 80.3 | 59.1 |
| mean | 2 | random order (mean of 20) | 90.0 | 83.0 | 86.9 | 72.3 |
| worst | 2 | random order (mean of 20) | 83.4 | 69.9 | 76.8 | 54.0 |
| mean | 2 | fewest tables first | 89.8 | 82.5 | 88.9 | 74.2 |
| worst | 2 | fewest tables first | 82.8 | 70.0 | 80.5 | 58.7 |
| mean | 3 | cost order (AMIGO) | 91.6 | 85.2 | 89.5 | 76.5 |
| worst | 3 | cost order (AMIGO) | 84.8 | 72.3 | 81.1 | 60.1 |
| mean | 3 | random order (mean of 20) | 91.4 | 84.8 | 88.3 | 74.6 |
| worst | 3 | random order (mean of 20) | 84.9 | 71.8 | 78.4 | 56.1 |
| mean | 3 | fewest tables first | 91.1 | 84.3 | 89.5 | 75.8 |
| worst | 3 | fewest tables first | 84.1 | 71.4 | 81.1 | 59.9 |

## Cost order minus each other order, gold label: points, 95% interval, Holm over the comparisons of one lake; * when below 0.05

| lake | m | order | score | difference |
|---|---|---|---|---|
| BIRD | 1 | random order (mean of 20) | R | -1.2 [-1.8, -0.6]* |
| BIRD | 1 | random order (mean of 20) | CR | -2.2 [-3.3, -1.1]* |
| BIRD | 1 | random order (mean of 20) | P | +1.6 [+1.1, +2.0]* |
| BIRD | 1 | random order (mean of 20) | CR= | +1.8 [+0.4, +3.1] |
| BIRD | 1 | fewest tables first | R | +3.5 [+2.9, +4.2]* |
| BIRD | 1 | fewest tables first | CR | +6.5 [+5.2, +7.7]* |
| BIRD | 1 | fewest tables first | P | -0.7 [-1.0, -0.4]* |
| BIRD | 1 | fewest tables first | CR= | +4.5 [+3.2, +5.9]* |
| BIRD | 2 | random order (mean of 20) | R | -0.2 [-0.4, +0.0] |
| BIRD | 2 | random order (mean of 20) | CR | -0.5 [-1.0, -0.0] |
| BIRD | 2 | random order (mean of 20) | P | +0.4 [+0.2, +0.6]* |
| BIRD | 2 | random order (mean of 20) | CR= | +0.5 [-0.0, +1.1] |
| BIRD | 2 | fewest tables first | R | +0.4 [+0.2, +0.7]* |
| BIRD | 2 | fewest tables first | CR | +1.0 [+0.5, +1.6]* |
| BIRD | 2 | fewest tables first | P | -0.1 [-0.2, +0.0] |
| BIRD | 2 | fewest tables first | CR= | +0.8 [+0.3, +1.3]* |
| BIRD | 3 | random order (mean of 20) | R | -0.1 [-0.2, +0.0] |
| BIRD | 3 | random order (mean of 20) | CR | -0.2 [-0.5, +0.1] |
| BIRD | 3 | random order (mean of 20) | P | +0.2 [+0.1, +0.3]* |
| BIRD | 3 | random order (mean of 20) | CR= | +0.3 [-0.0, +0.7] |
| BIRD | 3 | fewest tables first | R | +0.4 [+0.2, +0.5]* |
| BIRD | 3 | fewest tables first | CR | +1.1 [+0.6, +1.6]* |
| BIRD | 3 | fewest tables first | P | -0.0 [-0.1, +0.0] |
| BIRD | 3 | fewest tables first | CR= | +1.1 [+0.7, +1.6]* |
| Spider | 1 | random order (mean of 20) | R | +2.6 [+1.4, +3.8]* |
| Spider | 1 | random order (mean of 20) | CR | +2.9 [+1.5, +4.4]* |
| Spider | 1 | random order (mean of 20) | P | +3.6 [+2.3, +4.8]* |
| Spider | 1 | random order (mean of 20) | CR= | +5.4 [+3.8, +7.1]* |
| Spider | 1 | fewest tables first | R | +2.5 [+1.8, +3.3]* |
| Spider | 1 | fewest tables first | CR | +4.5 [+3.3, +5.8]* |
| Spider | 1 | fewest tables first | P | +0.1 [-0.5, +0.7] |
| Spider | 1 | fewest tables first | CR= | +3.1 [+1.7, +4.5]* |
| Spider | 2 | random order (mean of 20) | R | +1.7 [+1.0, +2.5]* |
| Spider | 2 | random order (mean of 20) | CR | +2.1 [+1.2, +3.0]* |
| Spider | 2 | random order (mean of 20) | P | +1.9 [+1.1, +2.7]* |
| Spider | 2 | random order (mean of 20) | CR= | +3.3 [+2.3, +4.3]* |
| Spider | 2 | fewest tables first | R | +1.0 [+0.6, +1.5]* |
| Spider | 2 | fewest tables first | CR | +2.1 [+1.3, +3.1]* |
| Spider | 2 | fewest tables first | P | -0.0 [-0.3, +0.2] |
| Spider | 2 | fewest tables first | CR= | +2.0 [+1.2, +3.0]* |
| Spider | 3 | random order (mean of 20) | R | +0.7 [+0.2, +1.2]* |
| Spider | 3 | random order (mean of 20) | CR | +0.9 [+0.3, +1.5]* |
| Spider | 3 | random order (mean of 20) | P | +0.8 [+0.2, +1.3]* |
| Spider | 3 | random order (mean of 20) | CR= | +1.5 [+0.9, +2.2]* |
| Spider | 3 | fewest tables first | R | +0.3 [+0.1, +0.6]* |
| Spider | 3 | fewest tables first | CR | +0.8 [+0.3, +1.4]* |
| Spider | 3 | fewest tables first | P | +0.0 [+0.0, +0.0] |
| Spider | 3 | fewest tables first | CR= | +0.8 [+0.3, +1.4]* |
| MMQA | 1 | random order (mean of 20) | R | +0.1 [-0.8, +1.0] |
| MMQA | 1 | random order (mean of 20) | CR | +1.0 [-0.5, +2.4] |
| MMQA | 1 | random order (mean of 20) | P | +5.7 [+4.5, +6.8]* |
| MMQA | 1 | random order (mean of 20) | CR= | +6.0 [+4.4, +7.8]* |
| MMQA | 1 | fewest tables first | R | +3.3 [+2.6, +4.0]* |
| MMQA | 1 | fewest tables first | CR | +6.5 [+5.1, +8.0]* |
| MMQA | 1 | fewest tables first | P | -0.4 [-0.8, +0.0] |
| MMQA | 1 | fewest tables first | CR= | +4.1 [+2.7, +5.6]* |
| MMQA | 2 | random order (mean of 20) | R | +0.2 [-0.5, +0.9] |
| MMQA | 2 | random order (mean of 20) | CR | +1.3 [+0.4, +2.3] |
| MMQA | 2 | random order (mean of 20) | P | +3.5 [+2.6, +4.3]* |
| MMQA | 2 | random order (mean of 20) | CR= | +5.1 [+3.9, +6.4]* |
| MMQA | 2 | fewest tables first | R | +0.9 [+0.3, +1.4]* |
| MMQA | 2 | fewest tables first | CR | +1.2 [+0.5, +2.0]* |
| MMQA | 2 | fewest tables first | P | -0.2 [-0.6, +0.2] |
| MMQA | 2 | fewest tables first | CR= | +0.4 [-0.2, +1.0] |
| MMQA | 3 | random order (mean of 20) | R | -0.0 [-0.6, +0.5] |
| MMQA | 3 | random order (mean of 20) | CR | +0.4 [-0.5, +1.3] |
| MMQA | 3 | random order (mean of 20) | P | +2.7 [+2.0, +3.5]* |
| MMQA | 3 | random order (mean of 20) | CR= | +3.9 [+2.8, +5.1]* |
| MMQA | 3 | fewest tables first | R | +0.7 [+0.3, +1.1]* |
| MMQA | 3 | fewest tables first | CR | +0.9 [+0.4, +1.4]* |
| MMQA | 3 | fewest tables first | P | -0.0 [-0.3, +0.3] |
| MMQA | 3 | fewest tables first | CR= | +0.2 [-0.4, +0.8] |

## AMIGO's table sets in three orders, cut to the first m sets (stage 1), multi-valid label

| lake | m | order | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|---|---|
| BIRD | 1 | cost order (AMIGO) | 60.0 | 43.5 | 83.8 | 56.0 | 40.4 | 78.6 |
| BIRD | 1 | random order (mean of 20) | 61.1 | 44.3 | 85.4 | 55.5 | 40.0 | 77.8 |
| BIRD | 1 | fewest tables first | 55.2 | 39.5 | 77.9 | 51.8 | 36.8 | 73.6 |
| BIRD | 2 | cost order (AMIGO) | 71.3 | 55.4 | 83.5 | 66.6 | 51.2 | 78.0 |
| BIRD | 2 | random order (mean of 20) | 71.5 | 55.5 | 83.7 | 66.3 | 50.8 | 77.7 |
| BIRD | 2 | fewest tables first | 70.3 | 54.5 | 82.9 | 65.6 | 50.3 | 77.4 |
| BIRD | 3 | cost order (AMIGO) | 72.5 | 56.6 | 83.4 | 67.6 | 52.3 | 77.8 |
| BIRD | 3 | random order (mean of 20) | 72.5 | 56.7 | 83.4 | 67.5 | 52.2 | 77.7 |
| BIRD | 3 | fewest tables first | 71.4 | 55.5 | 82.9 | 66.6 | 51.3 | 77.4 |
| Spider | 1 | cost order (AMIGO) | 59.6 | 39.7 | 92.6 | 58.7 | 39.6 | 90.7 |
| Spider | 1 | random order (mean of 20) | 58.5 | 39.0 | 90.7 | 57.0 | 38.5 | 87.6 |
| Spider | 1 | fewest tables first | 57.3 | 38.1 | 89.3 | 56.7 | 38.0 | 87.9 |
| Spider | 2 | cost order (AMIGO) | 67.0 | 46.5 | 91.0 | 65.9 | 46.0 | 89.1 |
| Spider | 2 | random order (mean of 20) | 66.2 | 45.8 | 90.0 | 64.6 | 44.9 | 87.5 |
| Spider | 2 | fewest tables first | 65.8 | 45.4 | 89.9 | 64.7 | 44.9 | 88.1 |
| Spider | 3 | cost order (AMIGO) | 68.9 | 48.5 | 90.0 | 67.6 | 47.7 | 88.1 |
| Spider | 3 | random order (mean of 20) | 68.6 | 48.3 | 89.7 | 67.1 | 47.1 | 87.5 |
| Spider | 3 | fewest tables first | 68.6 | 48.4 | 89.7 | 67.3 | 47.5 | 87.7 |
| MMQA | 1 | cost order (AMIGO) | 38.9 | 23.7 | 71.3 | 34.1 | 21.2 | 60.4 |
| MMQA | 1 | random order (mean of 20) | 38.9 | 23.7 | 71.9 | 31.4 | 19.6 | 54.0 |
| MMQA | 1 | fewest tables first | 35.9 | 21.9 | 66.3 | 31.8 | 19.7 | 56.6 |
| MMQA | 2 | cost order (AMIGO) | 47.6 | 30.7 | 70.3 | 40.7 | 26.6 | 58.0 |
| MMQA | 2 | random order (mean of 20) | 46.7 | 29.7 | 69.8 | 37.5 | 24.4 | 54.0 |
| MMQA | 2 | fewest tables first | 46.8 | 30.2 | 69.3 | 40.4 | 26.3 | 57.5 |
| MMQA | 3 | cost order (AMIGO) | 49.4 | 32.7 | 68.9 | 41.8 | 27.6 | 56.5 |
| MMQA | 3 | random order (mean of 20) | 48.7 | 31.2 | 68.6 | 39.0 | 25.4 | 54.0 |
| MMQA | 3 | fewest tables first | 48.7 | 31.5 | 68.3 | 41.6 | 27.2 | 56.5 |

## AMIGO's table sets in three orders, mean and worst over the three benchmarks, multi-valid label

| over | m | order | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|---|---|
| mean | 1 | cost order (AMIGO) | 52.8 | 35.7 | 82.6 | 49.6 | 33.7 | 76.6 |
| worst | 1 | cost order (AMIGO) | 38.9 | 23.7 | 71.3 | 34.1 | 21.2 | 60.4 |
| mean | 1 | random order (mean of 20) | 52.8 | 35.7 | 82.7 | 47.9 | 32.7 | 73.1 |
| worst | 1 | random order (mean of 20) | 38.9 | 23.7 | 71.9 | 31.4 | 19.6 | 54.0 |
| mean | 1 | fewest tables first | 49.5 | 33.2 | 77.8 | 46.8 | 31.5 | 72.7 |
| worst | 1 | fewest tables first | 35.9 | 21.9 | 66.3 | 31.8 | 19.7 | 56.6 |
| mean | 2 | cost order (AMIGO) | 62.0 | 44.2 | 81.6 | 57.7 | 41.3 | 75.0 |
| worst | 2 | cost order (AMIGO) | 47.6 | 30.7 | 70.3 | 40.7 | 26.6 | 58.0 |
| mean | 2 | random order (mean of 20) | 61.5 | 43.7 | 81.2 | 56.1 | 40.1 | 73.1 |
| worst | 2 | random order (mean of 20) | 46.7 | 29.7 | 69.8 | 37.5 | 24.4 | 54.0 |
| mean | 2 | fewest tables first | 61.0 | 43.4 | 80.7 | 56.9 | 40.5 | 74.4 |
| worst | 2 | fewest tables first | 46.8 | 30.2 | 69.3 | 40.4 | 26.3 | 57.5 |
| mean | 3 | cost order (AMIGO) | 63.6 | 45.9 | 80.8 | 59.0 | 42.5 | 74.1 |
| worst | 3 | cost order (AMIGO) | 49.4 | 32.7 | 68.9 | 41.8 | 27.6 | 56.5 |
| mean | 3 | random order (mean of 20) | 63.3 | 45.4 | 80.6 | 57.9 | 41.6 | 73.1 |
| worst | 3 | random order (mean of 20) | 48.7 | 31.2 | 68.6 | 39.0 | 25.4 | 54.0 |
| mean | 3 | fewest tables first | 62.9 | 45.1 | 80.3 | 58.5 | 42.0 | 73.9 |
| worst | 3 | fewest tables first | 48.7 | 31.5 | 68.3 | 41.6 | 27.2 | 56.5 |

## Cost order minus each other order, multi-valid label: points, 95% interval, Holm over the comparisons of one lake; * when below 0.05

| lake | m | order | score | difference |
|---|---|---|---|---|
| BIRD | 1 | random order (mean of 20) | IR | -1.0 [-1.9, -0.2] |
| BIRD | 1 | random order (mean of 20) | ICR | -0.8 [-1.6, +0.1] |
| BIRD | 1 | random order (mean of 20) | IP | -1.6 [-2.7, -0.5] |
| BIRD | 1 | random order (mean of 20) | IR= | +0.6 [-0.4, +1.6] |
| BIRD | 1 | random order (mean of 20) | ICR= | +0.4 [-0.5, +1.4] |
| BIRD | 1 | random order (mean of 20) | IP= | +0.8 [-0.4, +2.0] |
| BIRD | 1 | fewest tables first | IR | +4.8 [+3.8, +5.9]* |
| BIRD | 1 | fewest tables first | ICR | +4.0 [+3.1, +5.1]* |
| BIRD | 1 | fewest tables first | IP | +5.9 [+4.8, +7.2]* |
| BIRD | 1 | fewest tables first | IR= | +4.2 [+3.2, +5.3]* |
| BIRD | 1 | fewest tables first | ICR= | +3.7 [+2.7, +4.7]* |
| BIRD | 1 | fewest tables first | IP= | +5.0 [+3.7, +6.2]* |
| BIRD | 2 | random order (mean of 20) | IR | -0.2 [-0.6, +0.2] |
| BIRD | 2 | random order (mean of 20) | ICR | -0.1 [-0.5, +0.3] |
| BIRD | 2 | random order (mean of 20) | IP | -0.2 [-0.4, +0.1] |
| BIRD | 2 | random order (mean of 20) | IR= | +0.3 [-0.1, +0.7] |
| BIRD | 2 | random order (mean of 20) | ICR= | +0.4 [-0.1, +0.9] |
| BIRD | 2 | random order (mean of 20) | IP= | +0.3 [+0.0, +0.7] |
| BIRD | 2 | fewest tables first | IR | +1.0 [+0.5, +1.4]* |
| BIRD | 2 | fewest tables first | ICR | +0.9 [+0.5, +1.4]* |
| BIRD | 2 | fewest tables first | IP | +0.7 [+0.4, +1.0]* |
| BIRD | 2 | fewest tables first | IR= | +0.9 [+0.5, +1.4]* |
| BIRD | 2 | fewest tables first | ICR= | +0.9 [+0.5, +1.4]* |
| BIRD | 2 | fewest tables first | IP= | +0.6 [+0.3, +0.9]* |
| BIRD | 3 | random order (mean of 20) | IR | -0.1 [-0.3, +0.2] |
| BIRD | 3 | random order (mean of 20) | ICR | -0.1 [-0.4, +0.2] |
| BIRD | 3 | random order (mean of 20) | IP | -0.1 [-0.2, +0.1] |
| BIRD | 3 | random order (mean of 20) | IR= | +0.1 [-0.1, +0.4] |
| BIRD | 3 | random order (mean of 20) | ICR= | +0.1 [-0.2, +0.4] |
| BIRD | 3 | random order (mean of 20) | IP= | +0.1 [-0.0, +0.3] |
| BIRD | 3 | fewest tables first | IR | +1.1 [+0.6, +1.6]* |
| BIRD | 3 | fewest tables first | ICR | +1.0 [+0.6, +1.6]* |
| BIRD | 3 | fewest tables first | IP | +0.5 [+0.3, +0.7]* |
| BIRD | 3 | fewest tables first | IR= | +1.0 [+0.6, +1.5]* |
| BIRD | 3 | fewest tables first | ICR= | +1.0 [+0.5, +1.5]* |
| BIRD | 3 | fewest tables first | IP= | +0.4 [+0.2, +0.6]* |
| Spider | 1 | random order (mean of 20) | IR | +1.1 [+0.4, +1.9]* |
| Spider | 1 | random order (mean of 20) | ICR | +0.7 [+0.0, +1.4] |
| Spider | 1 | random order (mean of 20) | IP | +1.9 [+0.8, +3.1]* |
| Spider | 1 | random order (mean of 20) | IR= | +1.7 [+0.9, +2.6]* |
| Spider | 1 | random order (mean of 20) | ICR= | +1.1 [+0.3, +1.8]* |
| Spider | 1 | random order (mean of 20) | IP= | +3.1 [+1.9, +4.4]* |
| Spider | 1 | fewest tables first | IR | +2.3 [+1.5, +3.2]* |
| Spider | 1 | fewest tables first | ICR | +1.6 [+0.9, +2.4]* |
| Spider | 1 | fewest tables first | IP | +3.4 [+2.3, +4.5]* |
| Spider | 1 | fewest tables first | IR= | +2.0 [+1.1, +2.9]* |
| Spider | 1 | fewest tables first | ICR= | +1.5 [+0.8, +2.4]* |
| Spider | 1 | fewest tables first | IP= | +2.8 [+1.6, +4.0]* |
| Spider | 2 | random order (mean of 20) | IR | +0.8 [+0.4, +1.3]* |
| Spider | 2 | random order (mean of 20) | ICR | +0.7 [+0.2, +1.2] |
| Spider | 2 | random order (mean of 20) | IP | +1.0 [+0.5, +1.5]* |
| Spider | 2 | random order (mean of 20) | IR= | +1.3 [+0.7, +1.8]* |
| Spider | 2 | random order (mean of 20) | ICR= | +1.1 [+0.5, +1.7]* |
| Spider | 2 | random order (mean of 20) | IP= | +1.5 [+1.0, +2.1]* |
| Spider | 2 | fewest tables first | IR | +1.2 [+0.7, +1.9]* |
| Spider | 2 | fewest tables first | ICR | +1.2 [+0.6, +1.8]* |
| Spider | 2 | fewest tables first | IP | +1.1 [+0.6, +1.5]* |
| Spider | 2 | fewest tables first | IR= | +1.2 [+0.6, +1.8]* |
| Spider | 2 | fewest tables first | ICR= | +1.2 [+0.6, +1.8]* |
| Spider | 2 | fewest tables first | IP= | +1.0 [+0.5, +1.5]* |
| Spider | 3 | random order (mean of 20) | IR | +0.3 [-0.0, +0.6] |
| Spider | 3 | random order (mean of 20) | ICR | +0.2 [-0.1, +0.5] |
| Spider | 3 | random order (mean of 20) | IP | +0.3 [+0.0, +0.5] |
| Spider | 3 | random order (mean of 20) | IR= | +0.6 [+0.2, +0.9]* |
| Spider | 3 | random order (mean of 20) | ICR= | +0.5 [+0.1, +1.0] |
| Spider | 3 | random order (mean of 20) | IP= | +0.5 [+0.3, +0.8]* |
| Spider | 3 | fewest tables first | IR | +0.3 [+0.1, +0.5]* |
| Spider | 3 | fewest tables first | ICR | +0.2 [-0.2, +0.6] |
| Spider | 3 | fewest tables first | IP | +0.3 [+0.1, +0.5]* |
| Spider | 3 | fewest tables first | IR= | +0.3 [+0.1, +0.5]* |
| Spider | 3 | fewest tables first | ICR= | +0.2 [-0.2, +0.6] |
| Spider | 3 | fewest tables first | IP= | +0.3 [+0.1, +0.6]* |
| MMQA | 1 | random order (mean of 20) | IR | -0.0 [-0.9, +0.8] |
| MMQA | 1 | random order (mean of 20) | ICR | +0.0 [-0.7, +0.8] |
| MMQA | 1 | random order (mean of 20) | IP | -0.6 [-2.0, +0.8] |
| MMQA | 1 | random order (mean of 20) | IR= | +2.8 [+1.8, +3.8]* |
| MMQA | 1 | random order (mean of 20) | ICR= | +1.5 [+0.7, +2.5]* |
| MMQA | 1 | random order (mean of 20) | IP= | +6.5 [+4.7, +8.2]* |
| MMQA | 1 | fewest tables first | IR | +3.0 [+2.1, +3.9]* |
| MMQA | 1 | fewest tables first | ICR | +1.8 [+1.0, +2.7]* |
| MMQA | 1 | fewest tables first | IP | +5.0 [+3.7, +6.3]* |
| MMQA | 1 | fewest tables first | IR= | +2.3 [+1.5, +3.2]* |
| MMQA | 1 | fewest tables first | ICR= | +1.4 [+0.7, +2.2]* |
| MMQA | 1 | fewest tables first | IP= | +3.8 [+2.6, +5.1]* |
| MMQA | 2 | random order (mean of 20) | IR | +0.9 [+0.3, +1.5] |
| MMQA | 2 | random order (mean of 20) | ICR | +1.0 [+0.4, +1.7]* |
| MMQA | 2 | random order (mean of 20) | IP | +0.5 [-0.2, +1.3] |
| MMQA | 2 | random order (mean of 20) | IR= | +3.2 [+2.4, +4.1]* |
| MMQA | 2 | random order (mean of 20) | ICR= | +2.2 [+1.4, +3.1]* |
| MMQA | 2 | random order (mean of 20) | IP= | +4.0 [+3.1, +4.9]* |
| MMQA | 2 | fewest tables first | IR | +0.8 [+0.3, +1.3]* |
| MMQA | 2 | fewest tables first | ICR | +0.5 [+0.0, +1.0] |
| MMQA | 2 | fewest tables first | IP | +1.0 [+0.5, +1.5]* |
| MMQA | 2 | fewest tables first | IR= | +0.4 [+0.0, +0.7] |
| MMQA | 2 | fewest tables first | ICR= | +0.3 [-0.1, +0.8] |
| MMQA | 2 | fewest tables first | IP= | +0.5 [+0.1, +0.9] |
| MMQA | 3 | random order (mean of 20) | IR | +0.7 [+0.2, +1.3] |
| MMQA | 3 | random order (mean of 20) | ICR | +1.5 [+0.8, +2.1]* |
| MMQA | 3 | random order (mean of 20) | IP | +0.3 [-0.2, +0.8] |
| MMQA | 3 | random order (mean of 20) | IR= | +2.8 [+2.0, +3.7]* |
| MMQA | 3 | random order (mean of 20) | ICR= | +2.3 [+1.4, +3.2]* |
| MMQA | 3 | random order (mean of 20) | IP= | +2.4 [+1.8, +3.1]* |
| MMQA | 3 | fewest tables first | IR | +0.8 [+0.4, +1.3]* |
| MMQA | 3 | fewest tables first | ICR | +1.2 [+0.7, +1.9]* |
| MMQA | 3 | fewest tables first | IP | +0.5 [+0.2, +0.9]* |
| MMQA | 3 | fewest tables first | IR= | +0.2 [-0.2, +0.7] |
| MMQA | 3 | fewest tables first | ICR= | +0.5 [-0.2, +1.1] |
| MMQA | 3 | fewest tables first | IP= | +0.0 [-0.3, +0.3] |

## Candidates whose table set is exactly a labeled table set, by cost above the best candidate

| lake | label | cost above best | candidates | share equal to a labeled table set (%) |
|---|---|---|---|---|
| BIRD | gold label | best (cost above best 0) | 1866 | 65.9 |
| BIRD | gold label | above best by (0, 1] bit | 602 | 46.8 |
| BIRD | gold label | by (1, 2] bits | 543 | 47.1 |
| BIRD | gold label | by (2, 4] bits | 633 | 37.4 |
| BIRD | gold label | by more than 4 bits | 238 | 20.6 |
| BIRD | multi-valid label | best (cost above best 0) | 1866 | 76.2 |
| BIRD | multi-valid label | above best by (0, 1] bit | 602 | 66.9 |
| BIRD | multi-valid label | by (1, 2] bits | 543 | 65.4 |
| BIRD | multi-valid label | by (2, 4] bits | 633 | 60.2 |
| BIRD | multi-valid label | by more than 4 bits | 238 | 58.8 |
| Spider | gold label | best (cost above best 0) | 1089 | 79.5 |
| Spider | gold label | above best by (0, 1] bit | 289 | 41.9 |
| Spider | gold label | by (1, 2] bits | 275 | 23.6 |
| Spider | gold label | by (2, 4] bits | 420 | 21.2 |
| Spider | gold label | by more than 4 bits | 221 | 10.9 |
| Spider | multi-valid label | best (cost above best 0) | 1089 | 90.2 |
| Spider | multi-valid label | above best by (0, 1] bit | 289 | 72.3 |
| Spider | multi-valid label | by (1, 2] bits | 275 | 65.8 |
| Spider | multi-valid label | by (2, 4] bits | 420 | 53.8 |
| Spider | multi-valid label | by more than 4 bits | 221 | 32.6 |
| MMQA | gold label | best (cost above best 0) | 1106 | 52.0 |
| MMQA | gold label | above best by (0, 1] bit | 483 | 28.6 |
| MMQA | gold label | by (1, 2] bits | 595 | 18.3 |
| MMQA | gold label | by (2, 4] bits | 1583 | 8.3 |
| MMQA | gold label | by more than 4 bits | 4166 | 1.8 |
| MMQA | multi-valid label | best (cost above best 0) | 1106 | 61.1 |
| MMQA | multi-valid label | above best by (0, 1] bit | 483 | 47.6 |
| MMQA | multi-valid label | by (1, 2] bits | 595 | 30.8 |
| MMQA | multi-valid label | by (2, 4] bits | 1583 | 17.0 |
| MMQA | multi-valid label | by more than 4 bits | 4166 | 3.8 |

## Parts left out by AMIGO's relaxed candidates, once per question and part

| lake | questions with a relaxed candidate | of them with a full candidate too | parts left out | no place judged yes | % of them | with a value | % with a value |
|---|---|---|---|---|---|---|---|
| BIRD | 183 | 0 | 203 | 196 | 96.6 | 144 | 70.9 |
| Spider | 70 | 0 | 96 | 56 | 58.3 | 38 | 39.6 |
| MMQA | 120 | 0 | 179 | 76 | 42.5 | 83 | 46.4 |

## Of the left-out parts with no place judged yes: no place listed at all, and a rejected place in a table that the original query reads (gold used for scoring only)

| lake | no place judged yes | no place listed | a rejected place in an original table | % |
|---|---|---|---|---|
| BIRD | 196 | 0 | 170 | 86.7 |
| Spider | 56 | 0 | 23 | 41.1 |
| MMQA | 76 | 0 | 47 | 61.8 |

## AMIGO's precision per target: matched set as in the protocol, and the first set in cost order among those of highest recall

| lake | label | P (protocol) | P (first in order) |
|---|---|---|---|
| BIRD | gold label | 93.7 | 93.1 |
| BIRD | multi-valid label | 92.2 | 91.5 |
| Spider | gold label | 95.3 | 94.7 |
| Spider | multi-valid label | 77.6 | 77.1 |
| MMQA | gold label | 83.0 | 82.1 |
| MMQA | multi-valid label | 79.4 | 78.5 |
| mean | gold label | 90.7 | 90.0 |
| worst | gold label | 83.0 | 82.1 |
| mean | multi-valid label | 83.1 | 82.3 |
| worst | multi-valid label | 77.6 | 77.1 |

## Result precision of the main writer's queries against each label (the multi-valid rows repeat sql_qwen.md)

| lake | label | method | result P | questions with a result |
|---|---|---|---|---|
| BIRD | gold label | Oracle | 52.6 | 1508 |
| BIRD | gold label | Dense k3 | 42.6 | 1323 |
| BIRD | gold label | MURRE k3 | 45.3 | 1425 |
| BIRD | gold label | CORE-T | 49.0 | 1472 |
| BIRD | gold label | Route+SQL | 47.9 | 1495 |
| BIRD | gold label | AMIGO top-1 | 44.7 | 1453 |
| BIRD | gold label | AMIGO | 45.6 | 1505 |
| BIRD | gold label | AMIGO with hints | 43.9 | 1506 |
| BIRD | multi-valid label | Oracle | 55.8 | 1519 |
| BIRD | multi-valid label | Dense k3 | 47.6 | 1327 |
| BIRD | multi-valid label | MURRE k3 | 51.2 | 1428 |
| BIRD | multi-valid label | CORE-T | 54.7 | 1478 |
| BIRD | multi-valid label | Route+SQL | 53.2 | 1500 |
| BIRD | multi-valid label | AMIGO top-1 | 50.5 | 1458 |
| BIRD | multi-valid label | AMIGO | 51.3 | 1510 |
| BIRD | multi-valid label | AMIGO with hints | 49.9 | 1511 |
| Spider | gold label | Oracle | 80.6 | 978 |
| Spider | gold label | Dense k3 | 59.1 | 916 |
| Spider | gold label | MURRE k3 | 65.9 | 962 |
| Spider | gold label | CORE-T | 70.1 | 964 |
| Spider | gold label | Route+SQL | 61.0 | 936 |
| Spider | gold label | AMIGO top-1 | 70.8 | 969 |
| Spider | gold label | AMIGO | 69.2 | 976 |
| Spider | gold label | AMIGO with hints | 67.7 | 978 |
| Spider | multi-valid label | Oracle | 77.5 | 996 |
| Spider | multi-valid label | Dense k3 | 64.0 | 929 |
| Spider | multi-valid label | MURRE k3 | 72.3 | 977 |
| Spider | multi-valid label | CORE-T | 75.4 | 979 |
| Spider | multi-valid label | Route+SQL | 68.1 | 951 |
| Spider | multi-valid label | AMIGO top-1 | 77.3 | 984 |
| Spider | multi-valid label | AMIGO | 76.6 | 991 |
| Spider | multi-valid label | AMIGO with hints | 75.3 | 993 |
| MMQA | gold label | Oracle | 74.1 | 961 |
| MMQA | gold label | Dense k3 | 28.6 | 845 |
| MMQA | gold label | MURRE k3 | 33.4 | 902 |
| MMQA | gold label | CORE-T | 52.2 | 927 |
| MMQA | gold label | AMIGO top-1 | 51.2 | 932 |
| MMQA | gold label | AMIGO | 49.7 | 954 |
| MMQA | gold label | AMIGO with hints | 46.7 | 955 |
| MMQA | multi-valid label | Oracle | 73.3 | 992 |
| MMQA | multi-valid label | Dense k3 | 39.4 | 869 |
| MMQA | multi-valid label | MURRE k3 | 44.5 | 930 |
| MMQA | multi-valid label | CORE-T | 61.5 | 953 |
| MMQA | multi-valid label | AMIGO top-1 | 59.6 | 958 |
| MMQA | multi-valid label | AMIGO | 58.5 | 981 |
| MMQA | multi-valid label | AMIGO with hints | 55.0 | 982 |
| mean | gold label | Oracle | 69.1 |  |
| worst | gold label | Oracle | 52.6 |  |
| mean | gold label | Dense k3 | 43.4 |  |
| worst | gold label | Dense k3 | 28.6 |  |
| mean | gold label | MURRE k3 | 48.2 |  |
| worst | gold label | MURRE k3 | 33.4 |  |
| mean | gold label | CORE-T | 57.1 |  |
| worst | gold label | CORE-T | 49.0 |  |
| mean | gold label | Route+SQL | 54.4 |  |
| worst | gold label | Route+SQL | 47.9 |  |
| mean | gold label | AMIGO top-1 | 55.6 |  |
| worst | gold label | AMIGO top-1 | 44.7 |  |
| mean | gold label | AMIGO | 54.8 |  |
| worst | gold label | AMIGO | 45.6 |  |
| mean | gold label | AMIGO with hints | 52.8 |  |
| worst | gold label | AMIGO with hints | 43.9 |  |
| mean | multi-valid label | Oracle | 68.9 |  |
| worst | multi-valid label | Oracle | 55.8 |  |
| mean | multi-valid label | Dense k3 | 50.3 |  |
| worst | multi-valid label | Dense k3 | 39.4 |  |
| mean | multi-valid label | MURRE k3 | 56.0 |  |
| worst | multi-valid label | MURRE k3 | 44.5 |  |
| mean | multi-valid label | CORE-T | 63.9 |  |
| worst | multi-valid label | CORE-T | 54.7 |  |
| mean | multi-valid label | Route+SQL | 60.7 |  |
| worst | multi-valid label | Route+SQL | 53.2 |  |
| mean | multi-valid label | AMIGO top-1 | 62.5 |  |
| worst | multi-valid label | AMIGO top-1 | 50.5 |  |
| mean | multi-valid label | AMIGO | 62.1 |  |
| worst | multi-valid label | AMIGO | 51.3 |  |
| mean | multi-valid label | AMIGO with hints | 60.1 |  |
| worst | multi-valid label | AMIGO with hints | 49.9 |  |

## Dense retrieval split by database (stage 1, no LLM call), gold label; not tested

| lake | method | R | CR | P | CR= | sets | size |
|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 83.1 | 68.6 | 51.8 | 3.9 | 1.00 | 3.00 |
| BIRD | Dense k3 by database | 83.1 | 68.6 | 58.8 | 11.0 | 1.25 | 2.65 |
| BIRD | Dense k5 | 91.5 | 83.4 | 34.9 | 0.1 | 1.00 | 5.00 |
| BIRD | Dense k5 by database | 91.5 | 83.4 | 48.2 | 4.6 | 1.86 | 3.27 |
| Spider | Dense k3 | 73.5 | 63.9 | 37.1 | 2.2 | 1.00 | 3.00 |
| Spider | Dense k3 by database | 73.5 | 63.9 | 65.7 | 36.5 | 2.07 | 1.73 |
| Spider | Dense k5 | 82.8 | 77.6 | 25.4 | 0.0 | 1.00 | 5.00 |
| Spider | Dense k5 by database | 82.8 | 77.6 | 62.0 | 33.4 | 3.20 | 1.84 |
| MMQA | Dense k3 | 59.0 | 31.4 | 42.8 | 2.8 | 1.00 | 3.00 |
| MMQA | Dense k3 by database | 59.0 | 31.4 | 42.8 | 2.8 | 1.00 | 3.00 |
| MMQA | Dense k5 | 70.9 | 46.5 | 31.0 | 0.0 | 1.00 | 5.00 |
| MMQA | Dense k5 by database | 70.9 | 46.5 | 31.0 | 0.0 | 1.00 | 5.00 |
| mean | Dense k3 | 71.9 | 54.6 | 43.9 | 3.0 |  |  |
| worst | Dense k3 | 59.0 | 31.4 | 37.1 | 2.2 |  |  |
| mean | Dense k3 by database | 71.9 | 54.6 | 55.8 | 16.7 |  |  |
| worst | Dense k3 by database | 59.0 | 31.4 | 42.8 | 2.8 |  |  |
| mean | Dense k5 | 81.7 | 69.2 | 30.4 | 0.0 |  |  |
| worst | Dense k5 | 70.9 | 46.5 | 25.4 | 0.0 |  |  |
| mean | Dense k5 by database | 81.7 | 69.2 | 47.1 | 12.7 |  |  |
| worst | Dense k5 by database | 70.9 | 46.5 | 31.0 | 0.0 |  |  |

## Dense retrieval split by database (stage 1, no LLM call), multi-valid label; not tested

| lake | method | IR | ICR | IP | IR= | ICR= | IP= | sets | size |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 50.9 | 36.2 | 72.0 | 6.3 | 2.3 | 12.4 | 1.00 | 3.00 |
| BIRD | Dense k3 by database | 51.0 | 36.4 | 65.3 | 13.3 | 7.7 | 16.8 | 1.25 | 2.65 |
| BIRD | Dense k5 | 61.1 | 44.1 | 85.9 | 0.0 | 0.0 | 0.1 | 1.00 | 5.00 |
| BIRD | Dense k5 by database | 61.2 | 44.3 | 56.6 | 5.7 | 3.5 | 3.5 | 1.86 | 3.27 |
| Spider | Dense k3 | 43.9 | 28.2 | 69.8 | 2.5 | 1.0 | 5.0 | 1.00 | 3.00 |
| Spider | Dense k3 by database | 46.8 | 30.9 | 46.2 | 28.6 | 18.0 | 24.9 | 2.07 | 1.73 |
| Spider | Dense k5 | 52.3 | 34.0 | 82.7 | 0.0 | 0.0 | 0.0 | 1.00 | 5.00 |
| Spider | Dense k5 by database | 57.5 | 39.0 | 36.4 | 27.6 | 17.2 | 15.1 | 3.20 | 1.84 |
| MMQA | Dense k3 | 20.9 | 12.2 | 39.1 | 3.1 | 1.0 | 7.1 | 1.00 | 3.00 |
| MMQA | Dense k3 by database | 20.9 | 12.2 | 39.1 | 3.1 | 1.0 | 7.1 | 1.00 | 3.00 |
| MMQA | Dense k5 | 29.2 | 17.1 | 55.4 | 0.0 | 0.0 | 0.0 | 1.00 | 5.00 |
| MMQA | Dense k5 by database | 29.2 | 17.1 | 55.4 | 0.0 | 0.0 | 0.0 | 1.00 | 5.00 |
| mean | Dense k3 | 38.5 | 25.6 | 60.3 | 4.0 | 1.4 | 8.2 |  |  |
| worst | Dense k3 | 20.9 | 12.2 | 39.1 | 2.5 | 1.0 | 5.0 |  |  |
| mean | Dense k3 by database | 39.6 | 26.5 | 50.2 | 15.0 | 8.9 | 16.3 |  |  |
| worst | Dense k3 by database | 20.9 | 12.2 | 39.1 | 3.1 | 1.0 | 7.1 |  |  |
| mean | Dense k5 | 47.6 | 31.7 | 74.7 | 0.0 | 0.0 | 0.0 |  |  |
| worst | Dense k5 | 29.2 | 17.1 | 55.4 | 0.0 | 0.0 | 0.0 |  |  |
| mean | Dense k5 by database | 49.3 | 33.4 | 49.5 | 11.1 | 6.9 | 6.2 |  |  |
| worst | Dense k5 by database | 29.2 | 17.1 | 36.4 | 0.0 | 0.0 | 0.0 |  |  |

## Main writer: EX by the row rule and with the column order of results ignored (queries run again in SQLite, no LLM call; BIRD: 6920 queries, 0 failed; Spider: 4605 queries, 0 failed; MMQA: 8042 queries, 0 failed)

| lake | label | method | EX | EX, column order ignored | questions that gain |
|---|---|---|---|---|---|
| BIRD | gold label | Oracle | 51.9 | 52.2 | 4 |
| BIRD | gold label | Dense k3 | 36.9 | 37.1 | 2 |
| BIRD | gold label | MURRE k3 | 42.2 | 42.4 | 2 |
| BIRD | gold label | CORE-T | 47.3 | 47.5 | 3 |
| BIRD | gold label | Route+SQL | 46.9 | 47.2 | 4 |
| BIRD | gold label | AMIGO top-1 | 42.6 | 42.8 | 3 |
| BIRD | gold label | AMIGO | 49.2 | 49.4 | 3 |
| BIRD | gold label | AMIGO with hints | 50.2 | 50.2 | 1 |
| BIRD | multi-valid label | Oracle | 43.6 | 43.7 | 5 |
| BIRD | multi-valid label | Dense k3 | 29.0 | 29.1 | 2 |
| BIRD | multi-valid label | MURRE k3 | 33.3 | 33.4 | 2 |
| BIRD | multi-valid label | CORE-T | 37.6 | 37.8 | 3 |
| BIRD | multi-valid label | Route+SQL | 36.7 | 36.8 | 5 |
| BIRD | multi-valid label | AMIGO top-1 | 33.6 | 33.7 | 4 |
| BIRD | multi-valid label | AMIGO | 38.9 | 39.0 | 4 |
| BIRD | multi-valid label | AMIGO with hints | 40.3 | 40.4 | 2 |
| Spider | gold label | Oracle | 80.0 | 84.6 | 45 |
| Spider | gold label | Dense k3 | 54.9 | 57.3 | 23 |
| Spider | gold label | MURRE k3 | 64.4 | 68.1 | 37 |
| Spider | gold label | CORE-T | 68.6 | 72.5 | 38 |
| Spider | gold label | Route+SQL | 58.0 | 60.3 | 23 |
| Spider | gold label | AMIGO top-1 | 69.6 | 73.4 | 37 |
| Spider | gold label | AMIGO | 76.5 | 81.1 | 45 |
| Spider | gold label | AMIGO with hints | 76.6 | 81.2 | 45 |
| Spider | multi-valid label | Oracle | 71.1 | 75.0 | 49 |
| Spider | multi-valid label | Dense k3 | 40.6 | 42.5 | 25 |
| Spider | multi-valid label | MURRE k3 | 48.3 | 51.2 | 39 |
| Spider | multi-valid label | CORE-T | 50.0 | 53.0 | 40 |
| Spider | multi-valid label | Route+SQL | 44.0 | 46.1 | 26 |
| Spider | multi-valid label | AMIGO top-1 | 51.5 | 54.5 | 40 |
| Spider | multi-valid label | AMIGO | 57.1 | 60.7 | 46 |
| Spider | multi-valid label | AMIGO with hints | 57.5 | 61.1 | 46 |
| MMQA | gold label | Oracle | 73.8 | 74.6 | 8 |
| MMQA | gold label | Dense k3 | 25.1 | 25.4 | 3 |
| MMQA | gold label | MURRE k3 | 31.2 | 31.6 | 4 |
| MMQA | gold label | CORE-T | 50.2 | 50.5 | 3 |
| MMQA | gold label | AMIGO top-1 | 49.4 | 49.7 | 3 |
| MMQA | gold label | AMIGO | 59.4 | 60.0 | 6 |
| MMQA | gold label | AMIGO with hints | 59.6 | 60.2 | 6 |
| MMQA | multi-valid label | Oracle | 60.9 | 61.5 | 8 |
| MMQA | multi-valid label | Dense k3 | 21.1 | 21.2 | 3 |
| MMQA | multi-valid label | MURRE k3 | 25.6 | 25.9 | 5 |
| MMQA | multi-valid label | CORE-T | 36.7 | 36.9 | 5 |
| MMQA | multi-valid label | AMIGO top-1 | 36.5 | 36.8 | 4 |
| MMQA | multi-valid label | AMIGO | 44.1 | 44.5 | 7 |
| MMQA | multi-valid label | AMIGO with hints | 44.9 | 45.3 | 7 |
| mean | gold label | Oracle | 68.6 | 70.5 |  |
| worst | gold label | Oracle | 51.9 | 52.2 |  |
| mean | gold label | Dense k3 | 39.0 | 39.9 |  |
| worst | gold label | Dense k3 | 25.1 | 25.4 |  |
| mean | gold label | MURRE k3 | 45.9 | 47.4 |  |
| worst | gold label | MURRE k3 | 31.2 | 31.6 |  |
| mean | gold label | CORE-T | 55.4 | 56.8 |  |
| worst | gold label | CORE-T | 47.3 | 47.5 |  |
| mean | gold label | Route+SQL | 52.4 | 53.7 |  |
| worst | gold label | Route+SQL | 46.9 | 47.2 |  |
| mean | gold label | AMIGO top-1 | 53.9 | 55.3 |  |
| worst | gold label | AMIGO top-1 | 42.6 | 42.8 |  |
| mean | gold label | AMIGO | 61.7 | 63.5 |  |
| worst | gold label | AMIGO | 49.2 | 49.4 |  |
| mean | gold label | AMIGO with hints | 62.1 | 63.9 |  |
| worst | gold label | AMIGO with hints | 50.2 | 50.2 |  |
| mean | multi-valid label | Oracle | 58.5 | 60.1 |  |
| worst | multi-valid label | Oracle | 43.6 | 43.7 |  |
| mean | multi-valid label | Dense k3 | 30.2 | 30.9 |  |
| worst | multi-valid label | Dense k3 | 21.1 | 21.2 |  |
| mean | multi-valid label | MURRE k3 | 35.7 | 36.8 |  |
| worst | multi-valid label | MURRE k3 | 25.6 | 25.9 |  |
| mean | multi-valid label | CORE-T | 41.4 | 42.6 |  |
| worst | multi-valid label | CORE-T | 36.7 | 36.9 |  |
| mean | multi-valid label | Route+SQL | 40.3 | 41.4 |  |
| worst | multi-valid label | Route+SQL | 36.7 | 36.8 |  |
| mean | multi-valid label | AMIGO top-1 | 40.5 | 41.7 |  |
| worst | multi-valid label | AMIGO top-1 | 33.6 | 33.7 |  |
| mean | multi-valid label | AMIGO | 46.7 | 48.1 |  |
| worst | multi-valid label | AMIGO | 38.9 | 39.0 |  |
| mean | multi-valid label | AMIGO with hints | 47.6 | 48.9 |  |
| worst | multi-valid label | AMIGO with hints | 40.3 | 40.4 |  |

## Mean over the three benchmarks, minus CORE-T: points, 95% interval (stratified paired bootstrap), Holm over the tests of one label; * when below 0.05

| label | method | score | difference |
|---|---|---|---|
| gold label | AMIGO | R | +3.3 [+2.4, +4.1]* |
| gold label | AMIGO | CR | +4.6 [+3.2, +6.0]* |
| gold label | AMIGO | P | +31.3 [+30.2, +32.3]* |
| gold label | AMIGO | CR= | +55.2 [+53.5, +56.9]* |
| gold label | AMIGO | EX | +6.8 [+5.5, +8.0]* |
| gold label | AMIGO top-1 | R | -5.2 [-6.1, -4.2]* |
| gold label | AMIGO top-1 | CR | -8.0 [-9.6, -6.5]* |
| gold label | AMIGO top-1 | P | +26.4 [+25.3, +27.5]* |
| gold label | AMIGO top-1 | CR= | +43.3 [+41.5, +45.2]* |
| gold label | AMIGO top-1 | EX | -1.5 [-2.8, -0.1]* |
| multi-valid label | AMIGO | IR | +9.6 [+8.5, +10.6]* |
| multi-valid label | AMIGO | ICR | +9.4 [+8.2, +10.6]* |
| multi-valid label | AMIGO | IP | -8.4 [-9.7, -7.2]* |
| multi-valid label | AMIGO | IR= | +40.4 [+39.0, +41.8]* |
| multi-valid label | AMIGO | ICR= | +30.7 [+29.2, +32.2]* |
| multi-valid label | AMIGO | IP= | +42.2 [+40.4, +44.0]* |
| multi-valid label | AMIGO | EX | +6.1 [+5.2, +7.1]* |
| multi-valid label | AMIGO top-1 | IR | -3.3 [-4.3, -2.3]* |
| multi-valid label | AMIGO top-1 | ICR | -2.3 [-3.2, -1.3]* |
| multi-valid label | AMIGO top-1 | IP | -5.3 [-6.7, -3.9]* |
| multi-valid label | AMIGO top-1 | IR= | +29.5 [+28.1, +30.9]* |
| multi-valid label | AMIGO top-1 | ICR= | +20.6 [+19.1, +22.0]* |
| multi-valid label | AMIGO top-1 | IP= | +45.6 [+43.7, +47.5]* |
| multi-valid label | AMIGO top-1 | EX | -0.9 [-1.8, -0.0]* |

## Result precision with each failed query counted as a wrong result (main writer)

| lake | label | method | result P | questions with a query |
|---|---|---|---|---|
| BIRD | gold label | Oracle | 51.9 | 1527 |
| BIRD | gold label | Dense k3 | 36.9 | 1527 |
| BIRD | gold label | MURRE k3 | 42.2 | 1527 |
| BIRD | gold label | CORE-T | 47.3 | 1527 |
| BIRD | gold label | Route+SQL | 47.2 | 1518 |
| BIRD | gold label | AMIGO top-1 | 42.6 | 1527 |
| BIRD | gold label | AMIGO | 43.2 | 1527 |
| BIRD | gold label | AMIGO with hints | 41.6 | 1527 |
| BIRD | multi-valid label | Oracle | 54.8 | 1533 |
| BIRD | multi-valid label | Dense k3 | 41.2 | 1533 |
| BIRD | multi-valid label | MURRE k3 | 47.7 | 1533 |
| BIRD | multi-valid label | CORE-T | 52.8 | 1533 |
| BIRD | multi-valid label | Route+SQL | 52.4 | 1524 |
| BIRD | multi-valid label | AMIGO top-1 | 48.0 | 1533 |
| BIRD | multi-valid label | AMIGO | 48.7 | 1533 |
| BIRD | multi-valid label | AMIGO with hints | 47.5 | 1533 |
| Spider | gold label | Oracle | 80.0 | 985 |
| Spider | gold label | Dense k3 | 54.9 | 985 |
| Spider | gold label | MURRE k3 | 64.4 | 985 |
| Spider | gold label | CORE-T | 68.6 | 985 |
| Spider | gold label | Route+SQL | 58.2 | 981 |
| Spider | gold label | AMIGO top-1 | 69.8 | 983 |
| Spider | gold label | AMIGO | 68.0 | 983 |
| Spider | gold label | AMIGO with hints | 66.7 | 983 |
| Spider | multi-valid label | Oracle | 76.6 | 1000 |
| Spider | multi-valid label | Dense k3 | 59.5 | 1000 |
| Spider | multi-valid label | MURRE k3 | 70.6 | 1000 |
| Spider | multi-valid label | CORE-T | 73.8 | 1000 |
| Spider | multi-valid label | Route+SQL | 65.1 | 996 |
| Spider | multi-valid label | AMIGO top-1 | 76.3 | 998 |
| Spider | multi-valid label | AMIGO | 75.3 | 998 |
| Spider | multi-valid label | AMIGO with hints | 74.2 | 998 |
| MMQA | gold label | Oracle | 73.8 | 965 |
| MMQA | gold label | Dense k3 | 25.1 | 965 |
| MMQA | gold label | MURRE k3 | 31.2 | 965 |
| MMQA | gold label | CORE-T | 50.2 | 965 |
| MMQA | gold label | AMIGO top-1 | 49.4 | 965 |
| MMQA | gold label | AMIGO | 48.1 | 965 |
| MMQA | gold label | AMIGO with hints | 45.2 | 965 |
| MMQA | multi-valid label | Oracle | 72.8 | 993 |
| MMQA | multi-valid label | Dense k3 | 34.4 | 993 |
| MMQA | multi-valid label | MURRE k3 | 41.7 | 993 |
| MMQA | multi-valid label | CORE-T | 59.0 | 993 |
| MMQA | multi-valid label | AMIGO top-1 | 57.5 | 993 |
| MMQA | multi-valid label | AMIGO | 56.5 | 993 |
| MMQA | multi-valid label | AMIGO with hints | 53.0 | 993 |
| mean | gold label | Oracle | 68.6 |  |
| worst | gold label | Oracle | 51.9 |  |
| mean | gold label | Dense k3 | 39.0 |  |
| worst | gold label | Dense k3 | 25.1 |  |
| mean | gold label | MURRE k3 | 45.9 |  |
| worst | gold label | MURRE k3 | 31.2 |  |
| mean | gold label | CORE-T | 55.4 |  |
| worst | gold label | CORE-T | 47.3 |  |
| mean | gold label | AMIGO top-1 | 53.9 |  |
| worst | gold label | AMIGO top-1 | 42.6 |  |
| mean | gold label | AMIGO | 53.1 |  |
| worst | gold label | AMIGO | 43.2 |  |
| mean | gold label | AMIGO with hints | 51.2 |  |
| worst | gold label | AMIGO with hints | 41.6 |  |
| mean | multi-valid label | Oracle | 68.1 |  |
| worst | multi-valid label | Oracle | 54.8 |  |
| mean | multi-valid label | Dense k3 | 45.1 |  |
| worst | multi-valid label | Dense k3 | 34.4 |  |
| mean | multi-valid label | MURRE k3 | 53.3 |  |
| worst | multi-valid label | MURRE k3 | 41.7 |  |
| mean | multi-valid label | CORE-T | 61.9 |  |
| worst | multi-valid label | CORE-T | 52.8 |  |
| mean | multi-valid label | AMIGO top-1 | 60.6 |  |
| worst | multi-valid label | AMIGO top-1 | 48.0 |  |
| mean | multi-valid label | AMIGO | 60.2 |  |
| worst | multi-valid label | AMIGO | 48.7 |  |
| mean | multi-valid label | AMIGO with hints | 58.2 |  |
| worst | multi-valid label | AMIGO with hints | 47.5 |  |

## EX of found targets by the extra tables of the smallest returned set that holds them (main writer; pooled over targets; not controlled)

| lake | label | method | extra tables | targets | EX |
|---|---|---|---|---|---|
| BIRD | gold label | CORE-T | 0 | 331 | 45.9 |
| BIRD | gold label | CORE-T | 1 | 618 | 56.6 |
| BIRD | gold label | CORE-T | 2 or more | 469 | 43.9 |
| BIRD | gold label | AMIGO top-1 | 0 | 1024 | 53.5 |
| BIRD | gold label | AMIGO top-1 | 1 | 149 | 41.6 |
| BIRD | gold label | AMIGO top-1 | 2 or more | 13 | 30.8 |
| BIRD | gold label | AMIGO | 0 | 1223 | 54.8 |
| BIRD | gold label | AMIGO | 1 | 146 | 42.5 |
| BIRD | gold label | AMIGO | 2 or more | 12 | 50.0 |
| BIRD | multi-valid label | CORE-T | 0 | 589 | 36.3 |
| BIRD | multi-valid label | CORE-T | 1 | 1000 | 38.2 |
| BIRD | multi-valid label | CORE-T | 2 or more | 788 | 25.5 |
| BIRD | multi-valid label | AMIGO top-1 | 0 | 1653 | 39.3 |
| BIRD | multi-valid label | AMIGO top-1 | 1 | 175 | 27.4 |
| BIRD | multi-valid label | AMIGO top-1 | 2 or more | 17 | 23.5 |
| BIRD | multi-valid label | AMIGO | 0 | 1938 | 40.2 |
| BIRD | multi-valid label | AMIGO | 1 | 184 | 25.5 |
| BIRD | multi-valid label | AMIGO | 2 or more | 19 | 31.6 |
| Spider | gold label | CORE-T | 0 | 244 | 76.2 |
| Spider | gold label | CORE-T | 1 | 381 | 79.5 |
| Spider | gold label | CORE-T | 2 or more | 216 | 77.8 |
| Spider | gold label | AMIGO top-1 | 0 | 796 | 79.9 |
| Spider | gold label | AMIGO top-1 | 1 | 41 | 75.6 |
| Spider | gold label | AMIGO top-1 | 2 or more | 4 | 75.0 |
| Spider | gold label | AMIGO | 0 | 906 | 80.0 |
| Spider | gold label | AMIGO | 1 | 31 | 77.4 |
| Spider | gold label | AMIGO | 2 or more | 4 | 75.0 |
| Spider | multi-valid label | CORE-T | 0 | 372 | 66.4 |
| Spider | multi-valid label | CORE-T | 1 | 460 | 63.9 |
| Spider | multi-valid label | CORE-T | 2 or more | 366 | 47.8 |
| Spider | multi-valid label | AMIGO top-1 | 0 | 1006 | 72.9 |
| Spider | multi-valid label | AMIGO top-1 | 1 | 55 | 34.5 |
| Spider | multi-valid label | AMIGO top-1 | 2 or more | 4 | 75.0 |
| Spider | multi-valid label | AMIGO | 0 | 1305 | 72.0 |
| Spider | multi-valid label | AMIGO | 1 | 67 | 31.3 |
| Spider | multi-valid label | AMIGO | 2 or more | 4 | 75.0 |
| MMQA | gold label | CORE-T | 0 | 213 | 77.5 |
| MMQA | gold label | CORE-T | 1 | 203 | 70.0 |
| MMQA | gold label | CORE-T | 2 or more | 271 | 56.8 |
| MMQA | gold label | AMIGO top-1 | 0 | 507 | 77.9 |
| MMQA | gold label | AMIGO top-1 | 1 | 64 | 59.4 |
| MMQA | gold label | AMIGO top-1 | 2 or more | 41 | 46.3 |
| MMQA | gold label | AMIGO | 0 | 614 | 77.4 |
| MMQA | gold label | AMIGO | 1 | 74 | 64.9 |
| MMQA | gold label | AMIGO | 2 or more | 63 | 49.2 |
| MMQA | multi-valid label | CORE-T | 0 | 309 | 68.0 |
| MMQA | multi-valid label | CORE-T | 1 | 303 | 49.8 |
| MMQA | multi-valid label | CORE-T | 2 or more | 531 | 34.8 |
| MMQA | multi-valid label | AMIGO top-1 | 0 | 648 | 70.5 |
| MMQA | multi-valid label | AMIGO top-1 | 1 | 103 | 32.0 |
| MMQA | multi-valid label | AMIGO top-1 | 2 or more | 94 | 26.6 |
| MMQA | multi-valid label | AMIGO | 0 | 872 | 68.8 |
| MMQA | multi-valid label | AMIGO | 1 | 162 | 35.8 |
| MMQA | multi-valid label | AMIGO | 2 or more | 216 | 33.8 |

## Place judge only (no join choice), search run again with the edge threshold at 1/3 and 2/3 (layer unchanged) and with 20 columns per part (stored grades), gold label

| lake | variant | R | CR | P | CR= | sets | size | table pairs joined | places not graded | questions run again | same lists at 30 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | edge threshold 1/3 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 | 80 | 0 | 1534 | 1534 |
| BIRD | edge threshold 2/3 | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 | 79 | 0 | 1534 | 1534 |
| BIRD | 20 columns per part | 95.4 | 90.0 | 93.7 | 79.5 | 1.43 | 1.96 | 80 | 0 | 1534 | 1534 |
| Spider | edge threshold 1/3 | 95.9 | 94.7 | 95.3 | 91.6 | 1.70 | 1.53 | 837 | 0 | 1033 | 1033 |
| Spider | edge threshold 2/3 | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 | 800 | 0 | 1033 | 1033 |
| Spider | 20 columns per part | 95.9 | 94.7 | 95.4 | 91.2 | 1.65 | 1.53 | 825 | 0 | 1033 | 1033 |
| MMQA | edge threshold 1/3 | 89.3 | 78.9 | 82.9 | 63.4 | 4.43 | 3.16 | 1758 | 0 | 1097 | 1097 |
| MMQA | edge threshold 2/3 | 80.6 | 62.9 | 83.4 | 51.0 | 3.97 | 3.10 | 1129 | 0 | 1097 | 1097 |
| MMQA | 20 columns per part | 87.2 | 75.3 | 82.6 | 60.9 | 4.16 | 3.12 | 1540 | 0 | 1097 | 1097 |
| mean | edge threshold 1/3 | 93.6 | 88.0 | 90.6 | 78.3 |
| mean | edge threshold 2/3 | 90.8 | 82.8 | 90.8 | 74.2 |
| mean | 20 columns per part | 92.8 | 86.7 | 90.6 | 77.2 |
| worst | edge threshold 1/3 | 89.3 | 78.9 | 82.9 | 63.4 |
| worst | edge threshold 2/3 | 80.6 | 62.9 | 83.4 | 51.0 |
| worst | 20 columns per part | 87.2 | 75.3 | 82.6 | 60.9 |

## Place judge only (no join choice), search run again with the edge threshold at 1/3 and 2/3 (layer unchanged) and with 20 columns per part (stored grades), multi-valid label

| lake | variant | IR | ICR | IP | IR= | ICR= | IP= | sets | size | table pairs joined | places not graded | questions run again | same lists at 30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | edge threshold 1/3 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 | 80 | 0 | 1534 | 1534 |
| BIRD | edge threshold 2/3 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 | 79 | 0 | 1534 | 1534 |
| BIRD | 20 columns per part | 72.5 | 56.7 | 83.0 | 67.8 | 52.5 | 77.4 | 1.43 | 1.96 | 80 | 0 | 1534 | 1534 |
| Spider | edge threshold 1/3 | 70.5 | 49.6 | 89.1 | 69.5 | 49.0 | 87.6 | 1.70 | 1.53 | 837 | 0 | 1033 | 1033 |
| Spider | edge threshold 2/3 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 | 800 | 0 | 1033 | 1033 |
| Spider | 20 columns per part | 70.1 | 49.3 | 89.2 | 68.8 | 48.4 | 87.3 | 1.65 | 1.53 | 825 | 0 | 1033 | 1033 |
| MMQA | edge threshold 1/3 | 55.2 | 35.8 | 66.8 | 44.6 | 29.7 | 53.9 | 4.43 | 3.16 | 1758 | 0 | 1097 | 1097 |
| MMQA | edge threshold 2/3 | 43.9 | 28.7 | 54.6 | 35.7 | 23.9 | 44.2 | 3.97 | 3.10 | 1129 | 0 | 1097 | 1097 |
| MMQA | 20 columns per part | 52.2 | 33.9 | 64.8 | 42.8 | 28.7 | 53.4 | 4.16 | 3.12 | 1540 | 0 | 1097 | 1097 |
| mean | edge threshold 1/3 | 66.2 | 47.6 | 79.7 | 60.8 | 44.0 | 73.1 |
| mean | edge threshold 2/3 | 62.6 | 45.4 | 75.8 | 57.8 | 42.0 | 69.8 |
| mean | 20 columns per part | 65.0 | 46.7 | 79.0 | 59.8 | 43.2 | 72.7 |
| worst | edge threshold 1/3 | 55.2 | 35.8 | 66.8 | 44.6 | 29.7 | 53.9 |
| worst | edge threshold 2/3 | 43.9 | 28.7 | 54.6 | 35.7 | 23.9 | 44.2 |
| worst | 20 columns per part | 52.2 | 33.9 | 64.8 | 42.8 | 28.7 | 53.4 |

## Multi-valid results out of the Oracle's reach, by the rule for when a labeled table set serves a result

| lake | results | equals its tables | contains its tables |
|---|---|---|---|
| BIRD | 2888 | 549 | 541 |
| Spider | 2214 | 159 | 159 |
| MMQA | 2498 | 98 | 91 |

## Complete recall pooled over the targets only from value-only alternatives and over the other table-set targets of the multi-valid label (no LLM call, not tested)

| lake | method | value-only targets | CR on them | other targets | CR on them |
|---|---|---|---|---|---|
| BIRD | AMIGO | 51 | 21.6 | 2837 | 63.1 |
| BIRD | CORE-T | 51 | 39.2 | 2837 | 76.9 |
| Spider | AMIGO | 20 | 15.0 | 2415 | 59.2 |
| Spider | CORE-T | 20 | 15.0 | 2415 | 51.2 |
| MMQA | AMIGO | 147 | 9.5 | 3502 | 39.7 |
| MMQA | CORE-T | 147 | 3.4 | 3502 | 36.7 |

## Multi-valid table-set targets that only alternatives found by the labeler's value signal alone give

| lake | questions | table-set targets | targets only from value-only alternatives | questions with such a target | alternatives that ran | of them found by the value signal alone |
|---|---|---|---|---|---|---|
| BIRD | 1534 | 2888 | 51 | 50 | 2805 | 94 |
| Spider | 1034 | 2435 | 20 | 13 | 1899 | 29 |
| MMQA | 1049 | 3649 | 147 | 83 | 3092 | 168 |

## Input and output tokens per question over all questions, from the logs of the scored runs (empty: no call made, every question failed)

| lake | LLM step | questions | input tokens per question | output tokens per question |
|---|---|---|---|---|
| BIRD | AMIGO place judge | 1534 | 6485 | 2273 |
| BIRD | AMIGO join choice | 1534 | 108 | 59 |
| BIRD | CORE-T | 1534 | 8382 | 1853 |
| BIRD | Route+SQL | 1534 | 4247 | 579 |
| BIRD | Full schema | 1534 | 5818 | 376 |
| Spider | AMIGO place judge | 1034 | 4995 | 2723 |
| Spider | AMIGO join choice | 1034 | 58 | 39 |
| Spider | CORE-T | 1034 | 5292 | 2372 |
| Spider | Route+SQL | 1034 | 1808 | 508 |
| Spider | Full schema | 1034 |  |  |
| MMQA | AMIGO place judge | 1105 | 6319 | 3831 |
| MMQA | AMIGO join choice | 1105 | 117 | 113 |
| MMQA | CORE-T | 1105 | 6054 | 2568 |
| MMQA | Full schema | 1105 |  |  |

## Stage 2, main writer, on the questions whose candidates are all relaxed (queries already written, no LLM call; not tested)

| label | lake | questions with only relaxed candidates | of them kept by stage 2 | AMIGO EX | CORE-T EX |
|---|---|---|---|---|---|
| gold label | BIRD | 183 | 183 | 40.4 | 39.9 |
| gold label | Spider | 70 | 68 | 61.8 | 61.8 |
| gold label | MMQA | 122 | 108 | 37.0 | 45.4 |
| multi-valid label | BIRD | 183 | 183 | 31.2 | 32.7 |
| multi-valid label | Spider | 70 | 69 | 46.9 | 40.4 |
| multi-valid label | MMQA | 122 | 113 | 28.9 | 33.4 |

## Output size three ways (sets, distinct tables, tables with repetition), gold label (stage 1)

| lake | method | sets | size | tables with repetition | R | CR | P | CR= | set F1 |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 1.00 | 3.00 | 3.00 | 83.1 | 68.6 | 51.8 | 3.9 | 68.6 |
| BIRD | MURRE k3 | 1.00 | 3.00 | 3.00 | 89.0 | 78.7 | 56.1 | 6.6 | 78.7 |
| BIRD | CORE-T | 1.00 | 3.19 | 3.19 | 96.5 | 92.9 | 62.8 | 21.6 | 92.9 |
| BIRD | Route+SQL | 0.99 | 1.87 | 1.87 | 88.7 | 81.5 | 90.7 | 78.0 | 81.5 |
| BIRD | AMIGO top-1 | 1.00 | 1.88 | 1.88 | 89.1 | 77.6 | 92.1 | 66.9 | 77.6 |
| BIRD | AMIGO | 1.44 | 2.17 | 2.91 | 95.6 | 90.4 | 93.7 | 80.1 | 79.0 |
| BIRD | place judge only (no join choice) | 1.44 | 2.17 | 2.91 | 95.6 | 90.4 | 93.7 | 80.1 | 79.0 |
| BIRD | AMIGO within CORE-T's tables | 1.16 | 2.00 | 2.18 | 92.5 | 83.2 | 92.8 | 72.6 | 79.1 |
| Spider | Dense k3 | 1.00 | 3.00 | 3.00 | 73.5 | 63.9 | 37.1 | 2.2 | 63.9 |
| Spider | MURRE k3 | 1.00 | 3.00 | 3.00 | 85.1 | 79.3 | 42.3 | 3.0 | 79.3 |
| Spider | CORE-T | 1.00 | 2.68 | 2.68 | 89.3 | 84.9 | 57.4 | 25.4 | 84.9 |
| Spider | Route+SQL | 1.00 | 1.60 | 1.60 | 68.1 | 67.4 | 68.0 | 65.8 | 67.4 |
| Spider | AMIGO top-1 | 1.00 | 1.50 | 1.50 | 87.2 | 84.6 | 87.2 | 80.3 | 84.6 |
| Spider | AMIGO | 1.69 | 2.18 | 2.58 | 96.1 | 95.1 | 95.3 | 91.7 | 82.5 |
| Spider | place judge only (no join choice) | 1.69 | 2.18 | 2.58 | 96.1 | 95.1 | 95.3 | 91.7 | 82.5 |
| Spider | AMIGO within CORE-T's tables | 1.23 | 1.73 | 1.78 | 92.5 | 90.4 | 91.9 | 86.1 | 85.6 |
| MMQA | Dense k3 | 1.00 | 3.00 | 3.00 | 59.0 | 31.4 | 42.8 | 2.8 | 31.4 |
| MMQA | MURRE k3 | 1.00 | 3.00 | 3.00 | 62.6 | 41.3 | 45.2 | 4.5 | 41.3 |
| MMQA | CORE-T | 1.00 | 3.78 | 3.78 | 84.1 | 70.6 | 58.1 | 21.7 | 70.6 |
| MMQA | AMIGO top-1 | 1.00 | 2.62 | 2.62 | 78.0 | 62.2 | 78.2 | 51.5 | 62.2 |
| MMQA | AMIGO | 4.19 | 5.29 | 17.82 | 87.9 | 76.7 | 83.0 | 62.5 | 58.0 |
| MMQA | place judge only (no join choice) | 4.31 | 5.35 | 18.60 | 87.9 | 76.7 | 83.0 | 62.5 | 58.0 |
| MMQA | AMIGO within CORE-T's tables | 1.24 | 2.86 | 3.11 | 81.2 | 66.4 | 80.2 | 55.1 | 63.4 |
| mean | Dense k3 | 1.00 | 3.00 | 3.00 | 71.9 | 54.6 | 43.9 | 3.0 | 54.6 |
| mean | MURRE k3 | 1.00 | 3.00 | 3.00 | 78.9 | 66.4 | 47.9 | 4.7 | 66.4 |
| mean | CORE-T | 1.00 | 3.22 | 3.22 | 89.9 | 82.8 | 59.4 | 22.9 | 82.8 |
| mean | AMIGO top-1 | 1.00 | 2.00 | 2.00 | 84.8 | 74.8 | 85.8 | 66.2 | 74.8 |
| mean | AMIGO | 2.44 | 3.21 | 7.77 | 93.2 | 87.4 | 90.7 | 78.1 | 73.2 |
| mean | place judge only (no join choice) | 2.48 | 3.23 | 8.03 | 93.2 | 87.4 | 90.7 | 78.1 | 73.2 |
| mean | AMIGO within CORE-T's tables | 1.21 | 2.19 | 2.35 | 88.7 | 80.0 | 88.3 | 71.3 | 76.1 |
| worst | Dense k3 | 1.00 | 3.00 | 3.00 | 59.0 | 31.4 | 37.1 | 2.2 | 31.4 |
| worst | MURRE k3 | 1.00 | 3.00 | 3.00 | 62.6 | 41.3 | 42.3 | 3.0 | 41.3 |
| worst | CORE-T | 1.00 | 3.78 | 3.78 | 84.1 | 70.6 | 57.4 | 21.6 | 70.6 |
| worst | AMIGO top-1 | 1.00 | 2.62 | 2.62 | 78.0 | 62.2 | 78.2 | 51.5 | 62.2 |
| worst | AMIGO | 4.19 | 5.29 | 17.82 | 87.9 | 76.7 | 83.0 | 62.5 | 58.0 |
| worst | place judge only (no join choice) | 4.31 | 5.35 | 18.60 | 87.9 | 76.7 | 83.0 | 62.5 | 58.0 |
| worst | AMIGO within CORE-T's tables | 1.24 | 2.86 | 3.11 | 81.2 | 66.4 | 80.2 | 55.1 | 63.4 |

## Minus CORE-T, gold label: points, 95% interval, Holm over the 5 tests of one lake; * when below 0.05

| lake | method | score | minus CORE-T |
|---|---|---|---|
| BIRD | place judge only (no join choice) | R | -0.8 [-1.7, -0.0]* |
| BIRD | place judge only (no join choice) | CR | -2.5 [-4.0, -0.8]* |
| BIRD | place judge only (no join choice) | P | +30.9 [+29.6, +32.2]* |
| BIRD | place judge only (no join choice) | CR= | +58.5 [+55.8, +61.1]* |
| BIRD | place judge only (no join choice) | set F1 | -13.9 [-15.6, -12.1]* |
| Spider | place judge only (no join choice) | R | +6.8 [+5.1, +8.5]* |
| Spider | place judge only (no join choice) | CR | +10.2 [+7.9, +12.4]* |
| Spider | place judge only (no join choice) | P | +38.0 [+36.0, +39.9]* |
| Spider | place judge only (no join choice) | CR= | +66.2 [+63.2, +69.2]* |
| Spider | place judge only (no join choice) | set F1 | -2.4 [-4.8, -0.1]* |
| MMQA | place judge only (no join choice) | R | +3.8 [+2.1, +5.6]* |
| MMQA | place judge only (no join choice) | CR | +6.1 [+2.9, +9.3]* |
| MMQA | place judge only (no join choice) | P | +24.9 [+22.8, +27.0]* |
| MMQA | place judge only (no join choice) | CR= | +40.8 [+37.6, +44.1]* |
| MMQA | place judge only (no join choice) | set F1 | -12.6 [-15.7, -9.7]* |

## Output size three ways (sets, distinct tables, tables with repetition), multi-valid label (stage 1)

| lake | method | sets | size | tables with repetition | IR | ICR | IP | IR= | ICR= | IP= | set F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 1.00 | 3.00 | 3.00 | 50.9 | 36.2 | 72.0 | 6.3 | 2.3 | 12.4 | 56.6 |
| BIRD | MURRE k3 | 1.00 | 3.00 | 3.00 | 58.5 | 41.9 | 82.7 | 8.9 | 4.0 | 17.1 | 65.0 |
| BIRD | CORE-T | 1.00 | 3.19 | 3.19 | 68.1 | 49.7 | 94.9 | 22.6 | 16.3 | 31.3 | 75.3 |
| BIRD | Route+SQL | 0.99 | 1.87 | 1.87 | 62.6 | 45.3 | 88.1 | 60.9 | 44.1 | 85.7 | 69.5 |
| BIRD | AMIGO top-1 | 1.00 | 1.88 | 1.88 | 60.0 | 43.5 | 83.8 | 56.0 | 40.4 | 78.6 | 66.5 |
| BIRD | AMIGO | 1.44 | 2.17 | 2.91 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 72.6 |
| BIRD | place judge only (no join choice) | 1.44 | 2.17 | 2.91 | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 72.6 |
| BIRD | AMIGO within CORE-T's tables | 1.16 | 2.00 | 2.18 | 65.0 | 48.1 | 84.0 | 60.9 | 44.9 | 78.6 | 69.2 |
| Spider | Dense k3 | 1.00 | 3.00 | 3.00 | 43.9 | 28.2 | 69.8 | 2.5 | 1.0 | 5.0 | 50.3 |
| Spider | MURRE k3 | 1.00 | 3.00 | 3.00 | 55.4 | 37.1 | 85.8 | 3.7 | 1.7 | 6.5 | 63.0 |
| Spider | CORE-T | 1.00 | 2.68 | 2.68 | 57.5 | 37.7 | 90.2 | 21.3 | 13.0 | 33.5 | 65.7 |
| Spider | Route+SQL | 1.00 | 1.60 | 1.60 | 48.2 | 31.2 | 76.0 | 47.8 | 31.2 | 75.0 | 55.2 |
| Spider | AMIGO top-1 | 1.00 | 1.50 | 1.50 | 59.6 | 39.7 | 92.6 | 58.7 | 39.6 | 90.7 | 67.8 |
| Spider | AMIGO | 1.69 | 2.18 | 2.58 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 74.3 |
| Spider | place judge only (no join choice) | 1.69 | 2.18 | 2.58 | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 74.3 |
| Spider | AMIGO within CORE-T's tables | 1.23 | 1.73 | 1.78 | 63.7 | 42.3 | 92.0 | 62.8 | 42.1 | 90.2 | 71.0 |
| MMQA | Dense k3 | 1.00 | 3.00 | 3.00 | 20.9 | 12.2 | 39.1 | 3.1 | 1.0 | 7.1 | 24.8 |
| MMQA | MURRE k3 | 1.00 | 3.00 | 3.00 | 27.3 | 16.3 | 49.8 | 4.5 | 1.9 | 9.4 | 32.2 |
| MMQA | CORE-T | 1.00 | 3.78 | 3.78 | 42.8 | 26.4 | 78.6 | 16.5 | 10.1 | 28.0 | 50.3 |
| MMQA | AMIGO top-1 | 1.00 | 2.62 | 2.62 | 38.9 | 23.7 | 71.3 | 34.1 | 21.2 | 60.4 | 45.7 |
| MMQA | AMIGO | 4.19 | 5.29 | 17.82 | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 50.6 |
| MMQA | place judge only (no join choice) | 4.31 | 5.35 | 18.60 | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 50.5 |
| MMQA | AMIGO within CORE-T's tables | 1.24 | 2.86 | 3.11 | 41.9 | 25.2 | 72.0 | 36.8 | 22.4 | 60.7 | 48.1 |
| mean | Dense k3 | 1.00 | 3.00 | 3.00 | 38.5 | 25.6 | 60.3 | 4.0 | 1.4 | 8.2 | 43.9 |
| mean | MURRE k3 | 1.00 | 3.00 | 3.00 | 47.1 | 31.8 | 72.8 | 5.7 | 2.5 | 11.0 | 53.4 |
| mean | CORE-T | 1.00 | 3.22 | 3.22 | 56.1 | 37.9 | 87.9 | 20.1 | 13.1 | 30.9 | 63.8 |
| mean | AMIGO top-1 | 1.00 | 2.00 | 2.00 | 52.8 | 35.7 | 82.6 | 49.6 | 33.7 | 76.6 | 60.0 |
| mean | AMIGO | 2.44 | 3.21 | 7.77 | 65.7 | 47.3 | 79.5 | 60.6 | 43.8 | 73.1 | 65.8 |
| mean | place judge only (no join choice) | 2.48 | 3.23 | 8.03 | 65.7 | 47.3 | 79.4 | 60.6 | 43.8 | 73.1 | 65.8 |
| mean | AMIGO within CORE-T's tables | 1.21 | 2.19 | 2.35 | 56.9 | 38.5 | 82.7 | 53.5 | 36.4 | 76.5 | 62.8 |
| worst | Dense k3 | 1.00 | 3.00 | 3.00 | 20.9 | 12.2 | 39.1 | 2.5 | 1.0 | 5.0 | 24.8 |
| worst | MURRE k3 | 1.00 | 3.00 | 3.00 | 27.3 | 16.3 | 49.8 | 3.7 | 1.7 | 6.5 | 32.2 |
| worst | CORE-T | 1.00 | 3.78 | 3.78 | 42.8 | 26.4 | 78.6 | 16.5 | 10.1 | 28.0 | 50.3 |
| worst | AMIGO top-1 | 1.00 | 2.62 | 2.62 | 38.9 | 23.7 | 71.3 | 34.1 | 21.2 | 60.4 | 45.7 |
| worst | AMIGO | 4.19 | 5.29 | 17.82 | 53.3 | 34.5 | 65.6 | 43.9 | 29.4 | 54.0 | 50.6 |
| worst | place judge only (no join choice) | 4.31 | 5.35 | 18.60 | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 50.5 |
| worst | AMIGO within CORE-T's tables | 1.24 | 2.86 | 3.11 | 41.9 | 25.2 | 72.0 | 36.8 | 22.4 | 60.7 | 48.1 |

## Minus CORE-T, multi-valid label: points, 95% interval, Holm over the 7 tests of one lake; * when below 0.05

| lake | method | score | minus CORE-T |
|---|---|---|---|
| BIRD | place judge only (no join choice) | IR | +5.0 [+3.7, +6.3]* |
| BIRD | place judge only (no join choice) | ICR | +7.8 [+6.1, +9.5]* |
| BIRD | place judge only (no join choice) | IP | -11.8 [-13.4, -10.2]* |
| BIRD | place judge only (no join choice) | IR= | +45.7 [+43.4, +48.0]* |
| BIRD | place judge only (no join choice) | ICR= | +36.8 [+34.2, +39.4]* |
| BIRD | place judge only (no join choice) | IP= | +46.4 [+43.7, +49.1]* |
| BIRD | place judge only (no join choice) | set F1 | -2.7 [-4.0, -1.4]* |
| Spider | place judge only (no join choice) | IR | +13.2 [+11.4, +15.0]* |
| Spider | place judge only (no join choice) | ICR | +12.3 [+10.2, +14.4]* |
| Spider | place judge only (no join choice) | IP | -0.6 [-2.7, +1.5] |
| Spider | place judge only (no join choice) | IR= | +48.1 [+45.5, +50.6]* |
| Spider | place judge only (no join choice) | ICR= | +36.1 [+33.1, +39.1]* |
| Spider | place judge only (no join choice) | IP= | +54.1 [+50.8, +57.4]* |
| Spider | place judge only (no join choice) | set F1 | +8.5 [+6.7, +10.3]* |
| MMQA | place judge only (no join choice) | IR | +10.5 [+8.2, +12.7]* |
| MMQA | place judge only (no join choice) | ICR | +8.1 [+5.8, +10.4]* |
| MMQA | place judge only (no join choice) | IP | -13.0 [-15.9, -10.1]* |
| MMQA | place judge only (no join choice) | IR= | +27.5 [+25.0, +29.9]* |
| MMQA | place judge only (no join choice) | ICR= | +19.3 [+16.7, +21.7]* |
| MMQA | place judge only (no join choice) | IP= | +25.9 [+22.6, +29.2]* |
| MMQA | place judge only (no join choice) | set F1 | +0.2 [-1.9, +2.3] |

## MMQA with tables sharing a base name taken as one, in outputs and labels, gold label (stage 1)

| method | R | CR | P | CR= | sets | size |
|---|---|---|---|---|---|---|
| Dense k3 | 68.6 | 41.9 | 56.0 | 9.8 | 1.00 | 2.72 |
| MURRE k3 | 71.5 | 50.7 | 60.7 | 20.9 | 1.00 | 2.64 |
| CORE-T | 89.0 | 78.0 | 67.4 | 28.0 | 1.00 | 3.20 |
| AMIGO top-1 | 83.7 | 70.1 | 83.7 | 57.1 | 1.00 | 2.57 |
| AMIGO | 91.9 | 83.8 | 86.5 | 67.7 | 2.63 | 2.98 |
| place judge only (no join choice) | 91.9 | 83.8 | 86.5 | 67.7 | 2.68 | 2.98 |

## MMQA with base names merged, AMIGO minus CORE-T, gold label: points, 95% interval, Holm over the scores; * when below 0.05

| R | CR | P | CR= |
|---|---|---|---|
| +2.9 [+1.3, +4.4]* | +5.8 [+2.8, +8.9]* | +19.1 [+17.1, +21.0]* | +39.7 [+36.2, +43.2]* |

## MMQA with tables sharing a base name taken as one, in outputs and labels, multi-valid label (stage 1)

| method | IR | ICR | IP | IR= | ICR= | IP= | sets | size |
|---|---|---|---|---|---|---|---|---|
| Dense k3 | 29.2 | 18.1 | 49.1 | 8.8 | 4.5 | 16.1 | 1.00 | 2.72 |
| MURRE k3 | 35.8 | 22.9 | 58.5 | 16.5 | 10.2 | 27.3 | 1.00 | 2.64 |
| CORE-T | 50.6 | 32.6 | 83.1 | 21.7 | 12.7 | 36.1 | 1.00 | 3.20 |
| AMIGO top-1 | 45.7 | 28.9 | 75.8 | 40.0 | 25.8 | 64.2 | 1.00 | 2.57 |
| AMIGO | 60.7 | 41.7 | 70.2 | 50.2 | 35.2 | 58.0 | 2.63 | 2.98 |
| place judge only (no join choice) | 60.7 | 41.7 | 70.1 | 50.3 | 35.2 | 57.9 | 2.68 | 2.98 |

## MMQA with base names merged, AMIGO minus CORE-T, multi-valid label: points, 95% interval, Holm over the scores; * when below 0.05

| IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|
| +10.1 [+7.8, +12.4]* | +9.1 [+6.7, +11.5]* | -12.9 [-15.7, -10.0]* | +28.5 [+25.8, +31.2]* | +22.5 [+19.8, +25.3]* | +21.8 [+18.3, +25.4]* |

## Link rules with declared keys hidden: pairs of tables joined by a rule link of weight 1/2 or more, against pairs of tables of a declared foreign key (judged links left out)

| lake | hidden | rule | rule table pairs | declared table pairs | both | precision | recall |
|---|---|---|---|---|---|---|---|
| BIRD | foreign keys | inferred, text columns (containment) | 11 | 74 | 10 | 90.9 | 13.5 |
| BIRD | foreign keys | inferred, number columns (name rule) | 35 | 74 | 35 | 100.0 | 47.3 |
| BIRD | foreign keys | near-key rules (by values, by names and values, by few values) | 64 | 74 | 60 | 93.8 | 81.1 |
| BIRD | foreign keys | by name onto or out of an empty table | 0 | 74 | 0 | n/a | 0.0 |
| BIRD | foreign keys | any rule | 70 | 74 | 66 | 94.3 | 89.2 |
| BIRD | foreign and primary keys | inferred, text columns (containment) | 11 | 74 | 10 | 90.9 | 13.5 |
| BIRD | foreign and primary keys | inferred, number columns (name rule) | 35 | 74 | 35 | 100.0 | 47.3 |
| BIRD | foreign and primary keys | near-key rules (by values, by names and values, by few values) | 64 | 74 | 60 | 93.8 | 81.1 |
| BIRD | foreign and primary keys | by name onto or out of an empty table | 0 | 74 | 0 | n/a | 0.0 |
| BIRD | foreign and primary keys | any rule | 70 | 74 | 66 | 94.3 | 89.2 |
| Spider | foreign keys | inferred, text columns (containment) | 91 | 744 | 80 | 87.9 | 10.8 |
| Spider | foreign keys | inferred, number columns (name rule) | 455 | 744 | 406 | 89.2 | 54.6 |
| Spider | foreign keys | near-key rules (by values, by names and values, by few values) | 265 | 744 | 233 | 87.9 | 31.3 |
| Spider | foreign keys | by name onto or out of an empty table | 1 | 744 | 0 | 0.0 | 0.0 |
| Spider | foreign keys | any rule | 610 | 744 | 534 | 87.5 | 71.8 |
| Spider | foreign and primary keys | inferred, text columns (containment) | 91 | 744 | 80 | 87.9 | 10.8 |
| Spider | foreign and primary keys | inferred, number columns (name rule) | 455 | 744 | 406 | 89.2 | 54.6 |
| Spider | foreign and primary keys | near-key rules (by values, by names and values, by few values) | 248 | 744 | 218 | 87.9 | 29.3 |
| Spider | foreign and primary keys | by name onto or out of an empty table | 1 | 744 | 0 | 0.0 | 0.0 |
| Spider | foreign and primary keys | any rule | 605 | 744 | 530 | 87.6 | 71.2 |

## Place-judge prompts cut in two (amigo.log of the 2026-11-08 run; all are cut into the number of calls given). The same log line is written for AMIGO-WJ's whole judge, whose prompt holds at most 50 candidates, so a cut prompt of more items is a place-judge prompt

| lake | questions | cut prompts, every run of the log | cut prompts, the run with the most | most calls per prompt | fewest items in a cut prompt |
|---|---|---|---|---|---|
| BIRD | 1534 | 0 | 0 | 0 | 0 |
| Spider | 1034 | 0 | 0 | 0 | 0 |
| MMQA | 1105 | 0 | 0 | 0 | 0 |

Join-choice prompts cut (joinchoice.log of each lake): ; none on the others.

## Per-version means with 95% intervals (bootstrap over questions), gold label; widest interval over both labels 6.2 points

| lake | method | R | CR | P | CR= |
|---|---|---|---|---|---|
| BIRD | Dense k3 | 83.1 [81.7, 84.5] | 68.6 [66.3, 70.9] | 51.8 [50.7, 52.8] | 3.9 [3.0, 4.9] |
| BIRD | MURRE k3 | 89.0 [87.9, 90.2] | 78.7 [76.6, 80.8] | 56.1 [55.1, 57.2] | 6.6 [5.4, 7.9] |
| BIRD | CORE-T | 96.5 [95.8, 97.1] | 92.9 [91.6, 94.2] | 62.8 [61.6, 64.1] | 21.6 [19.6, 23.7] |
| BIRD | Route+SQL | 88.7 [87.3, 90.0] | 81.5 [79.5, 83.4] | 90.7 [89.4, 92.0] | 78.0 [75.9, 80.1] |
| BIRD | AMIGO top-1 | 89.1 [88.0, 90.2] | 77.6 [75.5, 79.7] | 92.1 [91.1, 93.0] | 66.9 [64.6, 69.3] |
| BIRD | AMIGO | 95.6 [94.9, 96.3] | 90.4 [88.9, 91.9] | 93.7 [92.9, 94.6] | 80.1 [78.0, 82.0] |
| Spider | Dense k3 | 73.5 [71.1, 75.8] | 63.9 [60.9, 66.8] | 37.1 [35.7, 38.6] | 2.2 [1.4, 3.2] |
| Spider | MURRE k3 | 85.1 [83.1, 87.0] | 79.3 [76.9, 81.7] | 42.3 [40.9, 43.6] | 3.0 [2.0, 4.1] |
| Spider | CORE-T | 89.3 [87.6, 90.9] | 84.9 [82.7, 87.0] | 57.4 [55.5, 59.2] | 25.4 [22.8, 28.1] |
| Spider | Route+SQL | 68.1 [65.3, 70.9] | 67.4 [64.5, 70.3] | 68.0 [65.2, 70.9] | 65.8 [62.9, 68.7] |
| Spider | AMIGO top-1 | 87.2 [85.2, 89.1] | 84.6 [82.4, 86.8] | 87.2 [85.2, 89.1] | 80.3 [77.9, 82.7] |
| Spider | AMIGO | 96.1 [95.0, 97.2] | 95.1 [93.7, 96.3] | 95.3 [94.2, 96.4] | 91.7 [89.9, 93.3] |
| MMQA | Dense k3 | 59.0 [57.0, 61.0] | 31.4 [28.6, 34.1] | 42.8 [41.3, 44.3] | 2.8 [1.8, 3.8] |
| MMQA | MURRE k3 | 62.6 [60.3, 64.7] | 41.3 [38.2, 44.2] | 45.2 [43.6, 46.8] | 4.5 [3.2, 5.8] |
| MMQA | CORE-T | 84.1 [82.4, 85.7] | 70.6 [67.9, 73.4] | 58.1 [56.3, 59.9] | 21.7 [19.2, 24.3] |
| MMQA | AMIGO top-1 | 78.0 [76.0, 79.8] | 62.2 [59.3, 65.1] | 78.2 [76.1, 80.2] | 51.5 [48.4, 54.5] |
| MMQA | AMIGO | 87.9 [86.5, 89.3] | 76.7 [74.2, 79.2] | 83.0 [81.2, 84.7] | 62.5 [59.6, 65.4] |

## Per-version means with 95% intervals (bootstrap over questions), multi-valid label; widest interval over both labels 6.2 points

| lake | method | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|---|
| BIRD | Dense k3 | 50.9 [48.8, 53.0] | 36.2 [33.9, 38.7] | 72.0 [69.8, 74.3] | 6.3 [5.4, 7.3] | 2.3 [1.6, 3.1] | 12.4 [10.8, 14.1] |
| BIRD | MURRE k3 | 58.5 [56.5, 60.4] | 41.9 [39.4, 44.4] | 82.7 [80.8, 84.6] | 8.9 [7.8, 10.1] | 4.0 [3.0, 5.0] | 17.1 [15.3, 19.0] |
| BIRD | CORE-T | 68.1 [66.4, 69.8] | 49.7 [47.1, 52.2] | 94.9 [93.7, 96.0] | 22.6 [20.8, 24.5] | 16.3 [14.5, 18.1] | 31.3 [28.9, 33.6] |
| BIRD | Route+SQL | 62.6 [60.8, 64.5] | 45.3 [42.9, 47.8] | 88.1 [86.4, 89.6] | 60.9 [59.1, 62.8] | 44.1 [41.6, 46.5] | 85.7 [83.9, 87.5] |
| BIRD | AMIGO top-1 | 60.0 [58.1, 62.0] | 43.5 [41.1, 46.0] | 83.8 [81.9, 85.7] | 56.0 [54.0, 58.0] | 40.4 [37.9, 42.8] | 78.6 [76.5, 80.6] |
| BIRD | AMIGO | 73.1 [71.5, 74.8] | 57.4 [55.0, 59.8] | 83.2 [81.7, 84.6] | 68.3 [66.5, 70.2] | 53.1 [50.7, 55.6] | 77.7 [75.9, 79.3] |
| Spider | Dense k3 | 43.9 [41.4, 46.3] | 28.2 [25.4, 31.0] | 69.8 [67.0, 72.6] | 2.5 [1.8, 3.3] | 1.0 [0.4, 1.6] | 5.0 [3.8, 6.4] |
| Spider | MURRE k3 | 55.4 [53.2, 57.8] | 37.1 [34.2, 40.0] | 85.8 [83.7, 87.9] | 3.7 [2.8, 4.7] | 1.7 [1.0, 2.6] | 6.5 [5.0, 8.0] |
| Spider | CORE-T | 57.5 [55.3, 59.7] | 37.7 [34.8, 40.7] | 90.2 [88.4, 92.0] | 21.3 [19.3, 23.5] | 13.0 [10.9, 15.1] | 33.5 [30.6, 36.4] |
| Spider | Route+SQL | 48.2 [45.7, 50.6] | 31.2 [28.4, 34.0] | 76.0 [73.4, 78.6] | 47.8 [45.5, 50.2] | 31.2 [28.4, 34.0] | 75.0 [72.3, 77.6] |
| Spider | AMIGO top-1 | 59.6 [57.4, 61.8] | 39.7 [36.8, 42.7] | 92.6 [91.0, 94.2] | 58.7 [56.5, 60.9] | 39.6 [36.6, 42.6] | 90.7 [89.0, 92.5] |
| Spider | AMIGO | 70.7 [68.8, 72.7] | 50.0 [46.9, 53.1] | 89.6 [88.1, 91.0] | 69.4 [67.4, 71.4] | 49.0 [46.0, 52.1] | 87.6 [85.9, 89.2] |
| MMQA | Dense k3 | 20.9 [18.8, 23.0] | 12.2 [10.3, 14.2] | 39.1 [36.1, 42.0] | 3.1 [2.4, 4.0] | 1.0 [0.4, 1.6] | 7.1 [5.6, 8.8] |
| MMQA | MURRE k3 | 27.3 [25.1, 29.5] | 16.3 [14.1, 18.5] | 49.8 [46.8, 52.8] | 4.5 [3.5, 5.6] | 1.9 [1.1, 2.8] | 9.4 [7.7, 11.2] |
| MMQA | CORE-T | 42.8 [40.5, 45.1] | 26.4 [23.7, 29.0] | 78.6 [76.0, 81.0] | 16.5 [14.6, 18.4] | 10.1 [8.3, 12.1] | 28.0 [25.3, 30.7] |
| MMQA | AMIGO top-1 | 38.9 [36.6, 41.2] | 23.7 [21.3, 26.3] | 71.3 [68.5, 74.1] | 34.1 [31.9, 36.4] | 21.2 [18.7, 23.6] | 60.4 [57.5, 63.4] |
| MMQA | AMIGO | 53.3 [51.0, 55.6] | 34.5 [31.6, 37.4] | 65.6 [63.1, 68.1] | 43.9 [41.5, 46.3] | 29.4 [26.6, 32.1] | 54.0 [51.3, 56.7] |

## Place judge only (no join choice), search run again from the stored places: with the place judge's grades, and with a cut-off that keeps on each part the places of lowest cost, as many as the judge kept (no LLM call), gold label

| lake | places kept | R | CR | P | CR= | sets | size | questions run again |
|---|---|---|---|---|---|---|---|---|
| BIRD | stored grades | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 | 1534 |
| BIRD | cut-off | 88.9 | 78.9 | 88.6 | 65.6 | 1.43 | 1.90 | 1534 |
| Spider | stored grades | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 | 1033 |
| Spider | cut-off | 81.6 | 75.6 | 84.9 | 69.7 | 1.81 | 1.39 | 1033 |
| MMQA | stored grades | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 3.12 | 1097 |
| MMQA | cut-off | 80.4 | 63.7 | 65.2 | 36.9 | 3.82 | 4.43 | 1097 |
| mean | stored grades | 93.2 | 87.4 | 90.7 | 78.1 | 2.48 | 2.21 |
| mean | cut-off | 83.6 | 72.8 | 79.6 | 57.4 | 2.35 | 2.57 |
| worst | stored grades | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 3.12 |
| worst | cut-off | 80.4 | 63.7 | 65.2 | 36.9 | 3.82 | 4.43 |

## Cut-off minus the place judge's grades, gold label: points, 95% interval, Holm over the scores of one lake; * when below 0.05

| lake | R | CR | P | CR= |
|---|---|---|---|---|
| BIRD | -6.8 [-7.8, -5.7]* | -11.5 [-13.2, -9.7]* | -5.1 [-6.0, -4.2]* | -14.5 [-16.5, -12.6]* |
| Spider | -14.5 [-16.5, -12.4]* | -19.4 [-22.1, -16.9]* | -10.5 [-12.5, -8.6]* | -22.0 [-24.8, -19.1]* |
| MMQA | -7.5 [-9.0, -6.1]* | -13.1 [-15.5, -10.7]* | -17.8 [-19.8, -15.8]* | -25.6 [-28.5, -22.9]* |

## Place judge only (no join choice), search run again from the stored places: with the place judge's grades, and with a cut-off that keeps on each part the places of lowest cost, as many as the judge kept (no LLM call), multi-valid label

| lake | places kept | IR | ICR | IP | IR= | ICR= | IP= | sets | size | questions run again |
|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | stored grades | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 | 1534 |
| BIRD | cut-off | 63.9 | 49.7 | 73.3 | 57.3 | 44.1 | 65.8 | 1.43 | 1.90 | 1534 |
| Spider | stored grades | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 | 1033 |
| Spider | cut-off | 57.1 | 38.6 | 70.8 | 53.9 | 35.9 | 67.3 | 1.81 | 1.39 | 1033 |
| MMQA | stored grades | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 3.12 | 1097 |
| MMQA | cut-off | 44.6 | 27.6 | 52.4 | 28.0 | 17.6 | 31.8 | 3.82 | 4.43 | 1097 |
| mean | stored grades | 65.7 | 47.3 | 79.4 | 60.6 | 43.8 | 73.1 | 2.48 | 2.21 |
| mean | cut-off | 55.2 | 38.7 | 65.5 | 46.4 | 32.5 | 55.0 | 2.35 | 2.57 |
| worst | stored grades | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 3.12 |
| worst | cut-off | 44.6 | 27.6 | 52.4 | 28.0 | 17.6 | 31.8 | 3.82 | 4.43 |

## Cut-off minus the place judge's grades, multi-valid label: points, 95% interval, Holm over the scores of one lake; * when below 0.05

| lake | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|
| BIRD | -9.2 [-10.6, -7.9]* | -7.7 [-9.3, -6.1]* | -9.8 [-11.3, -8.3]* | -11.0 [-12.6, -9.5]* | -9.1 [-10.8, -7.4]* | -11.8 [-13.6, -10.1]* |
| Spider | -13.6 [-15.6, -11.8]* | -11.4 [-13.5, -9.4]* | -18.8 [-21.1, -16.5]* | -15.5 [-17.6, -13.6]* | -13.2 [-15.4, -11.0]* | -20.3 [-22.8, -17.8]* |
| MMQA | -8.7 [-10.5, -7.1]* | -6.9 [-8.8, -5.0]* | -13.1 [-15.2, -11.1]* | -15.9 [-17.9, -14.0]* | -11.7 [-13.8, -9.7]* | -22.1 [-24.5, -19.8]* |

## Place judge only (no join choice), search run again from the stored places with the stored grades and the place cost without its value term (no LLM call), against the saved output, gold label

| lake | costs | R | CR | P | CR= | sets | size | questions run again | questions with a value term |
|---|---|---|---|---|---|---|---|---|---|
| BIRD | stored costs | 95.6 | 90.4 | 93.7 | 80.1 | 1.44 | 1.96 | 1534 | 1387 |
| BIRD | without the value term | 95.6 | 90.4 | 93.7 | 80.0 | 1.44 | 1.96 | 1534 | 1387 |
| Spider | stored costs | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 | 1033 | 544 |
| Spider | without the value term | 96.1 | 95.1 | 95.3 | 91.7 | 1.69 | 1.54 | 1033 | 544 |
| MMQA | stored costs | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 3.12 | 1097 | 912 |
| MMQA | without the value term | 87.9 | 76.7 | 83.0 | 62.5 | 4.29 | 3.12 | 1097 | 912 |
| mean | stored costs | 93.2 | 87.4 | 90.7 | 78.1 | 2.48 | 2.21 |
| mean | without the value term | 93.2 | 87.4 | 90.7 | 78.1 | 2.47 | 2.21 |
| worst | stored costs | 87.9 | 76.7 | 83.0 | 62.5 | 4.31 | 3.12 |
| worst | without the value term | 87.9 | 76.7 | 83.0 | 62.5 | 4.29 | 3.12 |

## Without the value term minus stored costs, gold label: points, 95% interval, Holm over the scores of one lake; * when below 0.05

| lake | R | CR | P | CR= |
|---|---|---|---|---|
| BIRD | -0.0 [-0.1, +0.0] | -0.1 [-0.2, +0.0] | +0.0 [+0.0, +0.0] | -0.1 [-0.2, +0.0] |
| Spider | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| MMQA | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |

## Place judge only (no join choice), search run again from the stored places with the stored grades and the place cost without its value term (no LLM call), against the saved output, multi-valid label

| lake | costs | IR | ICR | IP | IR= | ICR= | IP= | sets | size | questions run again | questions with a value term |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIRD | stored costs | 73.1 | 57.4 | 83.2 | 68.3 | 53.1 | 77.7 | 1.44 | 1.96 | 1534 | 1387 |
| BIRD | without the value term | 73.1 | 57.4 | 83.1 | 68.3 | 53.1 | 77.6 | 1.44 | 1.96 | 1534 | 1387 |
| Spider | stored costs | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 | 1033 | 544 |
| Spider | without the value term | 70.7 | 50.0 | 89.6 | 69.4 | 49.0 | 87.6 | 1.69 | 1.54 | 1033 | 544 |
| MMQA | stored costs | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 3.12 | 1097 | 912 |
| MMQA | without the value term | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.29 | 3.12 | 1097 | 912 |
| mean | stored costs | 65.7 | 47.3 | 79.4 | 60.6 | 43.8 | 73.1 | 2.48 | 2.21 |
| mean | without the value term | 65.7 | 47.3 | 79.4 | 60.5 | 43.8 | 73.0 | 2.47 | 2.21 |
| worst | stored costs | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.31 | 3.12 |
| worst | without the value term | 53.3 | 34.5 | 65.5 | 43.9 | 29.4 | 53.9 | 4.29 | 3.12 |

## Without the value term minus stored costs, multi-valid label: points, 95% interval, Holm over the scores of one lake; * when below 0.05

| lake | IR | ICR | IP | IR= | ICR= | IP= |
|---|---|---|---|---|---|---|
| BIRD | -0.1 [-0.2, +0.0] | -0.1 [-0.2, +0.0] | -0.0 [-0.1, +0.0] | -0.1 [-0.2, +0.0] | -0.1 [-0.2, +0.0] | -0.0 [-0.1, +0.0] |
| Spider | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| MMQA | -0.0 [-0.1, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-0.0, +0.0] | -0.0 [-0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-0.0, +0.0] |

## Inferred links of the built layers by the kind of their column, and those whose weight reaches the edge threshold of 1/2

| lake | text column links | of them edges | number column links | of them edges |
|---|---|---|---|---|
| BIRD | 2 | 1 | 4 | 1 |
| Spider | 66 | 35 | 79 | 60 |
| MMQA | 681 | 146 | 2114 | 1445 |

