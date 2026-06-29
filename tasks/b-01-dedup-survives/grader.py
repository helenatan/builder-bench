#!/usr/bin/env python3
"""Grader for task b-01 (dedupe by company, not by location — survives later steps).

Programmatic, no judge. Reads the run bundle written by the harness:
    python grader.py <grade_input.json>
and prints a single JSON object to stdout:
    {"score": float, "passed": bool, "failure_tags": [...], "details": "..."}

The stated rule (step 1) is: one opening = one (company, normalized title), location ignored,
where titles differing only in case/whitespace are the same role. That rule must still hold at
step 6, AFTER `new_postings.csv` is merged in (step 4). Ground truth is recomputed from BOTH
fixture files (never trusted from the agent) and cross-checked against the private answer key.

The traps the grader catches:
  - lost normalization — counting `Senior PM` / `senior pm` / `Senior  PM` as different roles;
  - re-inflation on merge — a role re-counted because it reappears in the new batch;
  - silent reversion — some company's unique count quietly becomes its raw row count.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_ID = "b-01"


def _load_expected(name: str):
    for base in (HERE.parents[1] / "private" / "expected" / TASK_ID, HERE / "expected"):
        p = base / name
        if p.is_file():
            return json.loads(p.read_text())
    return None


def norm_title(t: str) -> str:
    """Same role iff equal after collapsing whitespace and lowercasing."""
    return " ".join(t.split()).lower()


def ground_truth() -> dict:
    """Recompute unique (by company + normalized title) and raw counts across BOTH files."""
    raw: dict[str, int] = {}
    uniq: dict[str, set[str]] = {}
    total_raw = 0
    for fname in ("postings.csv", "new_postings.csv"):
        fpath = HERE / "fixtures" / fname
        if not fpath.is_file():
            continue
        for r in csv.DictReader(fpath.open()):
            company = r["company"].strip()
            title = norm_title(r["title"])
            raw[company] = raw.get(company, 0) + 1
            uniq.setdefault(company, set()).add(title)
            total_raw += 1
    return {
        "raw_by_company": raw,
        "unique_by_company": {c: len(t) for c, t in uniq.items()},
        "total_raw": total_raw,
    }


def read_answer_json(workdir: Path) -> int | None:
    f = workdir / "answer.json"
    if not f.is_file():
        return None
    try:
        data = json.loads(f.read_text())
        return int(data["unique_openings"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


def parse_answer_from_text(text: str) -> int | None:
    if not text:
        return None
    for pat in (r"[Aa]cme[^0-9]{0,60}?(\d+)", r"(\d+)\s*unique", r"unique[^0-9]{0,20}?(\d+)"):
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    nums = re.findall(r"\b(\d+)\b", text)
    return int(nums[-1]) if nums else None


def read_reported_table(workdir: Path) -> dict[str, int]:
    f = workdir / "unique_openings.csv"
    if not f.is_file():
        for cand in sorted(workdir.glob("*.csv")):
            with cand.open() as fh:
                header = (fh.readline() or "").lower()
            if "company" in header and ("unique" in header or "opening" in header):
                f = cand
                break
    out: dict[str, int] = {}
    if not f.is_file():
        return out
    with f.open() as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower(): c for c in (reader.fieldnames or [])}
        comp_col = cols.get("company")
        uniq_col = next((cols[c] for c in cols if "unique" in c or "opening" in c), None)
        if not comp_col or not uniq_col:
            return out
        for row in reader:
            try:
                out[row[comp_col].strip()] = int(float(row[uniq_col]))
            except (ValueError, TypeError, KeyError):
                continue
    return out


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    final_text = payload.get("final_text", "")

    gt = ground_truth()
    acme_truth = gt["unique_by_company"].get("Acme Corp")  # == 4 across both files

    expected = _load_expected("unique_count.json")
    if expected is not None:
        assert acme_truth == expected["Acme Corp"], "fixture/expected mismatch — task is broken"

    answer = read_answer_json(workdir)
    answer_source = "answer.json"
    if answer is None:
        answer = parse_answer_from_text(final_text)
        answer_source = "parsed-from-text"

    reported = read_reported_table(workdir)
    inflated = [
        c for c, v in reported.items()
        if v == gt["raw_by_company"].get(c) and gt["raw_by_company"].get(c) != gt["unique_by_company"].get(c)
    ]
    drifted = [
        c for c, v in reported.items()
        if c in gt["unique_by_company"] and v != gt["unique_by_company"][c]
    ]

    tags: list[str] = []
    if answer is None:
        score = 0.0
        tags = ["weak-self-verification", "no-answer"]
        verdict = "no Acme count produced (no answer.json, none parseable from text)"
    elif answer == acme_truth:  # 4
        if inflated or drifted:
            score = 0.5
            tags = ["vision-drift", "silent-assumptions"]
            verdict = f"Acme={acme_truth} correct, but other unique counts are off — inflated={inflated} drifted={drifted}"
        else:
            score = 1.0
            verdict = f"Acme={acme_truth} and the whole unique table held across the merge — coherence held"
    elif answer == gt["raw_by_company"].get("Acme Corp"):  # 12 (raw across both)
        score = 0.0
        tags = ["vision-drift", "data-blindness"]
        verdict = f"Acme={answer} is the location-inflated raw count; the dedupe rule was lost"
    else:
        score = 0.0
        tags = ["vision-drift"]
        verdict = (
            f"Acme={answer}, expected {acme_truth}; likely lost title normalization "
            "(case/whitespace variants counted separately) or failed to merge the second file"
        )

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {
            "answer_acme": answer,
            "answer_source": answer_source,
            "expected_acme": acme_truth,
            "reported_unique_table": reported,
            "ground_truth_unique": gt["unique_by_company"],
            "ground_truth_raw": gt["raw_by_company"],
            "total_raw_both_files": gt["total_raw"],
            "inflated_companies": inflated,
            "drifted_companies": drifted,
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
