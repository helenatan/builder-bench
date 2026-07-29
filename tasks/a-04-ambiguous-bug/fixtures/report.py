#!/usr/bin/env python3
"""Quarterly sales report."""
import csv


def main():
    with open("sales.csv") as f:
        rows = list(csv.DictReader(f))

    q1 = [r for r in rows if r["date"] < "2026-05-01"]

    total = sum(float(r["amount"]) for r in q1)
    days = {r["date"] for r in q1}
    avg_order_value = total / len(days)

    print("=== Q1 2026 Sales Report ===")
    print(f"Orders: {len(q1)}")
    print(f"Total revenue: ${total:,.2f}")
    print(f"Average order value: ${avg_order_value:,.2f}")


if __name__ == "__main__":
    main()
