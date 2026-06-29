#!/usr/bin/env bash
# Build the fixed starting state for task b-02.
set -euo pipefail

if [[ ! -f fixtures/transactions.csv ]]; then
  echo "FATAL: fixtures/transactions.csv missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/transactions.csv) - 1))
echo "[setup] b-02 ready: ${rows} transactions in fixtures/transactions.csv"
