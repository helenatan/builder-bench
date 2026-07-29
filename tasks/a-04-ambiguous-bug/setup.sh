#!/usr/bin/env bash
# Build the fixed starting state for task a-04.
# The sandbox copies fixtures into workdir/fixtures/; this task's files belong at the workdir
# root (the prompt says `python3 report.py`, and report.py reads sales.csv from cwd).
set -euo pipefail

for f in report.py sales.csv; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
  mv "fixtures/$f" "$f"
done
rmdir fixtures 2>/dev/null || true

echo "[setup] a-04 ready: a report script with more than one plausible bug"
