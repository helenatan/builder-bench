#!/usr/bin/env bash
# Build the fixed starting state for task d-10.
set -euo pipefail

for f in orders_us.csv orders_intl.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done

echo "[setup] d-10 ready: two storefront exports (date formats differ)"
