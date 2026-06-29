#!/usr/bin/env bash
# Build the fixed starting state for task c-03: a small working app with an unprotected
# /dashboard. Copy the base app to the project root so the agent extends a runnable app.
set -euo pipefail

if [[ ! -f fixtures/app.py || ! -f fixtures/run.sh ]]; then
  echo "FATAL: fixtures/app.py or fixtures/run.sh missing from sandbox workdir" >&2
  exit 1
fi
if [[ ! -f fixtures/acceptance_criteria.md ]]; then
  echo "FATAL: fixtures/acceptance_criteria.md missing from sandbox workdir" >&2
  exit 1
fi

cp fixtures/app.py app.py
cp fixtures/run.sh run.sh
chmod +x run.sh

echo "[setup] c-03 ready: app.py + run.sh at project root; /dashboard and /settings are currently public; QA's checks in fixtures/acceptance_criteria.md"
