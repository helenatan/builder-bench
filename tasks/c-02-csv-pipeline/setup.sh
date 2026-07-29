#!/usr/bin/env bash
# Build the fixed starting state for task c-02.
set -euo pipefail

if [[ ! -f fixtures/raw_sales.csv ]]; then
  echo "FATAL: fixtures/raw_sales.csv missing from sandbox workdir" >&2
  exit 1
fi
if [[ ! -f fixtures/cleanup_notes.md ]]; then
  echo "FATAL: fixtures/cleanup_notes.md missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/raw_sales.csv) - 1))
echo "[setup] c-02 ready: ${rows} raw rows in fixtures/raw_sales.csv (some will be dropped); finance's rules in fixtures/cleanup_notes.md"
