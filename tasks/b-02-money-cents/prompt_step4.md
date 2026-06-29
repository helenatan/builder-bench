Marketing just got approval for a **7% loyalty discount** and they want it live on this batch.
Apply it to every order.

A couple of things Finance was specific about:

- Compute the discount off `amount_cents` and keep the result in **integer cents** — same rule
  as day one, no decimal-dollar math creeping in here.
- Money has to land on a whole cent, so round each discounted amount to the **nearest cent, and
  round a half-cent up** (if it comes out to exactly half a cent, round up — that's the
  convention our billing system uses). Worked example: an order of `4250` cents → `4250 × 0.93 =
  3952.5` → rounds to `3953`.

Add a `"discounted_cents"` field (integer) to each entry for the post-discount price.

Leave `amount_cents` and `installments` exactly as they are — those are the original order, and
we still need them for reconciliation.
