#!/usr/bin/env bash
# Resume the new-model run: re-run ONLY the 44 (task, model) cells that came back empty
# ($0.00 / 0 tokens) when the subscription credential died partway through the first pass.
# Valid cells and the 4.x models are left untouched. report.py last-wins dedup overwrites
# the empty rows with these fresh ones.
# After this finishes, rebuild the site with: python3 -m harness.report
#
# Requires a live subscription credential — run `claude login` first. If cells still come
# back at $0.00, auth died again mid-run: re-login and re-run this script (it recomputes
# nothing; the pair list below is fixed, but empty cells are safe to overwrite again).
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/resume-new-models.log"
: > "$LOG"

# (task model) pairs that were empty after the first pass.
PAIRS=(
  "b-04 fable-5" "b-04 sonnet-5"
  "b-05 fable-5" "b-05 opus-5" "b-05 sonnet-5"
  "c-01 fable-5" "c-01 opus-5" "c-01 sonnet-5"
  "c-02 fable-5" "c-02 opus-5" "c-02 sonnet-5"
  "c-03 fable-5" "c-03 opus-5" "c-03 sonnet-5"
  "c-04r fable-5" "c-04r opus-5" "c-04r sonnet-5"
  "c-05 fable-5" "c-05 opus-5" "c-05 sonnet-5"
  "d-01 fable-5" "d-01 opus-5" "d-01 sonnet-5"
  "d-02 fable-5" "d-02 opus-5" "d-02 sonnet-5"
  "d-03 fable-5" "d-03 opus-5" "d-03 sonnet-5"
  "d-05 fable-5" "d-05 opus-5" "d-05 sonnet-5"
  "d-06 fable-5" "d-06 opus-5" "d-06 sonnet-5"
  "d-07 fable-5" "d-07 opus-5" "d-07 sonnet-5"
  "d-09 fable-5" "d-09 opus-5" "d-09 sonnet-5"
  "d-10 fable-5" "d-10 opus-5" "d-10 sonnet-5"
)

echo "[resume] start $(date)" | tee -a "$LOG"
total=${#PAIRS[@]}
n=0

for pair in "${PAIRS[@]}"; do
  set -- $pair
  t="$1"; m="$2"
  n=$(( n + 1 ))
  echo "" | tee -a "$LOG"
  echo "=== [$n/$total] $t / $m ===" | tee -a "$LOG"
  python3 -m harness.runner --task "$t" --model "$m" --attempts 3 --sandbox local >> "$LOG" 2>&1
  rc=$?
  line=$(grep -E '^\s*\[grade\]' "$LOG" | tail -1)
  echo "[resume] $t/$m rc=$rc ${line}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "[resume] done $(date)" | tee -a "$LOG"
echo "[resume] rebuild the site: python3 -m harness.report" | tee -a "$LOG"
