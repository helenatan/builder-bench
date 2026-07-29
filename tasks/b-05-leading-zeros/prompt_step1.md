Quick heads-up before anything else: our customer IDs are **fixed-width 5-digit strings with
leading zeros** — `00042`, not `42`. They're identifiers, not numbers, and other systems key on
the exact string, so keep them exactly as-is in anything you compute or produce.

`fixtures/customers.csv` is our customer list. How many customers do we have per region?

Write it to `answer.json` in the current directory:

```json
{"customers_by_region": {"west": <int>, "east": <int>, "central": <int>}}
```
