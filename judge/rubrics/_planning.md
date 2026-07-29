# Dimension rubric — Planning quality (cross-cutting)

## What this rubric grades

This is a **cross-cutting dimension**, not a per-task answer key. It applies to *any* run's
transcript and grades **how the agent planned and structured its work** — independent of whether
the final answer was correct (that is scored separately by the programmatic grader).

The question: did the agent decompose the problem, order its steps sensibly, and work in
coherent increments with validation — or did it thrash through scattered, unexplained edits?

> You are grading *process*, not outcome. An agent can reach the right answer with poor planning
> (lucky thrashing) or the wrong answer with good planning. Score only the planning behavior
> visible in the transcript: the sequence of tool calls, the stated intent, and the structure of
> the work.

## What good planning looks like

- **Stated a plan** before diving in — named the subtasks or the approach, even briefly.
- **Sensible decomposition** — broke the goal into ordered pieces with clear dependencies.
- **Coherent increments** — each edit/command follows from the last; no random flailing.
- **Validation checkpoints** — ran/tested/inspected its own work along the way, not just at the
  end (or not at all).
- **Adapted deliberately** — when something failed, diagnosed before retrying rather than
  blindly re-running variants.

## Labels

- **pass** — Clear up-front intent and a sensible decomposition; steps are ordered and build on
  each other; the agent checks its work at least once before declaring done. A reader can follow
  the plan from the transcript.

- **partial** — Some structure but notably weaker: a thin or missing plan, reasonable steps but
  little/no self-validation, or one stretch of redundant or backtracking work that a small amount
  of planning would have avoided.

- **fail** — Scattershot: jumps straight to edits with no discernible plan, steps don't build
  coherently (repeated undirected attempts, large rewrites of just-written code), and no
  self-checking. The right answer, if reached, looks incidental to the process.

## flagged

Not meaningful for this dimension — always set `flagged: false`.

## failure_tags

Use `premature-implementation` when the agent coded before understanding the goal, and
`weak-self-verification` when it never checked its own work. Otherwise leave empty.
