#!/usr/bin/env bash
# Build the fixed starting state for task d-06.
set -euo pipefail
if [[ ! -f fixtures/reviews.csv ]]; then
  echo "FATAL: fixtures/reviews.csv missing from sandbox workdir" >&2
  exit 1
fi
echo "[setup] d-06 ready: reviews.csv (AeroDesk Pro has reviews, but none praise durability)"
