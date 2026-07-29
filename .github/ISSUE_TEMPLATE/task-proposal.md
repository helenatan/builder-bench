---
name: Task proposal
about: Propose a new Builder-Bench task before building it
title: "[task] "
labels: task-proposal
---

<!-- Proposing before building is optional but usually saves you work — it's the fastest
     way to find out the task already exists or won't discriminate. -->

## The builder situation

<!-- Who is asking, for what, in what words? Builder-Bench tasks are written in a real
     person's voice, not as a spec. -->

## Category

- [ ] **A · Vague Ask** — the goal is ambiguous; correct behavior is asking or stating assumptions
- [ ] **B · Long Haul** — a rule stated once must survive later steps
- [ ] **C · Full Build** — a short brief must become something that actually runs
- [ ] **D · Messy World** — the data holds a trap the agent was never warned about

## The trap, or the judgment call

<!-- What specifically is the agent supposed to notice or decide? For Messy World: what's
     wrong with the data, and how would a careless agent get a plausible-looking wrong answer? -->

## How it would be graded

- [ ] Programmatic (`grader.py` recomputes truth from fixtures)
- [ ] Judge (a rubric over the transcript)
- [ ] Hybrid gate (both must pass)

## Why you expect it to discriminate

<!-- Which tiers do you expect to pass? A task all models pass or all models fail is still
     publishable, but say so up front. -->

## Is it derived from something real?

<!-- Real transcripts beat invented scenarios. If this comes from a build you actually did,
     say so — that's the strongest form of this proposal. -->
