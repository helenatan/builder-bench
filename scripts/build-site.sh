#!/usr/bin/env bash
# Regenerate the static leaderboard into public/ for deployment. The site is
# served at helenatan.ai/projects/builder-bench, so the pages live under that
# same path here (see vercel.json) and link to each other by absolute path.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m harness.report --base /projects/builder-bench/ --out public/projects/builder-bench/index.html
echo "[build-site] public/projects/builder-bench/ is up to date"
