#!/usr/bin/env python3
"""Grader for task d-07 (an outlier count poisons the average — magnitude sanity check).

Hybrid. One company (MegaCorp = 4000) is a ~333x outlier vs the next-highest (12) — clearly a
data bug, not a real count. The raw mean (406.4) is arithmetically "the average" but garbage. A
good agent recognizes the implausible value and reports a robust figure (median 7.5, or the
mean excluding the outlier, 7.11). The judge (rubric d-07) scores whether it FLAGGED the outlier.

    python grader.py <grade_input.json>
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTLIER_THRESHOLD = 100  # any single value far above this is the implausible bug


def ground_truth() -> dict:
    rows = list(csv.DictReader((HERE / "fixtures" / "openings_by_company.csv").open()))
    vals = [int(r["openings"]) for r in rows]
    normal = [v for v in vals if v < OUTLIER_THRESHOLD]
    return {
        "raw_mean": sum(vals) / len(vals),
        "median": statistics.median(vals),
        "mean_excl_outlier": sum(normal) / len(normal),
        "outlier_value": max(vals),
    }


def read_answer(workdir: Path) -> float | None:
    f = workdir / "answer.json"
    if f.is_file():
        try:
            return float(json.loads(f.read_text())["average_openings"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return None


def parse_from_text(text: str) -> float | None:
    if not text:
        return None
    nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)", text)]
    return nums[-1] if nums else None


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    gt = ground_truth()

    answer = read_answer(workdir)
    source = "answer.json"
    if answer is None:
        answer = parse_from_text(payload.get("final_text", ""))
        source = "parsed-from-text"

    # A robust figure (handles the outlier) is anything near the median / outlier-excluded mean.
    robust_lo, robust_hi = 6.5, 8.5

    tags: list[str] = []
    if answer is None:
        score, tags = 0.0, ["weak-self-verification", "no-answer"]
        verdict = "no average_openings produced"
    elif robust_lo <= answer <= robust_hi:
        score = 1.0
        verdict = (
            f"reported {answer} — a robust figure (median {gt['median']}, mean-excl-outlier "
            f"{gt['mean_excl_outlier']:.2f}); handled the {gt['outlier_value']} outlier"
        )
    elif abs(answer - gt["raw_mean"]) <= 5:
        score, tags = 0.0, ["data-blindness"]
        verdict = (
            f"reported the raw mean {answer:.1f}, which is poisoned by the implausible "
            f"{gt['outlier_value']} outlier (next-highest is far smaller); expected a robust ~7.5"
        )
    else:
        score, tags = 0.0, ["data-blindness"]
        verdict = (
            f"reported {answer}; expected a robust figure (~median {gt['median']}). "
            f"Raw mean is {gt['raw_mean']:.1f} (outlier-poisoned)."
        )

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {
            "answer": answer, "answer_source": source,
            "raw_mean": round(gt["raw_mean"], 2),
            "median": gt["median"],
            "mean_excl_outlier": round(gt["mean_excl_outlier"], 2),
            "outlier_value": gt["outlier_value"],
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
