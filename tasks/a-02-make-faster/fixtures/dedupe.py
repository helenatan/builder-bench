"""Find duplicate pairs of records by exact name match.

Reads records.csv and prints every pair of row indices that share the same (lowercased) name.
"""

import csv


def load_records(path="records.csv"):
    with open(path) as f:
        return list(csv.DictReader(f))


def find_duplicate_pairs(records):
    pairs = []
    # Compare every record against every other record (O(n^2)).
    for i in range(len(records)):
        for j in range(len(records)):
            if i < j:
                ni = records[i]["name"].strip().lower()
                nj = records[j]["name"].strip().lower()
                if ni == nj:
                    pairs.append((i, j))
    return pairs


if __name__ == "__main__":
    recs = load_records()
    dupes = find_duplicate_pairs(recs)
    print(f"{len(dupes)} duplicate pair(s) found")
    for i, j in dupes:
        print(f"  row {i} == row {j}: {recs[i]['name']}")
