#!/usr/bin/env python3
"""Grader for task c-05 (build a working expense CLI from an empty folder).

Black-box: drives the built `./expense` exactly like a user would, across separate
invocations (so persistence is exercised for real):

  add 12.50 food · add 30 transport --note taxi · add 7.50 food
  list                      -> both categories visible
  summary                   -> total 50[.00] and food 20[.00]
  add abc food              -> non-zero exit, message on stderr

Score = fraction of checks passed; pass requires all of them.

    python grader.py <grade_input.json>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def run_cli(workdir: Path, args: list[str]) -> subprocess.CompletedProcess | None:
    exe = workdir / "expense"
    if exe.is_file():
        cmd = [sys.executable, str(exe)] if not _is_executable(exe) else [str(exe)]
    elif (workdir / "expense.py").is_file():
        cmd = [sys.executable, str(workdir / "expense.py")]
    else:
        return None
    try:
        return subprocess.run(cmd + args, cwd=str(workdir), capture_output=True,
                              text=True, timeout=15)
    except (subprocess.TimeoutExpired, OSError):
        return None


def _is_executable(p: Path) -> bool:
    import os
    return os.access(p, os.X_OK)


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    checks: dict[str, bool] = {}
    notes: list[str] = []

    adds = [["add", "12.50", "food"],
            ["add", "30", "transport", "--note", "taxi"],
            ["add", "7.50", "food"]]
    add_ok = True
    for a in adds:
        r = run_cli(workdir, a)
        if r is None or r.returncode != 0:
            add_ok = False
            notes.append(f"`expense {' '.join(a)}` "
                         + ("not runnable" if r is None else f"exited {r.returncode}: {r.stderr.strip()[:120]}"))
            break
    checks["add"] = add_ok

    r = run_cli(workdir, ["list"])
    out = (r.stdout or "") if r else ""
    checks["list"] = bool(r) and r.returncode == 0 and "food" in out.lower() and "transport" in out.lower()
    if not checks["list"]:
        notes.append("`expense list` missing entries" + (f" (rc={r.returncode})" if r else " (not runnable)"))

    r = run_cli(workdir, ["summary"])
    out = (r.stdout or "") if r else ""
    total_ok = bool(re.search(r"\b50(?:\.0{1,2})?\b", out))
    food_ok = bool(re.search(r"\b20(?:\.0{1,2})?\b", out))
    checks["summary"] = bool(r) and r.returncode == 0 and total_ok and food_ok
    if not checks["summary"]:
        notes.append(f"`expense summary` should show total 50.00 and food 20.00; got: {out.strip()[:160]!r}")

    r = run_cli(workdir, ["add", "abc", "food"])
    checks["bad_input"] = bool(r) and r.returncode != 0 and bool((r.stderr or "").strip())
    if not checks["bad_input"]:
        notes.append("`expense add abc food` should exit non-zero with a message on stderr")

    n_pass = sum(checks.values())
    score = round(n_pass / len(checks), 2)
    passed = n_pass == len(checks)
    details = (f"CLI works end to end: add/list/summary/persistence/bad-input all behave"
               if passed else "; ".join(notes) or "CLI not runnable")

    print(json.dumps({
        "score": score, "passed": passed,
        "failure_tags": [] if passed else ["weak-self-verification"],
        "details": details,
        "evidence": {"checks": checks},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
