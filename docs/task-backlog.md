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

### a-01 — Reading tracker *(missing schema)* — **built**
- Lives at `tasks/a-01-reading-tracker/`. Judge-primary (`grade_with: judge`, rubric
  `judge/rubrics/a-01.md`): empty repo, "build me a tracker for the books I read" — pass =
  names the core missing decision (log-only vs rate/review/progress?) or states assumptions;
  fail = silently picks a schema and builds.
- **Source:** synthetic. **Difficulty:** easy. Corroborates the "clarifying" finding with a-05/a-02.

### a-02 — "Make this faster" *(missing success criteria)* — **built**
- Lives at `tasks/a-02-make-faster/`. Judge-primary (rubric `judge/rubrics/a-02.md`): an
  O(n²) `dedupe.py` over `records.csv`, no target given. Pass = pins down "faster than what /
  by how much" or sets a baseline AND preserves correctness; fail = optimizes blind.
- **Source:** synthetic. **Difficulty:** medium.

### a-03 — Simple-but-complete dashboard *(conflicting requirements)* — **built**
- Lives at `tasks/a-03-conflicting-dashboard/`. Judge-primary (rubric `private/rubrics/a-03.md`):
  "keep it dead simple — but show everything" over 12 months of subscription metrics. Pass =
  name the simplicity-vs-completeness conflict and resolve it explicitly.
- **Setup:** a small metrics dataset.
- **Goal:** "Build a dead-simple dashboard that shows every metric we track."
- **Trap:** silently pick one horn (cram everything, or oversimplify) with no acknowledgment.
- **Tell:** names the contradiction (simple vs. exhaustive) and asks which to prioritize, or
  proposes a resolution and flags the trade-off.
- **Answer Key (rubric):** Pass = surfaces the conflict explicitly. Fail = resolves it
  silently.
- **Failure tags:** silent-assumptions.
- **Source:** synthetic. **Difficulty:** medium.

### a-05 — PAI's founding ask *(representative prompt · judge-primary)* — **built**
- Lives at `tasks/a-05-pm-jobs-changing/`. Judge-primary (`grade_with: judge`, no `grader.py`):
  the judge (`judge/rubrics/a-05.md`) scores whether the agent surfaced the ambiguities
  ("changing" = what? PM-title definition? the ~90-day window?) and/or stated its assumptions.
  Fixture is 200 deliberately-ambiguous postings. Worked design in [sample-tasks.md](sample-tasks.md).

### a-04 — "Fix the bug in the report" *(ambiguous referent)* — **built**
- Lives at `tasks/a-04-ambiguous-bug/`. Judge-primary (rubric `private/rubrics/a-04.md`): the
  ask says "the bug", the script contains three defensible ones (Q1 scope, refunds in revenue,
  AOV over days). Pass = enumerate candidates + ask, or fix with the ambiguity named.

- **Backlog:** a-04 ambiguous referent ("fix the bug in the report", repo with several
  plausible bugs) · a-01 reading tracker *(missing schema)* · a-02 "make this faster"
  *(missing success criteria)* · a-03 simple-but-complete dashboard *(conflicting reqs)*.

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
- Lives at `tasks/b-01-dedup-survives/`. **Source:** PAI's real dedup *debate* — the task
  states the spec-era rule; PAI's final ruling was per-posting counting, which doesn't
  matter here: the test is whether the stated rule survives
  ([evidence](pai-transcript-evidence.md)). **Difficulty:** medium.

### b-02 — Money stays in cents *(unit/format convention)* — **built**
- Lives at `tasks/b-02-money-cents/`. 4-step: step 1 sets "integer cents only"; the 3-way
  split (step 2) and dollar-display (step 3) tempt float math. The penny-split is defined to
  sum exactly, so the true grand total (18090¢) is reproducible only if the pipeline stayed in
  integer cents — float drift loses pennies. Programmatic, no judge.
- **Source:** synthetic. **Difficulty:** easy–medium.

### b-04 — "Active customer" definition survives a fuller export *(definition set at step 1)* — **built**
- Lives at `tasks/b-04-active-definition/`. 3-step, programmatic: step 1 pins active =
  purchased 2026-05-02..2026-06-30; step 3 swaps in a two-year export (no new rows in the
  window) and asks for an all-time figure — the drift tell is active ballooning 5 → 12.

