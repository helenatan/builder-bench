#!/usr/bin/env bash
# Run all 15 tasks × 3 models with --attempts 3 (pass@3).
# Appends rows to results/leaderboard.json; report.py last-wins dedup picks these up.
# Fast/programmatic tasks first; server-boot tasks (c-01, c-03) last.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/run-pass3.log"
: > "$LOG"

TASKS=(d-02 d-03 d-05 d-06 d-07 d-01 a-01 a-02 a-05 b-01 b-02 b-03 c-02 c-01 c-03)
MODELS=(haiku sonnet opus)

echo "[pass3] start $(date)" | tee -a "$LOG"
total=$(( ${#TASKS[@]} * ${#MODELS[@]} ))
done=0

for t in "${TASKS[@]}"; do
  for m in "${MODELS[@]}"; do
    done=$(( done + 1 ))
    echo "" | tee -a "$LOG"
    echo "=== [$done/$total] $t / $m ===" | tee -a "$LOG"
    python3 -m harness.runner --task "$t" --model "$m" --attempts 3 --sandbox local >> "$LOG" 2>&1
    rc=$?
    line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
    echo "[pass3] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "[pass3] done $(date)" | tee -a "$LOG"
echo "[pass3] next: python3 -m harness.report && open public/index.html" | tee -a "$LOG"
