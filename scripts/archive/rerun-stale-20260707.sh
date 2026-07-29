#!/usr/bin/env bash
# Re-run the 9 cells report.py drops as STALE (task changed since the run), 2026-07-07:
#   a-03 × {haiku, sonnet}   (ran 4077b3374741, task now 40b327e6bc26)
#   b-04 × {opus}            (ran dcf0aee16207, task now a0d756ea6ccc)
#   c-04r × {haiku, sonnet, opus}  (ran 060b534123f8, task now 157b0c5d80ed)
#   d-09  × {haiku, sonnet, opus}  (ran 3a019aede169, task now 93bad819d331)
# Board standard is pass@3. Appends rows to results/leaderboard.json; report.py dedup
# keeps the best current-hash row per (task, model).
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/rerun-stale-20260707.log"
: > "$LOG"

PAIRS=(
  "a-03 haiku" "a-03 sonnet"
  "d-09 haiku" "d-09 sonnet" "d-09 opus"
  "c-04r haiku" "c-04r sonnet" "c-04r opus"
  "b-04 opus"
)

echo "[rerun-stale] start $(date)" | tee -a "$LOG"
total=${#PAIRS[@]}
i=0
for pair in "${PAIRS[@]}"; do
  read -r t m <<< "$pair"
  i=$(( i + 1 ))
  echo "" | tee -a "$LOG"
  echo "=== [$i/$total] $t / $m ===" | tee -a "$LOG"
  python3 -m harness.runner --task "$t" --model "$m" --attempts 3 --sandbox local >> "$LOG" 2>&1
  rc=$?
  line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
  echo "[rerun-stale] $t/$m rc=$rc ${line}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "[rerun-stale] done $(date)" | tee -a "$LOG"
echo "[rerun-stale] next: python3 -m harness.report  (stale rows should be gone)" | tee -a "$LOG"
