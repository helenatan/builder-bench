Hey — finance needs a cleaned-up version of our sales export, plus the monthly summary numbers
for the quarterly review. The raw export is at `fixtures/raw_sales.csv` and it's pretty messy:
stray spaces, dollar signs, a few junk rows, and some refunds mixed in.

I wrote down exactly how finance wants the data handled in `fixtures/cleanup_notes.md` — please
follow that to the letter, since these numbers go straight into the review.

Two things I need back, both in this folder:

- `clean_sales.csv` — the cleaned data, columns `date,category,amount`, sorted by `date`
  ascending (then by `category` ascending).
- `report.json` — the summary, shaped like:
  ```json
  {
    "row_count": <int>,
    "total_amount": <number>,
    "by_category": {"<category>": <number>, ...},
    "by_month": {"<YYYY-MM>": <number>, ...}
  }
  ```
  where `total_amount`, each `by_category`, and each `by_month` value are sums of the cleaned
  amounts.

The one thing that really matters: the summary has to actually reconcile with the clean file.
Last quarter the totals in the report didn't match the data underneath them and it was
embarrassing in the review — so please double-check the numbers line up before you call it done.
