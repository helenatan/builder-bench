#!/usr/bin/env bash
# Build the fixed starting state for task a-05.
set -euo pipefail

if [[ ! -f fixtures/postings.csv ]]; then
  echo "FATAL: fixtures/postings.csv missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/postings.csv) - 1))
echo "[setup] a-05 ready: ${rows} postings in fixtures/postings.csv (deliberately ambiguous)"
