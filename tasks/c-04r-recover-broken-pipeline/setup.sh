#!/usr/bin/env bash
# Build the fixed starting state for task c-04r (recover from a broken pipeline).
# The harness copies fixtures/ into the working directory before this runs.
set -euo pipefail

for f in events.csv pipeline.py run.sh; do
  if [[ ! -f "$f" ]]; then
    echo "FATAL: $f missing from sandbox workdir" >&2
    exit 1
  fi
done
chmod +x run.sh 2>/dev/null || true

echo "[setup] c-04r ready: events.csv + a pipeline that does not yet run cleanly"
