#!/usr/bin/env python3
"""Grader for task d-10 (top revenue month — the two exports use different date formats).

orders_us.csv is MM/DD/YYYY; orders_intl.csv is DD/MM/YYYY. The intl file proves its own
format (25/03/2026 cannot be month 25), but every intl date with day <= 12 parses "fine"
under a US reading — landing silently in the wrong month. The prompt states only the
question (the tell is in the data); it never says "check the formats" (the trap).

Two failure modes are distinguished:

  - format-blind          -> parsed both files as one format (dateutil-style: US order,
                             auto-swap when invalid) and crowned March at 3,100
  - anything else wrong   -> other

    python grader.py <grade_input.json>

Prints: {"score": float, "passed": bool, "failure_tags": [...], "details": "..."}
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_ID = "d-10"
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


def _month_us_first(d: str) -> str:
    """dateutil-style naive parse: assume MM/DD, swap only when that's impossible."""
    a, b, y = d.split("/")
    m = int(a) if int(a) <= 12 else int(b)
    return f"{y}-{m:02d}"


def ground_truth() -> dict:
    us = list(csv.DictReader((HERE / "fixtures" / "orders_us.csv").open()))
    intl = list(csv.DictReader((HERE / "fixtures" / "orders_intl.csv").open()))

    correct: dict[str, float] = {}
    naive: dict[str, float] = {}
    for r in us:  # MM/DD/YYYY — same under both readings by construction of the tell
        m, _, y = r["date"].split("/")
        key = f"{y}-{int(m):02d}"
        correct[key] = round(correct.get(key, 0.0) + float(r["amount"]), 2)
        nk = _month_us_first(r["date"])
        naive[nk] = round(naive.get(nk, 0.0) + float(r["amount"]), 2)
    for r in intl:  # DD/MM/YYYY
        _, m, y = r["date"].split("/")
        key = f"{y}-{int(m):02d}"
        correct[key] = round(correct.get(key, 0.0) + float(r["amount"]), 2)
        nk = _month_us_first(r["date"])
        naive[nk] = round(naive.get(nk, 0.0) + float(r["amount"]), 2)

    top = max(correct, key=correct.get)
    naive_top = max(naive, key=naive.get)
    return {"correct": correct, "naive": naive,
            "top": top, "top_revenue": correct[top],
            "naive_top": naive_top, "naive_revenue": naive[naive_top]}


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    gt = ground_truth()

    expected = _load_expected("answer.json")
    if expected is not None:
        assert expected["top_month"] == gt["top"], "fixture/expected mismatch — task is broken"
        assert abs(expected["revenue"] - gt["top_revenue"]) <= TOLERANCE, \
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

    got_month = str(got.get("top_month", "")).strip()
    try:
        got_rev = round(float(got.get("revenue")), 2)
    except (TypeError, ValueError):
        got_rev = None

    month_ok = got_month == gt["top"]
    rev_ok = got_rev is not None and abs(got_rev - gt["top_revenue"]) <= TOLERANCE

    if month_ok and rev_ok:
        result = {
            "score": 1.0, "passed": True, "failure_tags": [],
            "details": (
                f"Parsed each export in its own format: {gt['top']} tops at {gt['top_revenue']:.2f} "
                "(intl file read day-first, as its own day>12 rows require)"
            ),
        }
    elif got_month == gt["naive_top"] and got_rev is not None \
            and abs(got_rev - gt["naive_revenue"]) <= TOLERANCE:
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["data-blindness"],
            "details": (
                f"Format-blind: reported {got_month} at {got_rev} — both files parsed as US-style "
                f"dates. The intl export is day-first (its 25/03-style rows prove it); parsed "
                f"correctly, {gt['top']} wins at {gt['top_revenue']:.2f}."
            ),
        }
    else:
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["data-blindness"],
            "details": f"Incorrect: reported {got_month} at {got_rev}, "
                       f"expected {gt['top']} at {gt['top_revenue']:.2f}",
        }

    result["evidence"] = {
        "reported": {"top_month": got_month, "revenue": got_rev},
        "expected": {"top_month": gt["top"], "revenue": gt["top_revenue"]},
        "correct_by_month": gt["correct"],
        "format_blind_by_month": gt["naive"],
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
