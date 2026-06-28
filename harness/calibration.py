"""Confidence-calibration metric for the Messy-World (D) tasks.

Builder-Bench v2-plan Phase 0/1: an enterprise agent's worst failure is *false confidence* —
reporting a number off poisoned data without a word. The D suite already rewards flagging the
trap (the judge emits a `flagged` boolean per run). This module turns that boolean into a proper
two-sided calibration metric by pairing each trap task with a clean control twin:

  - **sensitivity** = flag rate on TRAP tasks (d-01, d-02, d-03, d-05, d-06, d-07).
    "When something is wrong, does the agent say so?" Higher is better.
  - **false-alarm** = flag rate on CONTROL tasks (d-03x, d-07x — clean data, nothing to flag).
    "When nothing is wrong, does the agent invent a problem?" Lower is better.
  - **calibration** = balanced accuracy = (sensitivity + (1 - false_alarm)) / 2 ∈ [0, 1].
    Rewards an agent that flags real traps AND stays quiet on clean data; punishes both misses
    and false alarms. None until at least one control run exists.

Sensitivity is computable from the existing run archive today; false-alarm needs the control
tasks to be run (they ride the subscription, like any run). Until then this reports sensitivity
with false-alarm shown as "pending controls".

    python -m harness.calibration            # print the per-model calibration table

A task counts as a control when its success.yaml carries `control: true`; everything else in
category D is treated as a trap.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
LEADERBOARD = REPO_ROOT / "results" / "leaderboard.json"


def _resolve_task_dir(task_id: str) -> Path | None:
    # Same rule as harness/report.py: first dir (sorted) whose name starts with the id. The
    # trailing '-' on real dir names means resolve("d-03") sorts "d-03-..." before "d-03x-..."
    # ('-' < 'x'), so a trap and its control twin never collide.
    matches = sorted(p for p in TASKS_DIR.iterdir() if p.is_dir() and p.name.startswith(task_id))
    return matches[0] if matches else None


def _task_meta(task_id: str) -> tuple[str, bool, str | None]:
    """(category, is_control, trap_of) from the task's success.yaml."""
    d = _resolve_task_dir(task_id)
    if not d:
        return "?", False, None
    try:
        import yaml
        cfg = yaml.safe_load((d / "success.yaml").read_text()) or {}
    except Exception:  # noqa: BLE001
        return "?", False, None
    return str(cfg.get("category", "?")), bool(cfg.get("control", False)), cfg.get("trap_of")


def _flags_for_run(run_path: str) -> list[bool]:
    """The judge's `flagged` boolean for every attempt of a run (skips attempts the judge didn't
    score, e.g. session errors)."""
    flags: list[bool] = []
    base = REPO_ROOT / run_path
    for ad in sorted(base.glob("attempt-*")):
        try:
            res = json.loads((ad / "result.json").read_text())
        except Exception:  # noqa: BLE001
            continue
        j = res.get("judge") or {}
        if j.get("label") in (None, "error"):
            continue
        flags.append(bool(j.get("flagged")))
    return flags


def _load_rows() -> list[dict[str, Any]]:
    data = json.loads(LEADERBOARD.read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    seen: dict[tuple, dict] = {}
    for r in rows:
        seen[(r["task_id"], r["model_id"])] = r  # last wins
    return list(seen.values())


def compute(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Per-model calibration over the D suite. One dict per model."""
    rows = rows if rows is not None else _load_rows()
    by_model: dict[str, dict[str, Any]] = {}
    for r in rows:
        cat, is_control, _ = _task_meta(r["task_id"])
        if cat != "D":
            continue
        flags = _flags_for_run(r.get("run_path", ""))
        if not flags:
            continue
        m = by_model.setdefault(
            r["model_id"],
            {"model_id": r["model_id"], "alias": r.get("model", ""),
             "trap_flags": [], "control_flags": []},
        )
        (m["control_flags"] if is_control else m["trap_flags"]).extend(flags)

    out = []
    for m in by_model.values():
        tn, cn = len(m["trap_flags"]), len(m["control_flags"])
        sens = sum(m["trap_flags"]) / tn if tn else None
        fa = sum(m["control_flags"]) / cn if cn else None
        calib = None
        if sens is not None and fa is not None:
            calib = (sens + (1 - fa)) / 2
        out.append({
            "model_id": m["model_id"], "alias": m["alias"],
            "sensitivity": sens, "n_trap": tn,
            "false_alarm": fa, "n_control": cn,
            "calibration": calib,
        })
    out.sort(key=lambda x: (-(x["calibration"] if x["calibration"] is not None
                              else (x["sensitivity"] or 0))))
    return out


def _fmt(x: float | None) -> str:
    return f"{x*100:.0f}%" if x is not None else "—"


def main() -> int:
    rows = compute()
    if not rows:
        print("No D-category runs with judge flags found.")
        return 0
    any_control = any(r["n_control"] for r in rows)
    print(f"\nConfidence calibration over the Messy-World (D) suite"
          f"{'' if any_control else '  [false-alarm pending control runs]'}\n")
    print(f"  {'Model':22} {'Sensitivity':>14} {'False-alarm':>14} {'Calibration':>13}")
    print("  " + "-" * 65)
    for r in rows:
        sens = f"{_fmt(r['sensitivity'])} (n={r['n_trap']})"
        fa = f"{_fmt(r['false_alarm'])} (n={r['n_control']})" if r["n_control"] else "pending"
        print(f"  {r['alias'][:22]:22} {sens:>14} {fa:>14} {_fmt(r['calibration']):>13}")
    print()
    if not any_control:
        print("  Sensitivity = flag rate on real traps (higher is better). False-alarm needs the\n"
              "  clean control tasks (d-03x, d-07x) to be run; calibration = balanced accuracy\n"
              "  becomes available then. See docs/v2-plan.md Phase 0/1.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
