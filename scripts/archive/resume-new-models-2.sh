#!/usr/bin/env bash
# Second resume pass: the 18 D-category cells still empty ($0.00) after resume pass 1, which
# died ~cell 28 when the subscription's rolling usage window was exhausted (~2h of runs).
# Only these cells run; everything else (incl. recovered b/c/d-01/d-02 cells) is left alone.
# report.py last-wins dedup overwrites the empty rows. Rebuild after: python3 -m harness.report
#
# If cells come back $0.00 again, the usage window is still capped — wait for it to reset
# (subscription rolling limit) and re-run, rather than hammering it.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="results/resume-new-models-2.log"
: > "$LOG"

PAIRS=(
  "d-03 fable-5" "d-03 opus-5" "d-03 sonnet-5"
  "d-05 fable-5" "d-05 opus-5" "d-05 sonnet-5"
  "d-06 fable-5" "d-06 opus-5" "d-06 sonnet-5"
  "d-07 fable-5" "d-07 opus-5" "d-07 sonnet-5"
  "d-09 fable-5" "d-09 opus-5" "d-09 sonnet-5"
  "d-10 fable-5" "d-10 opus-5" "d-10 sonnet-5"
)

echo "[resume2] start $(date)" | tee -a "$LOG"
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
  echo "[resume2] $t/$m rc=$rc ${line}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "[resume2] done $(date)" | tee -a "$LOG"
echo "[resume2] rebuild the site: python3 -m harness.report" | tee -a "$LOG"
