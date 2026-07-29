#!/usr/bin/env bash
# Re-run the updated B tasks across all three tiers at pass@3.
# TASKS overridable via env, e.g. TASKS="b-02 b-03" scripts/rerun-b-updated.sh
# Appends rows to results/leaderboard.json; report.py last-wins dedup keeps these latest rows.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

LOG="results/rerun-b-updated.log"
: > "$LOG"

read -r -a TASKS <<< "${TASKS:-b-01 b-02 b-03}"
MODELS=(haiku sonnet opus)

echo "[rerun-b] start $(date) tasks=${TASKS[*]}" | tee -a "$LOG"
total=$(( ${#TASKS[@]} * ${#MODELS[@]} ))
done=0
for t in "${TASKS[@]}"; do
  for m in "${MODELS[@]}"; do
    done=$(( done + 1 ))
    echo "" | tee -a "$LOG"
    echo "=== [$done/$total] $t / $m ===" | tee -a "$LOG"
    python -m harness.runner --task "$t" --model "$m" --attempts 3 --sandbox local >> "$LOG" 2>&1
    rc=$?
    line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
    echo "[rerun-b] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done
echo "" | tee -a "$LOG"
echo "[rerun-b] done $(date)" | tee -a "$LOG"
