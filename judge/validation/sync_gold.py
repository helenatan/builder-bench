"""Re-sync the judge_* columns of gold_set.csv from labels.csv.

    python -m judge.validation.sync_gold [--check]

The gold set is the FROZEN human-reference regression set: its `human_label`,
`human_flagged`, and `human_note` are the ground truth and are never touched here.
Its `judge_*` columns are only a snapshot of what the judge said — and every time the
judge or a rubric changes, that snapshot goes stale while `labels.csv` (which the
re-judge writes to) moves ahead.

Nothing in the scoring path reads the gold judge columns — `validate.py` and
`report.py` both load gold_set.csv *only for its set of run_paths* (to exclude
already-reconciled rows from the blind kappa). So this is archive hygiene, not a
results fix: it keeps the frozen file honest for anyone who reads it directly.

Safety: refuses to run if any gold `human_*` value disagrees with labels.csv (that
would mean the human reference itself drifted, which is not something a mechanical
sync should paper over — investigate by hand instead).

    --check   exit non-zero if a sync is needed, change nothing (for CI).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS_CSV = HERE / "labels.csv"
GOLD_CSV = HERE / "gold_set.csv"

JUDGE_COLS = ("judge_label", "judge_flagged", "judge_rationale")
HUMAN_COLS = ("human_label", "human_flagged", "human_note")


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def main(argv: list[str]) -> int:
    check_only = "--check" in argv

    labels = {r["run_path"]: r for r in _read(LABELS_CSV)[1]}
    fields, gold = _read(GOLD_CSV)

    # Guard: the human reference must already agree. If it doesn't, stop.
    human_drift = [
        (g["run_path"], c)
        for g in gold
        if g["run_path"] in labels
        for c in HUMAN_COLS
        if (g.get(c) or "") != (labels[g["run_path"]].get(c) or "")
    ]
    if human_drift:
        print("REFUSING to sync — gold human columns disagree with labels.csv:", file=sys.stderr)
        for rp, c in human_drift:
            print(f"  {rp}: {c}", file=sys.stderr)
        print("The human reference should not drift. Investigate by hand.", file=sys.stderr)
        return 2

    changes: list[tuple[str, str, str, str]] = []
    for g in gold:
        src = labels.get(g["run_path"])
        if not src:
            print(f"WARNING: gold row not in labels.csv: {g['run_path']}", file=sys.stderr)
            continue
        for c in JUDGE_COLS:
            old, new = g.get(c) or "", src.get(c) or ""
            if old != new:
                changes.append((g["run_path"], c, old, new))
                if not check_only:
                    g[c] = new

    if not changes:
        print("gold_set.csv judge columns already in sync with labels.csv — nothing to do.")
        return 0

    rows_touched = len({rp for rp, *_ in changes})
    verb = "would update" if check_only else "updated"
    print(f"{verb} {len(changes)} cell(s) across {rows_touched} row(s):")
    for rp, c, old, new in changes:
        if c == "judge_rationale":
            print(f"  {rp}  {c}: (rationale text refreshed)")
        else:
            print(f"  {rp}  {c}: {old!r} -> {new!r}")

    if check_only:
        print("\n--check: gold_set.csv is stale. Run without --check to sync.")
        return 1

    with GOLD_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(gold)
    print(f"\nWrote {GOLD_CSV.relative_to(HERE.parents[1])}. Human reference columns untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
