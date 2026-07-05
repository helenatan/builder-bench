#!/usr/bin/env python3
"""Grader for task d-05 (silent row-cap truncation).

Hybrid. `orders.csv` has exactly 1000 rows — a default export page-limit — but its order_ids run
up to ~5200, and `monthly_summary.csv` (the reporting source of record) totals 5234. The naive
answer is "1000 orders" (the truncated row count). The correct answer reconciles to 5234 and
recognizes orders.csv is truncated. The judge (rubric d-05) scores whether the agent flagged the
truncation (the suspiciously round 1000 / IDs exceeding the row count).

    python grader.py <grade_input.json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ground_truth() -> dict:
    orders = list(csv.DictReader((HERE / "fixtures" / "orders.csv").open()))
    summary = list(csv.DictReader((HERE / "fixtures" / "monthly_summary.csv").open()))
    return {
        "true_total": sum(int(r["order_count"]) for r in summary),  # 5234
        "truncated_rows": len(orders),                              # 1000
        "max_order_id": max(int(r["order_id"]) for r in orders),
    }


def read_answer(workdir: Path) -> int | None:
    f = workdir / "answer.json"
    if f.is_file():
        try:
            return int(json.loads(f.read_text())["total_orders"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return None


def parse_from_text(text: str, true_total: int, truncated: int) -> int | None:
    if not text:
        return None
    # First, look for explicit "answer: N" or "total: N" patterns.
    explicit = re.search(r"(?:answer|total)\s*[:=]\s*(\d[\d,]*)", text, re.IGNORECASE)
    if explicit:
        return int(explicit.group(1).replace(",", ""))
    # Extract all large numbers (3+ digits) from the text.
    nums = [int(n.replace(",", "")) for n in re.findall(r"(\d[\d,]{2,})", text)]
    if not nums:
        return None
    # If the true answer appears in the text, prefer it over other numbers.
    if true_total in nums:
        return true_total
    # Never return the trap value (truncated row count) if alternatives exist.
    nums_no_trap = [n for n in nums if n != truncated]
    if nums_no_trap:
        # Return the first non-trap number (agents usually state the answer early).
        return nums_no_trap[0]
    # If only the trap exists, reject it (will fall through to "no answer" case).
    return None


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    gt = ground_truth()
    true_total, truncated = gt["true_total"], gt["truncated_rows"]

    answer = read_answer(workdir)
    source = "answer.json"
    if answer is None:
        answer = parse_from_text(payload.get("final_text", ""), true_total, truncated)
        source = "parsed-from-text"

    tags: list[str] = []
    if answer is None:
        score, tags = 0.0, ["weak-self-verification", "no-answer"]
        verdict = "no total_orders produced"
    elif answer == true_total:
        score = 1.0
        verdict = f"correct total {true_total} (reconciled to the summary; saw orders.csv was truncated at {truncated})"
    elif answer == truncated:
        score, tags = 0.0, ["data-blindness", "weak-self-verification"]
        verdict = (f"reported {truncated} — the truncated row count of orders.csv (a default export "
                   f"limit); the true total is {true_total} per monthly_summary.csv")
    else:
        score, tags = 0.0, ["data-blindness"]
        verdict = f"reported {answer}; expected {true_total} (orders.csv is truncated at {truncated} rows)"

    print(json.dumps({
        "score": score, "passed": score >= 1.0,
        "failure_tags": tags, "details": verdict,
        "evidence": {"answer": answer, "answer_source": source,
                     "true_total": true_total, "truncated_rows": truncated,
                     "max_order_id": gt["max_order_id"]},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
