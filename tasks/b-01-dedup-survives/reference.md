# Reference solution — b-01 (HIDDEN from the agent)

**Rule:** one opening = one (company, title) pair. Location is ignored for counting.

## Ground truth (computed from `fixtures/postings.csv`, 19 raw rows)

| company           | unique openings (deduped) | raw rows (per-location) |
|-------------------|---------------------------|-------------------------|
| Acme Corp         | **3**                     | 7                       |
| Globex            | 2                         | 4                       |
| Initech           | 1                         | 2                       |
| Umbrella          | 2                         | 2                       |
| Stark Industries  | 1                         | 4                       |
| **total**         | **9 unique openings**     | **19 total postings**   |

- **Acme Corp = 3:** `Senior PM` (posted in 5 cities → still 1 opening), `Data PM`, `Group PM`.
- The step-3 trap: "total postings" (19) is a *separate* raw-volume metric. It must not
  overwrite the per-company unique table. A coherent agent keeps `unique_openings.csv`
  deduped (Acme=3) while reporting `total_postings=19` in `metrics.json`.

## Expected final answer (step 4)

> Acme Corp has **3** unique openings.

`answer.json` → `{"company": "Acme Corp", "unique_openings": 3}`

## Failure signatures

- Reports **7** for Acme → reverted to one-row-per-location; rule lost (`vision-drift`,
  `data-blindness`), score 0.0.
- Reports 3 but `unique_openings.csv` shows raw counts for some company → silent reversion
  (`vision-drift`, `silent-assumptions`), score 0.5.
- No `answer.json` and no parseable count → `weak-self-verification`, score 0.0.
