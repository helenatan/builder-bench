#!/usr/bin/env python3
"""Grader for task b-05 (customer IDs keep their leading zeros).

Step 1 states the convention: customer IDs are fixed-width 5-digit strings ("00042"),
identifiers not numbers. Steps 2-3 add a join and a CSV export where default dtype inference
(pandas, spreadsheets) silently turns them into ints. The tell is the final billing export:
IDs like "42" mean the convention drifted, even when every number is right.

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
TASK_ID = "b-05"
TOLERANCE = 0.01


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
    customers = list(csv.DictReader((HERE / "fixtures" / "customers.csv").open()))
    orders = list(csv.DictReader((HERE / "fixtures" / "orders.csv").open()))
    region = {c["customer_id"]: c["region"].strip() for c in customers}

    by_region: dict[str, int] = {}
    for c in customers:
        by_region[c["region"].strip()] = by_region.get(c["region"].strip(), 0) + 1

    revenue: dict[str, float] = {}
    spend: dict[str, float] = {}
    for o in orders:
        cid, amt = o["customer_id"], float(o["amount"])
        revenue[region[cid]] = round(revenue.get(region[cid], 0.0) + amt, 2)
        spend[cid] = round(spend.get(cid, 0.0) + amt, 2)

    top3 = sorted(spend.items(), key=lambda kv: -kv[1])[:3]
    return {"by_region": by_region, "revenue": revenue, "top3": top3}


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    gt = ground_truth()

    expected = _load_expected("answer.json")
    if expected is not None:
        assert expected["customers_by_region"] == gt["by_region"], "fixture/expected mismatch — task is broken"
        assert all(abs(expected["revenue_by_region"][k] - v) <= TOLERANCE
                   for k, v in gt["revenue"].items()), "fixture/expected mismatch — task is broken"
        assert [t[0] for t in gt["top3"]] == expected["top_customer_ids"], "fixture/expected mismatch — task is broken"

    problems: list[str] = []
    drift = False

    # answer.json: both dicts correct.
    f = workdir / "answer.json"
    got = {}
    if not f.is_file():
        problems.append("no answer.json produced")
    else:
        try:
            got = json.loads(f.read_text())
        except (json.JSONDecodeError, ValueError):
            problems.append("answer.json is not valid JSON")
    got_counts = got.get("customers_by_region") or {}
    got_rev = got.get("revenue_by_region") or {}
    if got and {k: int(v) for k, v in got_counts.items() if v is not None} != gt["by_region"]:
        problems.append(f"customers_by_region={got_counts} (expected {gt['by_region']})")
    if got:
        for k, v in gt["revenue"].items():
            try:
                ok = abs(float(got_rev.get(k)) - v) <= TOLERANCE
            except (TypeError, ValueError):
                ok = False
            if not ok:
                problems.append(f"revenue_by_region[{k}]={got_rev.get(k)} (expected {v})")
                break

    # top_customers.csv: right customers, right totals, IDs still 5-digit zero-padded strings.
    t = workdir / "top_customers.csv"
    if not t.is_file():
        problems.append("no top_customers.csv produced")
    else:
        rows = list(csv.DictReader(t.open()))
        cols = {c.lower().strip(): c for c in (rows[0].keys() if rows else [])}
        id_col, amt_col = cols.get("customer_id"), cols.get("total_spent")
        if not id_col or not amt_col:
            problems.append(f"top_customers.csv columns {list(cols)} != [customer_id, total_spent]")
        else:
            got_ids = [r[id_col].strip() for r in rows]
            want_ids = [cid for cid, _ in gt["top3"]]
            stripped = [cid.lstrip("0") or "0" for cid in want_ids]
            if got_ids == stripped or (
                    got_ids != want_ids and [g.lstrip("0") or "0" for g in got_ids] == stripped):
                drift = True
                problems.append(
                    f"IDs lost their leading zeros in the export: {got_ids} (expected {want_ids}) "
                    "— the step-1 convention (fixed-width string IDs) did not survive to the deliverable"
                )
            elif got_ids != want_ids:
                problems.append(f"top customers {got_ids} (expected {want_ids}, highest first)")
            else:
                for r, (cid, amt) in zip(rows, gt["top3"]):
                    try:
                        ok = abs(float(r[amt_col]) - amt) <= TOLERANCE
                    except (TypeError, ValueError):
                        ok = False
                    if not ok:
                        problems.append(f"total_spent for {cid}: {r[amt_col]} (expected {amt})")
                        break
                bad = [i for i in got_ids if not re.fullmatch(r"\d{5}", i)]
                if bad:
                    drift = True
                    problems.append(f"exported IDs not fixed-width 5-digit strings: {bad}")

    if not problems:
        result = {
            "score": 1.0, "passed": True, "failure_tags": [],
            "details": (
                f"Convention held: counts {gt['by_region']}, revenue {gt['revenue']}, "
                f"export {[cid for cid, _ in gt['top3']]} with leading zeros intact"
            ),
        }
    else:
        tags = ["vision-drift"] if drift else ["weak-self-verification"]
        if "no answer.json produced" in problems:
            tags.append("no-answer")
        result = {"score": 0.0, "passed": False, "failure_tags": tags,
                  "details": "; ".join(problems)}

    result["evidence"] = {
        "expected": {"customers_by_region": gt["by_region"], "revenue_by_region": gt["revenue"],
                     "top3": gt["top3"]},
        "problems": problems,
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
