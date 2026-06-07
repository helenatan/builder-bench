#!/usr/bin/env bash
# Build the fixed starting state for task d-01.
# The harness has already copied fixtures/ into the working directory; this script just
# asserts the known-good seed is present so a broken sandbox fails loudly and early.
set -euo pipefail

if [[ ! -f fixtures/postings.csv ]]; then
  echo "FATAL: fixtures/postings.csv missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/postings.csv) - 1))   # minus header
echo "[setup] d-01 ready: ${rows} raw postings in fixtures/postings.csv"
