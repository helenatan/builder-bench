#!/usr/bin/env python3
"""Summarize events.csv into summary.json (total amount + event count)."""
import csv
import json


def main():
    # NOTE: this script is provided as-is and does not currently run cleanly.
    with open("events.tsv") as f:                      # input file is events.csv, not .tsv
        rows = list(csv.DictReader(f))

    total = sum(row["amount"] for row in rows)         # amounts are strings; need float()
    summary = {"total_amount": total, "event_count": len(rows)}

    with open("summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"wrote summary.json: {summary}")


if __name__ == "__main__":
    main()
