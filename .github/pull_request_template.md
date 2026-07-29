<!--
Thanks for contributing. Delete the sections that don't apply.
Every commit needs a DCO sign-off (`git commit -s`) — see CONTRIBUTING.md.
-->

## What this changes

<!-- One or two sentences. -->

## Type

- [ ] New task
- [ ] Task fix (grader, fixture, or prompt)
- [ ] Harness / judge / reporting
- [ ] Docs

---

## For a new task

A task is accepted on evidence that it produces **signal**, not just that it runs.

- [ ] `python scripts/check_tasks.py` passes
- [ ] Runs from a clean clone — no `private/` dependency, no network, no external repo
- [ ] `grader.py` recomputes ground truth from the public `fixtures/` (it doesn't embed the answer)
- [ ] Piloted on ≥1 model — **paste the result below**

**Pilot result:**

```
model:
pass/fail:
what the failure looked like (or why every model passed):
```

**Why this task discriminates:** <!-- What behavior does it isolate? A task every tier
passes, or every tier fails, is real data but weak signal — say which you expect. -->

**Answer-key placement:** the reference solution and any machine-readable ground truth go
in `private/` (see `private/README.md`), *not* in the PR. Note here what you're sending
out-of-band.

---

## For a task fix

- [ ] I checked whether existing results in `results/` are invalidated by this change

<!-- Changing a fixture or grader changes the ground truth, which silently invalidates
     every run already published for that task. Say what needs re-running. -->

**Re-runs needed:**

---

## Checks

- [ ] `pytest -q` passes
- [ ] Commits are signed off (`git commit -s`)
