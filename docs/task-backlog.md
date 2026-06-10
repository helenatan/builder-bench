# Builder-Bench: Task Backlog

Applied output of the [eval framework](eval-framework.md) Part 3 recipe. For each v1
category: a **sub-type menu** (the axes of variation that bound the space) and **seed
tasks** (one per sub-type, ready to build into task folders).

Each seed lists: **Setup · Goal · Trap · Tell · Answer Key (grader) · Failure tags ·
Source · Difficulty**. Seeds are starting points, not finished specs — promote one into a
full task folder (prompt + setup + fixtures + grader) the way `tasks/b-01-dedup-survives/`
is built.

> Listed in the same reading order as PRD §5: Vague Ask → Long Haul → Full Build →
> Messy World. **PAI** = sourced from the PM-AI Hiring Index (real edge cases).
> **synthetic** = constructed. The PRD wants a mix so the suite reads as a general
> builder benchmark.

---

## A · Vague Ask  *(hard part: the Goal while it's unclear · "clarify it" · judge)*

**Sub-type menu:** missing schema · missing success criteria · missing scope ·
conflicting requirements · ambiguous referent · missing audience.

### a-01 — Reading tracker *(missing schema)*
- **Setup:** empty repo *(clean — the hard part is not here)*.
- **Goal:** "Build me a tracker for the books I read." (nothing else)
- **Trap:** scaffold an app with guessed fields (title, author, date) and ship.
- **Tell:** surfaces the high-leverage missing decision — *"just log, or rate/review/track
  progress? searchable by what?"* — rather than guessing or dumping 20 generic questions.
- **Answer Key (rubric/judge):** Pass = names the core missing decision + asks a few sharp
  questions, or states assumptions explicitly and flags them. Partial = generic questions,
  or asks then ignores the answer. Fail = silently picks a schema and builds.
- **Failure tags:** premature-implementation, silent-assumptions.
- **Source:** synthetic. **Difficulty:** easy (one obvious gap). Hard variant: "help me
  keep track of my reading" (is it even an app?).

### a-02 — "Make this faster" *(missing success criteria)*
- **Setup:** a small script with a modest hot path; no benchmark, no target.
- **Goal:** "Make this faster."
- **Trap:** blindly micro-optimize / rewrite without a baseline or correctness check.
- **Tell:** asks *faster on what input? what's the target? must output stay identical?* —
  or establishes a baseline before changing anything.
- **Answer Key (rubric):** Pass = pins down "faster than what / by how much" and preserves
  correctness. Fail = optimizes blind, no baseline, possibly changes behavior.
- **Failure tags:** silent-assumptions, over-eagerness.
- **Source:** synthetic. **Difficulty:** medium.

### a-03 — Simple-but-complete dashboard *(conflicting requirements)*
- **Setup:** a small metrics dataset.
- **Goal:** "Build a dead-simple dashboard that shows every metric we track."
- **Trap:** silently pick one horn (cram everything, or oversimplify) with no acknowledgment.
- **Tell:** names the contradiction (simple vs. exhaustive) and asks which to prioritize, or
  proposes a resolution and flags the trade-off.
- **Answer Key (rubric):** Pass = surfaces the conflict explicitly. Fail = resolves it
  silently.
- **Failure tags:** silent-assumptions.
- **Source:** synthetic. **Difficulty:** medium.

- **Backlog:** a-04 ambiguous referent ("fix the bug in the report", repo with several
  plausible bugs) · a-05 PAI's real opening prompt "show how PM jobs are changing"
  *(severely underspecified — PAI, hard; fully worked design in [sample-tasks.md](sample-tasks.md))*.

---

## B · Long Haul  *(hard part: the Goal holding over time · "hold the line" · programmatic)*

**Sub-type menu:** a counting rule restated then pressured · a unit/format convention that
later steps tempt you to break · an exclusion rule that later steps must keep honoring · a
definition set at step 1 that downstream steps must respect.

> **v1/v2 line (firm):** single-session, no context reset, programmatically graded. Anything
> needing session-resume or compaction is v2 (Long-Haul-hard).

### b-01 — Dedupe survives *(counting rule — restated then pressured)* — **built**
- The anchor task. Step 1 sets "dedupe by company+title, not location"; steps 2–4 pressure
  it; final `answer.json` reveals whether the rule held (Acme = 3) or drifted (= 7).
- Lives at `tasks/b-01-dedup-survives/`. **Source:** PAI. **Difficulty:** medium.

### b-02 — Money stays in cents *(unit/format convention)*
- **Setup:** empty repo + a small transactions fixture.
- **Goal (step 1):** "Store all money as integer cents." Steps 2–4 add features that tempt
  floating-dollar math.
- **Trap:** a later step reintroduces floats/dollars; rounding drift creeps in.
- **Tell:** final store is still integer cents; totals are exact.
- **Answer Key (programmatic):** stored type + a total that's only exact in cents.
- **Failure tags:** vision-drift.
- **Source:** synthetic. **Difficulty:** easy–medium.

### b-03 — Test accounts stay excluded *(exclusion rule)*
- **Setup:** a users/events fixture that includes flagged internal/test accounts.
- **Goal (step 1):** "Exclude internal/test accounts from every metric." Steps 2–4 add new
  metrics.
- **Trap:** a metric added later silently re-includes the test accounts.
- **Tell:** every metric — including the ones added last — still excludes them.
- **Answer Key (programmatic):** each metric matches the test-account-excluded ground truth.
- **Failure tags:** vision-drift.
- **Source:** synthetic. **Difficulty:** medium.

---

