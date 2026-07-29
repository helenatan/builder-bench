#!/usr/bin/env bash
# Build the fixed starting state for task b-05.
set -euo pipefail

for f in customers.csv orders.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done

echo "[setup] b-05 ready: customers + orders (IDs are fixed-width strings)"
