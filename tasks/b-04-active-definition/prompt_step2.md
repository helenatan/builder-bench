Nice. Now break that down by plan — `fixtures/customers.csv` maps each customer to their plan.

Update `answer.json` to:

```json
{"active_customers": <int>, "active_by_plan": {"basic": <int>, "pro": <int>}}
```
