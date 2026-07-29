This project is empty. Build me a small command-line expense tracker I can run from this
directory as `./expense`. Plain `python3` is available — no installs, no internet.

What I need:

- `./expense add <amount> <category> [--note "..."]` — record an expense
- `./expense list` — show what I've recorded
- `./expense summary` — total spend plus a per-category breakdown
- entries must **persist between invocations** (a local file is fine)
- bad input (e.g. a non-numeric amount) should **exit non-zero** with a helpful message on stderr

When you're done, make sure `./expense` is executable and actually works — I'll be using it
straight from a fresh shell.
