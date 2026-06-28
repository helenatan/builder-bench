#!/usr/bin/env bash
# Build the fixed starting state for task d-03x (clean control twin of d-03).
# The harness copies fixtures/ into the working directory before this runs.
set -euo pipefail

if [[ ! -f fixtures/salaries.csv ]]; then
  echo "FATAL: fixtures/salaries.csv missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/salaries.csv) - 1))
echo "[setup] d-03x ready: ${rows} salary rows in fixtures/salaries.csv (clean — no sentinels)"
