"""Merge labels exported from the hosted labeling site back into labels.csv (PRD §6).

    python -m judge.validation.import_labels <exported.csv>            # merge as primary labels
    python -m judge.validation.import_labels <exported.csv> --second   # don't merge; report
                                                                       # human-vs-human agreement

Primary merge fills human_label / human_flagged / human_note for matching run_paths in
labels.csv (rows are appended for run_paths not present yet, e.g. transcripts the judge hasn't
scored). Existing human labels are kept on conflict unless --overwrite. Every import is also
archived untouched under judge/validation/imports/.

--second treats the file as an independent second labeler and reports exact agreement and
Cohen's kappa against the human labels already in labels.csv — the human-human ceiling the
judge's kappa is read against.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

from judge.validation.validate import LABELS_CSV, LABEL_FIELDS, cohens_kappa

IMPORTS_DIR = Path(__file__).resolve().parent / "imports"


def _read(path: Path) -> list[dict]:
    with path.open() as f:
        rows = list(csv.DictReader(f))
    missing = {"run_path", "human_label"} - set(rows[0].keys() if rows else [])
    if missing:
        raise SystemExit(f"{path} is missing columns: {sorted(missing)}")
    return rows


def _merge(incoming: list[dict], overwrite: bool) -> None:
    existing: dict[str, dict] = {}
    order: list[str] = []
    if LABELS_CSV.is_file():
        for row in csv.DictReader(LABELS_CSV.open()):
            r = {k: row.get(k, "") for k in LABEL_FIELDS}
            existing[r["run_path"]] = r
            order.append(r["run_path"])

    added = merged = kept = 0
    for inc in incoming:
        rp = inc["run_path"]
        row = existing.get(rp)
        if row is None:
            row = {k: "" for k in LABEL_FIELDS}
            row.update(run_path=rp, task_id=inc.get("task_id", ""),
                       model=inc.get("model", ""), attempt=inc.get("attempt", ""))
            existing[rp] = row
            order.append(rp)
            added += 1
        if row["human_label"].strip() and not overwrite:
            if row["human_label"].strip().lower() != inc["human_label"].strip().lower():
                print(f"  conflict (kept existing): {rp} "
                      f"existing={row['human_label']} incoming={inc['human_label']}")
            kept += 1
            continue
        row["human_label"] = inc.get("human_label", "").strip().lower()
        row["human_flagged"] = inc.get("human_flagged", "").strip().lower()
        row["human_note"] = inc.get("human_note", "").strip()
        merged += 1

    with LABELS_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
        w.writeheader()
        w.writerows(existing[rp] for rp in order)
    print(f"Merged {merged} label(s) into {LABELS_CSV.name} "
          f"({added} new row(s), {kept} already-labeled row(s) kept).")
    print("Next: python -m judge.validation.validate kappa")


def _second(incoming: list[dict]) -> None:
    primary = {r["run_path"]: r for r in csv.DictReader(LABELS_CSV.open())
               if r.get("human_label", "").strip()} if LABELS_CSV.is_file() else {}
    pairs = [(primary[r["run_path"]]["human_label"].strip().lower(),
              r["human_label"].strip().lower())
             for r in incoming if r["run_path"] in primary and r["human_label"].strip()]
    if not pairs:
        print("No overlapping labeled run_paths between labels.csv and this file — "
              "label the same set first.")
        return
    exact = sum(1 for a, b in pairs if a == b) / len(pairs)
    kappa = cohens_kappa([p[0] for p in pairs], [p[1] for p in pairs])
    print(f"Human-vs-human agreement (the ceiling for judge kappa, PRD §6):")
    print(f"  n={len(pairs)}  exact={exact:.0%}  κ={kappa:.3f}")
    for a, b in [(r, primary[r["run_path"]]) for r in incoming
                 if r["run_path"] in primary and r["human_label"].strip()
                 and r["human_label"].strip().lower() != primary[r["run_path"]]["human_label"].strip().lower()]:
        print(f"  disagreement: {a['run_path']}  primary={b['human_label']}  second={a['human_label']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="import-labels", description=__doc__)
    p.add_argument("csv_path", type=Path)
    p.add_argument("--second", action="store_true",
                   help="report human-vs-human agreement instead of merging")
    p.add_argument("--overwrite", action="store_true",
                   help="let incoming labels replace existing human labels")
    args = p.parse_args(argv)

    if not args.csv_path.is_file():
        print(f"No such file: {args.csv_path}", file=sys.stderr)
        return 1
    incoming = _read(args.csv_path)
    IMPORTS_DIR.mkdir(exist_ok=True)
    shutil.copy2(args.csv_path, IMPORTS_DIR / args.csv_path.name)

    if args.second:
        _second(incoming)
    else:
        _merge(incoming, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
