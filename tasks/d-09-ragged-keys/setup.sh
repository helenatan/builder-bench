#!/usr/bin/env bash
# Build the fixed starting state for task d-09.
set -euo pipefail

if [[ ! -f "fixtures/subscriptions.csv" ]]; then
  echo "FATAL: fixtures/subscriptions.csv missing from sandbox workdir" >&2
  exit 1
fi

echo "[setup] d-09 ready: subscriptions export (country labels vary)"
