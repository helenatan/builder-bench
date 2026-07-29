#!/usr/bin/env bash
# Re-run the tasks changed in the 2026-06-14 hardening pass, across all three tiers.
# Appends rows to results/leaderboard.json; a later dedup keeps the latest per (task, model).
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/rerun-changed.log"
: > "$LOG"

# Fast/programmatic + judge tasks first, slow server-boot tasks (c-01, c-03) last.
TASKS=(a-02 d-03 b-02 b-03 b-01 c-02 c-01 c-03)
MODELS=(haiku sonnet opus)

echo "[rerun] start $(date)" | tee -a "$LOG"
for t in "${TASKS[@]}"; do
  for m in "${MODELS[@]}"; do
    echo "=== $t / $m ===" | tee -a "$LOG"
    python3 -m harness.runner --task "$t" --model "$m" --sandbox local >> "$LOG" 2>&1
    rc=$?
    line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
    echo "[rerun] $t/$m rc=$rc ${line}" | tee -a "$LOG"
  done
done
echo "[rerun] done $(date)" | tee -a "$LOG"
