#!/usr/bin/env bash
# Build the fixed starting state for task d-02.
# The harness copies fixtures/ into the working directory before this runs.
set -euo pipefail

if [[ ! -f fixtures/postings.csv ]]; then
  echo "FATAL: fixtures/postings.csv missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/postings.csv) - 1))
echo "[setup] d-02 ready: ${rows} raw posting rows in fixtures/postings.csv"