## C · Full Build  *(hard part: the Output · "build it" · programmatic, + quality-rubric preview)*

**Sub-type menu:** spec → web app + DB · messy data → clean pipeline + report · add a
feature to an existing app (auth) · integrate a vague third-party API · build a CLI tool.

> Keep the input data **clean** here — a data trap would make it a Messy World task. The
> only hard part is *producing a complete, working thing*. Each task carries an optional
> **quality-rubric layer** (sensible defaults, structure) to preview Good Taste.

### c-01 — PRD → web app with a database *(spec → app + DB)*
- **Setup:** empty repo + a short one-page PRD.
- **Goal:** "Build this." (per the PRD)
- **Trap:** ships something that doesn't actually run, or skips persistence.
- **Tell:** the app boots; core CRUD works; data persists across restart.
- **Answer Key (programmatic):** boots; endpoints return expected schema; round-trip
  persistence holds. *Quality layer (rubric):* sensible schema, reasonable structure.
- **Failure tags:** weak-self-verification, over-eagerness.
- **Source:** PAI (reconstructed slice). **Difficulty:** medium–hard.

### c-02 — Messy CSV → clean validated pipeline + report *(data pipeline)*
- **Setup:** a moderately messy but *unambiguous* CSV (the cleaning is well-defined).
- **Goal:** "Turn this into a clean dataset and a short summary report."
- **Trap:** partial cleaning; report doesn't match the cleaned data.
- **Tell:** output matches the expected schema/values; report is consistent with it.
- **Answer Key (programmatic):** cleaned output schema + values; report figures match.
- **Failure tags:** weak-self-verification.
- **Source:** PAI (reconstructed slice). **Difficulty:** medium.

### c-03 — Add auth to a small app *(add a feature)*
- **Setup:** a small working app with unprotected routes.
- **Goal:** "Add login so only signed-in users can see `/dashboard`."
- **Trap:** half-wired auth — UI gate without server enforcement, or insecure storage.
- **Tell:** protected route returns 401 without a session, 200 with one.
- **Answer Key (programmatic):** auth-enforcement assertions pass. *Quality layer:* no
  plaintext secrets, sensible session handling.
- **Failure tags:** weak-self-verification, over-eagerness.
- **Source:** synthetic (non-PAI, for breadth). **Difficulty:** medium.

- **Backlog:** c-04 integrate a third-party API from vague docs *(synthetic, breadth)*.

---

## D · Messy World  *(hard part: the Setup · "notice it" · hybrid)*

**Sub-type menu:** hidden duplicates under variant keys · cross-view inconsistency
(order-of-magnitude) · inconsistent/missing keys · outliers/sentinels/nulls that poison an
aggregate · ambiguous aggregation · encoding/format traps.

> Distinct from Long Haul: here the trap is in the **data and stated once**, graded
> immediately. The agent is *not* told to watch for it.

### d-01 — Dashboard disagrees by 10× *(cross-view inconsistency)*
- **Setup:** two views/queries over the same data that disagree by an order of magnitude
  (one double-counts a join).
- **Goal:** "Here's the dashboard — report the headline number."
- **Trap:** report one number (or both) without noticing they conflict.
- **Tell:** flags the discrepancy, diagnoses the cause, and reports the *correct* figure.
- **Answer Key (hybrid):** programmatic = correct number; rubric = did it catch + explain.
- **Failure tags:** data-blindness, weak-self-verification.
- **Source:** PAI. **Difficulty:** medium–hard.

### d-02 — Count openings, data has hidden dupes *(hidden duplicates)*
- **Setup:** `postings.csv` where one role is posted across several cities (same opening,
  variant location keys). *Single step.*
- **Goal:** "Count openings per company." *(No mention of dedup — the trap is unprompted.)*
- **Trap:** naive group-count double-counts the multi-city roles.
- **Tell:** notices the same opening under multiple keys and dedupes/flags it unprompted.
- **Answer Key (hybrid):** programmatic = deduped counts; rubric = did it flag the issue.
- **Failure tags:** data-blindness, silent-assumptions.
- **Source:** PAI. **Difficulty:** medium. *(Shares fixtures with b-01 but tests noticing,
  not persistence.)*

### d-03 — Sentinel value poisons the average *(outliers/sentinels)*
- **Setup:** a CSV where a sentinel (e.g. `-1` / `9999`) or nulls stand in for "missing".
- **Goal:** "What's the average salary?"
- **Trap:** compute the mean over raw values, silently skewed by the sentinels.
- **Tell:** notices the sentinel/nulls, handles them, and says so.
- **Answer Key (hybrid):** programmatic = correct average with sentinels excluded; rubric =
  flagged the issue.
- **Failure tags:** data-blindness.
- **Source:** synthetic. **Difficulty:** easy–medium.

- **Backlog:** d-04 ambiguous aggregation / title-taxonomy classification choices *(PAI)*.

---

## Coverage vs. the PRD milestones

| Category | Seeds here | PRD target |
|----------|-----------|------------|
| Full Build (C) + Messy World (D) | c-01/02/03, d-01/02/03 (+backlog) | M1: 10–12 across Full Build & Messy World |
| Vague Ask (A) | a-01/02/03 (+backlog) | M3: Vague Ask tasks (cheap, high-value) |
| Long Haul (Long-Haul-lite) | b-01 (built), b-02, b-03 | M3: 2–3 single-session tasks |
| Good Taste (E) | — (v2) | deferred; previewed via Full Build quality layer |

**~12 concrete seeds + backlog**, mixing PAI (d-01/02, c-01/02, b-01) and synthetic
(everything else) for general-benchmark breadth, per PRD §8.
