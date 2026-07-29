#!/usr/bin/env bash
# Run the 4 category-expansion tasks (a-04, b-05, c-05, d-10) plus the two clean-control
# twins (d-03x, d-07x) × 3 models with --attempts 3.
# Appends rows to results/leaderboard.json; report.py last-wins dedup picks these up.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/run-additions.log"
: > "$LOG"

TASKS=(b-05 d-10 a-04 c-05)
MODELS=(haiku sonnet opus)

echo "[additions] start $(date)" | tee -a "$LOG"
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
    echo "[additions] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "[additions] done $(date)" | tee -a "$LOG"
