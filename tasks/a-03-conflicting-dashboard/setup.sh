#!/usr/bin/env bash
# Build the fixed starting state for task a-03.
set -euo pipefail

if [[ ! -f "fixtures/metrics.csv" ]]; then
  echo "FATAL: fixtures/metrics.csv missing from sandbox workdir" >&2
  exit 1
fi

echo "[setup] a-03 ready: 12 months of subscription metrics"
