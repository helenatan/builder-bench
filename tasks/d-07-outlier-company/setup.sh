#!/usr/bin/env bash
# Build the fixed starting state for task d-07.
set -euo pipefail
if [[ ! -f fixtures/openings_by_company.csv ]]; then
  echo "FATAL: fixtures/openings_by_company.csv missing from sandbox workdir" >&2
  exit 1
fi
echo "[setup] d-07 ready: openings_by_company.csv (one company's count is an absurd outlier)"
