#!/usr/bin/env bash
# Regenerate the static leaderboard into public/ for deployment.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m harness.report --out public/index.html
echo "[build-site] public/index.html is up to date"
