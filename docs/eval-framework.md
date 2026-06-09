# Builder-Bench: Evaluation Framework

**The conceptual backbone behind the task suite.** This is the *design* reference;
for the outward-facing explanation (blog, README) we use the classic
`(input, expected, grader)` triple. This document is what we design *against*.

Status: v1 working draft. Owner: Helena Tan.

---

## Part 1 — The 6-part framework

Every task, in every category, decomposes into the same six parts. A task is:

> The **Contestant** wakes up in a **Setup**, is given a **Goal**, and produces
> **Output** (a Deliverable + a Transcript), which we judge against an **Answer Key**
> and tally into a **Scorecard**.

| # | Part | One-liner | Role |
|---|------|-----------|------|
| 1 | **Setup** | what the agent starts with — the files, data, and sandbox already in place | knob (task-defining) |
| 2 | **Goal** | what the agent is asked to achieve | knob (task-defining) |
| 3 | **Contestant** | the thing under test: a model run inside the same neutral harness as every other model | the variable we **compare** |
| 4 | **Output** | everything the agent produced — what it shipped (the **Deliverable**) and how it got there (the **Transcript**) | knob (which surface we grade) |
| 5 | **Answer Key** | what counts as correct, and how we check the Output against it | follows from the knobs |
| 6 | **Scorecard** | the tally across many runs — how often it succeeded (pass@1/@3) and what each solve cost | held constant (the **measure**) |

### Two parts are not category knobs

- **Contestant** is the *independent variable* — the thing we vary and rank. In v1 it
  is a `(model, harness)` pair; we hold the harness neutral so differences trace to the
  model. (See the harness-as-second-factor extension in PRD §9.)
- **Scorecard** is the *measure* — identical metrics for everyone (pass@1/@3,
  cost-per-solved-task, failure-mode tags).

What's left — **Setup, Goal, Output (surface), Answer Key** — are the four knobs that
*define* a task. Categories are built from these.

### The Output has two surfaces

- **Deliverable** — what shipped: files, a running app, an answer. The *result*.
- **Transcript** — the logged session: what it asked, assumed, and checked. The *journey*.

Different categories grade different surfaces. Grading the Transcript is only possible
because we log every run — this is why full transcripts are a first-class deliverable.

---

## Part 2 — The category design

**A category is a named answer to one question: "which knob is the bottleneck?"**

There are four task-knobs, and the **Goal** knob fails in two distinct ways (unclear
*now* vs. must-survive *over time*), so there are **five** logical categories.

| # | Category | Knob (bottleneck) | The hard verb | Graded on | Grader |
|---|----------|-------------------|---------------|-----------|--------|
| 1 | **Vague Ask** | Goal — clarity | **clarify it** | Transcript | judge |
| 2 | **Messy World** | Setup | **notice it** | Deliverable + Transcript | hybrid |
| 3 | **Full Build** | Output | **build it** | Deliverable | programmatic |
| 4 | **Long Haul** | Goal — persistence | **hold the line** | Deliverable (final) | programmatic |
| 5 | **Good Taste** | Answer Key | **judge it** | Deliverable + Transcript | judge |

The whole suite in five verbs: **clarify it · notice it · build it · hold the line · judge it.**

The **letter codes are retained as stable IDs** (task-id prefixes, leaderboard columns), mapped to the original taxonomy: **A = Full Build · B = Messy World · C = Vague Ask · D = Long Haul · E = Good Taste**. So `d-01` stays valid and existing letter references elsewhere in the PRD still resolve.

### v1 scope (Option A)

**v1 ships four categories** (Vague Ask, Messy World, Full Build, Long Haul). The fifth,
**Good Taste**, is deferred to v2 — but its concern (quality, not just correctness) is
*previewed* in v1 by adding an optional **quality-rubric layer to Full Build** tasks.
The 5-knob model stays the conceptual backbone: "there are five ways a builder task gets
hard; v1 ships four and previews the fifth."

### Why this beats the old A/B/C/D

- **One organizing principle**, not four mismatched ones — every category answers the
  same "which knob?" question, so they're finally parallel.
- **No overlaps.** A task has one home (the knob it's *designed* to stress) plus optional
  secondary tags. (D-01 used to be both B and D; it is now unambiguously Long Haul, with
  a secondary Messy-World tag — the data is just its vehicle.)
- **The gap is named.** All four knobs are covered; the previously-missing Answer-Key knob
  is now Good Taste, the category that most directly serves the "model taste" deliverable.

### Mapping from the old taxonomy

| Old | New | Note |
|-----|-----|------|
| A — spec-to-product | **Full Build** | + optional quality-rubric layer previews Good Taste |
| B — data judgment | **Messy World** | difficulty is in the Setup (the data), not the words |
| C — underspecification | **Vague Ask** | difficulty is in interpreting the Goal |
| D — long-horizon | **Long Haul** | difficulty is the Goal surviving over time |
| — | **Good Taste** (v2) | new; fills the Answer-Key knob |

---

## Part 3 — How to design a test case

A category is a *space*, and the space feels infinite. The resolution:

> **You don't sample the category. You sample its *failure surface*.** A test case is not
> "a vague ask" — it's "a vague ask that, handled badly, produces *one specific,
> gradeable failure*." Anchor every task to a failure and the space collapses.

### Three generators (where cases come from)

1. **Work backward from the failure**, not forward from the topic. Each category targets
   specific failures (see PRD §7 taxonomy). Start from the failure you want to catch; the
   task is whatever *minimally forces* the model to commit or avoid it. The topic is
   interchangeable; the failure is the target.
2. **Mine real sources.** Real ambiguity/traps beat invented ones. Harvest from your own
   Claude Code history, PAI transcripts, support tickets, real Slack asks.
3. **Enumerate sub-types, then sample the grid.** A category has *kinds*. Listing them
   turns infinity into a short menu; pick ~1 task per sub-type. (Menus live in
   `task-backlog.md`.)

### Three filters (what makes a candidate valid)

1. **Trap + Tell.** Every task needs a **trap** (the tempting wrong move) and a **tell**
   (the observable signal separating pass from fail). No trap → too easy. No tell → not
   gradeable. (This is the PRD §14 "no signal" risk made concrete.)
2. **Write the Answer Key first.** State what a good response does and what a bad one does
   *before* building the task. If you can't write the rubric, it's a vibe, not a test
   case — discard or reshape.
3. **Isolate the target knob.** The task must be hard *only* because of its knob. Strip
   incidental difficulty, or you confound categories and don't know what you measured.

### The recipe (any category)

1. **Name the failure** the task targets (PRD §7).
2. **Pick a sub-type** from the category's menu.
3. **Find a real seed** (transcript/ticket) or construct one.
4. **Define trap + tell.**
5. **Write the Answer Key first** — if you can't, kill it.
6. **Strip incidental difficulty** (isolate the knob).
7. **Make an easy + a hard variant; pilot on one model** to confirm signal (PRD §14).
8. **Tag** primary category + failure modes; freeze.

### Category-specific wrinkle: interactive tasks

**Vague Ask** (and parts of Good Taste) are *interactive* — the agent asks a question,
and grading what it does *next* may require feeding it a scripted user reply. So those
Setups often include a **canned clarification answer**, or you grade only the quality of
the question turn. These categories lean on the **Transcript** surface and the judge.
