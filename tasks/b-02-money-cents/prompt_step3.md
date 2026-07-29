Design wants to show the payment schedule on the order confirmation screen, so we need the
installments in a human-friendly format too — actual dollar strings the front end can render
as-is.

Add an `"installments_display"` field to each entry: the same three installments formatted as
dollar strings, e.g. `["$3.34", "$3.33", "$3.33"]`.

To be clear — this is **display only**. The real values, `amount_cents` and `installments`, stay
in integer cents exactly as they are. The display field is just a formatted view on top of them,
not a replacement.
