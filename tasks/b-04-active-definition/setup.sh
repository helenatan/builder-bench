#!/usr/bin/env bash
# Build the fixed starting state for task b-04.
set -euo pipefail

for f in purchases.csv purchases_full.csv customers.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done

echo "[setup] b-04 ready: purchase log + fuller export + customer plans"
