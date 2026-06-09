# Contributing to Builder-Bench

Thanks for helping build a benchmark for how non-engineers actually use coding agents.
Governance is intentionally lightweight in v1: GitHub PR flow, benevolent-dictator review
(the author reviews all PRs), **DCO sign-off (not a CLA)**.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying you wrote the change (or have the right to submit
it) under the project's licenses. Add a sign-off line with `git commit -s`:

```
Signed-off-by: Your Name <you@example.com>
```

## How to contribute a task

A good Builder-Bench task is **realistic, self-contained, reproducible from a clean clone, and
produces clear signal** (not trivially passed by every model, not impossible for all).

1. Copy the schema below into `tasks/<id>-<slug>/`. Use the next free id in your category
   (`a-` Vague Ask, `b-` Long Haul, `c-` Full Build, `d-` Messy World, `e-` Good Taste).
2. Write a **reference solution / expected output** (`reference.md`, optionally
   `expected/`). This is hidden from the agent.
3. Make the grade **programmatic where possible**. Only Vague Ask and the subjective part of
   Messy World should need the LLM judge; everything else should be a deterministic check.
4. **Pilot it on ≥1 model** and confirm it produces signal (some models pass, some fail, or it
   cleanly isolates one behavior). Include the pilot result in your PR description.
5. Ensure it runs from a clean clone in the sandbox — no dependency on private data, no network
   unless the task explicitly provides it, no reliance on any external repo.

### Task folder schema

```
tasks/<id>-<slug>/
  prompt.md  OR  prompt_step1.md ... prompt_stepN.md   # exactly what the agent sees
  setup.sh           # builds the fixed starting state (asserts fixtures, installs deps, etc.)
  fixtures/          # data/files the task needs (keep them small + hand-verifiable)
  success.yaml       # id, category, mode, ordered steps, pass_threshold, possible failure tags
  grader.py          # prints {score, passed, failure_tags, details} JSON; recompute truth itself
  reference.md       # expected output / known-good answer — HIDDEN from the agent
  expected/          # (optional) machine-readable ground truth used by grader.py
```

### `success.yaml`

```yaml
id: x-01
category: A | B | C | D | E
name: "..."
needs_judge: false        # true only for A (Vague Ask) / subjective D (Messy World)
mode: single | multi_step
steps: [prompt_step1.md, ...]   # omit for single prompt.md
grader: grader.py
pass_threshold: 1.0
failure_tags_possible: [vision-drift, silent-assumptions, ...]
```

### Grader contract

`grader.py` is invoked as `python grader.py <grade_input.json>` with the task dir as cwd. The
input bundle contains `{task_id, task_dir, workdir, transcript, final_text, attempt_dir}`. The
grader must **recompute ground truth itself** (don't trust agent-reported numbers) and print a
single JSON object to stdout:

```json
{"score": 0.0, "passed": false, "failure_tags": ["vision-drift"], "details": "..."}
```

Use the shared taxonomy for `failure_tags`: `premature-implementation`, `vision-drift`,
`silent-assumptions`, `weak-self-verification`, `data-blindness`, `over-eagerness`.

## Code contributions

- Keep the harness **neutral**: anything that helps one provider must help all. Provider
  specifics belong in `harness/adapters/<provider>.py` behind the `ModelAdapter` contract.
- Match the surrounding style; no new heavy dependencies without discussion.
- Run the existing task end to end (`python -m harness.runner --task b-01 --model haiku`)
  before opening a PR touching the harness.

## What not to submit

- Tasks that need the full PM-AI Hiring Index repo, private credentials, or live external state.
- Tasks requiring session resume / context reset (that's the deferred v2 "Long-Haul-hard" track).
- Anything that embeds the contamination canary GUID outside `DATASET_LICENSE`.
