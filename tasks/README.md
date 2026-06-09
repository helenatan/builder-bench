# Builder-Bench Tasks

A **task** is the reusable, model-independent unit of evaluation. Each task is one folder.
This README is the contributor schema.

## What a task is (and isn't)

A task freezes three of the six [framework](../docs/eval-framework.md) parts so any model
can be run against it:

| Framework part | In the task | Where |
|----------------|-------------|-------|
| **Setup** — the world the agent starts in | ✅ | `setup.sh` + `fixtures/` |
| **Goal** — what it's asked to do | ✅ | `prompt_step*.md` (or a single `prompt.md`) |
| **Answer Key** — what counts as correct + how we check | ✅ | `grader.py` + `expected/` + `reference.md` |
| **Contestant** — the model under test | ❌ | supplied at run time (`--model`) |
| **Output** — what the agent produced | ❌ | produced per run into the workdir |
| **Scorecard** — the aggregate verdict | ❌ | rolled up across runs |

So a task is the **question + answer key + environment**, frozen. One task → many **runs**.
Labels for judge validation come from *runs*, not tasks (see PRD §6).

## Folder layout (example: `d-01-dedup-survives/`)

```
d-01-dedup-survives/
  success.yaml        # manifest — the single source of truth
  setup.sh            # Setup: prepares the starting workdir
  fixtures/           # Setup: input data the agent sees
  prompt_step1.md     # Goal: shown to the agent, in order, for a multi-step task
  prompt_step2.md
  ...
  expected/           # Answer Key: ground-truth values the grader compares against
  grader.py           # Answer Key: prints a JSON score object on stdout
  reference.md        # Answer Key: hidden solution + failure signatures (never shown to the agent)
```

## `success.yaml` fields

| Field | Meaning |
|-------|---------|
| `id` | task id, `<letter><nn>` (e.g. `d-01`); the letter is the category code |
| `category` | A–E stable code — A Full Build · B Messy World · C Vague Ask · D Long Haul · E Good Taste |
| `name` | human-readable title |
| `derived_from` | provenance (e.g. a PAI edge case) — optional |
| `needs_judge` | `false` = programmatic only; `true` = hybrid (also routes to the LLM judge) |
| `mode` | descriptive label (`single` / `multi_step`); not load-bearing — see prompt resolution below |
| `steps` | ordered list of prompt files; the agent sees them one at a time in one continuous session |
| `grader` | grader script name (default `grader.py`) |
| `pass_threshold` | score (in `[0,1]`) at/above which a run counts as a pass; defaults to `1.0` |
| `failure_tags_possible` | taxonomy tags this task is designed to surface on failure (PRD §7) |
| `system_prompt` | optional system prompt for the session |

**Prompt resolution (what the runner actually loads):** if `steps` is present, those files
are used in order; otherwise it globs `prompt_step*.md` (sorted); otherwise it falls back to
a single `prompt.md`. `mode` is documentation, not logic.

## Naming & id convention

- Folder: `<id>-<slug>` → `d-01-dedup-survives`
- Id: `<letter><nn>` → the letter is the stable category code, `nn` a sequence within it.
- Keep the letter even though categories now have names (Long Haul = D); the codes are
  stable IDs that task paths, results, and the leaderboard depend on.

## The grader contract

`grader.py` runs in the agent's finished workdir and **prints one JSON object on stdout**:

```json
{ "score": 0.0, "failure_tags": ["vision-drift"], "details": "Acme reported as 7" }
```

- `score` is a float in `[0,1]` (partial credit allowed).
- The runner derives `passed = score >= pass_threshold` — graders don't set it.
- A missing grader, a crash, or unparseable output is scored `0.0` with a diagnostic tag.
- For `needs_judge: true`, the programmatic grader handles the objective part and the LLM
  judge scores the subjective rubric; see `judge/` and PRD §6.

## Running a task

```
builder-bench --task d-01 --model haiku --attempts 3
```

Outputs land in `results/runs/<task-id>/<model>/<timestamp>/attempt-N/`, with the full
transcript logged per run. pass@1 / pass@3 are computed from the attempts.

## Authoring checklist

Every task should have a **trap** (the tempting wrong move) and a **tell** (the observable
pass/fail signal), ship a reference solution, and be **piloted on ≥1 model** to confirm it
produces signal. The design recipe and the seed backlog:

- [`docs/eval-framework.md`](../docs/eval-framework.md) — Part 3, how to design a test case
- [`docs/task-backlog.md`](../docs/task-backlog.md) — sub-type menus + seed tasks per category
