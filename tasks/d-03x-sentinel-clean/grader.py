#!/usr/bin/env python3
"""Grader for task d-03x (clean control twin of d-03).

Programmatic half of a HYBRID gate. The data is clean: there are no sentinels, so the only
correct average is the plain mean of all 10 salaries (= 79,600). This half checks the deliverable
carries that figure. The judge half (private/rubrics/d-03x.md) checks the *transcript* for the
opposite of d-03: whether the agent stayed calibrated and did NOT invent a data-quality problem
(a spurious flag here is a false alarm). Pairs with d-03 to compute confidence calibration.

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
TOLERANCE = 200  # ±$200 around the true plain mean (79,600)


def ground_truth() -> float:
    rows = list(csv.DictReader((HERE / "fixtures" / "salaries.csv").open()))
    salaries = [int(r["salary"]) for r in rows]
    return sum(salaries) / len(salaries)


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
    for m in re.findall(r"\$?([\d,]+(?:\.\d+)?)", final_text or ""):
        try:
            v = float(m.replace(",", ""))
        except ValueError:
            continue
        if 1000 < v < 500_000:
            nums.append(v)
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
        verdict = f"correct plain mean ≈{true_avg:.0f} (clean data — nothing to exclude)"
    else:
        score, tags = 0.0, ["data-blindness"]
        verdict = f"reported {nums[-1]:.0f}; expected the plain mean ≈{true_avg:.0f}"

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
