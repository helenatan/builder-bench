# Builder-Bench: v2 Plan — Toward a Multi-Dimensional Builder Profile

**Status:** active. Companion to [`PRD.md`](PRD.md) (which defines v1).
**Origin:** external review of v1 arguing the benchmark over-indexes on a single correctness
axis and should score builders across many objectives at once. This doc records how we respond.

**Scope decision (committed):** Phase 0 and Phase 1 below are the active build scope. Phase 2
(the interactive simulated-user harness and long-horizon multi-session tasks) remains deferred —
it is the v2 flagship, taken on only after 0 + 1 land.

**Not v2 scope, but worth noting here:** in July 2026 the Claude 5 generation (Fable 5 / Opus 5 /
Sonnet 5) was added to v1 as new `--model` aliases alongside the original 4.x lineup — see PRD
§9/§14. That's a within-Anthropic model-lineup change, orthogonal to this doc's subject (scoring
dimensions) and to the cross-lab (GPT/Gemini) expansion that's still the actual v2 headline.
Noted here only so this doc doesn't read as stale about what "the current model set" means.

**What this costs in new tasks:** Phase 0 adds *no* new tasks (instrumentation + rubrics over
existing runs). Phase 1 adds ~4–5 task folders, ~3–4 of which are cheap clean-control *variants*
of existing D tasks, plus one genuinely new recovery task. The philosophy is to extract more
signal from existing tasks/runs, not to grow the suite. New metrics can be *built* now;
*populating* them with numbers requires running the new/control tasks on the subscription.

---

## 0. Implementation status (Phase 0 + 1)

The machinery for Phase 0 and Phase 1 is built and verified. What remains is *populating* the new
judge-scored metrics, which requires running the judge / new tasks on the subscription.

| Item | Status | Populated? |
|---|---|---|
| Cost-per-task + tokens/turns/tool-calls in `metrics` + leaderboard (`Cost/solved · Cost/task · Effort`) | **Built** | Yes — backfilled from existing runs, no re-run |
| Confidence-calibration metric (`harness/calibration.py`) + clean controls `d-03x`, `d-07x` | **Built** | Sensitivity yes, but only for the original 3-model generation (Opus 4.8 83 / Sonnet 4.6 72 / Haiku 4.5 28) — not yet re-measured for Claude 5. False-alarm still needs `d-03x`/`d-07x` actually built as task folders (planned, not yet built — see task-backlog.md) |
| Planning-quality dimension (`judge/dimensions.py` + `_planning.md`), retroactive over transcripts | **Built** | Needs a judge pass (subscription auth) |
| Product-quality dimension (`_product_quality.md`) + runner deliverable snapshot | **Built** | Needs new runs (to capture snapshots) + a judge pass |
| Tool-use signal (tool-call counts) | **Built** (effort columns) | Yes |
| Recovery-after-tool-failure task (`c-04r`) | **Built** | Populated — c-04r is folded into the standard 23-task suite with runs across all 6 models |

To populate: `python -m harness.calibration` (sensitivity now); `python -m judge.dimensions
--dimension planning` and `--dimension product_quality --include-deliverable` (judge auth);
re-run the new tasks (`d-03x`, `d-07x`, `c-04r`) through `harness.runner` for their cells.
**Phase 2 remains deferred.**

## 1. The through-line

The review's seven points share one thesis: **move from a single correctness axis to a
multi-dimensional builder profile** — score planning, tool use, interaction, uncertainty,
product quality, and cost alongside "did it work." That direction is right and is the spine of
v2.

But the seven points are not equal, and not all are gaps. Before building, sort them:

| # | Review point | Reality in v1 | Response type |
|---|---|---|---|
| **7** | No economic evaluation | **Already the signature metric.** `cost-per-solved-task` is a first-class leaderboard column (the explicit "angle SWE-bench lacks"); every run records `cost_usd`, `input_tokens`, `output_tokens`, `num_turns`. | **Surface, don't build** |
| **5** | Little evaluation of uncertainty | **Partly built.** All of category D (Messy World) rewards flagging; d-01 ("two views disagree by 10×") is the review's own "conflicting revenue numbers" example. The judge already emits a `flagged` boolean. | **Promote to a metric** |
| **2** | No long-horizon projects | **Roadmapped.** Long-Haul-hard (multi-session, compaction, session resets) is deferred to v2 by a firm line in PRD §5. | **Reprioritize** |
| **4** | No interaction quality | **Roadmapped.** A/Vague-Ask uses scripted next-prompts today; PRD §5 names conditional replies / branching as the v2 upgrade. | **Reprioritize** |
| **1** | Too much emphasis on correctness | **Genuine gap.** Only a thin quality-rubric preview exists in C; E/Good-Taste is deferred. No maintainability / UX / docs / observability scoring. | **Net-new** |
| **3** | No evaluation of planning | **Genuine gap.** Transcripts are logged but nothing scores decomposition, commit hygiene, or checkpointing. | **Net-new** |
| **6** | Weak tool-use evaluation | **Genuine gap.** Tool calls are *in* the transcript but nothing scores selection, retries, or recovery-after-failure. | **Net-new** |

**Summary: 2 of 7 are done-but-underexposed, 2 are already on the roadmap, 3 are genuine
net-new dimensions.** The honest response credits what exists (especially the cost work, which
the review missed), reprioritizes the roadmapped items, and builds the three real gaps — without
pretending we can validate ten judge dimensions to κ≥0.7 on a portfolio budget.

