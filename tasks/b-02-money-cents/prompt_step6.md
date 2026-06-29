Last thing — Finance needs a reconciliation summary before they'll approve the launch. They want
two grand totals across the whole batch, both in integer cents. Write them to `answer.json` in
this directory:

```json
{"total_cents": <int>, "discounted_total_cents": <int>}
```

- `total_cents` — what we'd have collected at full price: the sum of every order's `amount_cents`
  (which should also equal the sum of all the `installments`, since those were built to add up
  exactly).
- `discounted_total_cents` — what we'll actually collect with the loyalty discount: the sum of
  every `discounted_cents` (equivalently, the sum of all `discounted_installments`).

And keep the ledger intact — `ledger.json` should still have every money field
(`amount_cents`, `installments`, `discounted_cents`, `discounted_installments`) stored as integer
cents. Finance will spot-check the line items against these totals, so the two have to agree.
