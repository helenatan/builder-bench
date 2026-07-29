"""Task version fingerprinting — staleness detection for logged runs.

A run is only a valid run *of a task* if the task hasn't changed since. The runner stamps
every run with a fingerprint of the task folder it executed (`task_version` in result.json /
summary.json / the leaderboard row). Consumers compare that stamp against the task's current
fingerprint and refuse to mix versions:

  - harness/report.py drops stale leaderboard rows (with a loud warning) at build time.
  - judge/validation/validate.py skips stale transcripts so they never reach human labeling.

The fingerprint covers everything in the task folder that defines the task — prompts,
fixtures, grader, setup.sh, success.yaml. It deliberately does NOT cover the private split:
a rubric edit invalidates *judge labels* (re-judge with `validate collect`), not the runs
themselves, so it must not mark transcripts stale.

Audit CLI — compare every logged run against the current tasks:

    python -m harness.taskhash            # report fresh / STALE / legacy per run
    python -m harness.taskhash --quiet    # exit code only (1 if anything is stale)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
RUNS_DIR = REPO_ROOT / "results" / "runs"

_SKIP_PARTS = {"__pycache__", ".git", ".DS_Store"}
_SKIP_SUFFIXES = {".pyc"}


def task_version_hash(task_dir: Path) -> str:
    """Deterministic short fingerprint of a task folder: sha256 over the sorted
    (relative path, file bytes) of every file that defines the task."""
    h = hashlib.sha256()
    for p in sorted(task_dir.rglob("*")):
        rel = p.relative_to(task_dir)
        if not p.is_file():
            continue
        if any(part in _SKIP_PARTS for part in rel.parts) or p.suffix in _SKIP_SUFFIXES:
            continue
        h.update(str(rel).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:12]


def current_hashes() -> dict[str, str]:
    """{task_id: current fingerprint} for every task folder, keyed by the short id prefix
    (folder 'b-01-dedup-survives' -> id 'b-01') and also by the full folder name."""
    out: dict[str, str] = {}
    if not TASKS_DIR.is_dir():
        return out
    for d in sorted(TASKS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        digest = task_version_hash(d)
        out[d.name] = digest
        short = "-".join(d.name.split("-")[:2])  # 'b-01-dedup-survives' -> 'b-01'
        out.setdefault(short, digest)
    return out


def run_task_version(run_root: Path) -> str | None:
    """The task_version a logged run was stamped with, from summary.json or any attempt's
    result.json. None for legacy runs that predate stamping."""
    candidates = [run_root / "summary.json"]
    candidates += sorted(run_root.glob("attempt-*/result.json"))
    for p in candidates:
        try:
            v = json.loads(p.read_text()).get("task_version")
        except Exception:  # noqa: BLE001
            continue
        if v:
            return str(v)
    return None


def audit(quiet: bool = False) -> int:
    """Compare every run under results/runs/ to the current task fingerprints.
    Returns the number of stale runs found."""
    current = current_hashes()
    fresh, stale, legacy, orphaned = [], [], [], []
    if RUNS_DIR.is_dir():
        for run_root in sorted(RUNS_DIR.glob("*/*/*")):
            if not run_root.is_dir():
                continue
            task_id = run_root.relative_to(RUNS_DIR).parts[0]
            now = current.get(task_id)
            then = run_task_version(run_root)
            rel = str(run_root.relative_to(REPO_ROOT))
            if now is None:
                orphaned.append(rel)
            elif then is None:
                legacy.append(rel)
            elif then == now:
                fresh.append(rel)
            else:
                stale.append(f"{rel}  (ran {then}, task is now {now})")

    if not quiet:
        print(f"tasks: {len({k for k in current if k.count('-') == 1})}  "
              f"runs: fresh={len(fresh)} stale={len(stale)} legacy={len(legacy)} "
              f"orphaned={len(orphaned)}")
        for label, items in (("STALE — task changed since this run; archive and re-run", stale),
                             ("ORPHANED — no matching task folder", orphaned),
                             ("LEGACY — predates version stamping; verify by hand", legacy)):
            if items:
                print(f"\n{label}:")
                for it in items:
                    print(f"  {it}")
    return len(stale)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="builder-bench-taskhash",
                                description="Audit logged runs against current task versions")
    p.add_argument("--quiet", action="store_true", help="no output; exit 1 if stale runs exist")
    args = p.parse_args(argv)
    n_stale = audit(quiet=args.quiet)
    return 1 if n_stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
