# Builder-Bench: Evaluation Framework

**The conceptual backbone behind the task suite.** This is the *design* reference;
for the outward-facing explanation (blog, README) we use the classic
`(input, expected, grader)` triple. This document is what we design *against*.

Status: v1 working draft. Owner: Helena Tan.

---

## Part 1 — The anatomy of an evaluation

The six parts aren't a flat list — they fall into **three layers**, and the layers form a
pipeline. This matters: the parts live at different times and have different owners, so
treating them as peers is what makes "is the Contestant part of a task?" feel ambiguous.

> **Task** (Setup · Goal · Answer Key) → run by a **Contestant** → produces **Output** →
> scored by the Answer Key → rolled up into a **Scorecard**.

The three layers map directly onto the repo: `tasks/` → `results/runs/` → `leaderboard.json`.

### Layer 1 — The Task *(authored once, frozen)*

This *is* the task: the reusable, model-independent unit a contributor writes. Lives in `tasks/`.

| Part | Plain meaning |
|------|---------------|
| **Setup** | what the agent starts with — the files, data, and tools already on the desk (`setup.sh` + `fixtures/`) |
| **Goal** | what the agent is asked to achieve (the prompt or prompt-steps) |
| **Answer Key** | what counts as correct, and how we check (`grader.py` + `expected/` + a hidden reference) |

### Layer 2 — The Run *(one Contestant, one episode)*

One attempt at the task. Logged under `results/runs/`.

| Part | Plain meaning |
|------|---------------|
| **Contestant** | who's being tested: the model, run in the same neutral harness as everyone else so it's a fair race. In v1, three Anthropic tiers through one harness; cross-lab models + a second harness are v2 (see PRD §9) |
| **Output** | what it hands back — the finished work (**Deliverable**) and the record of how it got there (**Transcript**) |

The Answer Key (from Layer 1) is *applied* here to turn an Output into a score.

### Layer 3 — The Report *(across many runs)*

| Part | Plain meaning |
|------|---------------|
| **Scorecard** | the grades rolled up — pass@1/@3 and cost-per-solved-task, plus failure-mode tags. Ends up on the leaderboard |

### Which parts can be the "hard part"

Two of the six are never the source of a task's difficulty, because they aren't part of the
task itself: the **Contestant** (the thing we vary and compare) and the **Scorecard** (how
we measure, identical for everyone). The difficulty always sits in one of the other four —
**Setup, Goal, Output, Answer Key** — and **a category is named for which one is the hard
part** (Part 2).

### The Output has two surfaces

- **Deliverable** — what shipped: files, a running app, an answer. The *result*.
- **Transcript** — the logged session: what it asked, assumed, and checked. The *journey*.

Different categories grade different surfaces. Grading the Transcript is only possible
because we log every run — this is why full transcripts are a first-class deliverable.

---

## Part 2 — The category design

**A category is a named answer to one question: "which part is the hard part?"**

Four parts can be the hard part, and the **Goal** can be hard in two distinct ways (unclear
*now* vs. must-survive *over time*), so there are **five** categories. The letter codes run
**A→E in this reading order** and double as the stable task-id and leaderboard prefixes.

| Code | Category | Hard part | The hard verb | Graded on | Grader |
|------|----------|-----------|---------------|-----------|--------|
| A | **Vague Ask** | Goal — clarity | **clarify it** | Transcript | judge |
| B | **Long Haul** | Goal — persistence | **hold the line** | Deliverable (final) | programmatic |
| C | **Full Build** | Output | **build it** | Deliverable | programmatic |
| D | **Messy World** | Setup | **notice it** | Deliverable + Transcript | hybrid |
| E | **Good Taste** | Answer Key | **judge it** | Deliverable + Transcript | judge |

The whole suite in five verbs: **clarify it · hold the line · build it · notice it · judge it.**

The **letter codes are the stable task-id and leaderboard prefixes**: **A = Vague Ask ·
B = Long Haul · C = Full Build · D = Messy World · E = Good Taste**. A task id is
`<letter><nn>`, so the built Long Haul task is `b-01`.

### v1 scope (Option A)

**v1 ships four categories** (Vague Ask, Long Haul, Full Build, Messy World). The fifth,
**Good Taste**, is deferred to v2 — but its concern (quality, not just correctness) is
*previewed* in v1 by adding an optional **quality-rubric layer to Full Build** tasks. The
5-part model stays the conceptual backbone: "there are five ways a builder task gets hard;
v1 ships four and previews the fifth."

### Why this beats the old A/B/C/D

- **One organizing principle**, not four mismatched ones — every category answers the
  same "which part is the hard part?" question, so they're finally parallel.
- **No overlaps.** A task has one home (the part it's *designed* to stress) plus optional
  secondary tags. (b-01 used to be classifiable as both Messy World and Long Haul; it is now
  unambiguously Long Haul, with a secondary Messy-World tag — the data is just its vehicle.)
- **The gap is named.** Setup, Goal, Output, Answer Key are now all covered; the
  previously-missing Answer-Key part is now Good Taste, the category that most directly
  serves the "model taste" deliverable.

### Mapping from the old taxonomy

| Old | New | Note |
|-----|-----|------|
| spec-to-product | **Full Build** (C) | + optional quality-rubric layer previews Good Taste |
| data judgment | **Messy World** (D) | the hard part is the Setup (the data), not the words |
| underspecification | **Vague Ask** (A) | the hard part is interpreting the Goal |
| long-horizon | **Long Haul** (B) | the hard part is the Goal surviving over time |
| — | **Good Taste** (v2) | new; fills the Answer-Key part |

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
   gradeable. (This is the PRD §13 "no signal" risk made concrete.)
2. **Write the Answer Key first.** State what a good response does and what a bad one does
   *before* building the task. If you can't write the rubric, it's a vibe, not a test
   case — discard or reshape.
3. **Isolate the hard part.** The task must be hard *only* because of its one hard part.
   Strip incidental difficulty, or you confound categories and don't know what you measured.

### The recipe (any category)

1. **Name the failure** the task targets (PRD §7).
2. **Pick a sub-type** from the category's menu.
3. **Find a real seed** (transcript/ticket) or construct one.
4. **Define trap + tell.**
5. **Write the Answer Key first** — if you can't, kill it.
6. **Strip incidental difficulty** (isolate the hard part).
7. **Make an easy + a hard variant; pilot on one model** to confirm signal (PRD §13).
8. **Tag** primary category + failure modes; freeze.

### Category-specific wrinkle: interactive tasks

**Vague Ask** (and parts of Good Taste) are *interactive* — the agent asks a question,
and grading what it does *next* may require feeding it a scripted user reply. So those
Setups often include a **canned clarification answer**, or you grade only the quality of
the question turn. These categories lean on the **Transcript** surface and the judge.
