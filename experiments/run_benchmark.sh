#!/bin/bash
# One benchmark end to end, every LLM call on the local Qwen (labeler/llm.py has the vLLM
# start command): the baselines, AMIGO, then the scores against the gold query and the
# multi-valid label. The way BIRD, Spider and MMQA were run.
#   bash experiments/run_benchmark.sh LAKE    # questions: runs/labeler/LAKE/questions.jsonl
# Writes runs/eval_LAKE/. Safe to run again: done questions are skipped. On MMQA (one
# database of 710 tables) Route+SQL's prompt is over the context: drop bl_route_sql from B.
set -u
cd "$(dirname "$0")/.."
LAKE=$1
R=runs/eval_$LAKE
Q=qwen3.8-27b-fp8
export LLM_MODEL=$Q WHOLES_MODEL=$Q EVAL_QUESTIONS=runs/labeler/$LAKE/questions.jsonl EVAL_RUNS=$R AMIGO_CACHE_DIR=$R/cache
mkdir -p $R/score
py() { .venv/bin/python "$@"; }

# 1. baselines: up to 3 passes, a later one redoing only failed questions
one() {  # workers method settings...
  w=$1; shift
  name=$(echo "$@" | tr ' =' '__')
  for pass in 1 2 3; do py -m baselines.run "$@" --workers $w >> $R/$name.log 2>&1; done
  echo "$* done $(date '+%F %T')"
}
one 20 dense k=10 & one 20 crush4sql b=100 & one 60 murre k=10 & one 40 core_t & one 20 route_sql & one 20 dense k=3 sql=1 &
one 20 jar k=3   # before k=1, 5, 10, so they reuse its question splits
one 20 jar k=1 & one 20 jar k=5 & one 20 jar k=10 &
wait
for k in 1 3 5; do py -m baselines.cut bl_dense_k10 $k; py -m baselines.cut bl_murre_k10 $k; done
for t in 1 3 5 10; do py -m baselines.cut bl_crush4sql_b100 $t tables; done

# 2. AMIGO: split the questions, search and judge (48 questions at once), widen to 20 bits
export EVAL_HALF=all EVAL_EFFORT=medium
EVAL_SQL_WORKERS=48 py experiments/eval_lakes.py split > $R/split_medium.log 2>&1
EVAL_WORKERS=48 py experiments/eval_lakes.py amigo amigo > $R/amigo.log 2>&1
py experiments/eval_lakes.py widen amigo amigo_w 20 > $R/amigo_w.log 2>&1

# 3. scores (no LLM call)
B="bl_dense_k1 bl_dense_k3 bl_dense_k5 bl_dense_k10 bl_jar_k1 bl_jar_k3 bl_jar_k5 bl_jar_k10 bl_crush4sql_t1 bl_crush4sql_t3 bl_crush4sql_t5 bl_crush4sql_t10 bl_murre_k1 bl_murre_k3 bl_murre_k5 bl_murre_k10 bl_core_t bl_route_sql bl_dense_k3_sql1"
py experiments/eval_lakes.py report $B > $R/score/scores_gold.md 2> $R/score/scores_gold.log
EVAL_LABEL=plus py experiments/eval_lakes.py report $B > $R/score/scores_plus.md 2> $R/score/scores_plus.log
for w in 0 1 2 3 4 5 6; do py experiments/eval_lakes.py score2 amigo_w $w; done
py experiments/eval_lakes.py compare $(for w in 0 1 2 3 4 5 6; do echo -n "amigo_w@$w "; done) > $R/score/compare_amigo_w.md 2> $R/score/compare_amigo_w.log
py experiments/eval_lakes.py match amigo_w $B > $R/score/matched.md 2> $R/score/matched.log
echo "all done $(date '+%F %T')"
