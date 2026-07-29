Customers on the loyalty discount still pay in 3, so we need a Pay-in-3 schedule on the
**discounted** price too. Same rules as the original split — nothing new to learn here, just
applied to the discounted amount:

- Whole cents only.
- The three installments sum **exactly** to `discounted_cents` — not a penny off, since this is
  what the customer actually gets charged.
- Any leftover cent(s) go to the **earliest** installment(s).

Add a `"discounted_installments"` field to each entry: the list of 3 integers.