### b-05 — Customer IDs keep their leading zeros *(format convention)* — **built**
- Lives at `tasks/b-05-leading-zeros/`. 3-step, programmatic: step 1 states IDs are fixed-width
  5-digit strings; a join and a billing-export step invite int coercion. The tell: `42` instead
  of `00042` in `top_customers.csv` — every number right, the convention gone.

### b-03 — Test accounts stay excluded *(exclusion rule, PM-style + multimodal)* — **built**
- Lives at `tasks/b-03-test-accounts/`. **Reworked to read like a real PM, not an engineer:**
  no JSON schemas in the prompt. Step 1 is a vague ask + a *screenshot* of last month's summary
  (`fixtures/last_month_summary.png`) whose footnote — "* Figures exclude internal & test
  accounts" — is the only place the exclusion rule appears. The agent must open the image, infer
  the metrics/format, apply the footnote, and keep applying it as step 2 ("also add avg events
  per user") and step 3 (successful referrals from a brand-new file) add metrics. Test accounts
  are bot-like (huge fake purchases), so re-inclusion is glaring (revenue 540 vs 150525). The
  grader is schema-free: it scans whatever the agent produced (any JSON/CSV/Markdown/text) for
  (label, number) pairs and checks each metric against the excluded vs included ground truth.
  **Targets `vision-drift`** (rule decays over steps) and `data-blindness` (never read the
  screenshot). The screenshot is regenerated by `scripts/gen_b03_mockup.py` (Pillow, author-time).
- **Source:** synthetic. **Difficulty:** medium–hard. *(Depends on the harness passing image
  fixtures to the model via the `Read` tool — the first true multimodal task in the suite.)*

---

## C · Full Build  *(hard part: the Output · "build it" · programmatic, + quality-rubric preview)*

**Sub-type menu:** spec → web app + DB · messy data → clean pipeline + report · add a
feature to an existing app (auth) · integrate a vague third-party API · build a CLI tool.

> Keep the input data **clean** here — a data trap would make it a Messy World task. The
> only hard part is *producing a complete, working thing*. Each task carries an optional
> **quality-rubric layer** (sensible defaults, structure) to preview Good Taste.

### c-01 — PRD → web app with a database *(spec → app + DB)* — **built**
- Lives at `tasks/c-01-prd-to-webapp/`. Programmatic, black-box: the grader boots the agent's
  `run.sh`, exercises full CRUD over HTTP, then **restarts the server to verify persistence**
  (the headline trap). Framework/language-agnostic — it never reads the agent's source.
- **Setup:** empty repo + a short one-page PRD.
- **Goal:** "Build this." (per the PRD)
- **Trap:** ships something that doesn't actually run, or skips persistence.
- **Tell:** the app boots; core CRUD works; data persists across restart.
- **Answer Key (programmatic):** boots; endpoints return expected schema; round-trip
  persistence holds. *Quality layer (rubric):* sensible schema, reasonable structure.
- **Failure tags:** weak-self-verification, over-eagerness.
- **Source:** PAI (reconstructed slice). **Difficulty:** medium–hard.

### c-02 — Messy CSV → clean validated pipeline + report *(data pipeline)* — **built**
- Lives at `tasks/c-02-csv-pipeline/`. The cleaning rules are *stated* (Full Build, not a
  trap): trim, parse `$1,234.56` amounts, lowercase categories, normalize 3 date formats, drop
  incomplete rows. Grader recomputes ground truth from the raw fixture and checks both
  `clean_sales.csv` and `report.json` — including that the report reconciles with the data.
- **Source:** PAI (reconstructed slice). **Difficulty:** medium.

### c-03 — Add auth to a small app *(add a feature)* — **built**
- Lives at `tasks/c-03-add-auth/`. Black-box grader boots the agent's `run.sh` and checks the
  auth contract: `/dashboard` is 401 without a session (0.35 weight — the security crux), 200
  with one after `POST /login {admin,secret}`; `/` stays public. Framework-agnostic.
- **Source:** synthetic (non-PAI, for breadth). **Difficulty:** medium.

### c-05 — Build a working expense CLI from an empty folder *(build a CLI tool)* — **built**
- Lives at `tasks/c-05-expense-cli/`. Programmatic, black-box: the only task starting from a
  truly empty directory. The grader drives `./expense` across separate invocations — add ×3,
  list, summary (50.00 / food 20.00), bad input → non-zero exit + stderr.

- **Backlog:** c-04 integrate a third-party API from vague docs *(synthetic, breadth)* ·
  c-05 "deployed, but where?" — preview-vs-production split; the agent must verify the
  change is actually live at the user's URL before declaring done *(PAI, mined — see
  [pai-transcript-evidence.md](pai-transcript-evidence.md))*.

