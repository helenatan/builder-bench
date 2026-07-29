Great, the ledger looks good. Now the actual "Pay in 3" mechanic: every order gets split into
**3 equal installments** that the customer pays over time.

The thing Finance and Support both care about here is that **the installments add back up to
exactly what the customer was charged** — we can't have a customer paying a penny more or less
than their order total across the three payments. So:

- Each installment is a whole number of cents (no fractional cents — those don't exist).
- The three installments must sum **exactly** to that order's `amount_cents`.
- When the total doesn't divide cleanly by 3, push the leftover cent(s) onto the **earliest**
  installment(s) — customers would rather pay the rounding up front than discover a surprise on
  the last payment. So `1000` cents becomes `[334, 333, 333]`.

Add an `"installments"` field to each ledger entry: the list of 3 integers.
