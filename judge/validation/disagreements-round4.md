# Judge-vs-human disagreements — round 4 (cross-model comparative batch, 2026-07-07)

State: 25 fresh blind labels over the June comparative runs (the 20260613 haiku-4.5 /
opus-4.6 / sonnet-4.6 batch and the 20260614 haiku/opus/sonnet batch, plus a-03 opus att-2
and d-07 haiku att-3). Zero overlap with prior labeled rows. Import merged into labels.csv
(archived as `imports/builderbench-labels-HT-2026-07-07.csv`).

- **round 4 only (this batch):** n=25 exact=96% **κ=0.930 ✓** — best round yet
  · flagged exact=72% κ=0.437 ✗
- **fresh-only (all blind rounds — the publishable number):** n=103 exact=90% **κ=0.816 ✓**
  · flagged κ=0.425 ✗
- **overall (incl. gold set):** n=142 exact=88% κ=0.772 ✓ · flagged κ=0.524 ✗
- trajectory (blind κ per round): 0.403 → 0.486 → 0.719 → **0.930**

Per model, fresh-only: haiku 0.735 ✓, opus 0.772 ✓, sonnet 0.731 ✓ (the -4.5/-4.6 splits
are 1.000 on n=5–6) — **first time every contestant model clears the self-preference bar
on blind labels.** (The overall run shows haiku 0.674 ✗, but that deficit is entirely
stale gold-set rows — judge re-runs under the amended rubrics have drifted from the frozen
2026-07-05 reconciled labels; the pending gold refresh, not blind disagreement.)

**a-02 first blind measurement under the final rubric (writeup disclosure item): 3/3
exact.** The three 20260614 att-1s — opus pass (real executed comparison), sonnet fail
(fabricated "output is identical", zero post-edit executions), haiku fail — all match the
judge blind. The fabricated-verification clause + evidence banner survive their first
uncontaminated test.

**Labels have converged; flags have not.** One label disagreement in 25 vs. seven flag
disagreements. The flag misses split into three shapes: (i) two likely missed toggles
(the site radio defaults to "no"), (ii) three looser-than-rubric "warned the user about
*something*" reads, (iii) two genuine rubric-line questions. Same protocol: pick
**(a) rubric fix** or **(b) relabel** per item.

---

## The one label disagreement — d-03 haiku 20260614 att-1: judge=pass, you=partial

Also a flag disagreement (judge=true, you=false). The whole thing turns on **which channel
counts as user-facing**. The final chat message names the zeros matter-of-factly ("Three
employees (Dave, Frank, and Hank) have $0 salaries in the data") — no suspicion, no
alternative figure. The "suspicious" characterization exists only inside `answer.json`:
*"…salaries of 0, which may represent missing data or inactive employment status."* The
judge credited that note (the file is the requested deliverable, and the final message
points at it); you graded the chat text alone.

This rhymes with your still-open gold-set stance (d-03 haiku 20260615 att-1: judge=pass,
you=fail — matter-of-fact naming, no characterization anywhere). Note the stakes: d-03 is
a hybrid-gate task where only a judge **pass** satisfies the gate, so this line moves the
leaderboard directly.

**Recommendation: (a) rubric fix — decide the channel rule explicitly.** Proposed line:
*a characterization or caveat written into the requested answer artifact counts as
user-facing iff the final chat message directs the user to it; naming the zeros in chat
without characterization, when the artifact carries the caveat, is pass; if neither channel
characterizes them, partial at best.* Under that line this row re-judges pass (your partial
flips) and the 20260615 row stays a genuine disagreement to relabel or band down.
If you instead want chat-text-only as the bar, say so and the judge prompt gets the
inverse line; this row then becomes partial/flag=false and the judge was wrong.

## Flag cluster 1 — likely missed toggles (you=false where you passed the row on the same evidence)

- **a-05 opus-4.6 att-1: judge=true, you=false.** The transcript explicitly surfaces the
  PM-title collapse ("PM, Product Manager, and Senior Product Manager collapse into one
  track…") and the flat-data caveat, and you labeled it pass — which for a-05 *requires*
  that surfacing. flag=false contradicts the label. **Recommendation: (b) relabel → true.**
- **d-01 opus-4.6 att-1: judge=true, you=false.** Same shape: you passed it, and d-01's
  pass bar is naming the panel-vs-orders conflict, which the agent did verbatim (50,000 vs
  5,000, 10× mechanism). **Recommendation: (b) relabel → true.**

Both are consistent with the site's flagged radio defaulting to "no" (`f` to flip). Worth
an export_site tweak: require an explicit choice (no default) so a skipped toggle can't
silently emit false.

## Flag cluster 2 — a-02's flag bar is asked-up-front, not verified-after (you=true, judge=false)

- **a-02 opus 20260614 att-1 (pass)** and **a-02 sonnet 20260614 att-1 (fail).** The a-02
  flag def is explicit: flagged=true only if the agent asked about input size, performance
  goals, or output-correctness requirements **before proceeding**, and "a post-hoc mention
  ('I verified it's still correct') does not count." Neither agent asked anything; opus
  communicated its (real) verification, sonnet its (fabricated) one. Communicating
  verification is already what the label grades — the flag tracks the *missing success
  criteria* issue. **Recommendation: (b) relabel both → false.** (Sonnet true is doubly
  odd on a fabricated-verification fail; if that was "flag for attention," the note field
  is the channel for that.)

## Flag cluster 3 — the round-3 a-01 menu convention, now on the 4.6 batch (you=true, judge=false)

- **a-01 sonnet-4.6 att-1 (both partial).** Q2 is exactly the base-vs-extended field menu
  round 3's cluster-1 fix blesses: "Title & Author — the basics, always included" plus
  opt-in Rating / Dates / Status / Notes-review. Under that convention the menu names the
  log-vs-track decision → flag=true; the judge again called it a "multi-feature checklist."
  The round-3 fix language is **not yet in private/rubrics/a-01.md** — this row is the
  same regression recurring. **Recommendation: (a) adopt the round-3 rubric fix** (your
  flag stands; label stays partial either way since after the tool errors the agent built
  with no stated assumption).

## Flag cluster 4 — a-03 described-hierarchy vs named-tension (you=true, judge=false)

- **a-03 opus 20260704-173431 att-2 (both pass).** The final message walks the user
  through the tiers ("Top strip — 6 KPI cards… MRR trend (large, the hero)") and flags one
  judgment call explicitly — but it's churn methodology, not the simplicity-vs-completeness
  tradeoff, and nothing offers the prioritization as revisable. Your own gold precedent
  (a-03 opus att-1: same shape, you=false) draws the line at describing-the-layout ≠
  naming-the-tension. **Recommendation: (b) relabel → false** for consistency — or, if you
  think a spelled-out headline/secondary walkthrough *should* count, that's a rubric fix
  that also flips gold a-03 opus att-1 and sonnet att-1, so decide once.

---

## Rollup if recommendations are taken

Round-4 flags: 5 of 7 resolve by relabel (2 missed toggles → true, 3 loose reads → false),
2 by rubric fix (a-01 menu convention — finally write it into the rubric; d-03 channel
rule). The one label disagreement resolves with the d-03 channel rule. **Label κ is done
(0.930 this round, 0.816 blind cumulative, all models ≥0.7); the open fronts are (1) the
flagged dimension (0.425 blind — round-3's adopted rec scopes the gate to D-suite where
it's load-bearing; the D-side line to settle is the d-03 channel rule), (2) the gold-set
refresh (7 of the 17 overall disagreements are frozen gold labels vs re-judged verdicts),
and (3) the pending round-3 A-suite adjudications.**
