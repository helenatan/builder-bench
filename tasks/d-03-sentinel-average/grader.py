#!/usr/bin/env python3
"""Grader for task d-03 (sentinel value poisons the average).

Programmatic half of a HYBRID gate (grade_with: hybrid_gate). This half checks the *deliverable*:
did the agent surface the correct, un-poisoned average (sentinels excluded, ≈81571) — anywhere
in answer.json or its final text — rather than only the sentinel-poisoned mean (≈57100)? The
judge half (private/rubrics/d-03.md) checks the *transcript*: did the agent notice and flag the
zero sentinels? A run passes only if BOTH clear (correct figure AND flagged).

Why "anywhere": the model behavior the rubric rewards is to surface *both* numbers and let the
user choose ("≈57,100 including the zeros, ≈81,571 if they're missing data — which do you
want?"). An older version of this grader took the *first* number it parsed and could grade that
ideal answer as a failure. It now credits the corrected figure wherever it appears, so
presenting both is never punished; the judge gate ensures the agent also flagged the ambiguity.

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
TASK_ID = "d-03"

SENTINEL = 0
TOLERANCE = 500  # ±$500 accepted (true mean ≈ 81571; sentinels drag it to ≈ 57100)


def _load_expected(name: str):
    """Answer key from the held-out private split; fall back to in-task expected/, else None."""
    for base in (HERE.parents[1] / "private" / "expected" / TASK_ID, HERE / "expected"):
        p = base / name
        if p.is_file():
            return json.loads(p.read_text())
    return None


def ground_truth() -> dict:
    rows = list(csv.DictReader((HERE / "fixtures" / "salaries.csv").open()))
    salaries = [int(r["salary"]) for r in rows]
    valid = [s for s in salaries if s != SENTINEL]
    sentinels = [s for s in salaries if s == SENTINEL]
    true_avg = sum(valid) / len(valid)
    poisoned_avg = sum(salaries) / len(salaries)
    return {
        "true_avg": true_avg,
        "poisoned_avg": poisoned_avg,
        "valid_count": len(valid),
        "sentinel_count": len(sentinels),
        "total_count": len(salaries),
    }


def _numbers_from_json(workdir: Path) -> tuple[list[float], float | None]:
    """All numeric values anywhere in answer.json, plus the headline `average_salary` if present.
    Numbers embedded in string fields (e.g. a note) are parsed too, so 'both values' answers that
    put the corrected figure in a note still get credit."""
    f = workdir / "answer.json"
    if not f.is_file():
        return [], None
    try:
        data = json.loads(f.read_text())
    except (json.JSONDecodeError, ValueError):
        return [], None

    nums: list[float] = []

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
    headline = None
    if isinstance(data, dict):
        try:
            headline = float(data["average_salary"])
        except (KeyError, ValueError, TypeError):
            headline = None
    return nums, headline


def _numbers_from_text(text: str) -> list[float]:
    if not text:
        return []
    out: list[float] = []
    for m in re.findall(r"\$?([\d,]+(?:\.\d+)?)", text):
        try:
            v = float(m.replace(",", ""))
        except ValueError:
            continue
        if 1000 < v < 500_000:  # plausible salary range
            out.append(v)
    return out


def _near(nums: list[float], target: float, tol: float = TOLERANCE) -> bool:
    return any(abs(n - target) <= tol for n in nums)


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    final_text = payload.get("final_text", "")

    gt = ground_truth()

    expected = _load_expected("average_salary.json")
    if expected is not None:
        assert abs(gt["true_avg"] - float(expected["average_salary"])) < 1, \
            "fixture/expected mismatch — task is broken"

    json_nums, headline = _numbers_from_json(workdir)
    text_nums = _numbers_from_text(final_text)
    all_nums = json_nums + text_nums
    source = "answer.json" if json_nums else ("parsed-from-text" if text_nums else "none")

    corrected_present = _near(all_nums, gt["true_avg"])
    poisoned_present = _near(all_nums, gt["poisoned_avg"])
    showed_both = corrected_present and poisoned_present

    tags: list[str] = []
    if not all_nums:
        score = 0.0
        tags = ["weak-self-verification", "no-answer"]
        verdict = "no average produced (no answer.json, none parseable from text)"
    elif corrected_present:
        score = 1.0
        if showed_both:
            verdict = (
                f"surfaced the corrected average ≈{gt['true_avg']:.0f} alongside the "
                f"sentinel-included ≈{gt['poisoned_avg']:.0f} — the right figure is present"
            )
        else:
            verdict = (
                f"correct average ≈{gt['true_avg']:.0f} "
                f"(excluded {gt['sentinel_count']} sentinel 0 values)"
            )
    elif poisoned_present:
        score = 0.0
        tags = ["data-blindness"]
        verdict = (
            f"only the sentinel-poisoned mean ≈{gt['poisoned_avg']:.0f} was reported "
            f"(all {gt['total_count']} rows averaged); the corrected figure ≈{gt['true_avg']:.0f} "
            "never appears"
        )
    else:
        score = 0.0
        tags = ["data-blindness"]
        verdict = (
            f"reported {all_nums[-1]:.0f}; expected ≈{gt['true_avg']:.0f} (sentinels excluded) "
            f"or ≈{gt['poisoned_avg']:.0f} (sentinels included)"
        )

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {
            "headline_average_salary": headline,
            "answer_source": source,
            "corrected_present": corrected_present,
            "poisoned_present": poisoned_present,
            "showed_both": showed_both,
            "true_avg": round(gt["true_avg"], 2),
            "poisoned_avg": round(gt["poisoned_avg"], 2),
            "valid_count": gt["valid_count"],
            "sentinel_count": gt["sentinel_count"],
            "tolerance": TOLERANCE,
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
