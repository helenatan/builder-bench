# Archive

One-off scripts from specific historical runs (re-grading a task after a rubric change,
resuming a benchmark sweep after the subscription's usage window was exhausted mid-run, etc.).
Kept for provenance — each script's log is referenced from commit messages and `suite-state`
notes — but they're tied to a specific incident, not reusable tooling.

For running the suite today, use `python -m harness.runner` directly (see the root
[README](../../README.md#quickstart)) or `scripts/build-site.sh` to rebuild the leaderboard.
