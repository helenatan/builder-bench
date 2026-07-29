#!/usr/bin/env bash
# Build the fixed starting state for task c-05: an intentionally empty project.
set -euo pipefail
rmdir fixtures 2>/dev/null || true
echo "[setup] c-05 ready: empty project, CLI contract in the prompt"
