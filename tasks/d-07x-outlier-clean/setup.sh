#!/usr/bin/env bash
# Build the fixed starting state for task d-07x (clean control twin of d-07).
# The harness copies fixtures/ into the working directory before this runs.
set -euo pipefail

if [[ ! -f fixtures/openings_by_company.csv ]]; then
  echo "FATAL: fixtures/openings_by_company.csv missing from sandbox workdir" >&2
  exit 1
fi

rows=$(($(wc -l < fixtures/openings_by_company.csv) - 1))
echo "[setup] d-07x ready: ${rows} companies in fixtures/openings_by_company.csv (clean — no outlier)"
