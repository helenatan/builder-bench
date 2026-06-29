#!/usr/bin/env python3
"""Grader for task c-02 (messy CSV -> clean validated pipeline + report).

Programmatic, no judge. Full Build: the messiness is *stated and unambiguous* (the cleaning
rules are in fixtures/cleanup_notes.md, the doc finance hands over), so there's a single correct
cleaned dataset and report. The grader
recomputes ground truth from fixtures/raw_sales.csv with the same rules, then checks the
agent's clean_sales.csv and report.json against it — and that the report is consistent with
the cleaned data (the headline Full-Build failure: a report that doesn't match its own data).

Harder than the original: amounts may be negative (leading minus OR accounting parentheses), a
fourth date format (`D-Mon-YYYY`) appears, exact-duplicate rows must be de-duplicated, and the
report now includes a per-month rollup that must reconcile too.

    python grader.py <grade_input.json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MONTHS = {m: i for i, m in enumerate(
    ["january","february","march","april","may","june","july","august",
     "september","october","november","december"], start=1)}
MONTHS_ABBR = {m[:3]: i for m, i in MONTHS.items()}


def parse_date(s: str) -> str | None:
    s = s.strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):                      # YYYY-MM-DD
        return s
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)            # MM/DD/YYYY
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s)     # Month D, YYYY
    if m and m.group(1).lower() in MONTHS:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", s)        # D-Mon-YYYY
    if m and m.group(2).lower() in MONTHS_ABBR:
        return f"{int(m.group(3)):04d}-{MONTHS_ABBR[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


def parse_amount(s: str):
    """Handle $, thousands commas, leading minus, and accounting parentheses for negatives."""
    s = s.strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()
    s = s.replace("$", "").replace(",", "").strip()
    if s.startswith("+"):
        s = s[1:]
    if s.startswith("-"):
        neg = True
        s = s[1:]
    if not s:
        return None
    try:
        val = round(float(s), 2)
    except ValueError:
        return None
    return round(-val, 2) if neg else val


def ground_truth() -> dict:
    seen = set()
    rows = []
    with (HERE / "fixtures" / "raw_sales.csv").open() as f:
        for r in csv.DictReader(f):
            date = parse_date((r.get("date") or ""))
            cat = (r.get("category") or "").strip().lower() or None
            amt = parse_amount((r.get("amount") or ""))
            if not date or not cat or amt is None:
                continue
            key = (date, cat, amt)
            if key in seen:                 # de-duplicate exact rows
                continue
            seen.add(key)
            rows.append((date, cat, amt))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    by_cat: dict[str, float] = {}
    by_month: dict[str, float] = {}
    for d, c, a in rows:
        by_cat[c] = round(by_cat.get(c, 0.0) + a, 2)
        ym = d[:7]
        by_month[ym] = round(by_month.get(ym, 0.0) + a, 2)
    return {
        "rows": rows,
        "row_count": len(rows),
        "total_amount": round(sum(a for *_, a in rows), 2),
        "by_category": by_cat,
        "by_month": by_month,
    }


def read_clean_csv(workdir: Path) -> list[tuple] | None:
    f = workdir / "clean_sales.csv"
    if not f.is_file():
        return None
    out = []
    with f.open() as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}
        if not {"date", "category", "amount"} <= set(cols):
            return None
        for row in reader:
            out.append((
                row[cols["date"]].strip(),
                row[cols["category"]].strip(),
                parse_amount(str(row[cols["amount"]])),
            ))
    return out


def amounts_close(a, b, tol=0.01) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def _dict_close(got: dict, exp: dict) -> bool:
    return set(got) == set(exp) and all(amounts_close(got[k], exp[k]) for k in exp)


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    gt = ground_truth()

    notes: list[str] = []
    tags: list[str] = []

    # ---- clean_sales.csv ----
    clean = read_clean_csv(workdir)
    clean_ok = False
    if clean is None:
        notes.append("clean_sales.csv missing or lacks date/category/amount columns")
    else:
        def norm(rows):
            return sorted((d, c, round(a, 2) if a is not None else None) for d, c, a in rows)
        exp = gt["rows"]
        content_ok = norm(clean) == norm(exp)
        order_ok = clean == sorted(clean, key=lambda x: (x[0], x[1], x[2]))
        clean_ok = content_ok and order_ok
        if not content_ok:
            if len(clean) != len(exp):
                notes.append(f"clean_sales has {len(clean)} rows, expected {len(exp)} (drop/dedup/parse rules?)")
            else:
                diffs = [g for g, e in zip(norm(clean), norm(exp)) if g != e][:3]
                notes.append(f"clean rows differ from expected, e.g. {diffs}")
        elif not order_ok:
            notes.append("clean rows are correct but not sorted by date then category")

    # ---- report.json ----
    report_ok = False
    report = None
    rp = workdir / "report.json"
    if not rp.is_file():
        notes.append("report.json missing")
    else:
        try:
            report = json.loads(rp.read_text())
            rc = int(report.get("row_count"))
            tot = float(report.get("total_amount"))
            bc = {str(k).strip().lower(): round(float(v), 2) for k, v in (report.get("by_category") or {}).items()}
            bm = {str(k).strip(): round(float(v), 2) for k, v in (report.get("by_month") or {}).items()}
            checks = {
                "row_count": rc == gt["row_count"],
                "total_amount": amounts_close(tot, gt["total_amount"]),
                "by_category": _dict_close(bc, gt["by_category"]),
                "by_month": _dict_close(bm, gt["by_month"]),
            }
            report_ok = all(checks.values())
            if not report_ok:
                bad = [k for k, ok in checks.items() if not ok]
                notes.append(f"report mismatch on {bad}: got row_count={rc} total={tot} "
                             f"by_category={bc} by_month={bm}; expected row_count={gt['row_count']} "
                             f"total={gt['total_amount']} by_category={gt['by_category']} by_month={gt['by_month']}")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            notes.append(f"report.json unreadable/incomplete: {exc}")

    # ---- consistency: report should match the agent's OWN cleaned data ----
    if clean is not None and report is not None and not report_ok:
        tags.append("weak-self-verification")

    score = round((0.5 if clean_ok else 0.0) + (0.5 if report_ok else 0.0), 2)
    if score < 1.0 and "weak-self-verification" not in tags:
        tags.append("weak-self-verification")

    if score >= 1.0:
        verdict = f"clean dataset ({gt['row_count']} rows) and report both correct and consistent"
    else:
        parts = []
        if not clean_ok:
            parts.append("clean_sales.csv wrong")
        if not report_ok:
            parts.append("report.json wrong")
        verdict = f"{', '.join(parts)}. " + "; ".join(notes[:4])

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": list(dict.fromkeys(tags)),
        "details": verdict,
        "evidence": {
            "expected_row_count": gt["row_count"],
            "expected_total": gt["total_amount"],
            "expected_by_category": gt["by_category"],
            "expected_by_month": gt["by_month"],
            "clean_ok": clean_ok, "report_ok": report_ok,
            "notes": notes[:8],
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
