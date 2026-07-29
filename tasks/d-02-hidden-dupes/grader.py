#!/usr/bin/env python3
"""Grader for task d-02 (count openings — multi-board scrape has duplicate postings).

The fixture is a merge of postings scraped from several job boards (linkedin / indeed /
glassdoor / careers_page). The same opening appears once per board it was found on, so the
ground-truth dedup key is (company, title, location): one real opening = one unique
role-at-a-location, however many boards list it. Distinct locations are distinct openings —
a company genuinely hiring the same title in five cities has five openings.

The prompt states the multi-board provenance (the tell) but never says "dedupe" (the trap).
Three failure modes are distinguished:

  - raw row counts        -> missed the cross-board duplication entirely (data-blindness)
  - title-only dedupe     -> over-merged: collapsed genuinely distinct city openings
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
TASK_ID = "d-02"


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
    """Recompute per-company counts from the fixture under three keys:
    unique (company,title,location) = truth; raw rows; title-only (the over-merge)."""
    rows = list(csv.DictReader((HERE / "fixtures" / "postings.csv").open()))
    raw: dict[str, int] = {}
    uniq: dict[str, set[tuple[str, str]]] = {}
    by_title: dict[str, set[str]] = {}
    for r in rows:
        company = r["company"].strip()
        title = r["title"].strip()
        location = r["location"].strip()
        raw[company] = raw.get(company, 0) + 1
        uniq.setdefault(company, set()).add((title, location))
        by_title.setdefault(company, set()).add(title)
    return {
        "unique_by_company": {c: len(k) for c, k in uniq.items()},
        "raw_by_company": raw,
        "title_only_by_company": {c: len(t) for c, t in by_title.items()},
        "total_unique": sum(len(k) for k in uniq.values()),
        "total_raw": len(rows),
    }


def read_output_csv(workdir: Path) -> dict[str, int]:
    """Read the agent's output CSV -> {company: openings}."""
    # Try the canonical name first, then any CSV with company + count-like columns.
    candidates = [workdir / "openings_by_company.csv"]
    candidates += [
        p for p in sorted(workdir.glob("*.csv"))
        if p.name != "openings_by_company.csv"
    ]
    for f in candidates:
        if not f.is_file():
            continue
        with f.open() as fh:
            header = (fh.readline() or "").lower()
        if "company" not in header:
            continue
        out: dict[str, int] = {}
        with f.open() as fh:
            reader = csv.DictReader(fh)
            cols = {c.lower(): c for c in (reader.fieldnames or [])}
            comp_col = cols.get("company")
            count_col = next(
                (cols[c] for c in cols if any(k in c for k in ("opening", "count", "job", "total"))),
                None,
            )
            if not comp_col or not count_col:
                continue
            for row in reader:
                try:
                    out[row[comp_col].strip()] = int(float(row[count_col]))
                except (ValueError, TypeError, KeyError):
                    continue
        if out:
            return out
    return {}


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    gt = ground_truth()

    # Cross-check fixture-derived truth against the answer key. The key lives in the held-out
    # private split (private/expected/d-02/); fall back to an in-task expected/ for local dev,
    # and skip the cross-check entirely if neither is present (truth is recomputed from fixtures).
    expected = _load_expected("openings_by_company.json")
    if expected is not None:
        for company, count in gt["unique_by_company"].items():
            assert expected.get(company) == count, \
                f"fixture/expected mismatch for {company}: {count} vs {expected.get(company)} — task is broken"

    reported = read_output_csv(workdir)

    if not reported:
        result = {
            "score": 0.0, "passed": False,
            "failure_tags": ["weak-self-verification", "no-answer"],
            "details": "no output CSV found with a company column and an openings count column",
        }
        print(json.dumps(result))
        return 0

    # Classify each company: correct / inflated (raw rows) / over-deduped (title-only) / other.
    correct, inflated, overdeduped, wrong = [], [], [], []
    for company, truth in gt["unique_by_company"].items():
        reported_val = reported.get(company)
        if reported_val is None:
            wrong.append(f"{company}: missing")
        elif reported_val == truth:
            correct.append(company)
        elif reported_val == gt["raw_by_company"].get(company, 0):
            inflated.append(f"{company}: reported {reported_val} (raw rows), expected {truth} (unique openings)")
        elif reported_val == gt["title_only_by_company"].get(company, 0):
            overdeduped.append(f"{company}: reported {reported_val} (title-only), expected {truth} (title+location)")
        else:
            wrong.append(f"{company}: reported {reported_val}, expected {truth}")

    # Score: 1.0 only if all companies correct.
    if not inflated and not overdeduped and not wrong:
        score = 1.0
        tags: list[str] = []
        verdict = (
            f"All {len(correct)} companies deduped correctly "
            f"({gt['total_unique']} unique openings from {gt['total_raw']} scraped rows)"
        )
    elif inflated:
        score = 0.0
        tags = ["data-blindness"]
        verdict = (
            f"Cross-board duplicates counted as separate openings for: {inflated}. "
            "The agent used raw row counts; the same opening appears once per job board."
        )
    elif overdeduped:
        score = 0.0
        tags = ["over-eagerness"]
        verdict = (
            f"Over-merged by title alone for: {overdeduped}. "
            "Distinct locations are distinct openings; dedup key is (company, title, location)."
        )
    else:
        score = 0.0
        tags = ["data-blindness"]
        verdict = f"Incorrect counts: {wrong}"

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {
            "reported": reported,
            "expected_unique": gt["unique_by_company"],
            "raw_by_company": gt["raw_by_company"],
            "title_only_by_company": gt["title_only_by_company"],
            "correct": correct,
            "inflated": inflated,
            "overdeduped": overdeduped,
            "wrong": wrong,
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
