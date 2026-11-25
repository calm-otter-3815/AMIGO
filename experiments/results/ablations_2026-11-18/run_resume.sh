#!/bin/bash
# The two offline ablations of offline.py: build each lake copy, then the paper's AMIGO lazy on it
# (runs/rerun_2026-11-08/run.sh, place judge then join judge), from the paper's saved splits and
# a copy of its reply cache, so identical prompts are not asked again.
#   bash experiments/results/ablations_2026-11-18/run_resume.sh   (cwd: the worktree at aeb4dac)
# Resume version: a lake build runs again (resuming its unfinished steps) unless driver.log shows it ended with exit 0.
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT=$ROOT/runs/ablations_2026-11-18
OLD=$ROOT/runs/rerun_2026-11-08
PY=.venv/bin/python
S=experiments/results/ablations_2026-11-18/offline.py
LOG=$OUT/driver.log
mkdir -p $OUT
for v in LLM_SERVICE_TIER EVAL_USER PICK_BACKEND JUDGE_EFFORT EVAL_LABEL AMIGO_ABLATE AMIGO_CACHE AMIGO_WINDOW; do unset $v; done
export LLM_MODEL=qwen3.8-27b-fp8 WHOLES_MODEL=qwen3.8-27b-fp8 EVAL_EFFORT=medium DECOMPOSE_EFFORT=medium \
  EVAL_HALF=all OPENAI_API_KEY= OPENROUTER_API_KEY= CUDA_VISIBLE_DEVICES= HF_HUB_OFFLINE=1 \
  TOKENIZERS_PARALLELISM=false EVAL_WORKERS=${EVAL_WORKERS:-32} EVAL_SQL_WORKERS=32 \
  QWEN_URL=${QWEN_URL:-http://localhost:8000/v1}

run() {  # run NAME LOGFILE CMD...: one step, its start, end and exit code in driver.log
  local name=$1 log=$2; shift 2
  mkdir -p "$(dirname "$log")"
  echo "$(date '+%F %T') start $name" >> $LOG
  local t=$(date +%s)
  "$@" >> "$log" 2>&1
  local code=$?
  echo "$(date '+%F %T') end $name exit $code $(( $(date +%s) - t )) s" >> $LOG
  return $code
}

chain() {  # chain VARIANT LAKE
  local variant=$1 lake=$2 runs=$OUT/$1/$2
  mkdir -p $runs/logs
  [ -f $runs/split_medium.json ] || cp $OLD/$lake/split_medium.json $runs/
  [ -d $runs/cache ] || cp -r $OLD/$lake/cache $runs/cache
  grep -q "end $variant $lake build exit 0" $LOG || run "$variant $lake build" $runs/logs/build.log $PY $S build $variant $lake || return 1
  local E=(env EVAL_RUNS=$runs EVAL_QUESTIONS=$ROOT/runs/labeler/$lake/questions.jsonl AMIGO_CACHE_DIR=$runs/cache
           ABL_LAKES=$OUT/lakes_$variant $PY $S eval)
  run "$variant $lake amigo (place judge)" $runs/logs/amigo.log "${E[@]}" amigo placed || return 1
  run "$variant $lake joins" $runs/logs/joins.log "${E[@]}" joins $runs/placed joinchoice || return 1
  run "$variant $lake score2" $runs/logs/joins.log "${E[@]}" score2 joinchoice inf
}

echo "$(date '+%F %T') start, pid $$, code $(git rev-parse --short HEAD)" >> $LOG
for lake in bird_dev spider_dev; do chain nodesc $lake & done  # MMQA left out for now (user, 2026-11-23)
for lake in bird_dev spider_dev; do chain nofk $lake & done
wait
$PY $S score >> $LOG 2>&1
echo "$(date '+%F %T') done" >> $LOG
