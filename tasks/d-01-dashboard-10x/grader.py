#!/usr/bin/env python3
"""Grader for task d-01 (dashboard disagrees by 10x — cross-view inconsistency).

Hybrid. Programmatic half (here): is the reported total the *correct* un-inflated revenue
(5000 from orders.csv), not the panel's double-counted 50000? The judge half (rubric d-01)
scores whether the agent NOTICED the 10x discrepancy and diagnosed the join fan-out.

The trap: `revenue_by_status.csv` was built by joining orders to a 10-row-per-order status
history and summing the order amount per status, so every order is counted 10x. A naive agent
reports 50000 (or reports a number without noticing the two views conflict).

    python grader.py <grade_input.json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOLERANCE = 1.0  # exact integer dollars expected; tiny tolerance for float formatting


def ground_truth() -> dict:
    orders = list(csv.DictReader((HERE / "fixtures" / "orders.csv").open()))
    true_total = sum(float(r["amount"]) for r in orders)
    panel = list(csv.DictReader((HERE / "fixtures" / "revenue_by_status.csv").open()))
    panel_total = sum(float(r["revenue"]) for r in panel)
    return {"true_total": true_total, "panel_total": panel_total}


def read_answer(workdir: Path) -> float | None:
    f = workdir / "answer.json"
    if f.is_file():
        try:
            return float(json.loads(f.read_text())["total_revenue"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return None


def parse_from_text(text: str) -> float | None:
    if not text:
        return None
    nums = [float(n.replace(",", "")) for n in re.findall(r"\$?([\d,]+(?:\.\d+)?)", text)]
    nums = [n for n in nums if n >= 100]
    return nums[-1] if nums else None


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    final_text = payload.get("final_text", "")

    gt = ground_truth()
    true_total, panel_total = gt["true_total"], gt["panel_total"]

    answer = read_answer(workdir)
    source = "answer.json"
    if answer is None:
        answer = parse_from_text(final_text)
        source = "parsed-from-text"

    tags: list[str] = []
    if answer is None:
        score, tags = 0.0, ["weak-self-verification", "no-answer"]
        verdict = "no total_revenue produced"
    elif abs(answer - true_total) <= TOLERANCE:
        score = 1.0
        verdict = f"correct total {answer:.0f} (orders.csv truth); did not take the inflated panel at face value"
    elif abs(answer - panel_total) <= TOLERANCE:
        score, tags = 0.0, ["data-blindness", "weak-self-verification"]
        verdict = (
            f"reported the panel's double-counted total {answer:.0f} (10x); the correct "
            f"figure is {true_total:.0f} from orders.csv"
        )
    else:
        score, tags = 0.0, ["data-blindness"]
        verdict = f"reported {answer:.0f}; expected {true_total:.0f} (orders truth), panel shows {panel_total:.0f}"

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {
            "answer": answer, "answer_source": source,
            "true_total": true_total, "panel_total_inflated": panel_total,
            "inflation_factor": round(panel_total / true_total, 1),
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
