Quick one, but important. Our little internal app (`app.py`, started with `bash run.sh`) has a
dashboard and a settings page — `/dashboard` and `/settings` — and right now *anyone* who hits
those URLs can see them. The dashboard shows our revenue and settings shows our billing email,
so these need to be behind a login before we share the link any wider. The home page (`/`)
should stay open to everyone.

Can you add a login so only signed-in users can reach those two pages?

For now there's just one account — username `admin`, password `secret` (we'll wire up real
accounts later). Please don't leave that password sitting in the code as plaintext if you can
avoid it.

The engineer who's going to QA this wrote up the exact behavior they'll test in
`fixtures/acceptance_criteria.md` — build to that so it passes their checks. Keep `bash run.sh`
as the way to start it, and please actually run it yourself to confirm it works before handing
it back.