---

## 2. The Builder Quality profile (tiered by measurement rigor)

Adopt the review's multi-dimensional scorecard — but **tiered by how rigorously each axis can
be measured**, not as ten equally-ranked columns (see Cautions, §4).

- **Tier 1 — programmatic, primary (keep as-is):** execution correctness. Stays the headline.
- **Tier 2 — derived from existing instrumentation (nearly free):** cost-efficiency
  (cost / tokens / turns / tool-calls / wall-clock) and confidence-calibration. Data already
  recorded per run.
- **Tier 3 — validated judge dimensions (pick 2–3, validate honestly):** planning quality,
  tool-use quality, product quality (maintainability / UX / docs). Each needs its own rubric +
  κ check, so be selective.
- **Tier 4 — needs new harness (v2 flagship):** interaction quality (simulated user) and
  long-horizon recovery.

Present Tier 3/4 as a **profile (radar), not a ranking.**

---

## 3. Phased plan

### Phase 0 — Reframe + mine existing runs *(≈ a weekend, almost no new harness)*

1. **Expose the economics already captured.** Add `output_tokens`, `num_turns`, and a derived
   `tool_calls` count (parsed from the transcript) to the leaderboard + a success-per-dollar
   frontier plot. One writeup paragraph: point #7 is already the headline metric.

2. **Add `cost-per-task` alongside `cost-per-solved-task`.** *(Recorded from the cost-metric
   discussion.)*
   - **What:** `cost_per_task_usd = total_cost_usd / attempts`. A pure *price* number, in
     contrast to cost-per-solved-task (spend on all attempts ÷ tasks solved), which is a *value*
     number that folds in reliability.
   - **Why add it, as a secondary column (not the headline):**
     1. **It rescues the zero-solve rows.** cost-per-solved-task is `null` whenever a model
        solves nothing (e.g. the a-01 / a-02 leaderboard rows), so those cells currently report
        no cost signal at all. cost-per-task always has a value.
     2. **The gap between the two is itself a metric** — `cost-per-solved ÷ cost-per-task` ≈ the
        *reliability tax* (what you pay for retries and dead ends). Clean addition to the
        economic-evaluation story.
     3. **It's free** — `total_cost_usd` and `attempts` are already on every leaderboard row;
        this is one derived column, no new instrumentation.
   - **Keep cost-per-solved-task as the headline** (PRD §6 rationale: a flagship that costs more
     per token but solves more can be cheaper *per solved task* than a cheap-but-unreliable
     model — cost-per-task alone would flatter the unreliable one). cost-per-task is the
     stable-denominator companion, not a replacement.
   - **Touch points:** leaderboard schema (`results/leaderboard.json` rows), the report
     generator (`harness/report.py`), and the leaderboard HTML.

3. **Promote calibration to a real metric.** The judge already logs `flagged` on every D run.
   Define calibration = **flag rate on trap tasks (true positives) vs. flag rate on clean
   control tasks (false alarms).** Rigorous, novel, and exactly the "false confidence" failure
   the review cares about. (Needs the clean controls in Phase 1 for the false-alarm denominator.)

4. **Retroactive planning-quality pass.** Run a new judge rubric ("stated a plan before editing?
   coherent small steps vs. scattershot edits?") over transcripts already collected — free signal
   on runs already paid for.

### Phase 1 — The three genuine gaps *(v1.x, a few weekends)*

5. **Clean-control variants** of 3–4 D tasks (same data, trap removed) — the false-alarm
   denominator for the calibration metric.

6. **Tool-use scoring + a recovery task.** Derive tool metrics from transcripts (call count,
   redundant/failed calls, retry-after-error). Add one task sub-type that *injects* a tool
   failure (missing dep, flaky command) and grades recovery — directly answering "recovery after
   tool failure" (#6).

7. **Expand C's quality rubric** into a named multi-axis product-quality rubric (maintainability,
   readability, docs) — the concrete form of #1, reusing the quality-rubric layer C already has.

### Phase 2 — v2 flagship *(biggest lift; the two reframed-but-roadmapped items)*

8. **Interactive harness:** a "simulated PM" agent that responds to the contestant's clarifying
   questions, turning A/Vague-Ask into real 2–4 turn loops (#4). The single biggest
   differentiator and the largest engineering item.

9. **Long-horizon multi-session tasks** with session resets / compaction and milestone /
   checkpoint scoring (#2 + the planning-graph part of #3). The PAI (PM-AI Hiring Index — see
   PRD §8) "fragmented sessions / lost context" story is the authentic origin for this.

---

## 4. Cautions / what *not* to do

- **Don't ship ten equally-weighted ranked dimensions.** Each judge dimension needs κ≥0.7
  against human labels (PRD §6); we can honestly validate ~2–3, not ten. Present Tier 3/4 as a
  profile, not a ranking — and say so. Admitting this *is* a model-taste signal.
- **Keep correctness programmatic and primary.** The multi-dimensional layer is a richer overlay,
  not a replacement; otherwise we trade a defensible benchmark for a pile of subjective judge
  scores.
- **Reframe, don't apologize, on #2 / #4 / #5 / #7.** These were deliberate scope lines, and one
  (#7) is the headline. The review *validates the v2 roadmap and helps prioritize it* — that's the
  writeup narrative.
