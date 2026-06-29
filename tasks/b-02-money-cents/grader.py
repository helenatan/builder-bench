#!/usr/bin/env python3
"""Grader for task b-02 (money stays in integer cents — survives later steps).

Programmatic, no judge. The "integer cents" convention stated at step 1 must still hold at the
end, across SIX steps that repeatedly tempt floating-dollar math:
  - the 3-way installment split (step 2),
  - the dollar-formatted display (step 3),
  - a 7% discount with half-up rounding (step 4)  <-- the headline new float trap,
  - splitting the *discounted* amount too (step 5),
  - two grand totals (step 6).

Because every split is defined to sum exactly, the raw grand total equals the sum of amounts
and the discounted grand total equals the sum of the half-up-rounded discounts — both
reproducible ONLY if the whole pipeline stayed in integer cents and used the specified rounding.

    python grader.py <grade_input.json>

Prints: {"score": float, "passed": bool, "failure_tags": [...], "details": "..."}
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DISCOUNT_PCT = 7  # 7% loyalty discount


def discounted_half_up(amount_cents: int) -> int:
    """amount * 0.93, rounded to the nearest whole cent, half up — in pure integer math."""
    keep = 100 - DISCOUNT_PCT          # 93
    return (amount_cents * keep + 50) // 100


def ground_truth() -> dict:
    rows = list(csv.DictReader((HERE / "fixtures" / "transactions.csv").open()))
    cents = {}
    for r in rows:
        whole, _, frac = r["amount"].strip().partition(".")
        frac = (frac + "00")[:2]
        cents[int(r["id"])] = int(whole) * 100 + int(frac)
    disc = {i: discounted_half_up(c) for i, c in cents.items()}
    return {
        "by_id": cents,
        "disc_by_id": disc,
        "total": sum(cents.values()),
        "disc_total": sum(disc.values()),
    }


def expected_split(amount_cents: int) -> list[int]:
    base, rem = divmod(amount_cents, 3)
    return [base + (1 if i < rem else 0) for i in range(3)]


def read_answer(workdir: Path) -> dict:
    f = workdir / "answer.json"
    out = {"total_cents": None, "discounted_total_cents": None}
    if not f.is_file():
        return out
    try:
        data = json.loads(f.read_text())
        for k in out:
            try:
                out[k] = int(data[k])
            except (KeyError, ValueError, TypeError):
                out[k] = None
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return out


def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])

    gt = ground_truth()
    true_total = gt["total"]            # 56165 for the shipped fixture
    true_disc_total = gt["disc_total"]  # 52235 for the shipped fixture

    ans = read_answer(workdir)

    # --- inspect ledger.json: integer-cents convention + correct splits + correct discount ----
    ledger_path = workdir / "ledger.json"
    convention_ok = True
    split_ok = True
    discount_ok = True
    float_fields: list[str] = []
    notes: list[str] = []

    if ledger_path.is_file():
        try:
            ledger = json.loads(ledger_path.read_text())
            by_id = {int(e["id"]): e for e in ledger if isinstance(e, dict) and "id" in e}
            for tid, amt in gt["by_id"].items():
                e = by_id.get(tid)
                if e is None:
                    notes.append(f"id {tid} missing from ledger")
                    split_ok = discount_ok = False
                    continue

                # amount_cents — integer + correct value
                ac = e.get("amount_cents")
                if not _is_int(ac):
                    convention_ok = False
                    float_fields.append(f"id{tid}.amount_cents={ac!r}")
                elif ac != amt:
                    split_ok = False
                    notes.append(f"id {tid}: amount_cents={ac}, expected {amt}")

                # installments of the raw amount
                inst = e.get("installments")
                if isinstance(inst, list) and len(inst) == 3:
                    if any(not _is_int(x) for x in inst):
                        convention_ok = False
                        float_fields.append(f"id{tid}.installments={inst!r}")
                    elif sum(inst) != amt:
                        split_ok = False
                        notes.append(f"id {tid}: installments {inst} sum to {sum(inst)}, not {amt}")
                else:
                    split_ok = False
                    notes.append(f"id {tid}: installments missing or not a 3-list ({inst!r})")

                # discounted_cents — integer + correct half-up value
                dc = e.get("discounted_cents")
                want_dc = gt["disc_by_id"][tid]
                if not _is_int(dc):
                    convention_ok = False
                    float_fields.append(f"id{tid}.discounted_cents={dc!r}")
                elif dc != want_dc:
                    discount_ok = False
                    notes.append(f"id {tid}: discounted_cents={dc}, expected {want_dc} (7% off, half up)")

                # installments of the discounted amount
                dinst = e.get("discounted_installments")
                if isinstance(dinst, list) and len(dinst) == 3:
                    if any(not _is_int(x) for x in dinst):
                        convention_ok = False
                        float_fields.append(f"id{tid}.discounted_installments={dinst!r}")
                    elif _is_int(dc) and sum(dinst) != dc:
                        split_ok = False
                        notes.append(f"id {tid}: discounted_installments {dinst} sum to {sum(dinst)}, not {dc}")
                else:
                    split_ok = False
                    notes.append(f"id {tid}: discounted_installments missing or not a 3-list ({dinst!r})")
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            notes.append(f"ledger.json unreadable: {exc}")
            convention_ok = False
    else:
        notes.append("ledger.json not found")
        convention_ok = False

    # --- scoring: totals gate first, then convention/splits/discount ------------------------
    tags: list[str] = []
    totals_ok = ans["total_cents"] == true_total and ans["discounted_total_cents"] == true_disc_total

    if ans["total_cents"] is None or ans["discounted_total_cents"] is None:
        score, tags = 0.0, ["weak-self-verification", "no-answer"]
        verdict = "answer.json missing total_cents and/or discounted_total_cents"
    elif ans["total_cents"] != true_total:
        score, tags = 0.0, ["vision-drift"]
        off = true_total - ans["total_cents"]
        verdict = (f"raw grand total {ans['total_cents']} != exact {true_total} (off by {off} cents) — "
                   "pennies lost; integer-cents convention drifted to float dollars")
    elif ans["discounted_total_cents"] != true_disc_total:
        score, tags = 0.0, ["vision-drift"]
        off = true_disc_total - ans["discounted_total_cents"]
        verdict = (f"raw total correct, but discounted grand total {ans['discounted_total_cents']} != "
                   f"exact {true_disc_total} (off by {off}) — the discount used float math or the wrong rounding")
    elif not convention_ok:
        score, tags = 0.5, ["vision-drift", "silent-assumptions"]
        verdict = f"both totals correct, but money is no longer stored as integer cents: {float_fields[:5]}"
    elif not discount_ok:
        score, tags = 0.5, ["vision-drift"]
        verdict = f"totals correct, but per-transaction discounted_cents are off: {notes[:5]}"
    elif not split_ok:
        score, tags = 0.5, ["vision-drift"]
        verdict = f"totals correct, but ledger splits are inconsistent: {notes[:5]}"
    else:
        score = 1.0
        verdict = (f"raw total {true_total} and discounted total {true_disc_total} both exact; every "
                   "amount, discount, and installment stored as integer cents — convention held across 6 steps")

    result = {
        "score": score,
        "passed": score >= 1.0,
        "failure_tags": tags,
        "details": verdict,
        "evidence": {
            "answer": ans,
            "expected_total_cents": true_total,
            "expected_discounted_total_cents": true_disc_total,
            "convention_integer_cents": convention_ok,
            "discount_half_up_correct": discount_ok,
            "splits_penny_exact": split_ok,
            "totals_ok": totals_ok,
            "float_fields": float_fields[:10],
            "ledger_notes": notes[:10],
        },
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
