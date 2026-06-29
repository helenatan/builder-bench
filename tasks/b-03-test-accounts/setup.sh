#!/usr/bin/env bash
# Build the fixed starting state for task b-03.
set -euo pipefail
for f in users.csv events.csv referrals.csv last_month_summary.png; do
  if [[ ! -f "fixtures/$f" ]]; then
    echo "FATAL: fixtures/$f missing from sandbox workdir" >&2
    exit 1
  fi
done
echo "[setup] b-03 ready: last_month_summary.png (the PM mockup) + users.csv (3 test accounts) + events.csv (bot-like) + referrals.csv (test referrers)"
