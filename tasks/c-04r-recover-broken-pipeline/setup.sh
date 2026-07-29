#!/usr/bin/env bash
# Build the fixed starting state for task c-04r (recover from a broken pipeline).
# The sandbox copies the task's fixtures into workdir/fixtures/; this task's files belong at
# the workdir root (the prompt says `bash run.sh`, and pipeline.py reads events.csv from cwd).
set -euo pipefail

for f in events.csv pipeline.py run.sh; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
  mv "fixtures/$f" "$f"
done
rmdir fixtures 2>/dev/null || true
chmod +x run.sh 2>/dev/null || true

echo "[setup] c-04r ready: events.csv + a pipeline that does not yet run cleanly"
