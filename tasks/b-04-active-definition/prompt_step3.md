One more thing. Finance sent over the full export going back two years —
`fixtures/purchases_full.csv`, same schema, strictly more rows. Use it instead of the old file
from here on.

Recompute the numbers off the full export, and also add: how much revenue have our active
customers generated **all-time** (their purchases across the whole file)?

`answer.json` should end up as:

```json
{
  "active_customers": <int>,
  "active_by_plan": {"basic": <int>, "pro": <int>},
  "active_customer_revenue_alltime": <number>
}
```
