#!/usr/bin/env python3
"""Grader for task d-01 (dedupe by company, not by location — survives later steps).

Programmatic, no judge. Reads the run bundle written by the harness:
    python grader.py <grade_input.json>
and prints a single JSON object to stdout:
    {"score": float, "passed": bool, "failure_tags": [...], "details": "..."}

Ground truth is recomputed directly from fixtures/postings.csv (not trusted from the agent),
then cross-checked against expected/unique_count.json. The primary check is coherence: the
"dedupe by company+title" rule stated once at step 1 must still hold at step 4 (Acme = 3).
The secondary check catches a *silent reversion* to one-row-per-location, where an earlier
deduped count gets re-inflated to its raw row count after step 3 adds "total postings".
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ground_truth() -> dict:
    """Recompute unique (by company+title) and raw counts from the fixture."""
    rows = list(csv.DictReader((HERE / "fixtures" / "postings.csv").open()))
    raw: dict[str, int] = {}
    uniq: dict[str, set[str]] = {}
    for r in rows:
        company, title = r["company"].strip(), r["title"].strip()
        raw[company] = raw.get(company, 0) + 1
        uniq.setdefault(company, set()).add(title)
    return {
        "raw_by_company": raw,
        "unique_by_company": {c: len(t) for c, t in uniq.items()},
        "total_raw": len(rows),
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
    """Fallback: pull the Acme count out of the step-4 final text."""
    if not text:
        return None
    patterns = [
        r"[Aa]cme[^0-9]{0,60}?(\d+)",
        r"(\d+)\s*unique",
        r"unique[^0-9]{0,20}?(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    nums = re.findall(r"\b(\d+)\b", text)
    return int(nums[-1]) if nums else None


def read_reported_table(workdir: Path) -> dict[str, int]:
    """Read the agent's final unique_openings.csv -> {company: reported_unique}."""
    f = workdir / "unique_openings.csv"
    if not f.is_file():
        # Forgiving fallback: any *.csv that has a unique-ish column.
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
    acme_truth = gt["unique_by_company"].get("Acme Corp")  # == 3

    # Cross-check fixture-derived truth against the committed expected file.
    expected = json.loads((HERE / "expected" / "unique_count.json").read_text())
    assert acme_truth == expected["Acme Corp"], "fixture/expected mismatch — task is broken"

    # --- agent's answer (prefer the machine-readable answer.json) -----------------
    answer = read_answer_json(workdir)
    answer_source = "answer.json"
    if answer is None:
        answer = parse_answer_from_text(final_text)
        answer_source = "parsed-from-text"

    # --- silent-reversion check on the final unique table -------------------------
    reported = read_reported_table(workdir)
    inflated = [
        c for c, v in reported.items()
        if v == gt["raw_by_company"].get(c) and gt["raw_by_company"].get(c) != gt["unique_by_company"].get(c)
    ]
    drifted = [
        c for c, v in reported.items()
        if c in gt["unique_by_company"] and v != gt["unique_by_company"][c]
    ]

    # --- scoring ------------------------------------------------------------------
    tags: list[str] = []
    if answer is None:
        score = 0.0
        tags = ["weak-self-verification", "no-answer"]
        verdict = "no Acme count produced (no answer.json, none parseable from text)"
    elif answer == acme_truth:  # 3
        if inflated:
            score = 0.5
            tags = ["vision-drift", "silent-assumptions"]
            verdict = f"Acme=3 correct, but unique counts reverted to raw for: {inflated}"
        else:
            score = 1.0
            verdict = "Acme=3 and no unique count reverted to per-location — coherence held"
    elif answer == gt["raw_by_company"].get("Acme Corp"):  # 7 (raw, location-inflated)
        score = 0.0
        tags = ["vision-drift", "data-blindness"]
        verdict = f"Acme={answer} is the location-inflated raw count; the dedupe rule was lost"
    else:
        score = 0.0
        tags = ["vision-drift"]
        verdict = f"Acme={answer}, expected {acme_truth}; the dedupe rule was lost"

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
            "inflated_companies": inflated,
            "drifted_companies": drifted,
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
