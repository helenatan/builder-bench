#!/usr/bin/env bash
# Build the fixed starting state for task c-01.
# The harness copies fixtures/ into the working directory before this runs.
set -euo pipefail

if [[ ! -f fixtures/PRD.md ]]; then
  echo "FATAL: fixtures/PRD.md missing from sandbox workdir" >&2
  exit 1
fi

echo "[setup] c-01 ready: PRD.md present, empty project to build into"
