# Builder-Bench: Build Kickoff (for Claude Code)

Paste this file (or point Claude Code at it) to start the build. It summarizes the decided
design and gives concrete first steps. The full rationale lives in `Builder-Bench-PRD.md`;
two worked example tasks live in `Builder-Bench-sample-tasks.md`. Read both before building.

---

## What we're building

An open-source agentic eval suite that measures how well coding agents take a person from
a rough idea to a working product (the "builder" persona), with a cost-per-solved-task angle
SWE-bench lacks. Four task categories: A Vague Ask (underspecification), B Long Haul (coherence;
Long-Haul-lite only in v1), C Full Build (spec-to-product), D Messy World (data judgment). Output surfaces: a static leaderboard site, this
repo, a writeup, and downloadable per-run transcripts.

## Decisions already locked (do not re-litigate in v1)

- **Harness:** one NEUTRAL harness for all models, built on the Claude Agent SDK in headless
  mode, with a thin adapter to swap the underlying model. Caveat stated in the writeup: models
  tuned for their own native harness may be slightly disadvantaged.
- **Sandboxing:** each task runs in an isolated Docker container from a fixed starting state.
- **Models (one flagship + one budget per lab):** Opus 4.6 / Haiku 4.5; GPT-5.5 / GPT-5.4-mini;
  Gemini 3.5 Pro / 3.5 Flash (interim: Flash / Flash-Lite until 3.5 Pro ships).
- **Metrics:** pass@1, pass@3, cost-per-solved-task, plus failure-mode tags.
- **Grading:** programmatic first; LLM judge only for Vague Ask and the subjective part of Messy World; validate
  the judge against hand labels (kappa >= 0.7) before trusting it.
- **Long Haul (Category B):** v1 ships Long-Haul-lite (single-session, programmatic). Long-Haul-hard (multi-session, context
  resets) is v2. Firm line: anything needing session resume is v2.
- **License:** Apache 2.0 for code; MIT or CC-BY-4.0 for tasks + canary GUID + private held-out
  split. DCO sign-off, PR-based contributions, author reviews all PRs.

## Target repo structure

```
builder-bench/
  README.md
  LICENSE                      # Apache 2.0 (code)
  DATASET_LICENSE              # MIT or CC-BY-4.0 (tasks) + canary GUID + no-train notice
  CONTRIBUTING.md              # PR flow, task template, DCO sign-off
  pyproject.toml               # or package.json if Node; Python recommended
  harness/
    runner.py                  # headless agent loop via Claude Agent SDK
    adapters/                  # model adapters: anthropic.py, openai.py, google.py
    sandbox.py                 # Docker container setup/teardown
    metrics.py                 # pass@1, pass@3, cost-per-solved-task
  judge/
    judge.py                   # LLM-judge runner
    rubrics/                   # per-task rubric.yaml files
    validation/                # human labels + agreement (kappa) report
  tasks/
    a-01-.../ ... b-.../ c-.../ d-.../ e-.../
      prompt.md
      setup.sh
      fixtures/
      success.yaml             # programmatic checks + (optional) rubric ref
      grader.py
      reference.md             # expected output / known-good (hidden from agent)
  results/
    runs/                      # logged transcripts per model per task
    leaderboard.json           # generated; feeds the static site
  site/                        # static leaderboard generator
  private/                     # held-out split, gitignored, run manually
```

## Task folder schema (every task conforms)

- `prompt.md` — exactly what the agent sees. Nothing hidden leaks in here.
- `setup.sh` — builds the fixed starting state inside the container.
- `fixtures/` — data/files the task needs.
- `success.yaml` — programmatic checks; for subjective tasks, points to a rubric in `judge/rubrics/`.
- `grader.py` — runs checks (and invokes the judge if needed), emits {score, pass, failure_tags}.
- `reference.md` — expected output / known-good answer. HIDDEN from the agent.

See `Builder-Bench-sample-tasks.md` for two fully worked examples (a-01 and b-01).

## First milestone — M0 (do this first)

Goal: prove the runner works end to end on one task with a clean programmatic grade.

1. Scaffold the repo structure above. Python + Docker. Add Apache 2.0 LICENSE and a stub README.
2. Implement `harness/runner.py` against the Claude Agent SDK in headless mode, with the
   Anthropic adapter only (other adapters come later).
3. Implement `harness/sandbox.py` for Docker container setup/teardown from a task's `setup.sh`.
4. Implement task **b-01** ("dedupe by company, not by location") from the sample-tasks file:
   `prompt_step1..4.md`, `fixtures/postings.csv` with the known duplicates, `grader.py` that
   checks the final Acme count == 3 and that earlier unique counts didn't silently inflate.
5. Run Opus 4.6 against b-01 in the sandbox. Confirm: transcript is logged to `results/runs/`,
   grader emits a score, metrics compute. Pick b-01 first BECAUSE it needs no judge.

Done when: `python -m harness.runner --task b-01 --model opus-4.6` runs the agent in Docker,
logs the transcript, grades it programmatically, and writes a result row.

## Then (M1 to M4, see PRD Section 11)

- M1: 10 to 12 tasks across Full Build and Messy World with graders.
- M2: LLM judge + hand-labeled validation set + agreement report.
- M3: remaining Vague Ask tasks, 1 to 2 more Long-Haul-lite tasks, all model adapters, full run.
- M4: writeup (taxonomy + 3 recommendations + PAI case study), blog post, static site, launch.

## Source material to pull from (PAI)

The author's PM-AI Hiring Index built real edge cases. Mine its transcripts and data for:
Messy World tasks (dedup-by-location, order-of-magnitude dashboard discrepancy, title taxonomy), the
a-01 vague-prompt task, the b-01 dedup task, the failure taxonomy, and the Long-Haul-hard case study.
Single transcript pass: tag each moment with a taxonomy tag, a Clarify tag, or a Drift tag. Keep tasks
reproducible from a clean clone — extract the pattern and data, never depend on the live PAI repo.

## Guardrails

- Don't build a hosted submission pipeline in v1. Static site from your own runs only.
- Don't let Long-Haul-lite drift into Long-Haul-hard.
- Round every displayed number. Log every transcript. Pin model versions.
- State the harness-neutrality caveat plainly in the writeup; it's a feature, not a weakness.
