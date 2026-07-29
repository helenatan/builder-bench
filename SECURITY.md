# Security

## Reporting a vulnerability

Report privately via [GitHub Security Advisories](https://github.com/helenatan/builder-bench/security/advisories/new).
Please don't open a public issue for a vulnerability.

This is a research project maintained by one person — expect a first response within a week,
not within hours.

## Know this before you run the benchmark

**The `local` sandbox is not a security boundary.** Builder-Bench runs coding agents and then
executes what they produce. Two backends:

| Backend | What's isolated | Reality |
|---------|-----------------|---------|
| `docker` | Pinned `python:3.12-slim`, `--network none` | Builds the starting state in a container. |
| `local` | A throwaway temp dir | **The agent's Bash runs on your host, as you.** |

`--sandbox auto` (the default) picks Docker when it's available and silently falls back to
`local` when it isn't. Full in-container *agent execution* — running the agent's tool calls
inside the container, not just constructing the state — is a tracked hardening item, not
something the current code does.

So: **run this on a machine you're willing to have an LLM execute shell commands on.** Use
`--sandbox docker` if you want the container path and want it to fail loudly rather than
degrade. Graders also execute task code (`c-01`, `c-03`, `c-04r`, and `c-05` start the app the
agent wrote), so the same applies to grading a run you didn't produce.

Do not run task folders or run artifacts from an untrusted PR on a machine you care about.
`setup.sh` and `grader.py` are ordinary code with no sandbox around them.

## Credentials

The runner is subscription-billed by default and **strips `ANTHROPIC_API_KEY` and
`ANTHROPIC_AUTH_TOKEN` from the child environment** unless you pass `--allow-api`, so a stray
key in your shell can't silently bill the API. Nothing in this repo reads, stores, or logs a
credential.

Run transcripts under `results/runs/` capture everything the agent saw and did. They're
gitignored by default. If you commit a curated set, read them first — they contain whatever
your fixtures contained.

## Scope

Out of scope: the benchmark tasks deliberately contain broken code, bad data, and (in `c-03`) a
hardcoded weak password, because catching that is the thing being tested. Those aren't
vulnerabilities in Builder-Bench; they're the exam questions.