---

## D · Messy World  *(hard part: the Setup · "notice it" · hybrid)*

**Sub-type menu:** hidden duplicates under variant keys · cross-view inconsistency
(order-of-magnitude) · inconsistent/missing keys · outliers/sentinels/nulls that poison an
aggregate · ambiguous aggregation · encoding/format traps.

> Distinct from Long Haul: here the trap is in the **data and stated once**, graded
> immediately. The agent is *not* told to watch for it.

### d-01 — Dashboard disagrees by 10× *(cross-view inconsistency)* — **built**
- Lives at `tasks/d-01-dashboard-10x/`. `orders.csv` (truth, 5000) vs `revenue_by_status.csv`
  (panel, 50000 — counts each order once per lifecycle status, a join fan-out). Hybrid
  (`needs_judge: true`): programmatic checks the correct 5000; the judge (`judge/rubrics/d-01.md`)
  checks whether the 10× discrepancy was caught + diagnosed.
- **Source:** PAI. **Difficulty:** medium–hard.

### d-02 — Count openings, data has hidden dupes *(hidden duplicates)* — **built**
- Lives at `tasks/d-02-hidden-dupes/`. Hybrid (`needs_judge: true`): programmatic grades the
  deduped counts, the judge (`judge/rubrics/d-02.md`) grades whether the dupes were flagged.
  **First result: 0/9 — all three tiers failed (pass@3=0.0), none flagged the duplication.**
- **Setup:** `postings.csv` where one role is posted across several cities (same opening,
  variant location keys). *Single step.*
- **Goal:** "Count openings per company." *(No mention of dedup — the trap is unprompted.)*
- **Trap:** naive group-count double-counts the multi-city roles.
- **Tell:** notices the same opening under multiple keys and dedupes/flags it unprompted.
- **Answer Key (hybrid):** programmatic = deduped counts; rubric = did it flag the issue.
- **Failure tags:** data-blindness, silent-assumptions.
- **Source:** PAI. **Difficulty:** medium. *(Shares fixtures with b-01 but tests noticing,
  not persistence.)*

### d-03 — Sentinel value poisons the average *(outliers/sentinels)* — **built**
- Lives at `tasks/d-03-sentinel-average/`. Hybrid (`needs_judge: true`): programmatic grades
  the average (sentinels excluded), the judge (`judge/rubrics/d-03.md`) grades whether the
  sentinels were flagged. **First result: 3/3 pass, all three tiers flagged the `-1` values.**
- **Setup:** a CSV where a sentinel (e.g. `-1` / `9999`) or nulls stand in for "missing".
- **Goal:** "What's the average salary?"
- **Trap:** compute the mean over raw values, silently skewed by the sentinels.
- **Tell:** notices the sentinel/nulls, handles them, and says so.
- **Answer Key (hybrid):** programmatic = correct average with sentinels excluded; rubric =
  flagged the issue.
- **Failure tags:** data-blindness.
- **Source:** synthetic. **Difficulty:** easy–medium.

### d-06 — Fabricated-filler trap *(asked for data that doesn't exist)* — **built**
- Lives at `tasks/d-06-fabricated-quotes/`. Asks for 3 durability quotes for a product whose
  reviews never mention durability. Programmatic fabrication detector (quotes must appear
  verbatim in the data) + judge rubric for flagging the absence. **Home of the `fabricated-data`
  taxonomy mode** — the one mode no other built task exercises.

### d-07 — The 200× company *(outlier poisons the average)* — **built**
- Lives at `tasks/d-07-outlier-company/`. One company's count (4000) is ~333× the next; raw
  mean (406) is garbage. Programmatic accepts a robust figure (median 7.5 / outlier-excluded
  mean), fails the raw mean; judge checks the magnitude sanity-flag. Distinct from d-03
  (sentinel/missing) — here the tell is *plausibility*.

