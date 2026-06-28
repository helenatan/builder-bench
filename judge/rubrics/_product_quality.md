# Dimension rubric — Product quality (cross-cutting)

## What this rubric grades

A **cross-cutting dimension**, not a per-task answer key. It applies to runs that produce a
*built artifact* (mainly Full Build / category C) and grades the **quality of what was shipped**
beyond "does it run" — the half the programmatic grader cannot see.

The question: if a teammate inherited this, would they thank the agent or curse it?

> You are grading the deliverable's craft, not its correctness (the grader already checked it
> runs and meets spec). Judge what you can see of the produced files and structure in the
> transcript and any included deliverable snapshot.

## Dimensions to weigh

- **Maintainability / structure** — sensible file layout and separation of concerns; not one
  500-line dump; names that say what they mean.
- **Readability** — clear code a non-author could follow; no dead code or commented-out cruft
  left behind.
- **Documentation** — a brief README or run instructions where the task warrants it; key
  decisions noted; how to run/build is discoverable.
- **Robustness defaults** — input validation, error handling, and sane edge-case behavior that a
  thoughtful builder includes without being told.
- **Restraint** — solved what was asked without gratuitous scope, dependencies, or speculative
  abstraction.

## Labels

- **pass** — A teammate could pick this up comfortably: coherent structure, readable code,
  enough documentation to run it, reasonable defaults, no obvious cruft or over-engineering.

- **partial** — Works but rough: monolithic or muddled structure, thin/absent docs, or notable
  cruft / over-build — usable but with real friction for the next person.

- **fail** — Poor craft: tangled or opaque, undocumented in a way that blocks a handoff, or
  reckless defaults — the kind of thing that runs in the demo and rots in the repo.

## flagged

Not meaningful for this dimension — always set `flagged: false`.

## failure_tags

Use `over-eagerness` for gratuitous scope/abstraction beyond the ask. Otherwise leave empty.
