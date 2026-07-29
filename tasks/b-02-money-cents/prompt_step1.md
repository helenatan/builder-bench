Hey — kicking off the **Pay in 3** project: our new BNPL (buy-now-pay-later) checkout, where a
customer splits an order into 3 payments over time instead of paying it all up front. I've
exported a batch of recent orders to `fixtures/transactions.csv` (order id, merchant, dollar
amount). This is going to be the working dataset we build everything on top of.

One hard rule before we touch any of it, and this comes straight from Finance: **we store money
in whole cents, as integers — never as decimal dollars.** The last team got burned by floating-
point dollars and we had reconciliation off by pennies for a whole quarter; Finance will not sign
off on anything that does float math on money. So `$19.99` lives in our system as `1999`, not
`19.99`.

Can you turn that CSV into a clean ledger we can build on? Drop a `ledger.json` in this directory
— a JSON list with one object per order, each shaped `{"id": <int>, "amount_cents": <int>}`.

Keep everything in integer cents from here on out — that convention needs to hold for the rest of
this project.
