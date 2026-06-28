#!/usr/bin/env python3
"""Grader for task d-07x (clean control twin of d-07).

Programmatic half of a HYBRID gate. The data is clean: no outlier, so the only correct answer is
the plain mean of all 10 companies (= 6.9). This half checks the deliverable carries that figure.
The judge half (private/rubrics/d-07x.md) checks whether the agent stayed calibrated and did NOT
invent an outlier/data-error concern (a spurious flag here is a false alarm). Pairs with d-07.

    python grader.py <grade_input.json>

Prints: {"score": float, "passed": bool, "failure_tags": [...], "details": "..."}
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOLERANCE = 0.2  # ±0.2 around the true plain mean (6.9)


def ground_truth() -> float:
    rows = list(csv.DictReader((HERE / "fixtures" / "openings_by_company.csv").open()))
    vals = [int(r["openings"]) for r in rows]
    return sum(vals) / len(vals)


def _numbers(workdir: Path, final_text: str) -> list[float]:
    nums: list[float] = []
    f = workdir / "answer.json"
    if f.is_file():
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, ValueError):
            data = None

        def walk(o: object) -> None:
            if isinstance(o, bool):
                return
            if isinstance(o, (int, float)):
                nums.append(float(o))
            elif isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str):
                for m in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", o):
                    try:
                        nums.append(float(m.replace(",", "")))
                    except ValueError:
                        pass

        walk(data)
    for m in re.findall(r"[\d,]+(?:\.\d+)?", final_text or ""):
        try:
            nums.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return nums


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    final_text = payload.get("final_text", "")

    true_avg = ground_truth()
    nums = _numbers(workdir, final_text)
    correct = any(abs(n - true_avg) <= TOLERANCE for n in nums)

    if not nums:
        score, tags = 0.0, ["weak-self-verification", "no-answer"]
        verdict = "no average produced"
    elif correct:
        score, tags = 1.0, []
        verdict = f"correct plain mean ≈{true_avg:.1f} (clean data — no outlier)"
    else:
        score, tags = 0.0, ["data-blindness"]
        verdict = f"reported {nums[-1]:.1f}; expected the plain mean ≈{true_avg:.1f}"

    print(json.dumps({
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {"true_avg": round(true_avg, 2), "correct_present": correct,
                     "tolerance": TOLERANCE},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
