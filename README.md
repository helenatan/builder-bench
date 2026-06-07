# Builder-Bench

**An open-source agentic eval suite for the non-engineer "builder" persona — measuring how
well coding agents take a person from a rough idea to a working product.**

Existing benchmarks (e.g. SWE-bench) test agents on engineer-written GitHub issues inside
mature codebases. Builder-Bench measures the fastest-growing way people actually use coding
agents: a PM, analyst, or indie builder describing what they want and expecting the agent to
build it end to end. Four task categories — **A** spec-to-product, **B** data judgment,
**C** underspecification, **D** long-horizon coherence — graded with programmatic checks plus
a validated LLM judge, reported with **cost-per-solved-task** (the angle SWE-bench lacks).

> Status: **M0** (scaffold + first end-to-end task). See [Roadmap](#roadmap).

## Project docs

The design lives in [`docs/`](docs/):

- [`docs/PRD.md`](docs/PRD.md) — the full product requirements doc (motivation, categories, grading, models, milestones).
- [`docs/BUILD-KICKOFF.md`](docs/BUILD-KICKOFF.md) — the M0 build brief this scaffold was built from.
- [`docs/sample-tasks.md`](docs/sample-tasks.md) — two fully worked example tasks (C-01 and D-01).

---

## What's in M0

M0 proves the neutral runner works end to end on one task with a clean programmatic grade:

- The repo scaffold + task schema.
- A **neutral headless harness** (`harness/runner.py`) built on the Claude Agent SDK, with an
  Anthropic adapter (other labs come in M3).
- A **dual-backend sandbox** (`harness/sandbox.py`): Docker (spec-compliant isolation) with a
  local-tmpdir fallback so the runner executes even without Docker installed.
- Task **D-01** ("dedupe by company, not by location") — a single-session, programmatically
  graded D-lite coherence task.
- Metrics: pass@1 / pass@3 / cost-per-solved-task.

## Quickstart

```bash
# 1. Install (Python 3.11+). A virtualenv is recommended on externally-managed Pythons.
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # or: pip install claude-agent-sdk pyyaml

# 2. Authenticate the runner (see "Authentication" below)
export ANTHROPIC_API_KEY=sk-ant-...     # or: claude setup-token

# 3. Run a task
python -m harness.runner --task d-01 --model opus-4.6
```

When it finishes you get:

- A full logged trajectory at `results/runs/<task>/<model>/<stamp>/attempt-N/`
  (`transcript.json`, `transcript.md`, `result.json`).
- A summary with pass@k + cost-per-solved-task.
- An appended row in `results/leaderboard.json`.

### CLI

```
python -m harness.runner --task d-01 --model opus-4.6 \
    [--attempts 3]               # for pass@3
    [--sandbox auto|docker|local]
    [--budget-usd 2.0]           # per-attempt spend cap
    [--max-turns 40]
```

## Authentication

The harness runs each model through the Claude Agent SDK, which drives the `claude` CLI as a
subprocess. That subprocess needs its own credentials:

- **API key:** `export ANTHROPIC_API_KEY=sk-ant-...` (pay-per-use API billing), **or**
- **Subscription token:** run `claude setup-token` (or `claude login`) once to store an
  OAuth credential the SDK will reuse.

> **Note for Claude Desktop "local agent mode":** inside a host-brokered session, auth is
> provided to the in-session model by the host and is *not* inherited by spawned subprocesses.
> A child `claude` will 401 unless you provide one of the credentials above. Run the benchmark
> from a normal terminal with `ANTHROPIC_API_KEY` set (or after `claude setup-token`).

## Sandboxing

Each task builds a fixed starting state in an isolated working directory, then the agent runs
with that directory as its cwd.

| Backend  | Isolation | When used | Notes |
|----------|-----------|-----------|-------|
| `docker` | Container (pinned `python:3.12-slim`, `--network none`) builds the state | auto-selected when Docker is available | Spec-compliant path. |
| `local`  | Throwaway temp dir on the host | fallback when Docker is absent | **Not a security boundary** — the agent's Bash runs on the host. Prints a loud warning. Dev use only. |

`--sandbox auto` (default) picks Docker if available, else local. Full in-container *agent
execution* (running the agent's tool calls inside the container, not just state construction)
is a tracked v1.x hardening item.

## Task schema

Every task is a folder under `tasks/` conforming to:

```
tasks/<id>-<slug>/
  prompt.md  OR  prompt_step1.md ... prompt_stepN.md   # exactly what the agent sees
  setup.sh           # builds the fixed starting state in the sandbox
  fixtures/          # data/files the task needs
  success.yaml       # metadata, prompt-step order, pass threshold, possible failure tags
  grader.py          # prints {score, passed, failure_tags, details} as JSON
  reference.md       # expected output / known-good answer — HIDDEN from the agent
  expected/          # (optional) machine-readable ground truth for the grader
```

The **grader contract**: `python grader.py <grade_input.json>` reads a bundle the harness
writes (`{workdir, transcript, final_text, ...}`) and prints a single JSON object:
`{"score": float, "passed": bool, "failure_tags": [...], "details": "..."}`.

## Models

`--model` takes a stable alias resolved in `harness/adapters/__init__.py`:

| Alias | Resolves to (this machine) |
|-------|----------------------------|
| `opus-4.6`, `opus` | `claude-opus-4-8` |
| `sonnet-4.6`, `sonnet` | `claude-sonnet-4-6` |
| `haiku-4.5`, `haiku` | `claude-haiku-4-5-20251001` |

> The PRD targets `opus-4.6`; that exact id is not available in the current environment, so
> the Anthropic aliases map to the latest shipping ids. Re-pin to the PRD ids when running for
> record. OpenAI and Google adapters arrive in M3.

## Failure taxonomy

Runs are tagged with builder-persona failure modes: `premature-implementation`, `vision-drift`,
`silent-assumptions`, `weak-self-verification`, `data-blindness`, `over-eagerness`. D-01 is
designed to surface `vision-drift` and `silent-assumptions` when the early dedupe rule is lost.

## Roadmap

| Milestone | Scope |
|-----------|-------|
| **M0** ✅ | Scaffold, schema, dual-backend runner, D-01 end to end |
| M1 | 10–12 tasks across categories A and B with graders |
| M2 | LLM judge + human-labeled validation set + agreement (Cohen's κ ≥ 0.7) report |
| M3 | Remaining C tasks, 1–2 more D-lite tasks, all model adapters, full run |
| M4 | Writeup (taxonomy + 3 recommendations + PAI case study), blog post, static site, launch |

## License

- **Code** (`harness/`, `judge/` runners, `site/`, graders): Apache-2.0 — see [LICENSE](LICENSE).
- **Tasks/dataset** (`tasks/`, `judge/rubrics/`): CC-BY-4.0 + a contamination canary and a
  "do not train" notice — see [DATASET_LICENSE](DATASET_LICENSE).

Contributions welcome via PR with DCO sign-off — see [CONTRIBUTING.md](CONTRIBUTING.md).
