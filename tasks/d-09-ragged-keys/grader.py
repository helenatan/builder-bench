#!/usr/bin/env python3
"""Grader for task d-09 (top country by revenue — the country labels are ragged).

The billing export spells the same country several ways ("United States" / "USA" / "US" /
"U.S."). Grouping by the raw label fragments the US into four chunks, so the naive top country
is Germany (2500/mo); consolidated, the US wins at 6000/mo. The prompt states only the question
(the tell is in the data); it never says "normalize" (the trap).

Two failure modes are distinguished:

  - fragmented group-by   -> reported Germany (or a single US fragment) — missed the ragged keys
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
TASK_ID = "d-09"
TOLERANCE = 0.01

# Raw label -> canonical country. The fixture's full alias inventory.
CANON = {
    "united states": "US", "usa": "US", "us": "US", "u.s.": "US", "u.s": "US",
    "united states of america": "US", "america": "US",
    "united kingdom": "UK", "uk": "UK", "u.k.": "UK", "u.k": "UK", "great britain": "UK",
    "germany": "Germany", "de": "Germany", "deutschland": "Germany",
    "canada": "Canada", "france": "France",
}


def _norm(label: str) -> str:
    return CANON.get(label.strip().lower().rstrip("."), label.strip())


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
    rows = list(csv.DictReader((HERE / "fixtures" / "subscriptions.csv").open()))
    canon: dict[str, float] = {}
    raw: dict[str, float] = {}
    for r in rows:
        price = float(r["monthly_price"])
        canon[_norm(r["country"])] = canon.get(_norm(r["country"]), 0.0) + price
        raw[r["country"].strip()] = raw.get(r["country"].strip(), 0.0) + price
    top = max(canon, key=canon.get)
    naive_top = max(raw, key=raw.get)
    return {
        "canon": {k: round(v, 2) for k, v in canon.items()},
        "raw": {k: round(v, 2) for k, v in raw.items()},
        "top": top, "top_revenue": round(canon[top], 2),
        "naive_top": naive_top, "naive_revenue": round(raw[naive_top], 2),
    }


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    gt = ground_truth()

    expected = _load_expected("answer.json")
    if expected is not None:
        assert _norm(expected["top_country"]) == gt["top"], "fixture/expected mismatch — task is broken"
        assert abs(expected["monthly_revenue"] - gt["top_revenue"]) <= TOLERANCE, \
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

    got_country = str(got.get("top_country", "")).strip()
    try:
        got_rev = round(float(got.get("monthly_revenue")), 2)
    except (TypeError, ValueError):
        got_rev = None

    country_ok = _norm(got_country) == gt["top"]
    rev_ok = got_rev is not None and abs(got_rev - gt["top_revenue"]) <= TOLERANCE

    if country_ok and rev_ok:
        result = {
            "score": 1.0, "passed": True, "failure_tags": [],
            "details": (
                f"Consolidated correctly: {got_country} at {gt['top_revenue']:.2f}/mo "
                f"(the raw labels split it across {sum(1 for k in gt['raw'] if _norm(k) == gt['top'])} spellings)"
            ),
        }
    elif _norm(got_country) == _norm(gt["naive_top"]) and got_rev is not None \
            and abs(got_rev - gt["naive_revenue"]) <= TOLERANCE:
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["data-blindness"],
            "details": (
                f"Fragmented group-by: reported {got_country} at {got_rev}, the top of the *raw* "
                f"label counts. Consolidated, {gt['top']} leads at {gt['top_revenue']:.2f}/mo — "
                "the same country is spelled several ways in the export."
            ),
        }
    elif country_ok and got_rev is not None and any(
            abs(got_rev - v) <= TOLERANCE for k, v in gt["raw"].items() if _norm(k) == gt["top"]):
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["data-blindness"],
            "details": (
                f"Right country, fragment revenue: reported {got_rev} (one spelling's subtotal), "
                f"expected {gt['top_revenue']:.2f} across all spellings."
            ),
        }
    else:
        result = {
            "score": 0.0, "passed": False, "failure_tags": ["data-blindness"],
            "details": f"Incorrect: reported {got_country} at {got_rev}, "
                       f"expected {gt['top']} at {gt['top_revenue']:.2f}",
        }

    result["evidence"] = {
        "reported": {"top_country": got_country, "monthly_revenue": got_rev},
        "expected": {"top_country": gt["top"], "monthly_revenue": gt["top_revenue"]},
        "canonical_totals": gt["canon"],
        "raw_label_totals": gt["raw"],
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
