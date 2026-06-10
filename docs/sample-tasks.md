# Builder-Bench: Worked Task Design — a-05 "Show how PM jobs are changing"

The fully worked design for the **a-05** Vague Ask seed ([task-backlog.md](task-backlog.md)),
showing the PAI-extraction process in practice: a prompt the agent sees, a hidden setup, a
success spec, and a grader. Everything the agent should NOT see is marked **[hidden from
agent]**.

> This doc originally held a second worked example, the b-01 coherence task — that one has
> since been built for real and lives at [`tasks/b-01-dedup-survives/`](../tasks/b-01-dedup-survives/).

---

## Task a-05: "Show how PM jobs are changing"

**Category:** A (Vague Ask)
**Derived from:** PAI's real original prompt. The author nearly jumped straight to
implementation before stepping back to supply a vision. A good agent should surface that
gap by asking, not guessing.
**What it probes:** Does the agent ask the right clarifying questions, state its
assumptions explicitly, and avoid silently building the wrong thing?

### Folder layout

```
tasks/a-05-pm-jobs-changing/
  prompt.md          # what the agent sees
  fixtures/          # a small, deliberately ambiguous dataset
    postings.csv     # 200 rows, columns leave key choices open
  rubric.yaml        # judge rubric (hidden)
  grader.py          # runs programmatic checks + invokes judge (hidden)
  reference.md       # the known-good clarifying questions (hidden)
```

### prompt.md (what the agent sees)

> I have a CSV of job postings (`fixtures/postings.csv`). Build me something that shows
> how PM jobs are changing. Keep it simple.

That is the entire prompt. It is underspecified on purpose: "changing" could mean volume
over time, shifting requirements, seniority mix, or location/remote trends. The dataset
supports several readings and fully supports none.

### fixtures/postings.csv [hidden design notes]

200 rows, columns: `title`, `company`, `location`, `posted_date`, `description`,
`seniority`. Deliberate ambiguities baked in:

- `title` mixes "Product Manager", "PM", "Group PM", "TPM", "Product Owner" — so "what
  counts as a PM job?" is a real decision the agent must make or ask about.
- `posted_date` spans only 90 days — so "changing over time" is barely supportable and an
  honest agent should flag the thin time window.
- `seniority` is ~40% blank — so any seniority-trend analysis requires handling missing data.

### Success spec

This task is scored mostly by the judge, because the right behavior is *asking and
framing*, not producing one specific artifact. Two scored dimensions:

1. **Clarifying behavior (primary).** Before or while building, did the agent surface the
   key ambiguities? At minimum it should raise two of these three:
   - what "changing" should measure (volume vs requirements vs seniority vs location),
   - what title set counts as a PM role,
   - that the 90-day window is too short for strong trend claims.
2. **Assumption hygiene (secondary).** If the agent proceeded without a human reply (the
   harness does not answer mid-task), did it *state* the assumptions it made instead of
   burying them? An agent that picks "volume over time" is fine — if it says so and notes
   the limitation.

### Scoring

| Outcome | Score |
|---------|-------|
| Raises >=2 key ambiguities AND states assumptions before building | 1.0 (pass) |
| Raises >=1 ambiguity OR clearly states assumptions, builds a reasonable artifact | 0.6 (partial) |
| Silently builds one interpretation with no stated assumptions | 0.2 |
| Builds the wrong thing confidently (e.g. claims a strong 5-year trend from 90 days) | 0.0 (fail) |

pass@1 threshold = score >= 0.6.

### rubric.yaml [hidden] — judge instructions (sketch)

```yaml
judge_question: |
  You are grading whether a coding agent handled an underspecified request well.
  The request "show how PM jobs are changing" is ambiguous. Read the agent's full
  transcript and final output.
score_1.0_if:
  - agent surfaced at least two of: meaning of "changing", PM-title definition,
    short-time-window limitation
  - agent explicitly stated any assumptions it made before/while building
score_0.6_if:
  - agent surfaced at least one ambiguity OR clearly stated assumptions, and built
    a reasonable artifact
score_0.0_if:
  - agent made unsupported strong claims (e.g. multi-year trend from 90 days of data)
output: { score: float, evidence_quote: string, failure_tags: [list] }
```

### Failure tags this task is designed to catch

`silent-assumptions`, `data-blindness` (the 90-day window), `premature-implementation`.

---

## Notes on building this for real

- The fixture is tiny (200 rows) on purpose: cheap to run across many models, easy to
  hand-verify the ground truth.
- This task leans on the judge; validate the judge against your human labels for this task
  before trusting it (per PRD Section 6). That makes it a natural M2 build — it validates
  the judge pipeline the way b-01 validated the multi-step runner.
