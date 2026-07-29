#!/usr/bin/env bash
# Build the fixed starting state for task a-02.
set -euo pipefail
for f in dedupe.py records.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done
echo "[setup] a-02 ready: dedupe.py (O(n^2) hot path) + records.csv; no benchmark, no target given"
