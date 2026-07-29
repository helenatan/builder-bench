# Builder-Bench

**An open-source agentic eval suite for the non-engineer "builder" persona — measuring how
well coding agents take a person from a rough idea to a working product.**

Existing benchmarks (e.g. SWE-bench) test agents on engineer-written GitHub issues inside
mature codebases. Builder-Bench measures a rapidly growing way people actually use coding
agents: a PM, analyst, or indie builder describing what they want and expecting the agent to
build it end to end. Four task categories — **A** Vague Ask (underspecified requests), **B** Long Haul (coherence
over a long build), **C** Full Build (spec-to-product), **D** Messy World (data judgment) — graded with programmatic checks plus
a validated LLM judge, reported with **cost-per-solved-task** (the angle SWE-bench lacks).

> Status: **M3** — 23 tasks across all four categories, **6 Claude models across 4 tiers**
> (Frontier / Flagship / Mid / Budget — the current Claude 5 generation alongside the 4.x
> lineup) run at 3 attempts each, LLM judge validated against blind human labels (κ = 0.79, bar
> was 0.7). Live leaderboard: **[builder-bench-delta.vercel.app](https://builder-bench-delta.vercel.app/)**.
> See [Roadmap](#roadmap).

## Project docs

The design lives in [`docs/`](docs/):

- [`docs/findings.md`](docs/findings.md) — **the findings & recommendations**: what the runs showed and the three model-behavior changes the evidence supports.
- [`docs/PRD.md`](docs/PRD.md) — the full product requirements doc (motivation, categories, grading, models).
- [`docs/eval-framework.md`](docs/eval-framework.md) — the design backbone: the six-part anatomy of an evaluation, the five categories, and how to design a test case.
- [`docs/task-backlog.md`](docs/task-backlog.md) — sub-type menus and seed tasks for each v1 category.
- [`docs/sample-tasks.md`](docs/sample-tasks.md) — the fully worked design for the a-05 Vague Ask task.
- [`tasks/README.md`](tasks/README.md) — the task-folder schema for contributors.

---

## Results so far

23 tasks × 6 models, 3 attempts each. Pass@1 is the unbiased estimator over those attempts.

| Model | Tier | Mean pass@1 | Solved outright | Total spend |
|-------|------|------------:|:---------------:|------------:|
| Claude Haiku 4.5 | Budget | 55% | 14/23 | $4.51 |
| Claude Sonnet 4.6 | Mid | 72% | 19/23 | $15.48 |
| Claude Opus 4.8 | Flagship | 75% | 18/23 | $19.97 |
| Claude Sonnet 5 | Mid | 88% | 22/23 | $30.88 |
| Claude Fable 5 | Frontier | 90% | 22/23 | $42.14 |
| Claude Opus 5 | Flagship | **90%** | 23/23 | $43.88 |

By category — where models actually separate:

| Category | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 | Sonnet 5 | Fable 5 | Opus 5 |
|----------|------:|-------:|-----:|------:|-------:|-----:|
| A · Vague Ask (5) | 0.00 | 0.20 | 0.13 | 0.80 | 0.80 | 0.80 |
| B · Long Haul (5) | 0.87 | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 |
| C · Full Build (5) | 0.87 | 0.93 | 1.00 | 0.87 | 1.00 | 1.00 |
| D · Messy World (8) | 0.50 | 0.75 | 0.83 | 0.88 | 0.83 | 0.88 |

**Read this as a capability profile, not a ranking.** With 23 tasks the 95% CIs overlap; 9 of 23
tasks come out the same across all six models, so most of the ordering turns on the other 14.
The headline is the shape, not the ordering: **the entire generational jump lives in one
category.** Every 4.x model is near-floor on Vague Ask (0.13–0.20) — the category where the
correct move is to ask a question before building — while every Claude 5 model jumps to 0.80.
On well-specified build work (B, C), 4.x was already near-ceiling, and the 5-generation models
are statistically tied with it there. Within the Claude 5 generation, the three models cluster
within 2 points of each other (0.88–0.90); Sonnet 5 gets ~98% of Opus 5's accuracy at 60% of the
cost, and Fable 5 reaches the same top-line accuracy as Opus 5 in roughly half the agent turns.

Full standings, the task × model matrix, per-task teardowns and every transcript:
**[builder-bench-delta.vercel.app](https://builder-bench-delta.vercel.app/)**.
What it all means — the findings and the three model-behavior recommendations the evidence
supports: **[docs/findings.md](docs/findings.md)**.

## What's here

- A **neutral headless harness** (`harness/runner.py`) built on the Claude Agent SDK, with an
  Anthropic adapter (other labs deferred to v2).
- A **dual-backend sandbox** (`harness/sandbox.py`): Docker (spec-compliant isolation) with a
  local-tmpdir fallback so the runner executes even without Docker installed.
- **23 tasks** across the four categories, 18 with programmatic graders.
- An **LLM judge** (`judge/`) for behavioral rubrics, plus the validation harness
  (`judge/validation/`) that measures it against blind human labels.
- Metrics: pass@1 / pass@3 / cost-per-solved-task, and a static site generator (`harness/report.py`).

## Quickstart

```bash
# 1. Install (Python 3.11+). A virtualenv is recommended on externally-managed Pythons.
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # or: pip install claude-agent-sdk pyyaml

# 2. Authenticate the runner on your Claude subscription (see "Authentication" below)
claude setup-token          # one-time; stores an OAuth login the SDK reuses

# 3. Run a task
python -m harness.runner --task b-01 --model opus-4.8
```

When it finishes you get:

- A full logged trajectory at `results/runs/<task>/<model>/<stamp>/attempt-N/`
  (`transcript.json`, `transcript.md`, `result.json`).
- A summary with pass@k + cost-per-solved-task.
- An appended row in `results/leaderboard.json`.

### CLI

```
python -m harness.runner --task b-01 --model opus-4.8 \
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
```

Validate every manifest with `python scripts/check_tasks.py` (CI runs this on each PR).

The **grader contract**: `python grader.py <grade_input.json>` reads a bundle the harness
writes (`{workdir, transcript, final_text, ...}`) and prints a single JSON object:
`{"score": float, "failure_tags": [...], "details": "..."}`. The runner recomputes
`passed` as `score >= pass_threshold`; anything the grader prints for it is overwritten.

## What a clean clone can and can't reproduce

The answer keys live in a `private/` split that is gitignored and excluded from the deploy — so
a model under test can't read them out of its own environment. That split is **not** in this
repo. Here's what that means for you:

| | Works on a fresh clone | Needs `private/` |
|---|---|---|
| Run any task against a model | ✅ | |
| **Programmatic grading** (18 of 23 tasks) | ✅ graders recompute ground truth from the public `fixtures/` | optional cross-check only |
| `pytest` | ✅ | |
| **Judge grading** (all of A, the behavioral half of D) | ❌ | per-task rubrics live in `private/rubrics/` |
| Reproduce the published leaderboard end to end | partially — programmatic tasks only | |

So a clone reproduces every programmatic number. The judge-graded ones need the rubrics; the
graders themselves degrade gracefully rather than crashing (`_load_expected()` returns `None`
and the cross-check is skipped), and CI asserts that this actually holds rather than trusting it.

Note the asymmetry: the answer keys are held back from *the repo*, not from *you* — every
task's full teardown, including its answer key and failure analysis, is published on the
[site](https://builder-bench-delta.vercel.app/) by design. The split protects against runtime
leakage into a graded run, not against readers. Contributors and graders who need `private/`
should ask for it out of band.

## Judge validation

Category A and the behavioral half of Messy World are graded by an LLM judge, which is only
worth anything if it agrees with a human. The bar was set **before** labeling: Cohen's κ ≥ 0.7.

```bash
python -m judge.validation.validate kappa --fresh-only
```

| Measure | n | Exact | κ | |
|---------|--:|------:|--:|---|
| Pass/partial/fail label, blind | 103 | 89% | **0.79** | ✅ clears the bar |
| Same, excluding a-02 (rubric changed post-labeling) | 94 | 88% | 0.76 | ✅ robust to the caveat |
| All labels incl. reconciled gold set | 142 | 87% | 0.74 | ✅ |

Blind κ climbed 0.40 → 0.49 → 0.72 → 0.93 across four labeling rounds as the rubrics tightened
(`judge/validation/disagreements-round*.md` records every disagreement and what changed).

One thing to be clear about: **per-model, Opus sits at κ = 0.66** — below the bar, even though
the pooled number clears it. Worth knowing before citing a per-model behavioral result.

A canary regression (`judge/validation/canary.py`) guards against the judge sliding back into
grading the agent's *prose* instead of its *results*: it takes a real transcript whose
verification genuinely succeeded and flips only that tool result to a failure. A judge reading
evidence must fail the doctored twin; one reading confident-sounding claims passes both.

## Models

`--model` takes a stable alias resolved in `harness/adapters/__init__.py`:

| Alias | Resolves to (this machine) | Tier |
|-------|----------------------------|------|
| `opus-4.8`, `opus` | `claude-opus-4-8` | Flagship |
| `sonnet-4.6`, `sonnet` | `claude-sonnet-4-6` | Mid |
| `haiku-4.5`, `haiku` | `claude-haiku-4-5-20251001` | Budget |
| `opus-5` | `claude-opus-5` | Flagship |
| `sonnet-5` | `claude-sonnet-5` | Mid |
| `fable-5` | `claude-fable-5` | Frontier |

> The Anthropic aliases map to the concrete shipping ids on this machine. `opus`/`sonnet` still
> resolve to the 4.x models by default — use the `-5` aliases explicitly for the current Claude 5
> generation. v1 is Anthropic-only (no OpenAI/Gemini models); a second harness to measure the
> harness effect is deferred to v2 for API-cost reasons (PRD §9).

## Failure taxonomy

Runs are tagged with builder-persona failure modes: `premature-implementation`, `vision-drift`,
`silent-assumptions`, `weak-self-verification`, `data-blindness`, `over-eagerness`,
`fabricated-data`. All seven are mined from real transcripts of building **PAI** (the PM-AI
Hiring Index — a real product built end to end with Claude Code, and the source of several of
this suite's tasks; see [PRD §8](docs/PRD.md#8-leveraging-pm-ai-hiring-index-pai-as-source-material)
and [docs/pai-transcript-evidence.md](docs/pai-transcript-evidence.md) for the full story). b-01
is designed to surface `vision-drift` and `silent-assumptions` when the early dedupe rule is lost.

## Roadmap

| Milestone | Scope | |
|-----------|-------|---|
| **M0** | Scaffold, schema, dual-backend runner, b-01 end to end | ✅ |
| **M1** | 10–12 tasks across the Full Build and Messy World categories with graders | ✅ |
| **M2** | LLM judge + human-labeled validation set + agreement (Cohen's κ ≥ 0.7) report | ✅ κ = 0.79 |
| **M3** | Remaining Vague Ask tasks, more Long-Haul tasks, full suite run | ✅ 23 tasks |
| M4 | Public launch — repo + live leaderboard site | ✅ site live |

> M3 shipped as a three-tier run (Opus 4.8 / Sonnet 4.6 / Haiku 4.5); the Claude 5 generation
> (Fable 5 / Opus 5 / Sonnet 5) was added as a post-M3 extension in July 2026, bringing the
> suite to its current 6 models across 4 tiers — see [PRD §13](docs/PRD.md), Open Questions.

## Contributing

Contributions welcome via PR with DCO sign-off (`git commit -s`) — see
[CONTRIBUTING.md](CONTRIBUTING.md) for the task schema and what a task needs to be accepted
(short version: it has to produce *signal*, and you have to show the pilot run). New task ideas
are best proposed as an issue first. Disputes about a published grade are welcome too — every
transcript is published so they can be settled on evidence.

Also: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [SECURITY.md](SECURITY.md)

> ⚠️ **Before you run anything:** with `--sandbox local` (the automatic fallback when Docker
> isn't present) the agent's Bash runs on your host, as you. It is not a security boundary.
> See [SECURITY.md](SECURITY.md).

## License

- **Code** (`harness/`, `judge/` runners, `site/`, graders): Apache-2.0 — see [LICENSE](LICENSE).
- **Tasks/dataset** (`tasks/`, rubrics): CC-BY-4.0 + a contamination canary and a
  "do not train" notice — see [DATASET_LICENSE](DATASET_LICENSE).

Published tasks are treated as **burned for future-model evaluation** — once they're on the
public site they may end up in a training corpus, and the canary GUID in
[DATASET_LICENSE](DATASET_LICENSE) is the detection instrument if that happens. Results are a
snapshot of the models current at run time.
