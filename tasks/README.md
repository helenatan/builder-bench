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

## Folder layout (example: `b-01-dedup-survives/`)

```
b-01-dedup-survives/
  success.yaml        # manifest — the single source of truth
  setup.sh            # Setup: prepares the starting workdir
  fixtures/           # Setup: input data the agent sees
  prompt_step1.md     # Goal: shown to the agent, in order, for a multi-step task
  prompt_step2.md
  ...
  grader.py           # Answer Key: prints a JSON score object on stdout (recomputes truth from fixtures)
```

### Disclosure & the private split

The site publishes every task's **full teardown** — answer key, trap, failure narratives,
transcripts — by design: this benchmark is built to be understood, and readers should see what
correctness looks like. Be clear-eyed about what that means, in two threat models:

1. **Runtime leakage** (the agent under test finding the key in its environment): solved by the
   `private/` split below — gitignored, excluded from the deploy — plus the sandbox workdir
   being isolated from the repo.
2. **Training contamination** (a future model having read the public tasks): accepted, and not
   solvable for an open benchmark. Published tasks are treated as **burned** for future-model
   evaluation the moment they go public. Exclusion is best-effort at the crawler layer
   (robots.txt blocks training crawlers, `X-Robots-Tag: noai` on every response, a "do not
   train" notice and canary GUID in `DATASET_LICENSE`) — all of which are requests, not
   controls. The canary is the detection instrument if a request is ignored. Results are a
   snapshot of the models current at run time.

   > This repo is public, so the tasks are readable from source as well as from the site.
   > That's a deliberate trade: auditability over shelf life. A benchmark nobody can inspect
   > can't be trusted, and one whose tasks are secret can't be contributed to. The mitigation
   > for decay is refreshing the suite, not hiding it — see `docs/v2-plan.md`.

The held-out files (runtime-leakage protection + grading integrity, not site secrecy):

```
private/expected/<id>/...   private/reference/<id>.md   private/rubrics/<id>.md
```

The grader (`grader.py`) stays public — it is code that recomputes ground truth from the public
`fixtures/`, and only *cross-checks* against `private/expected/` when that key is present (see
`private/README.md`). To run the suite, restore `private/` at the repo root.

## `success.yaml` fields

| Field | Meaning |
|-------|---------|
| `id` | task id, `<letter><nn>` (e.g. `b-01`); the letter is the category code |
| `category` | A–E stable code — A Vague Ask · B Long Haul · C Full Build · D Messy World · E Good Taste |
| `name` | human-readable title |
| `derived_from` | provenance (e.g. a PAI / PM-AI Hiring Index edge case — see [PRD §8](../docs/PRD.md#8-leveraging-pm-ai-hiring-index-pai-as-source-material)) — optional |
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

- Folder: `<id>-<slug>` → `b-01-dedup-survives`
- Id: `<letter><nn>` → the letter is the stable category code, `nn` a sequence within it.
- Keep the letter even though categories now have names (Long Haul = B); the codes are
  stable IDs that task paths, results, and the leaderboard depend on.

## The grader contract

`grader.py` is invoked as `python grader.py <grade_input.json>` with the **task dir** as cwd;
the input bundle carries the paths it needs (`{workdir, transcript, final_text, ...}`). It
**prints one JSON object on stdout**:

```json
{ "score": 0.0, "failure_tags": ["vision-drift"], "details": "Acme reported as 7" }
```

- `score` is a float in `[0,1]` (partial credit allowed).
- The runner recomputes `passed = score >= pass_threshold`; anything the grader prints for
  it is overwritten.
- A missing grader, a crash, or unparseable output is scored `0.0` with a diagnostic tag.
- For `needs_judge: true`, the programmatic grader handles the objective part and the LLM
  judge scores the subjective rubric; see `judge/` and PRD §6.

## Running a task

```
builder-bench --task b-01 --model haiku --attempts 3
```

Outputs land in `results/runs/<task-id>/<model>/<timestamp>/attempt-N/`, with the full
transcript logged per run. pass@1 / pass@3 are computed from the attempts.

### Task versioning — editing a task invalidates its old runs

Every run is stamped with a fingerprint of the task folder it executed (`task_version`, from
`harness/taskhash.py`). If you edit a task's prompt, fixtures, grader, or setup, old runs stop
being valid runs of that task: the leaderboard build drops their rows with a warning, and the
judge-validation collector skips their transcripts. Audit at any time with:

```
python -m harness.taskhash        # fresh / STALE / legacy per logged run
```

Stale runs should be moved to `results/archive/` and the task re-run. (Editing only the
private rubric does *not* stale runs — it invalidates judge labels; re-judge with
`python -m judge.validation.validate collect`.)

## Authoring checklist

Every task should have a **trap** (the tempting wrong move) and a **tell** (the observable
pass/fail signal), ship a reference solution, and be **piloted on ≥1 model** to confirm it
produces signal. The design recipe and the seed backlog:

- [`docs/eval-framework.md`](../docs/eval-framework.md) — Part 3, how to design a test case
- [`docs/task-backlog.md`](../docs/task-backlog.md) — sub-type menus + seed tasks per category
