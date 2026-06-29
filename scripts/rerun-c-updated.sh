#!/usr/bin/env bash
# Re-run c-01/c-02/c-03 after the 2026-06-28 edits, pass@3, all tiers.
# Appends rows to results/leaderboard.json; report.py last-wins dedup picks these up.
# Programmatic c-02 first; server-boot c-01/c-03 last.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/rerun-c-updated.log"
: > "$LOG"

TASKS=(c-02 c-01 c-03)
MODELS=(haiku sonnet opus)

echo "[rerun-c] start $(date) tasks=${TASKS[*]}" | tee -a "$LOG"
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
    echo "[rerun-c] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done
echo "" | tee -a "$LOG"
echo "[rerun-c] done $(date)" | tee -a "$LOG"
