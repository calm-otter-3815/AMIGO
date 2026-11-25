# AMIGO

AMIGO stands for AMbiguity-aware, Interactive, Grounded, Open-domain table
retrieval over data lakes. It answers a question written in plain English over a
data lake of many databases. It does not guess which table or column you meant: it
returns every interpretation the lake supports, each a set of tables that join,
cheapest first. Grounded means every interpretation uses real columns, real stored
values and real links between tables. Ambiguity is an output, not a problem to hide.

The method is in `amigo/interpret.py`; the live page (`amigo serve`) runs it as a guided
search, described further down.

## How AMIGO works

1. **Layer.** `amigo build` reads every database in the lake once: tables, columns,
   types, sample values, descriptions, and the links between tables.
2. **Split.** One LLM call splits the question into parts: what each part asks for in
   plain words, plus a value when the question gives one.
3. **Lookups.** No LLM call. Embeddings and the value index find the places (columns or
   tables) that could hold each part, and which columns store each value.
4. **Search.** No LLM call. Each interpretation picks one place per part and the
   cheapest way to join their tables (a Steiner tree in the link graph); other join
   paths come next (Lawler's k-best). Each one has a cost in bits: minus log2 of its
   odds, from the lookup ranks and the join links.
5. **Judge, call 1.** One LLM call says yes or no for each (part, place) pair. The
   search runs again on the places it says yes to.
6. **Relaxed.** When no interpretation places every part, the search returns the ones
   that leave out the fewest parts, each marked with what it leaves out.
7. **Judge, call 2.** One LLM call says yes or no for every interpretation found, as a
   whole, since some meanings show only in how the parts combine. The ones it says no to
   are dropped; when it says no to all of them, all are kept, each marked "judged no".
8. **Answer.** Every interpretation kept, cheapest first, up to 50 (`judge.MOST`). In
   `amigo interpret`, up to 3 questions on where a part sits can then narrow it; an
   answer makes the interpretations that disagree less likely, it does not remove them.

So a question costs three LLM calls. The same question gives the same outcome on every
run: each LLM reply is kept by what was asked, under `runs/cache/`, and given back the
next time. `AMIGO_CACHE=off` turns this off.

## Results

The paper's numbers come from one run of every method on BIRD, Spider and MMQA, all LLM
calls on a local Qwen3.8-27B (2026-10-20, raw files in `runs/paper_2026-10-20/`, not in
git). The code of that run (the added baselines BM25, hybrid, Greedy JAR and full schema,
and `experiments/paper_results.py`, which writes every table and figure) is on branch
`night-eval-2026-10-20`, not yet in main. Baselines here (`baselines/`, see its README):
dense retrieval, JAR, CRUSH4SQL, MURRE, CORE-T, Route+SQL.

## The live page

`amigo serve` (the live page) runs AMIGO above and shows each interpretation as a card:
its tables, the place of each part, its joins, and a note with its odds against the best
and whether it leaves out a part or was judged no. With several cards, you tick the ones
you meant; then the steps below write and run their SQL. The model menu also sets the
thinking: off, or one level for every call, or each step's own level. A level the model does
not take goes at the closest one below it (Qwen has no "high", so "high" goes at "medium").

Once you tick the interpretations you meant:

1. **SQL.** One model call per interpretation writes a SQLite SELECT plus one
   sentence saying what it computes. Before it runs, code checks that it
   follows its interpretation: it reads only the interpretation's tables, uses
   every bound column and every column of its joins, never a column of another
   role, and compares each value as stored. A failed check, an SQLite error or,
   once, no rows goes back to the model with the reason, up to 5 tries. Code
   runs it read-only and stops it after a fixed number of SQLite steps. Then
   one small call says the answer in one to three plain sentences, from the
   rows only; code drops it when it states a number that the rows, the
   bindings and the question do not show.
2. **Present.** Every interpretation is shown with its answer in words, its
   sentence, its columns and why they were picked, its SQL, and the first
   rows. You pick the one you meant; the choice is written to the run log. A
   typed follow-up that only changes the chosen query's filters, grouping,
   order or limit rewrites its SQL over the same columns; one that needs a new
   column starts a full run.

The same question gives the same outcome on every run: each model reply is
kept by what was asked, under `runs/cache/`, and given back the next time.
`AMIGO_CACHE=off` turns this off, to measure how much the replies vary.

## Setup

Python 3.11.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then fill in the keys you need (variable names only in git)
```

- AMIGO's default LLM is `gpt-6-luna` through the OpenAI API (`OPENAI_API_KEY`), on the
  flex tier.
- The results above use a local Qwen3.8-27B served by vLLM on a GPU (start command in
  `labeler/llm.py`). Set `LLM_MODEL=qwen3.8-27b-fp8` and `WHOLES_MODEL=qwen3.8-27b-fp8`;
  `QWEN_URL` when the server runs elsewhere. The labeler and the baselines use the same
  server.
- torch runs the embeddings and the join search's shortest paths on the GPU when there is
  one; install the torch build that matches your CUDA.

Benchmark data is not in this repository. Put BIRD dev at `benchmarks/bird/` (so that
`benchmarks/bird/dev.json` and `benchmarks/bird/dev_databases/` exist); `lakes.json`
says where each other lake's files go.

## Usage

Build the lake once (reads the databases, writes the index):

```bash
.venv/bin/python -m amigo build bird_dev
.venv/bin/python -m amigo verify bird_dev
```

Ask AMIGO a question. It prints the interpretations, then asks up to 3 questions on
where a part sits, answered with place numbers (several allowed, 0 for none of these,
Enter to stop):

```bash
.venv/bin/python -m amigo interpret bird_dev "Which publisher has the most heroes with blue eyes?"
```

Run a whole benchmark, baselines and AMIGO, then the scores:

```bash
bash experiments/run_benchmark.sh bird_dev
```

The live page that runs AMIGO and shows its interpretations as cards:

```bash
.venv/bin/python -m amigo serve bird_dev --port 8765
```

With no lake named, `serve` serves every built lake at once. `lakes.json` lists the
benchmarks (bird_dev, spider_dev, beaver_dw, beaver_nw, fiben, mmqa, taco_us); build each
one first with `.venv/bin/python -m amigo build <lake>`.

Tests:

```bash
.venv/bin/python -m pytest -q
```

## Multi-valid labels

The multi-valid labels of the paper are in `multi_valid_labels/<benchmark>/labels.jsonl.gz`, with the questions they label in `questions.jsonl.gz`, for BIRD, Spider and MMQA. To score against them, unpack each pair into `runs/labeler/<benchmark>/`.

## Benchmark labels

`labeler/` rebuilds the gold of BIRD and Spider (and the other lakes) so that a
question keeps every valid answer, not only the one its gold SQL gives. It never
imports `amigo`, so the labels cannot borrow AMIGO's choices. Per question:

1. **Sample.** Run the gold SQL and keep its health (ok, empty, error, slow).
2. **Link.** An LLM call ties the question's words to the gold's tables and columns.
3. **Pool.** Code and embeddings find other tables and columns across the lake
   that could hold the same thing; a few wrong ones are added on purpose as decoys.
4. **Judge.** The LLM votes on each option: could these words mean it? Best of
   three when it says yes.
5. **Swap.** Each accepted option replaces the gold item: plain code when a simple
   swap works, else one LLM call rewrites the gold SQL (or says that database cannot
   answer). Code runs it and compares its rows with the gold's.
6. **Label.** Code groups the queries by their result rows: one group per valid answer.

The LLM is a local Qwen3.8-27B served by vLLM (start command in `labeler/llm.py`).
Replies are cached, so a stopped run resumes for free.

```bash
LABEL_RUN=bird_dev .venv/bin/python -m labeler.sample bird_dev
LABEL_RUN=bird_dev .venv/bin/python -m labeler.go       # writes runs/labeler/bird_dev/labels.jsonl
LABEL_RUN=bird_dev .venv/bin/python -m labeler.label    # summary per lake
```

Replies go to `runs/labeler/cache-<run>.jsonl`. `LABEL_URL` points at another vLLM server and
`LABEL_CACHE` at another cache file.

## Layout

```
amigo/         AMIGO: layer, bundle (split, lookups), candidates (search), judge,
               interpret, guide, serve; solve, answer (joins and the SQL step)
baselines/     the baselines, run on the same lakes and scored the same way
prompts/       the LLM prompts, one text file per call
ui/            the page served by `serve`
labeler/       benchmark relabeling: every valid answer per question
experiments/   evaluation scripts
tests/         unit tests, run with pytest
```

## Status

Research prototype.
Interfaces change without notice. Not packaged, not versioned, not supported.