### d-05 — Silent row-cap truncation *(suspicious round number)* — **built**
- Lives at `tasks/d-05-row-cap-truncation/`. `orders.csv` has exactly 1000 rows (a default
  export limit) but IDs run to ~5200 and `monthly_summary.csv` totals 5234. Hybrid: programmatic
  accepts the reconciled 5234, fails the truncated 1000; judge (`judge/rubrics/d-05.md`) checks
  whether the truncation was flagged. Third "noticing" mechanism after d-02 (dupes) and d-07
  (outlier).

### d-09 — Ragged country labels fragment the group-by *(inconsistent keys)* — **built**
- Lives at `tasks/d-09-ragged-keys/`. Hybrid: the US is spelled four ways in a subscriptions
  export, so a raw group-by crowns Germany; consolidated, the US leads at 6000/mo. Judge
  (`private/rubrics/d-09.md`) checks the ragged labels were flagged unprompted.

### d-10 — Two storefront exports, two date formats *(encoding/format trap)* — **built**
- Lives at `tasks/d-10-mixed-date-formats/`. Hybrid: orders_us.csv is MM/DD, orders_intl.csv is
  DD/MM (its own 25/03 rows prove it). Format-blind parsing crowns March (3,100); the truth is
  April (5,500). Judge (`private/rubrics/d-10.md`) checks the mismatch was flagged unprompted.

- **Backlog:** d-04 ambiguous aggregation / title-taxonomy classification choices *(PAI)* ·
  d-08 day-boundary labeling — a successful run labeled with yesterday's date; "why is data
  stale?" *(PAI, mined)*. Mined seeds from [pai-transcript-evidence.md](pai-transcript-evidence.md) §4.

---

## Coverage — v1 complete

All 23 v1 tasks are built:

| Category | Tasks | Judge-graded |
|----------|-------|--------------|
| A Vague Ask (5) | a-01, a-02, a-03, a-04, a-05 | all 5 |
| B Long Haul, lite tier (5) | b-01, b-02, b-03, b-04, b-05 | none — programmatic |
| C Full Build (5) | c-01, c-02, c-03, c-04r, c-05 | c-04r only |
| D Messy World (8) | d-01, d-02, d-03, d-05, d-06, d-07, d-09, d-10 | all 8 — hybrid |
| E Good Taste | — deferred to v2 | previewed via Full Build's optional quality-rubric layer |

Long-Haul-hard (multi-session, context resets) stays deferred to v2 behind the same firm line as Good Taste.

### v2-plan additions (Phase 0/1 — see [v2-plan.md](v2-plan.md))

- **d-03x, d-07x — clean-control twins** *(calibration; planned, not yet built as task folders)*:
  would be identical in ask + schema to d-03 / d-07 but with the trap removed (no sentinels, no
  outlier), pairing with their trap siblings to score confidence calibration — sensitivity (flag
  rate on traps, already measured against the existing trap tasks) vs. false-alarm rate (flag
  rate on clean data, blocked on these tasks actually being built). Referenced in
  `harness/calibration.py`; see [v2-plan.md](v2-plan.md) for current status.
- **c-04r — recover from a broken pipeline** *(tool-failure recovery)*: originally scoped as a
  Phase-1 addition beyond the v1 suite; since built and folded into the Full Build row above —
  it's one of the 23, not extra. Its `pipeline.py` crashes on arrival; the agent must diagnose,
  fix, re-run, and verify. Grader recomputes ground truth so fabricated totals fail.

Cross-cutting dimensions (planning, product-quality) are scored over *existing* tasks by
`judge/dimensions.py` and add no new task folders.

---

**23 tasks built across all four v1 categories.** Mix of PAI (d-01/02/05/06/07, c-01/02, a-05,
b-01) and synthetic for general-benchmark breadth (PRD §8). The judge touches 14 of the 23:
all of Vague Ask (a-01–a-05), all of Messy World (hybrid — programmatic answer check + judge
flags the trap), and one Full Build task (c-04r, tool-failure recovery); Long Haul stays fully
programmatic. All seven taxonomy failure modes (PRD §7) now have a home task —
`fabricated-data` (d-06, c-04r) and `vision-drift` (across Long Haul) included.
