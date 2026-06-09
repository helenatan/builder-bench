# Builder-Bench: Sample Tasks (A Vague Ask and B Long Haul)

Two fully-specified example tasks derived from PM-AI Hiring Index (PAI), showing the
extraction in practice. Each follows the task-folder schema from the PRD: a prompt the
agent sees, a hidden setup, a success spec, and a grader. Everything the agent should
NOT see is marked **[hidden from agent]**.

---

## Task a-01: "Show how PM jobs are changing"

**Category:** A (Vague Ask)
**Derived from:** PAI's real original prompt. The author nearly jumped straight to
implementation before stepping back to supply a vision. A good agent should surface that
gap by asking, not guessing.
**What it probes:** Does the agent ask the right clarifying questions, state its
assumptions explicitly, and avoid silently building the wrong thing?

### Folder layout

```
tasks/a-01-pm-jobs-changing/
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

## Task b-01: "Dedupe by company, not by location"

**Category:** B (Long Haul / long-horizon coherence)
**Derived from:** PAI's real dedup decision. The same opening posted in five cities was
initially counted five times; the author chose to dedupe by company+title, not by
location. The author also lived the core D problem: across many fragmented sessions, early
decisions got lost on resume. This task checks whether a single, clearly-stated early
requirement survives several later steps.
**What it probes:** Requirement drift. Does an instruction given once at step 1 still hold
after the agent has done three more rounds of unrelated-feeling work?

### Folder layout

```
tasks/b-01-dedup-survives/
  prompt_step1.md ... prompt_step4.md   # the agent sees these one at a time
  fixtures/
    postings.csv     # contains known multi-location duplicates
  expected/
    unique_count.json  # ground-truth unique count under the company+title rule (hidden)
  grader.py          # checks the final artifact against the rule (hidden)
```

### The step sequence (the agent sees each prompt in order, in one continuous session)

**Step 1 (the requirement is stated ONCE here):**
> Load `fixtures/postings.csv`. Important: the same role is often posted in multiple
> cities. Treat one role as one opening — dedupe by company + title, NOT by location.
> Build a small table of unique openings per company.

**Step 2 (unrelated-feeling work):**
> Now add a column showing each company's most common posting location.

**Step 3 (a tempting trap):**
> Add a "total postings" metric to the dashboard so we can see overall volume.

> [hidden design note] This is the drift trap. A coherent agent keeps "unique openings"
> (deduped) distinct from "total postings" (raw rows) and does not silently revert the
> dataset to one-row-per-location, which would re-inflate every earlier number.

**Step 4 (the coherence check):**
> Give me the final count of unique openings for company "Acme Corp".

### fixtures/postings.csv [hidden design notes]

Acme Corp has one real role ("Senior PM") posted in 5 cities, plus 2 genuinely distinct
roles. Ground-truth unique count for Acme = **3**. Several other companies have similar
multi-location duplicates so the rule matters throughout, not just for Acme.

### expected/unique_count.json [hidden]

```json
{ "Acme Corp": 3, "_rule": "dedupe by company+title, ignore location" }
```

### Success spec

Programmatic, no judge needed for the primary check:

1. **Coherence (primary).** Final answer at Step 4 must equal the deduped count (Acme = 3).
   If the agent reports 7 (raw rows) or any location-inflated number, the early requirement
   was lost — fail.
2. **No silent reversion (secondary).** When Step 3 adds "total postings", the unique-
   openings figures from Step 1–2 must remain deduped in the final artifact. The grader
   re-reads the final table and confirms unique counts did not silently change.

### Scoring

| Outcome | Score |
|---------|-------|
| Step 4 answer = 3 AND earlier unique counts unchanged after Step 3 | 1.0 (pass) |
| Step 4 answer = 3 BUT a unique count drifted somewhere after Step 3 | 0.5 |
| Step 4 answer reflects location-inflated count (e.g. 7) | 0.0 (fail) |

pass@1 threshold = score = 1.0 (coherence is binary here).

### grader.py [hidden] — logic (sketch)

```python
final_answer = parse_step4_answer(transcript)          # the number the agent reported
final_table  = load_final_artifact(workdir)            # unique-openings table at the end
assert_rule  = load("expected/unique_count.json")

score = 0.0
if final_answer == assert_rule["Acme Corp"]:           # 3
    score = 1.0
    # secondary: did any earlier unique count silently inflate after step 3?
    if any_unique_count_reverted_to_per_location(final_table):
        score = 0.5
tags = [] if score == 1.0 else ["vision-drift", "silent-assumptions"]
```

### Why this is a valid D task even in v1

It is fully automatable (the check is a number), it is short (4 steps, one session), and it
isolates exactly one early requirement so a failure cleanly means "the model lost a stated
constraint." The harder, multi-session-with-context-reset version of this same idea is the
v2 expansion noted in the PRD; this v1 version still produces a real coherence signal now.

### Failure tags this task is designed to catch

`vision-drift`, `silent-assumptions`, `data-blindness`.

---

## Notes on building these for real

- Both fixtures are tiny (200 rows) on purpose: cheap to run across many models, easy to
  hand-verify the ground truth.
- a-01 leans on the judge; validate the judge against your human labels for this task
  before trusting it (per PRD Section 6).
- b-01 needs no judge, which makes it a great early task to build first — it proves the
  multi-step runner works end to end with a clean programmatic grade.
- Suggested build order: b-01 first (validates the runner + grading), then a-01 (validates
  the judge pipeline).
