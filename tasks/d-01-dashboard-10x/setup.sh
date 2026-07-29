#!/usr/bin/env bash
# Build the fixed starting state for task d-01.
set -euo pipefail

for f in orders.csv revenue_by_status.csv order_status_history.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done

echo "[setup] d-01 ready: orders + revenue_by_status panel (which double-counts) + status history"
