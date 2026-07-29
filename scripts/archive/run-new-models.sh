#!/usr/bin/env bash
# Run the three current-gen models (Opus 5 / Sonnet 5 / Fable 5) across the full 23-task
# suite × --attempts 3. The 4.x models (opus/sonnet/haiku) are NOT re-run here — their rows
# already live in results/leaderboard.json and stay as-is.
# Appends rows to results/leaderboard.json; report.py last-wins dedup picks these up.
# After this finishes, rebuild the site with: python3 -m harness.report
#
# Requires a live subscription credential — run `claude login` first (a bare 401 / $0 run
# means the runner has no credential).
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/run-new-models.log"
: > "$LOG"

TASKS=(a-01 a-02 a-03 a-04 a-05 b-01 b-02 b-03 b-04 b-05 c-01 c-02 c-03 c-04r c-05 d-01 d-02 d-03 d-05 d-06 d-07 d-09 d-10)
MODELS=(opus-5 sonnet-5 fable-5)

echo "[new-models] start $(date)" | tee -a "$LOG"
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
    echo "[new-models] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "[new-models] done $(date)" | tee -a "$LOG"
echo "[new-models] rebuild the site: python3 -m harness.report" | tee -a "$LOG"
