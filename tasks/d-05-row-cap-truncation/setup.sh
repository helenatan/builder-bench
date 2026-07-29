#!/usr/bin/env bash
# Build the fixed starting state for task d-05.
set -euo pipefail
for f in orders.csv monthly_summary.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done
rows=$(($(wc -l < fixtures/orders.csv) - 1))
echo "[setup] d-05 ready: orders.csv (${rows} rows — suspiciously round) + monthly_summary.csv"
