#!/usr/bin/env bash
# Run the 4 retired exemplar tasks (a-03, b-04, c-04r, d-09) × 3 models with --attempts 3.
# Appends rows to results/leaderboard.json; report.py last-wins dedup picks these up.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/run-retired-exemplars.log"
: > "$LOG"

TASKS=(b-04 d-09 c-04r a-03)
MODELS=(haiku sonnet opus)

echo "[retired] start $(date)" | tee -a "$LOG"
total=$(( ${#TASKS[@]} * ${#MODELS[@]} ))
n=0

for t in "${TASKS[@]}"; do
  for m in "${MODELS[@]}"; do
    n=$(( n + 1 ))
    echo "" | tee -a "$LOG"
    echo "=== [$n/$total] $t / $m ===" | tee -a "$LOG"
    python3 -m harness.runner --task "$t" --model "$m" --attempts 3 --sandbox local >> "$LOG" 2>&1
    rc=$?
    line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
    echo "[retired] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "[retired] done $(date)" | tee -a "$LOG"
