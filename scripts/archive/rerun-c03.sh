#!/usr/bin/env bash
# Re-run c-03 (prompt.md rewritten in PM voice, 2026-07-04) across all three tiers at pass@3.
# Appends rows to results/leaderboard.json; report.py last-wins dedup keeps these.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/rerun-c03.log"
: > "$LOG"

MODELS=(haiku sonnet opus)

echo "[rerun-c03] start $(date)" | tee -a "$LOG"
for m in "${MODELS[@]}"; do
  echo "=== c-03 / $m ===" | tee -a "$LOG"
  python3 -m harness.runner --task c-03 --model "$m" --attempts 3 --sandbox local >> "$LOG" 2>&1
  rc=$?
  line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
  echo "[rerun-c03] c-03/$m rc=$rc ${line}" | tee -a "$LOG"
done
echo "[rerun-c03] done $(date)" | tee -a "$LOG"
