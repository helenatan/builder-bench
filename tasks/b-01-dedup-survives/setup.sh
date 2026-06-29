#!/usr/bin/env bash
# Build the fixed starting state for task b-01.
# The harness has already copied fixtures/ into the working directory; this script just
# asserts the known-good seed is present so a broken sandbox fails loudly and early.
set -euo pipefail

for f in postings.csv new_postings.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done

rows=$(($(wc -l < fixtures/postings.csv) - 1))   # minus header
new=$(($(wc -l < fixtures/new_postings.csv) - 1))
echo "[setup] b-01 ready: ${rows} postings + ${new} new_postings (merged at step 4)"
