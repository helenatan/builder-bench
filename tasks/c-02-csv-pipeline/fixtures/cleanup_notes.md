# How finance wants the sales data cleaned

These are the rules we apply every quarter so the numbers reconcile across teams. Please apply
all of them, exactly as written.

**Every field:** strip leading and trailing whitespace.

**Amount**
- Drop the `$` and any thousands commas — e.g. `"$1,234.56"` → `1234.56`. Store it as a number
  with 2 decimal places.
- Some amounts are negative (refunds and adjustments). They show up two ways, and both mean a
  negative number:
  - a leading minus, e.g. `-$25.00` → `-25.00`
  - accounting style in parentheses, e.g. `($50.00)` → `-50.00`

**Category:** lowercase it, so `Home`, `home`, and `HOME` all roll up together.

**Date:** convert everything to ISO `YYYY-MM-DD`. The export mixes four formats:
- `MM/DD/YYYY`
- `YYYY-MM-DD`
- `Month D, YYYY` (e.g. `March 7, 2026`)
- `D-Mon-YYYY` (e.g. `7-Mar-2026`)

**Drop the junk rows:** if a row is missing its date, amount, or category, leave it out
entirely — don't try to guess the missing value.

**De-duplicate:** after the cleaning above, if two rows end up identical in `date`, `category`,
and `amount`, keep only one. (The export system occasionally writes the same sale twice.)
