# Builder-Bench: PRD

**An open-source agentic eval suite for coding agents, built around the "non-engineer builder" persona.**

Author: Helena Tan
Status: v1 — in build (M0 shipped; all open questions resolved, see Section 14)
Last updated: June 2026

---

## 1. Summary

Builder-Bench measures how well coding agents (Claude Code, Codex, and others) take a person from a rough idea to a working, shipped product, the way a PM, designer, or analyst actually works, rather than the way an engineer fixes bugs in an existing repo.

Existing benchmarks like SWE-bench test agents on engineer-written GitHub issues inside mature codebases. That misses a rapidly growing way people use coding agents: a non-engineer describing what they want and expecting the agent to build it end to end. Builder-Bench fills that gap with a graded task suite, a failure taxonomy mined from real transcripts, and a writeup that translates results into concrete recommendations for a model team.

This is a portfolio project with two audiences: the open-source community (a useful benchmark) and Anthropic's Claude Code model performance team (evidence of eval-building skill and model taste).

---

## 2. Goals and non-goals

### Goals

1. Produce a reproducible, open-source benchmark of 20 to 30 tasks across four categories that reflect real "builder" workflows.
2. Grade agents automatically with a hybrid harness (programmatic checks plus a validated LLM judge).
3. Run the benchmark across three Anthropic tiers (Opus, Sonnet, Haiku) and report pass rates, cost per solved task, and failure modes.
4. Publish a writeup with a failure taxonomy and three concrete model-behavior changes, backed by transcript evidence.

### Non-goals

- Not a general SWE benchmark. We are not re-testing bug-fixing in large legacy repos.
- Not a cross-lab comparison in v1. OpenAI and Gemini models — and the second-harness experiment that only makes sense with them — are out of scope due to API cost; they are the headline v2 extension (Section 9).
- Not a leaderboard service. v1 is a static repo with results, not a hosted, continuously updated leaderboard.
- Not a model-training artifact. We measure and diagnose; we do not fine-tune.
- Not enterprise permission/security testing. That is a separate project.

---

## 3. Why this matters (motivation)

The job-to-be-done for a coding agent is shifting. A growing share of users are not professional engineers; they are people with domain knowledge and a clear goal who want the agent to handle implementation. Their tasks look different: vague specs, judgment calls about data, "just make it work" requests, and long multi-session builds.

No public benchmark measures this well. Building one demonstrates a thesis the Claude Code team cares about and creates a concrete tool for improving the model for this persona. It also draws on direct experience building real products this way, including the PM-AI Hiring Index, which is a source of realistic tasks and edge cases.

---

## 4. Users

| User | What they get |
|------|---------------|
| Model/eval teams | A diagnostic suite that surfaces builder-persona failure modes and a methodology they can extend |
| Coding-agent users (PMs, analysts, indie builders) | Evidence of which agents handle builder work (vague ask → working product), and how reliably |
| The author | A public artifact proving eval-building skill and refined model taste |

---

## 5. Scope: task categories

Tasks fall into five categories, derived from the anatomy below. Four ship in v1 — roughly 5 to 8 tasks each, 20 to 30 total — and the fifth is deferred to v2. Each task is realistic, self-contained, and gradeable.

### The anatomy of an evaluation

Picture handing someone an assignment, then grading a stack of them:

> **Task** (Setup · Goal · Answer Key) → run by a **Contestant** → produces **Output** → scored by the Answer Key → rolled up into a **Scorecard**.

**Task layer — the question** *(authored once, frozen; this is all a contributor writes)*
- **Setup** — what the agent starts with: the files, data, and tools already on the desk.
- **Goal** — what we ask it to achieve.
- **Answer Key** — what counts as correct, and how we check.

**Run layer — the attempt** *(one model, one episode)*
- **Contestant** — who's being tested: the model, run in the same neutral harness as everyone else so it's a fair race.
- **Output** — what it hands back: the finished work (the **Deliverable**) and the record of how it got there (the **Transcript**).

