#!/usr/bin/env python3
"""Grader for task b-03 (test accounts stay excluded — PM-style, conveyed via a screenshot).

Programmatic, no judge. The exclusion rule is stated exactly once — in the footnote of the
mockup screenshot the PM references at step 1 ("* Figures exclude internal & test accounts") —
and must still hold after later steps add metrics and a brand-new data file. The trap: a metric
computed without that exclusion silently re-includes the bot-like test accounts, whose activity
is enormous, so re-inclusion is unmistakable in the numbers (e.g. revenue 540 vs 150525).

Because a real PM never dictates an output schema, this grader does NOT require fixed JSON keys.
It collects (label, number) pairs from whatever the agent produced — any JSON/CSV/Markdown/text
in the workdir plus the final message — matches each of the five metrics by keyword, and checks
the value against the *excluded* ground truth (correct) vs the *included* one (the drift trap).

    python grader.py <grade_input.json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The five metrics that appear across the three steps (the screenshot shows the first three).
GRADED = ["active_users", "total_revenue", "avg_revenue_per_active_user",
          "avg_events_per_user", "successful_referrals"]
# Per-metric absolute tolerance (averages allow rounding wiggle; counts/revenue are tight).
TOL = {"active_users": 0.5, "total_revenue": 0.5, "successful_referrals": 0.5,
       "avg_revenue_per_active_user": 1.0, "avg_events_per_user": 0.5}
# Metrics whose excluded/included values are large and distinctive enough to detect drift from
# the raw number alone, even if the agent's label doesn't match our keywords.
BIG_MAGNITUDE = {"total_revenue", "avg_revenue_per_active_user"}


def ground_truth() -> dict:
    users = list(csv.DictReader((HERE / "fixtures" / "users.csv").open()))
    test_ids = {int(u["id"]) for u in users if u["is_test"].strip().lower() == "true"}
    events = list(csv.DictReader((HERE / "fixtures" / "events.csv").open()))
    referrals = list(csv.DictReader((HERE / "fixtures" / "referrals.csv").open()))

    def _conv(r):
        return str(r["converted"]).strip().lower() == "true"

    def metrics(exclude: bool) -> dict:
        keep = [e for e in events if (int(e["user_id"]) not in test_ids) or not exclude]
        active = {int(e["user_id"]) for e in keep}
        revenue = sum(float(e["value"]) for e in keep if e["event_type"] == "purchase")
        avg_ev = round(len(keep) / len(active), 2) if active else 0.0
        avg_rev = round(revenue / len(active), 2) if active else 0.0
        ref = sum(1 for r in referrals if _conv(r) and ((int(r["referrer_id"]) not in test_ids) or not exclude))
        return {
            "active_users": len(active),
            "total_revenue": revenue,
            "avg_revenue_per_active_user": avg_rev,
            "avg_events_per_user": avg_ev,
            "successful_referrals": ref,
        }

    return {"excluded": metrics(True), "included": metrics(False)}


# ---------------------------------------------------------------- collect (label, number) pairs
def _nums(s: str) -> list[float]:
    out = []
    for m in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", s or ""):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


# A PM-style summary mirrors the screenshot's "Metric | Value" table, so agents very often emit a
# list of records — [{"name": "Active users", "value": 7}, ...] — where the metric name lives in a
# sibling field, not the JSON key path. Flattening by key path alone collapses every row to
# ("metrics value", N) and loses the name. So we ALSO detect the record pattern and pair the
# name-ish field with the value-ish field.
_NAME_KEYS = ("name", "metric", "metric_name", "label", "key", "dimension", "kpi")
_VALUE_KEYS = ("value", "val", "amount", "count", "number", "result", "figure", "total", "metric_value")


def _coerce_num(x) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        ns = _nums(x)
        return ns[0] if len(ns) == 1 else None  # a value field should hold a single number
    return None


def _flatten_json(obj, prefix: str, pairs: list[tuple[str, float]]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        pairs.append((prefix.strip().lower().replace("_", " "), float(obj)))
    elif isinstance(obj, dict):
        # record pattern: {name-ish: "Active users", value-ish: 7} -> ("active users", 7)
        label = next((obj[k] for k in _NAME_KEYS if isinstance(obj.get(k), str)), None)
        if label:
            v = next((_coerce_num(obj[k]) for k in _VALUE_KEYS if _coerce_num(obj.get(k)) is not None), None)
            if v is not None:
                pairs.append((label.strip().lower(), v))
        for k, v in obj.items():
            _flatten_json(v, f"{prefix} {k}", pairs)
    elif isinstance(obj, list):
        for v in obj:
            _flatten_json(v, prefix, pairs)
    elif isinstance(obj, str):
        for n in _nums(obj):
            pairs.append((prefix.strip().lower().replace("_", " "), n))


def _pairs_from_text(text: str, pairs: list[tuple[str, float]]) -> None:
    for line in (text or "").splitlines():
        # "Active users: 7", "avg revenue per user = $77.14"
        for lab, val in re.findall(r"([A-Za-z][A-Za-z .\-/&]+?)\s*[:=]\s*\$?([\d,]+(?:\.\d+)?)", line):
            pairs.append((lab.strip().lower(), float(val.replace(",", ""))))
        # Markdown row: | Active users | $612 |
        for lab, val in re.findall(r"\|\s*([A-Za-z][A-Za-z .\-/&]+?)\s*\|\s*\$?([\d,]+(?:\.\d+)?)\s*\|", line):
            pairs.append((lab.strip().lower(), float(val.replace(",", ""))))


def collect_pairs(workdir: Path, final_text: str) -> tuple[list[tuple[str, float]], list[float]]:
    pairs: list[tuple[str, float]] = []
    for p in sorted(workdir.rglob("*")):
        if not p.is_file() or "fixtures" in p.relative_to(workdir).parts:
            continue  # skip the provided inputs
        if p.suffix.lower() == ".json":
            try:
                _flatten_json(json.loads(p.read_text()), "", pairs)
            except Exception:  # noqa: BLE001
                _pairs_from_text(p.read_text(errors="replace"), pairs)
        elif p.suffix.lower() in (".csv", ".md", ".txt", ".tsv"):
            try:
                _pairs_from_text(p.read_text(errors="replace"), pairs)
            except Exception:  # noqa: BLE001
                pass
    _pairs_from_text(final_text, pairs)
    return pairs, [v for _, v in pairs]


# --------------------------------------------------------------------------- metric matching
def _label_matches(metric: str, label: str) -> bool:
    l = label
    if metric == "active_users":
        return "active" in l and "revenue" not in l and "event" not in l and "per" not in l
    if metric == "total_revenue":
        return "revenue" in l and not any(w in l for w in ("per", "avg", "average"))
    if metric == "avg_revenue_per_active_user":
        return "revenue" in l and any(w in l for w in ("per", "avg", "average"))
    if metric == "avg_events_per_user":
        return "event" in l and any(w in l for w in ("per", "avg", "average"))
    if metric == "successful_referrals":
        return "referral" in l
    return False


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    final_text = payload.get("final_text", "")
    gt = ground_truth()
    exc, inc = gt["excluded"], gt["included"]

    pairs, all_nums = collect_pairs(workdir, final_text)
    if not pairs:
        print(json.dumps({"score": 0.0, "passed": False,
                          "failure_tags": ["weak-self-verification", "no-answer"],
                          "details": "no summary found — no numbers in any output file or the final message",
                          "evidence": {"expected_excluded": exc}}))
        return 0

    def close(a, b, tol):
        return abs(a - b) <= tol

    results: dict[str, str] = {}
    drifted: list[str] = []
    for metric in GRADED:
        tol = TOL[metric]
        cands = [v for lab, v in pairs if _label_matches(metric, lab)]
        # Big-magnitude metrics: also scan every number, so drift is caught even if the agent
        # labeled it unusually.
        pool = cands + (all_nums if metric in BIG_MAGNITUDE else [])
        if any(close(v, exc[metric], tol) for v in cands) and not any(
                close(v, inc[metric], tol) for v in cands):
            results[metric] = "ok"
        elif any(close(v, inc[metric], tol) for v in pool):
            results[metric] = "included-test"
            drifted.append(metric)
        elif cands:
            results[metric] = f"wrong({cands[0]}!={exc[metric]})"
        else:
            results[metric] = "missing"

    ok = sum(1 for r in results.values() if r == "ok")
    score = round(ok / len(GRADED), 4)
    tags: list[str] = []
    if drifted:
        tags.append("vision-drift")
    if all(results[m] == "missing" for m in GRADED):
        tags.append("data-blindness")  # likely never interpreted the screenshot at all

    if score >= 1.0:
        verdict = "all five metrics exclude test accounts — the screenshot's exclusion rule held across every step"
    elif drifted:
        verdict = f"exclusion rule drifted — these metrics re-included test accounts: {drifted}"
    else:
        bad = {k: r for k, r in results.items() if r != "ok"}
        verdict = f"summary incomplete/incorrect: {bad}"

    print(json.dumps({
        "score": score, "passed": score >= 1.0, "failure_tags": tags, "details": verdict,
        "evidence": {"per_metric": results, "expected_excluded": exc, "if_included": inc,
                     "pairs_found": pairs[:40]},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
