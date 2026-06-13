# Builder-Bench

**An open-source agentic eval suite for the non-engineer "builder" persona — measuring how
well coding agents take a person from a rough idea to a working product.**

Existing benchmarks (e.g. SWE-bench) test agents on engineer-written GitHub issues inside
mature codebases. Builder-Bench measures a rapidly growing way people actually use coding
agents: a PM, analyst, or indie builder describing what they want and expecting the agent to
build it end to end. Four task categories — **A** Vague Ask (underspecified requests), **B** Long Haul (coherence
over a long build), **C** Full Build (spec-to-product), **D** Messy World (data judgment) — graded with programmatic checks plus
a validated LLM judge, reported with **cost-per-solved-task** (the angle SWE-bench lacks).

> Status: **M0** (scaffold + first end-to-end task). See [Roadmap](#roadmap).

## Project docs

The design lives in [`docs/`](docs/):

- [`docs/PRD.md`](docs/PRD.md) — the full product requirements doc (motivation, categories, grading, models, milestones).
- [`docs/eval-framework.md`](docs/eval-framework.md) — the design backbone: the six-part anatomy of an evaluation, the five categories, and how to design a test case.
- [`docs/task-backlog.md`](docs/task-backlog.md) — sub-type menus and seed tasks for each v1 category.
- [`docs/sample-tasks.md`](docs/sample-tasks.md) — the fully worked design for the a-05 Vague Ask task.
- [`tasks/README.md`](tasks/README.md) — the task-folder schema for contributors.

---

## What's in M0

M0 proves the neutral runner works end to end on one task with a clean programmatic grade:

- The repo scaffold + task schema.
- A **neutral headless harness** (`harness/runner.py`) built on the Claude Agent SDK, with an
  Anthropic adapter (other labs deferred to v2).
- A **dual-backend sandbox** (`harness/sandbox.py`): Docker (spec-compliant isolation) with a
  local-tmpdir fallback so the runner executes even without Docker installed.
- Task **b-01** ("dedupe by company, not by location") — a single-session, programmatically
  graded Long-Haul-lite coherence task.
- Metrics: pass@1 / pass@3 / cost-per-solved-task.

## Quickstart

```bash
# 1. Install (Python 3.11+). A virtualenv is recommended on externally-managed Pythons.
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # or: pip install claude-agent-sdk pyyaml

# 2. Authenticate the runner on your Claude subscription (see "Authentication" below)
claude setup-token          # one-time; stores an OAuth login the SDK reuses

# 3. Run a task
python -m harness.runner --task b-01 --model opus-4.6
```

When it finishes you get:

- A full logged trajectory at `results/runs/<task>/<model>/<stamp>/attempt-N/`
  (`transcript.json`, `transcript.md`, `result.json`).
- A summary with pass@k + cost-per-solved-task.
- An appended row in `results/leaderboard.json`.

### CLI

```
python -m harness.runner --task b-01 --model opus-4.6 \
    [--attempts 3]               # for pass@3
    [--sandbox auto|docker|local]
    [--budget-usd 2.0]           # per-attempt spend cap
    [--max-turns 40]
    [--allow-api]                # opt into pay-per-use API billing (default: subscription only)
```

## Authentication — subscription by default

The harness runs each model through the Claude Agent SDK, which drives the `claude` CLI as a
subprocess. **v1 is subscription-only:** runs bill to your Claude subscription, not the
pay-per-use API.

- **Subscription (default):** run `claude setup-token` (or `claude login`) once to store an
  OAuth login the SDK reuses. The runner **strips `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`
  from the child env by default**, so a stray API key can't silently bill the API — billing
  falls through to your subscription login.
- **API (opt-in):** pass `--allow-api` and set `ANTHROPIC_API_KEY=sk-ant-...` to use pay-per-use
  API billing instead (e.g. for an unthrottled, batch-priced record run).

> Subscription runs are subject to your plan's rate limits (5-hour / weekly windows), so large
> batches may need spreading across days. Cost-per-solved-task is still reported, imputed from
> token counts at list prices regardless of how a run was paid for.

> **Note for Claude Desktop "local agent mode":** inside a host-brokered session, auth is
> provided to the in-session model by the host and is *not* inherited by spawned subprocesses.
> A child `claude` will 401 unless you have your own login. Run the benchmark from a normal
> terminal after `claude setup-token`.

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
`{"score": float, "failure_tags": [...], "details": "..."}`. The runner recomputes
`passed` as `score >= pass_threshold`; anything the grader prints for it is overwritten.

## Models

`--model` takes a stable alias resolved in `harness/adapters/__init__.py`:

| Alias | Resolves to (this machine) |
|-------|----------------------------|
| `opus-4.6`, `opus` | `claude-opus-4-8` |
| `sonnet-4.6`, `sonnet` | `claude-sonnet-4-6` |
| `haiku-4.5`, `haiku` | `claude-haiku-4-5-20251001` |

> The PRD targets `opus-4.6`; that exact id is not available in the current environment, so
> the Anthropic aliases map to the latest shipping ids. Re-pin to the PRD ids when running for
> record. v1 is Anthropic-only (Opus / Sonnet / Haiku); OpenAI and Gemini models, plus a
> second harness to measure the harness effect, are deferred to v2 for API-cost reasons (PRD §9).

## Failure taxonomy

Runs are tagged with builder-persona failure modes: `premature-implementation`, `vision-drift`,
`silent-assumptions`, `weak-self-verification`, `data-blindness`, `over-eagerness`,
`fabricated-data`. All seven are mined from real PAI build transcripts
([docs/pai-transcript-evidence.md](docs/pai-transcript-evidence.md)). b-01 is
designed to surface `vision-drift` and `silent-assumptions` when the early dedupe rule is lost.

## Roadmap

| Milestone | Scope |
|-----------|-------|
| **M0** ✅ | Scaffold, schema, dual-backend runner, b-01 end to end |
| M1 | 10–12 tasks across the Full Build and Messy World categories with graders |
| M2 | LLM judge + human-labeled validation set + agreement (Cohen's κ ≥ 0.7) report |
| M3 | Remaining Vague Ask tasks, 1–2 more Long-Haul-lite tasks, full three-tier run |
| M4 | Writeup (taxonomy + 3 recommendations + PAI case study), blog post, static site, launch |

## License

- **Code** (`harness/`, `judge/` runners, `site/`, graders): Apache-2.0 — see [LICENSE](LICENSE).
- **Tasks/dataset** (`tasks/`, `judge/rubrics/`): CC-BY-4.0 + a contamination canary and a
  "do not train" notice — see [DATASET_LICENSE](DATASET_LICENSE).

Contributions welcome via PR with DCO sign-off — see [CONTRIBUTING.md](CONTRIBUTING.md).
