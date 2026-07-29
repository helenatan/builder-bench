#!/usr/bin/env python3
"""Grader for task b-04 ("active customer" definition survives a fuller export).

Step 1 pins the definition: active = at least one purchase dated 2026-05-02..2026-06-30, a
fixed window. Step 3 swaps in purchases_full.csv (two years of history, no new rows inside the
window) and asks for an all-time revenue figure — the pressure point where "active" is tempted
to drift into "appears anywhere in the full file."

Ground truth is recomputed from the fixtures. Two failure modes are distinguished:

  - drifted definition   -> active count/by-plan computed over the whole file (12), or the
                            window re-anchored, instead of the pinned window (5)
  - anything else wrong  -> other

    python grader.py <grade_input.json>

Prints: {"score": float, "passed": bool, "failure_tags": [...], "details": "..."}
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_ID = "b-04"
WINDOW_START, WINDOW_END = "2026-05-02", "2026-06-30"
TOLERANCE = 0.01


def _load_expected(name: str):
    """Answer key lives in the held-out private split; fall back to an in-task expected/ dir.
    Returns the parsed JSON, or None if no key is present (the grader recomputes truth from
    fixtures regardless — the key is only a guard against the task silently drifting)."""
    for base in (HERE.parents[1] / "private" / "expected" / TASK_ID, HERE / "expected"):
        p = base / name
        if p.is_file():
            return json.loads(p.read_text())
    return None


def ground_truth() -> dict:
    plans = {r["customer_id"]: r["plan"].strip()
             for r in csv.DictReader((HERE / "fixtures" / "customers.csv").open())}
    full = list(csv.DictReader((HERE / "fixtures" / "purchases_full.csv").open()))

    active = {r["customer_id"] for r in full if WINDOW_START <= r["date"].strip() <= WINDOW_END}
    by_plan: dict[str, int] = {}
    for c in active:
        by_plan[plans[c]] = by_plan.get(plans[c], 0) + 1
    revenue = round(sum(float(r["amount"]) for r in full if r["customer_id"] in active), 2)

    # The drift shape: "active" = appears anywhere in the full export.
    drifted = {r["customer_id"] for r in full}
    drifted_by_plan: dict[str, int] = {}
    for c in drifted:
        drifted_by_plan[plans[c]] = drifted_by_plan.get(plans[c], 0) + 1

    return {
        "active": len(active), "by_plan": by_plan, "revenue": revenue,
        "drifted_active": len(drifted), "drifted_by_plan": drifted_by_plan,
    }


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    gt = ground_truth()

    expected = _load_expected("metrics.json")
    if expected is not None:
        assert expected["active_customers"] == gt["active"], "fixture/expected mismatch — task is broken"
        assert expected["active_by_plan"] == gt["by_plan"], "fixture/expected mismatch — task is broken"
        assert abs(expected["active_customer_revenue_alltime"] - gt["revenue"]) <= TOLERANCE, \
            "fixture/expected mismatch — task is broken"

    f = workdir / "answer.json"
    if not f.is_file():
        print(json.dumps({
            "score": 0.0, "passed": False,
            "failure_tags": ["weak-self-verification", "no-answer"],
            "details": "no answer.json produced",
        }))
        return 0
    try:
        got = json.loads(f.read_text())
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({
            "score": 0.0, "passed": False, "failure_tags": ["weak-self-verification"],
            "details": "answer.json is not valid JSON",
        }))
        return 0

    try:
        got_active = int(got.get("active_customers"))
    except (TypeError, ValueError):
        got_active = None
    got_plan = got.get("active_by_plan") if isinstance(got.get("active_by_plan"), dict) else {}
    got_plan = {k: v for k, v in got_plan.items()}
    try:
        got_rev = round(float(got.get("active_customer_revenue_alltime")), 2)
    except (TypeError, ValueError):
        got_rev = None

    active_ok = got_active == gt["active"]
    plan_ok = {k: int(v) for k, v in got_plan.items() if v is not None} == gt["by_plan"]
    rev_ok = got_rev is not None and abs(got_rev - gt["revenue"]) <= TOLERANCE

    if active_ok and plan_ok and rev_ok:
        result = {
            "score": 1.0, "passed": True, "failure_tags": [],
            "details": (
                f"Definition held: {gt['active']} active (window {WINDOW_START}..{WINDOW_END}), "
                f"by-plan {gt['by_plan']}, all-time revenue {gt['revenue']:.2f}"
            ),
        }
    elif got_active == gt["drifted_active"] or got_plan == gt["drifted_by_plan"]:
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["vision-drift"],
            "details": (
                f"Definition drifted at step 3: reported active={got_active} "
                f"(= every customer in the full export), expected {gt['active']} "
                f"(the pinned {WINDOW_START}..{WINDOW_END} window)"
            ),
        }
    else:
        wrong = []
        if not active_ok:
            wrong.append(f"active_customers={got_active} (expected {gt['active']})")
        if not plan_ok:
            wrong.append(f"active_by_plan={got_plan} (expected {gt['by_plan']})")
        if not rev_ok:
            wrong.append(f"active_customer_revenue_alltime={got_rev} (expected {gt['revenue']:.2f})")
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["weak-self-verification"],
            "details": "Incorrect: " + "; ".join(wrong),
        }

    result["evidence"] = {
        "reported": {"active_customers": got_active, "active_by_plan": got_plan,
                     "active_customer_revenue_alltime": got_rev},
        "expected": {"active_customers": gt["active"], "active_by_plan": gt["by_plan"],
                     "active_customer_revenue_alltime": gt["revenue"]},
        "drift_shape": {"active_customers": gt["drifted_active"], "active_by_plan": gt["drifted_by_plan"]},
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