**Report layer — the verdict** *(across many runs)*
- **Scorecard** — the grades rolled up: success rate (pass@1/@3) and cost.

A **task** is exactly the Task layer — Setup, Goal, and Answer Key, frozen in a folder. The Contestant, Output, and Scorecard only come into being when the task is run.

So where can a task's difficulty live? Not in the **Contestant** — that is *who we're testing*, and it changes every run. Not in the **Scorecard** — that is *how we measure*, and it is identical for everyone. The difficulty is designed into one of the other four parts:

- the **Setup** can hide a trap (flawed data),
- the **Goal** can be hard to pin down, or hard to hold onto,
- the **Output** demanded can be a whole working product,
- the **Answer Key** can hinge on judgment, not just checks.

**A category is named for which part carries the difficulty.** (Full detail, including how the layers map onto the repo, in [`docs/eval-framework.md`](eval-framework.md).)

There is one category per hard part — except the Goal, which gets two, because it can be hard in two different ways: unclear *now* (the agent must clarify it), or clear but easy to lose *over time* (the agent must hold onto it). That makes five categories:

PAI in the last column is the PM-AI Hiring Index — the real product the author built end to end with Claude Code; Section 8 details what it contributes and the boundaries on reusing it.

| Category *(the hard part · the verb)* | What it is — and what it probes | Examples | Graded on | v1 scope | PAI leverage |
|---|---|---|---|---|---|
| **A — Vague Ask** *(the Goal, while it's unclear · "clarify it")* | Deliberately ambiguous requests. Does the agent ask the right clarifying question, state assumptions explicitly, or silently guess? | "Build me a tracker for my reading" (no schema); "Make this faster" (no target); conflicting requirements in one prompt | The **Transcript** (asked the right question, or stated its assumptions) — judge. v1 grades the question/assumption turn only; a scripted "user reply" is a fixed next prompt-step (conditional replies are a v2 harness feature) | **Ship.** Cheap, high-value | Moderate. PAI's founding ask — *"Is AI eliminating PM roles, transforming them, or creating new ones?"* (its PRD v0.8; the true first prompt predates the transcripts) — was genuinely underspecified; extract the *pattern* into 1–2 tasks, round out with non-data tasks |
| **B — Long Haul** *(the Goal, holding over time · "hold the line")* | A vision or key requirement stated once at the start must survive later steps. Probes requirement drift (and, in v2, compaction and session resets) | "Dedupe by company, not by location," stated at step 1 and still binding at step 4 (the built b-01); "store all money as integer cents" while later features tempt floating-dollar math | The **final Deliverable** (the requirement still holds) — programmatic, often a single number | **Ship 2–3 lite tasks.** Build b-01 first — it validates the multi-step runner. The hard tier is v2 (see the tiers note below) | High. PAI's real dedup *debate* seeds the lite tasks — b-01 states the spec-era rule; the final PAI ruling went the other way, which is fine: the test is whether a *stated* rule survives ([evidence](pai-transcript-evidence.md)). The fragmented-session resume failures become the writeup case study and the v2 design source |
| **C — Full Build** *(the Output · "build it")* | Build a working artifact from a short PRD or plain-language request; the input data is deliberately *clean* (a data trap would make it Messy World). Probes end-to-end execution, sensible defaults, shipping something that actually runs | PRD → web app with a database; messy CSV → clean pipeline + dashboard; add auth to a small app; integrate a third-party API from vague docs | The **Deliverable** (runs, matches the schema) — programmatic. An optional quality rubric previews E (feeds the writeup only, not a leaderboard column) | **Ship — core.** Most automatable, clearest signal | High. PAI was itself a PRD-to-web-app-with-pipeline build; reconstruct a clean slice (e.g. "ingest job postings and dedupe them") with known fixtures and a known definition of done |
| **D — Messy World** *(the Setup · "notice it")* | Correctness requires noticing data-quality problems, not just writing code — the trap lives in the data, and the agent is *not* told to watch for it. Probes unprompted flagging, and defending choices when challenged | The same record under multiple keys ("one job posted in five locations"); two dashboard views disagreeing by an order of magnitude; ambiguous aggregation choices | The **Deliverable** (the right answer) + the **Transcript** (flagged the issue unprompted) — hybrid | **Ship — core.** Most automatable, clearest signal | Highest. Dedup-by-location, the order-of-magnitude discrepancy, and the title-taxonomy choices are real PAI edge cases with known answers and known traps; source most of D from PAI |
| **E — Good Taste** *(the Answer Key · "judge it")* | A *working* answer is not enough: "correct" is subtle or contested, and the agent must exercise judgment. Probes quality, not just function | Two plausible answers conflict — pick the right one and defend it; a product/design call where several options work but one is clearly better | The **Deliverable** (its quality) + the **Transcript** (its reasoning) — judge | **Defer to v2.** Hardest to grade reliably; v1 previews it via C's quality rubric. Most directly serves the "model taste" deliverable (Section 10) | — |

Notes on the table:

- **Long Haul's two tiers.** *Lite* (v1, automatable): single session, one requirement stated at step 1, several more steps, a final programmatic check — no judge needed; b-01 is exactly this. *Hard* (v2, deferred): multi-session builds with a real context reset or compaction, requiring session-resume plumbing, harness instrumentation, and likely judge-assisted grading — the richest version, worth a proper v2 rather than a rushed corner. **The line is firm:** anything requiring session resume, compaction, or harness instrumentation is v2, full stop — this keeps lite from creeping into hard and blowing the timeline.
- **The letters** are the stable task-id and leaderboard prefixes. Sub-type menus and seed tasks live in [`docs/task-backlog.md`](task-backlog.md).
- **PAI's overall share:** roughly 6 to 10 of the 20 to 30 tasks (most of D, part of C, 1–2 of A, the template for B), plus the failure taxonomy and the writeup's narrative spine — capped there so the suite reads as a general builder benchmark, not evals for one project (Section 8).

---

## 6. How grading works

Grading implements the **Answer Key** from Section 5, and it splits along the two Output surfaces: programmatic checks grade the **Deliverable**; an LLM judge grades the **Transcript**. Every task uses the first; only the categories that grade behavior need the second.

1. **Programmatic checks first.** Does it run? Do the tests pass? Does the data validation hold? Does the output match expected schema/values? This grades the Deliverable, and it fully covers Full Build, Long Haul, and the objective half of Messy World.
2. **LLM judge for the subjective parts.** A rubric-scored judge evaluates the Transcript: the quality of clarifying questions (Vague Ask) and whether the agent flagged and explained data issues (Messy World). Each rubric is explicit and per-task. Only Vague Ask and the subjective half of Messy World need it.

**Validating the judge before trusting it.** Labels come from runs, not tasks, and only two categories need the judge, so the subjective subset is small — roughly 25 to 40 transcripts across the three-model contestant set. Therefore:

- Hand-label the **entire** subjective subset once, rather than sampling it.
- Target agreement: Cohen's kappa >= 0.7 (or ~85% exact agreement), reported honestly.
- Label ~15 to 20 cases twice to establish a human-human ceiling (the judge is not expected to beat it).
- If the judge falls short, fix the rubric, not the judge model, and re-label.
- Read every judge-vs-human disagreement to surface systematic bias (good writeup material).
- **Guard against self-preference:** name the judge model in the report, and stratify judge-vs-human agreement **by contestant model** — a Claude judge must not be systematically kinder to Claude transcripts. If a per-model skew appears, report it and rebalance the rubric.
- Freeze a ~20 to 30 case gold set as a regression check for rubric or judge-model changes.

The grades roll up into the **Scorecard**, reported per task and per category:

- **pass@1** and **pass@3** (single attempt and best of three)
- **Cost per solved task** — defined as total spend on **all** attempts, including failed ones, divided by the number of tasks solved; failed retries are part of a model's real cost. Undefined when a model solves zero tasks in a slice (shown as "—", never ranked). Costs are **imputed from token counts at list API prices** regardless of how a run was actually paid for (subscription vs. API key), so comparisons stay apples-to-apples; the payment mode is noted per run.
- **Failure mode tags** (from the taxonomy in Section 7)

**Reading the numbers honestly.** With 5 to 8 tasks per category, a single task flipping moves a category pass rate by 12 to 20 points — so per-category results are directional, not rankings. The report shows confidence intervals on every pass rate, declines to rank models whose intervals overlap, and treats overall pass@1 across the full suite as the primary comparison. Where a category-level claim feeds a recommendation, run extra attempts on that cell before making it.

---

## 7. Failure taxonomy

The taxonomy is mined from the author's real Claude Code transcripts (the PAI build — Section 8; the tagged evidence lives in [`docs/pai-transcript-evidence.md`](pai-transcript-evidence.md)) and seeds both task design and result tagging. Seven failure modes, each with a primary "home": the task category designed to provoke it. The categories and the taxonomy are two views of the same map — a failure can surface anywhere, but each has one place we deliberately hunt it.

| Failure mode | What it looks like | Home category |
|--------------|--------------------|---------------|
| **Premature implementation** | jumps to code before understanding the goal | A — Vague Ask |
| **Silent assumptions** | guesses on ambiguity instead of asking or flagging | A — Vague Ask · D — Messy World |
| **Vision drift** | loses the originally stated objective over a long session | B — Long Haul |
| **Weak self-verification** | does not check its own work; ships broken output | C — Full Build |
| **Over-eagerness** | does more than asked, introducing scope or risk | C — Full Build · E — Good Taste |
| **Data blindness** | does not notice data-quality problems | D — Messy World |
| **Fabricated data** | invents plausible content (numbers, quotes, history) instead of flagging that real data is missing | D — Messy World |

Each failure observed in a run gets tagged. The taxonomy is a deliverable in its own right: it is the bridge from "scores" to "here is what to change in the model."

---

## 8. Leveraging PM-AI Hiring Index (PAI) as source material

PAI — the PM-AI Hiring Index, the author's web app built end to end with Claude Code — is a primary source for this benchmark rather than a coincidental side project. It contributes in four ways, ordered by value.

**As real, battle-tested tasks.** The strongest benchmark tasks come from real problems, not invented ones. PAI's actual edge cases (dedup-by-location, the order-of-magnitude dashboard discrepancy, title-taxonomy classification) become Messy World tasks with known correct answers and known traps. A reconstructed pipeline slice becomes a Full Build task. The vague original prompt becomes a Vague Ask task. A multi-session feature becomes the template for a Long Haul task. See the per-category notes in Section 5 for which tasks each category draws from PAI.

**As a transcript mine for the failure taxonomy.** PAI was built entirely through Claude Code, so its real session transcripts directly seed Section 7. Rather than theorizing failure modes, tag the actual moments they occurred.

**As built-in credibility for the writeup.** The narrative arc ("I built a real product with Claude Code, hit these specific failure modes, turned them into a benchmark, and here is what I would change in the model") is authentic because PAI is the origin story. It doubles as proof the author is a daily Claude Code user who ships.

**As a real-world case study for Long Haul.** PAI was built across many fragmented sessions because of usage limits, and losing context on session resume was the author's biggest documented frustration. That is a lived long-horizon coherence failure that can carry the Long Haul section even before full automation exists.

### Transcript-tagging workflow

**Status: done.** The pass ran over all 27 sessions (May 17 – June 7, 2026); the tagged evidence lives in [`docs/pai-transcript-evidence.md`](pai-transcript-evidence.md).

A single pass over the PAI transcripts produces material for three deliverables at once. While reading, tag each notable moment with one or more of:

- **Taxonomy tag** (Section 7 categories): seeds the failure taxonomy and result tagging.
- **Clarify tag** (any moment an ambiguous request had to be clarified): seeds Vague Ask task design.
- **Drift tag** (any moment context or a stated requirement was lost across a session boundary): seeds Long Haul task design and the writeup case study.

### Boundaries on PAI reuse

- Extract the *pattern and the data*, not the live codebase. Every task must start from a fixed, minimal starting state so anyone can reproduce it from a clean clone.
- No task may require the full PAI repo, PAI's Supabase credentials, or any private context.
- PAI is data/dashboard-heavy, so cap its share at roughly 6 to 10 of 20 to 30 tasks and deliberately add non-PAI tasks (auth, API integration, a non-data app) so the suite reads as a general builder benchmark.

---

## 9. Technical design

- **Runner:** headless agent execution through one **neutral harness**, the **Claude Agent SDK**, with a thin adapter layer so the scaffolding is identical for every model run. v1 is Anthropic-only, so a single harness suffices and no rival lab's model is disadvantaged by Claude-native scaffolding; the two-harness second-factor design moves to v2 with the cross-lab comparison. See the harness note below.
- **Sandboxing:** each task runs in an isolated Docker container with a fixed starting state, so runs are reproducible and tasks cannot interfere.
- **Task format & definition:** a **task** is the reusable, model-independent unit of evaluation — a folder that freezes three of the six framework parts so any contestant can be run against it: the **Goal** (the prompt or prompt-steps), the **Setup** (`setup.sh` + `fixtures/`), and the **Answer Key** (`grader.py` + `expected/` + a hidden reference solution), bound by a `success.yaml` manifest. The other three parts live *outside* the task: the **Contestant** is supplied at run time (`--model`), the **Output** is produced into the run's workdir, and the **Scorecard** is aggregated across runs. One task → many **runs** (attempts); pass@k aggregates them, and labels for judge validation come from *runs*, not tasks (see §6). This is also why a task is not the same as a single "test case": a test case is one input→expected→grader row evaluated in one model call, whereas a task is an *environment* an agent works in across many turns, graded on its trajectory and end-state. The folder schema is documented in [`tasks/README.md`](../tasks/README.md) so others can contribute tasks.
- **Models in v1 (Anthropic only, three tiers):** Claude **Opus 4.6** (flagship, primary system under test), Claude **Sonnet 4.6** (mid-tier), and Claude **Haiku 4.5** (budget). Three points on the cost-capability curve answer the question the suite cares about: "what do you give up by going cheaper, and is the cheap tier good enough for builder tasks?"
  - **Out of scope for v1 — API cost:** OpenAI (GPT-5.5 / GPT-5.4-mini) and Google (Gemini 3.5 Pro / Flash). Anthropic runs ride the author's Claude subscription through the Claude Agent SDK; competitor models would require pay-per-use API spend (as would Anthropic models driven through any second harness). The cross-lab comparison is the headline v2 extension, and the adapter layer is built so adding those models is a config change, not a rewrite.
  - Report **cost-per-solved-task** alongside pass rates for each tier.

#### Reference pricing (per 1M tokens, input / output, as of June 2026)

| Tier | Model | Price (in / out) |
|------|-------|------------------|
| Flagship | Claude Opus 4.6 | $5 / $25 |
| Mid | Claude Sonnet 4.6 | $3 / $15 |
| Budget | Claude Haiku 4.5 | $1 / $5 |

> Prices move; confirm at run time. Batch/cached pricing can cut these substantially (Anthropic Batch API ~50% off), so note which pricing mode each run used. The headline metric is **cost-per-solved-task**, not raw token price: a flagship that solves twice as many tasks can be cheaper per solved task than a budget model that fails and retries.
>
> Back-of-envelope for the full v1 matrix: ~26 tasks × 3 models × 3 attempts ≈ **~230 runs**, all through the Claude Agent SDK. On the subscription the marginal dollar cost is ~$0, but the 5-hour/weekly usage windows throttle batches — spread the record run across several days, or switch it to an API key (~**$120–$470** at $0.50–$2.00 per attempt) for batch pricing, no throttling, and clean accounting. Either way, *report* imputed costs at list prices (Section 6).

- **Reproducibility:** pinned model versions, sampling settings recorded per run (LLM APIs are not reliably seedable, and pass@k depends on attempt variance — record, don't pretend to fix), logged transcripts for every run. Each result also records the model's training cutoff vs. the task's publication date: public tasks become trainable the day they ship, and the private held-out split is the long-term contamination check.

### Harness note: why one harness is fine in v1, and the v2 second-factor plan

Each lab ships its own agent harness (Claude Code, OpenAI Codex, Google Antigravity), and running a model inside a harness measures *model + harness*, not the model alone. That is only a fairness problem when labs are being *compared*: in an Anthropic-only v1, running Claude tiers through Claude's own Agent SDK disadvantages no one, so a single harness is methodologically clean. Within v1, harness and tasks are held constant and only the model tier varies — differences trace to the model.

When the cross-lab comparison arrives in v2, the harness becomes a **second factor we measure** rather than assume away: a 2×N matrix (Claude Agent SDK + OpenAI Agents SDK × the model set) separates the **model effect** (down a column), the **harness effect** (across a row), and the **home-field advantage** (a model in its own lab's harness vs. a rival's — the interaction, and the most actionable result for a model team). The known limits of that design, recorded now for then: the two harnesses must be configured as equivalently as possible (same tools, budget, max-turns, prompts — neutrality is engineered, not assumed); Gemini has no home field in that set (Antigravity is not included); and the matrix roughly doubles run cost.

---

## 10. Deliverables: what the final product looks like

The reference point is swebench.com — a good north star. The finished product has four surfaces; the first three are required for v1.

1. **Leaderboard site — the public face.** A ranked table of models by overall pass@1, with category columns (A–D) and `cost-per-solved-task` sitting right next to the pass rate; each row links to that model's run details. All v1 runs use the single neutral harness (Section 9), so the headline number has one meaning. Backed by an in-repo results report that includes the judge-vs-human agreement number. Two deliberate differences from swebench.com: cost is a first-class column (SWE-bench largely ignores it), and the category breakdown exposes *where* a model wins — which is what turns a result into a recommendation.
2. **GitHub repo — the substance.** The task suite, the neutral runner, the graders, and contribution docs so others can submit tasks or models.
3. **Writeup — the credibility.** Methodology, the failure taxonomy with transcript excerpts as evidence, the harness-effect result (Section 9), and **three concrete, prioritized model-behavior recommendations** — the most important deliverable, because it demonstrates model taste rather than just engineering. The writeup doubles as the blog post and the interview artifact.
4. **Dataset + per-run trajectories — the receipts.** Every task plus the full logged transcript of every run, so anyone can audit a pass or failure.

### Positioning

Do not position Builder-Bench as "SWE-bench but mine." Position it as the complementary benchmark for how non-engineers actually use coding agents (vague asks, long-running builds, spec-to-product, messy real-world data), with the cost angle SWE-bench lacks. More defensible, more memorable.

### v1 vs aspirational

| Surface | v1 | Aspirational (v2+) |
|---------|-----|--------------------|
| Leaderboard | Static site generated from the author's own runs | Live site with community model/task submissions |
| Repo | Tasks, neutral harness, graders, contribution docs | Plugin ecosystem, CI that re-runs on new model releases |
| Writeup | One report + blog post with taxonomy and 3 recommendations | Ongoing series; methodology paper |
| Trajectories | Logged transcripts downloadable per run | Interactive in-browser trajectory viewer |
| Submission flow | None (author runs everything) | Hosted submission + validation pipeline |
| Coverage | ~26 tasks across A–D (Long Haul at the lite tier), 3 Anthropic tiers (Opus / Sonnet / Haiku), single harness | Good Taste (E), Long-Haul-hard multi-session tasks, cross-lab models (GPT, Gemini) + the second-harness matrix, native harness per lab |

> v1 is intentionally a static, self-run artifact: no submission pipeline, no hosting ops. That burden is only worth taking on if the project gains traction.

---

## 11. Milestones

| Milestone | Scope | Rough effort |
|-----------|-------|--------------|
| M0: Scaffold | Repo, task schema, Docker runner, plus one Long-Haul-lite task (b-01) end to end to validate the multi-step runner early | Weekend 1 |
| M1: Core tasks | 10 to 12 tasks across the Full Build and Messy World categories with graders, built in priority order so a partial weekend still yields a coherent subset | Weekend 2 |
| M2: Judge + validate | LLM judge, human-labeled validation set, agreement reported | Weekend 3 |
| M3: Full suite + run | Remaining Vague Ask tasks, 1 to 2 more Long-Haul-lite tasks, run all models, collect results | Weekend 4 |
| M4: Writeup + publish | Taxonomy, recommendations, PAI long-horizon case study, blog post, repo polish, launch | Weekend 5 |

> Target: a credible v1 in about 4 to 5 weekends. If time runs short, the pre-agreed cut is the Sonnet mid-tier — Opus vs. Haiku still gives the cost-capability contrast — never the writeup. (Long-Haul-hard is already deferred to v2, and the cross-lab comparison is already out of scope; see Sections 5 and 9.)

---

## 12. Success criteria

**Project is successful if:**

- The repo runs end to end for someone else from a clean clone (reproducibility).
- The LLM judge agrees with human labels at a defensible rate (Cohen's kappa >= 0.7, Section 6; report the actual number honestly).
- Results show a clear, defensible difference between models or a clear pattern of failures.
- The writeup names three specific model-behavior changes that a model team could act on.

**Stretch signals:**

- Community engagement: stars, forks, or task contributions from others.
- A member of a model/eval team engages with or references the work.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Tasks too easy or too hard (no signal) | Pilot each task on one model first; tune difficulty before scaling the run |
| LLM judge is unreliable | Validate against human labels before trusting it; keep programmatic checks as the primary grader |
| Scope creep (too many tasks/categories) | Hard-cap v1 at 30 tasks; pre-agreed cut in Section 11 (Sonnet mid-tier) |
| Reproducibility breaks across machines | Docker + pinned versions + logged transcripts from day one |
| Subscription usage windows throttle the record run | ~230 runs ride the Claude subscription's 5-hour/weekly limits; spread batches across days, or switch the record run to an API key (~$120–$470, Section 9) for batch pricing and clean accounting |

---

## 14. Open questions — all resolved

The decisions live in their home sections; this list records that each question was asked and closed.

- ~~Which competitor models, and is API access straightforward?~~ **Re-resolved (June 2026): descoped.** v1 is Anthropic-only — Opus / Sonnet / Haiku through the Claude Agent SDK, covered by the author's subscription. OpenAI and Gemini models, and the second-harness matrix that only makes sense with them, are out of scope for v1 due to API cost; together they are the headline v2 extension. Details in **Section 9**.
- ~~How many human labels are enough to trust the judge?~~ **Resolved:** hand-label the entire subjective subset (~50 to 70 transcripts), validate to Cohen's kappa >= 0.7 against a human-human ceiling, and freeze a gold regression set. Full protocol in **Section 6**.
- ~~Should Long Haul ship in v1 or move to v2?~~ **Resolved:** split it — Long-Haul-lite ships in v1, Long-Haul-hard (multi-session, context resets) is deferred to v2 behind a firm line. Tiers in **Section 5**.
- ~~What license and contribution model?~~ **Resolved (the one decision not recorded elsewhere in this PRD):**
  - **License by asset type:** code (harness, graders) under **Apache 2.0**; tasks/dataset under **MIT or CC-BY-4.0**, plus a contamination guard — a canary GUID, a "do not train on this" statement, and a small **private held-out split** kept out of the public repo (run manually in v1).
  - **Contribution flow:** GitHub PRs against the task template in `CONTRIBUTING.md`; CI validates each submission (schema check, grader runs in sandbox, reproducible from a clean clone); every task ships a reference solution and is piloted on >=1 model to confirm signal.
  - **Governance:** DCO sign-off (not a CLA); author reviews all PRs. A hosted submission pipeline is deferred to v2.
