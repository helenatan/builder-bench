# Builder-Bench Findings: What the Runs Showed, and What I Would Change

I built Builder-Bench to answer one question: which model is best for product management
tasks? This is the answer from the July 2026 run: 23 tasks, four categories, six Claude
models, three attempts each. Every score and transcript is live at
[builder-bench-delta.vercel.app](https://builder-bench-delta.vercel.app/).

One caveat up front: the judge that grades behavioral tasks was validated on the older model
generation, not this one. Keep that in mind wherever a Vague Ask number appears. More on
trusting these numbers at the end.

## The Numbers

| Model | Tier | Mean pass@1 | Vague Ask | Long Haul | Full Build | Messy World |
|-------|------|--:|--:|--:|--:|--:|
| Claude Haiku 4.5 | Budget | 55% | 0% | 87% | 87% | 50% |
| Claude Sonnet 4.6 | Mid | 72% | 20% | 100% | 93% | 75% |
| Claude Opus 4.8 | Flagship | 75% | 13% | 100% | 100% | 83% |
| Claude Sonnet 5 | Mid | 88% | 80% | 100% | 87% | 88% |
| Claude Fable 5 | Frontier | 90% | 80% | 100% | 100% | 83% |
| Claude Opus 5 | Flagship | 90% | 80% | 93% | 100% | 88% |

Three findings came out of this table and the transcripts behind it. The first is boring on
purpose. The other two are why I ran the benchmark.

## Finding 1: If the Ask Is Well Specified, Any Model Ships It

Long Haul and Full Build are near-ceiling for every model, budget tier included: a one-page
PRD becomes a working app with a real database, a rule stated at step one still holds at step
six. For well-specified build work, the cheap model is the rational choice.

## Finding 2: The Claude 5 Models Gained the Most on Vague Ask and Messy World

| Where the 4.x models stood | Where the Claude 5 models land |
|---|---|
| Vague Ask near-floor: 0% / 20% / 13% | All three new models jump to 80% |
| d-02, the hardest Messy World trap (same job under five city keys): 0 for 9 | Sonnet 5 and Fable 5 solve it; Opus 5 at 67% |
| Long Haul and Full Build near-ceiling | Unchanged; no headroom to gain |

## Finding 3: Fable 5 Reaches the Same Accuracy Far More Efficiently

Fable 5 and Opus 5 both score 90%, but Fable 5 gets there in about half the work:

| | Fable 5 | Opus 5 |
|---|---|---|
| Score | 90% | 90% |
| Agent turns per task | ~18 | ~33 |
| Output tokens per task | ~12,000 | ~30,000 |

The transcripts show why: Opus 5 re-verifies and narrates; Fable 5 reasons, then acts. That
extra work buys Opus 5 nothing except a small edge on Messy World (88% vs 83%).

Tier buys efficiency, not accuracy. All three Claude 5 models sit at 88% to 90% with
identical Vague Ask scores.

Opus 5 spends double the turns and tokens of Fable 5 for the same 90%, and the surplus goes
to re-verification and narration that never converts to accuracy. Users pay for that on
every request, in latency and in cost. For future models, knowing when to verify, how much
to narrate, and when the simple answer is sufficient would be a huge value add, especially
as users are increasingly expected to pay for their own consumption.

## How Much to Trust This

**The judge was validated on the old generation, not this one.** Vague Ask is judge-graded,
and that judge has not been checked against Claude 5 transcripts. Until a fresh blind-labeling
round covers them, Finding 2's headline number carries an asterisk. Protocol in
[PRD §6](PRD.md).

**The sample size is small.** 23 tasks, three attempts each. A few cells are single-attempt
misses on otherwise-solved tasks (Opus 5 on b-04, Sonnet 5 on c-03, Fable 5 on d-10). Noise,
not signal. Confidence intervals overlap within each generation: this is a capability profile,
not a ranking.

**Costs are imputed** from token counts at list prices. The turns/tokens comparison in
Finding 3 is measured directly.

Everything above is checkable: every run's full transcript is published on
[the site](https://builder-bench-delta.vercel.app/), the methodology is in the
[README](../README.md), the design in the [PRD](PRD.md), and the task provenance, including
the real product whose failures seeded the suite, in [PRD §8](PRD.md) and
[pai-transcript-evidence.md](pai-transcript-evidence.md).
