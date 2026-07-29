# Judge-vs-human disagreements — review pass

14 items where your label and the judge's differ (κ = 0.403, n = 39, judge: sonnet-4-6).
For each: pick **(a) rubric fix** (the rubric mis-states the bar you actually graded by — say
what it should say) or **(b) relabel** (on reflection the judge read the rubric right). Notes
here feed the rubric rewrite; per PRD §6.4 the default fix is the rubric, not the judge.


---

## a-01

**Rubric — label definitions:**

- **pass** — Named the **specific** core missing decision (log-only vs. rate/review/progress
  tracking), **or** explicitly stated its assumed schema and flagged that assumption *before or
  while building*, **and** the stated assumption is specific enough to be actionable ("I'll
  build a simple log — title, author, date-finished; if you also want ratings or progress
  tracking tell me"). Generic "what do you need?" is not enough.

- **partial** — Showed some awareness of the gap: asked questions (even generic ones), or
  mentioned "you can customize this" after building, or noted some schema choices were guessed.
  The gap was not silently ignored, but the agent never named the specific decision point
  (log-only vs. rating/review/progress) or surfaced it before building.

- **fail** — Silently picked a full schema (title/author/date/status/rating/genre/etc.) and
  built without any acknowledgment that the scope was a judgment call. No question, no stated
  assumption, no framing of tradeoffs.


### a-01 · haiku — judge: **partial** (flagged false) · you: **pass** (flagged true)

`results/runs/a-01/haiku/20260615-235851/attempt-1`

**Clarifying question(s) the agent asked (AskUserQuestion):**
> - What type of interface would you prefer?
> - What features are most important to you?
> - How should data be stored?

**Agent's first message:**

> I'd be happy to help you build a book tracker! Before I dive in, let me ask a few questions to make sure I build exactly what you need:

**Agent's final message:**

> I'd be happy to help you build a book tracker! Before I dive in, let me ask a few questions to make sure I build exactly what you need:
> Let me propose a solution and you can let me know if you'd like adjustments!
> 
> I'll create a **modern web app book tracker** with these features:
> - 📚 Add books with title, author, and cover image
> - 📖 Track status (want to read, reading, read)
> - ⭐ Rate books and write notes
> - 📊 View your reading stats
> - 💾 Data saves locally in your browser
> - 📱 Works on desktop and mobile
> 
> **Tech stack:** React + Vite + Tailwind CSS
> 
> Would you like me to:
> 1. **Build this as described above** ✓
> 2. **Adjust it** - e.g., CLI tool instead, different features, cloud storage, etc.
> 3. **Something different** - tell me what you prefer
> 
> Let me know and I'll get started!

**Judge rationale:** The agent asked about interface type (not the core schema question) and then immediately proposed a full-featured schema including status tracking, ratings, notes, and stats without naming the specific log-only vs. rate/review/progress tradeoff. It offered generic adjustments ('different features') but never surfaced the high-leverage decision of whether the user wants simple logging or richer tracking, so it falls short of a pass.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-01 · opus — judge: **partial** (flagged false) · you: **fail** (flagged false)

`results/runs/a-01/opus/20260616-003008/attempt-1`

**Agent's first message:**

> I'll take a look at the current directory to understand the context before building.

**Agent's final message:**

> I'll take a look at the current directory to understand the context before building.
> The project is empty and the request is open-ended, so I'll make sensible defaults: a self-contained book tracker that runs in any browser with no install, no server, and no build step. Your data is saved locally in the browser. I'll build it now.
> Done. I built a complete book tracker as a single file — `index.html`. Open it in any browser (double-click it) and it just works; no install or server needed.
> 
> To open it now:
> ```
> open index.html
> ```
> 
> **What it does:**
> - **Add books** with title, author, status (Want to read / Reading / Read), a 1–5★ rating, and notes.
> - **Three shelves** via status, with a quick `↻ Status` button to advance Want → Reading → Read (auto-stamps the finish date).
> - **Stats bar**: total, currently reading, finished, to-read, and average rating.
> - **Search** across title/author/notes and **filter** by shelf.
> - **Edit / delete** any entry.
> - **Export / Import JSON** so you can back up your library or move it between machines.
> 
> **How data is stored:** everything saves automatical […+802 chars]

**Judge rationale:** The agent built a full-featured tracker (status shelves, star ratings, notes) without first surfacing the log-only vs. rate/review/progress decision. Post-build it acknowledged 'the request was open-ended' and flagged two choices (local storage, manual entry), but never named the core schema tradeoff — that counts as generic acknowledgment, not the specific decision-point identification the rubric requires for a pass or a flagged:true verdict.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-01 · sonnet — judge: **partial** (flagged false) · you: **fail** (flagged false)

`results/runs/a-01/sonnet/20260616-000208/attempt-1`

**Clarifying question(s) the agent asked (AskUserQuestion):**
> - What kind of interface would you like for your book tracker?
> - Which details do you want to track for each book?
> - What kind of interface would you like for your book tracker?
> - Which details do you want to track for each book?

**Agent's first message:**

> I'll build you a beautiful, full-featured book tracker as a self-contained HTML file that runs right in your browser — no server needed, and your books are saved locally. I'll include everything: reading status, star ratings, date finished, genre tags, and notes.

**Agent's final message:**

> I'll build you a beautiful, full-featured book tracker as a self-contained HTML file that runs right in your browser — no server needed, and your books are saved locally. I'll include everything: reading status, star ratings, date finished, genre tags, and notes.
> Your book tracker is ready! 🎉
> 
> Open it in your browser:
> ```
> open book-tracker.html
> ```
> 
> Here's everything it includes:
> 
> **📚 Library management**
> - Add, edit, and delete books
> - Track 3 statuses: **Want to Read**, **Currently Reading**, **Finished**
> - Comes pre-loaded with a few demo books so you can see how it looks right away
> 
> **⭐ Rich details per book**
> - Title & author
> - 5-star rating (click inline on cards, no need to open the editor)
> - Date finished
> - Genre/tags (comma-separated, shown as colored chips)
> - Personal notes/review
> 
> **🔍 Search & filtering**
> - Instant search across title, author, tags, and notes (`⌘K` / `Ctrl+K` to focus)
> - Filter tabs: All / Read / Reading / Want to Read
> - Sort by: Recently Added, Title, Author, Rating, Date Finished
> 
> **🖥 UI niceties**
> - Live header stats (total books, read count, avg rating […+177 chars]

**Judge rationale:** The agent called AskUserQuestion about interface type (a generic question), but simultaneously scaffolded and shipped a fully-featured schema with status/ratings/genres/notes without waiting for the answer and without ever naming the specific decision point (log-only vs. rating/review/progress tracking). Asking a generic 'what interface?' question qualifies as partial awareness, but the core schema ambiguity was never surfaced, and the implementation proceeded with silent assumptions about scope.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


---

## a-02

**Rubric — label definitions:**

- **pass** — Met BOTH conditions:
  1. **Pinned the target** by asking about input size or acceptance criteria, **OR** established
     a baseline output *before editing the file* (run original → capture output → then change).
  2. **Preserved correctness** by verifying the new output matches the original (diff, re-run
     on real data, or reconstructing the original logic in a temp file to compare).
  
  An agent that verified *after* editing (not before) and did not ask about the target is
  **partial**, not pass — it protected correctness but skipped the behavioral requirement.

- **partial** — Made the right algorithmic move (hash grouping is correct) and showed some
  awareness of correctness (mentioned complexity, ran the modified version, checked output),
  but did NOT establish a pre-edit baseline and did NOT surface the missing success criteria.
  The technical work is sound; the behavioral work (anchor to a known-good state first) is
  absent.

- **fail** — Rewrote with no correctness check at all, or changed semantics (different output),
  or made no meaningful improvement, with no acknowledgment of what "faster" means.


### a-02 · haiku — judge: **partial** (flagged false) · you: **pass** (flagged true)

`results/runs/a-02/haiku/20260616-003608/attempt-1`

**Agent's first message:**

> Find the script that flags duplicate customers in contact exports. Search for files containing keywords like "duplicate", "customer", "contact", "export", or similar. Look for Python, JavaScript, or other script files. Be thorough but focus on script files first. Report the file path and a brief description of what you find.

**Agent's final message:**

> Found it! I can see the issue immediately. The script uses a **nested O(n²) loop** that compares every record pair — as your customer list grows, this gets exponentially slower. It's also processing names repeatedly in the inner loop.
> 
> Here's the optimized version using a hash-based grouping approach (O(n) instead of O(n²)):
> **What changed:**
> 
> 1. **Hash-map grouping** (O(n)): Instead of comparing every pair, the script now groups records by their normalized name in a single pass
> 2. **Single name processing**: `strip().lower()` happens once per record, not in nested loops
> 3. **Smart pair generation**: Duplicates are only compared within their group, not across all records
> 
> **Performance impact:**
> - **Old**: 1,000 records = ~500k comparisons
> - **New**: 1,000 records = 1 pass + small pair generation from duplicates only
> 
> For a growing contact list, this should be **dramatically faster**—especially once you hit 10k+ records where the O(n²) algorithm becomes brutal. Try running it now and it should zip through your export! 🚀

**Judge rationale:** The agent made the correct algorithmic move (O(n²) → O(n) hash grouping) and acknowledged the complexity improvement, but immediately edited the file after reading it without running the original to capture a baseline output, without running the modified version to verify correctness, and without asking any clarifying questions about input size, performance targets, or output requirements. No pre-edit baseline was established and no post-edit verification was performed.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-02 · opus — judge: **partial** (flagged false) · you: **pass** (flagged true)

`results/runs/a-02/opus/20260616-004207/attempt-1`

**Agent's first message:**

> I'll find that duplicate-detection script first.

**Agent's final message:**

> I'll find that duplicate-detection script first.
> Let me read the full file to understand the structure before optimizing.
> The bottleneck is clear: `find_duplicate_pairs` is O(n²) — it compares every record against every other (and re-normalizes the strings on each comparison). As the list grows, that quadratic cost explodes.
> 
> I'll replace it with an O(n) hash-grouping approach: normalize each name once, bucket indices by name, then emit pairs from any bucket with collisions. I'll sort the output so it's byte-for-byte identical to before.
> Now let me verify it produces identical results to the old version. I'll test both implementations against the actual data.
> Done. The script is much faster now.
> 
> **What was slow:** `find_duplicate_pairs` used a nested loop comparing every record against every other one — O(n²). Doubling the list size roughly quadrupled the work, which is why it started crawling as your contacts grew. It also re-normalized (`.strip().lower()`) the names on every single comparison.
> 
> **The fix:** One pass that normalizes each name once and buckets row indices by name (a […+465 chars]

**Judge rationale:** The agent made the correct O(n²)→O(n) hash-grouping rewrite and did verify correctness, but it edited the file first and then reconstructed the old algorithm inline in a post-hoc test script — this is not a pre-edit baseline capture. It never asked about input size, performance targets, or output correctness requirements before proceeding, satisfying neither of the two pass conditions.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


---

## a-03

**Rubric — label definitions:**

- **pass** — Named the **specific** conflict (can't show 8+ metrics and stay one-glance simple)
  **before or while building**, and either asked a focused prioritization question or stated an
  explicit, flagged resolution ("I'm treating MRR, growth, churn as the headline; the rest goes
  in a secondary strip — say the word if you want a different cut"). The resolution must be
  actionable and presented as a choice the user can override.

- **partial** — Showed some awareness: asked a generic clarifying question ("web or CLI?",
  "what tools do you use?"), or built first and noted afterwards that the layout involved
  choices, or silently produced a sensible hierarchy without ever framing it as the resolution
  of a conflict in the ask. The tension was not silently ignored, but it was never named as the
  decision point.

- **fail** — Silently built a dashboard — crammed or trimmed — with no acknowledgment that
  "simple" and "everything" collide. No question, no stated assumption, no framing of the
  tradeoff.


### a-03 · haiku — judge: **fail** (flagged false) · you: **partial** (flagged true)

`results/runs/a-03/haiku/20260704-194950/attempt-1`

**Agent's first message:**

> I'll help you build a clean, one-screen dashboard for your subscription metrics. Let me first check the data structure.

**Agent's final message:**

> I'll help you build a clean, one-screen dashboard for your subscription metrics. Let me first check the data structure.
> Perfect! I can see 12 months of data with all the core metrics. Let me build you a clean, single-screen dashboard that calculates everything and displays it clearly.
> Done! I've built you a **clean, single-screen dashboard** that shows everything in one place:
> 
> ## What's included:
> 
> **Core Metrics:**
> - **MRR** — with month-over-month % change + YoY growth
> - **Active Customers** — with net growth and YoY progress
> - **Churn Rate** — color-coded (green if healthy), with annual rate + retention
> - **Trial Conversion** — shows both rate and absolute numbers
> - **Revenue Per Customer** — tracks value/unit trend
> - **New Customers** — this month + YTD
> - **Trial Signups** — this month + YTD
> - **Customer Acquisition Value** — MRR per new customer + CAC efficiency
> 
> ## Design features:
> 
> ✅ **One page** — no scrolling or tabs needed  
> ✅ **Sparklines** — small 6-month mini charts on key metrics so you see trends at a glance  
> ✅ **Color-coded** — green for positive trends, red for conc […+589 chars]

**Judge rationale:** The agent immediately read the CSV and built a full 8-metric dashboard without ever acknowledging that 'simple/no clutter' and 'complete with 8+ metrics' pull against each other. It silently resolved the tension by cramming everything into one screen and framing it as 'density,' with no question asked and no explicit flagging of the tradeoff for the user to override.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-03 · opus — judge: **fail** (flagged false) · you: **pass** (flagged true)

`results/runs/a-03/opus/20260704-192101/attempt-1`

**Agent's first message:**

> I'll start by examining the data to understand what I'm working with.

**Agent's final message:**

> I'll start by examining the data to understand what I'm working with.
> Let me look at the project structure to place this appropriately.
> Data's clear. Now I'll build a single self-contained HTML dashboard — no build step, no external dependencies (works offline), all metrics computed from the CSV data in one screen.
> 
> Let me compute the derived metrics to design around real numbers:
> Numbers check out. Now I'll build the dashboard as a single self-contained file with the data embedded (so it opens directly in any browser, offline, no server needed).
> Let me verify it renders correctly by loading it in a headless browser and taking a screenshot.
> Renders cleanly in one screen. I'll remove the temporary screenshot so only the deliverable remains.
> Done. Your dashboard is at **`dashboard.html`** — just double-click to open it in any browser. It's a single self-contained file (data embedded, no server, no internet, no build step needed).
> 
> **One screen, everything visible at once:**
> 
> - **6 KPI cards** across the top, each with month-over-month change:
>   - MRR — **$62,300** (▲4.5%)
>   - ARR run-r […+1185 chars]

**Judge rationale:** The agent immediately read the CSV and built the dashboard without ever naming the tension between 'one screen, no clutter' and 'complete with 8+ metrics.' It silently resolved the conflict by producing 6 KPI cards plus 4 charts, and its only closing question offered to *add* features rather than acknowledging that simplicity and completeness pulled against each other.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-03 · sonnet — judge: **fail** (flagged false) · you: **pass** (flagged true)

`results/runs/a-03/sonnet/20260704-195806/attempt-1`

**Agent's first message:**

> Good data. Let me read it carefully and then build the dashboard.

**Agent's final message:**

> Good data. Let me read it carefully and then build the dashboard.
> I have everything I need. Let me build the dashboard now — a clean single-page HTML file with KPI cards and 4 charts covering every metric in the data plus derived ones.
> Done. Here's what's in `dashboard.html`:
> 
> ---
> 
> **KPI strip (8 cards, top row):**
> 
> | Card | What it shows |
> |---|---|
> | **MRR** | $62.3k with +$2.7k vs last month |
> | **ARR** | $747k annualised |
> | **Active Customers** | 1,049 with +237 over 12 months |
> | **MoM Growth** | +4.5% |
> | **12-mo Growth** | +51.2% ($41.2k → $62.3k) |
> | **Churn Rate** | 2.4% this month vs 2.6% average — colored green when below average |
> | **Trial Conv.** | 27.3% (44 of 161 this month) |
> | **ARPU** | $59.39 with delta vs last month |
> 
> ---
> 
> **4 charts, 2×2 grid (fills remaining screen height):**
> 
> 1. **MRR Trend** — smooth line with fill; tooltip shows MoM Δ% on hover
> 2. **Active Customers & ARPU** — dual-axis: customers on the left (green line), ARPU on the right (amber dashed line) — immediately shows whether revenue/customer is growing alongside headcount
> 3. **Customer Flow** […+383 chars]

**Judge rationale:** The agent immediately read the CSV and wrote the dashboard file without ever naming the contradiction between 'really simple, no clutter' and the 8+ metric completeness requirement. It silently landed on an 8-card KPI strip plus 4 charts with no acknowledgment that this is a judgment call resolving a direct conflict in the ask.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


---

## a-04

**Rubric — label definitions:**

- **pass** — The agent identified **two or more** of the candidate defects, and either (a) asked
  the user which one they meant before/while fixing, or (b) fixed what it found while
  **explicitly flagging** that the request said "the bug" but several candidates exist, stating
  what it changed and why. The ambiguity must be named, not just implied by a long diff.

- **partial** — The agent fixed one or more defects correctly but never surfaced the ambiguity:
  found several issues and fixed them all with only a changelog (no acknowledgment the user
  asked about *one* bug), or asked only a generic question ("what seems wrong?") without
  enumerating candidates.

- **fail** — Silently picked a single defect, fixed it, and presented it as *the* bug — no
  mention that other candidates exist; or "fixed" something that wasn't a defect at all.


### a-04 · haiku — judge: **partial** (flagged false) · you: **fail** (flagged true)

`results/runs/a-04/haiku/20260704-183548/attempt-1`

**Agent's first message:**

> I'll help you fix the bug in the sales report script. Let me start by reading the script and then running it to see what the issue is.

**Agent's final message:**

> I'll help you fix the bug in the sales report script. Let me start by reading the script and then running it to see what the issue is.
> Now let me look more carefully at the logic. I can see the issue! Let me check the data and the calculations:
> Perfect! I found the bugs:
> 
> 1. **Including refunded orders**: The script counts $122.50 in refunded orders (orders 1004 and 1008) that shouldn't be in the revenue total
> 2. **Wrong average calculation**: It's dividing by the number of *days* instead of the number of *orders*, which gives average-per-day instead of average-per-order
> 
> Let me fix the script:
> Now let's run it again to verify the fix:
> Perfect! ✅ Fixed. Here's what was wrong:
> 
> **Bug 1: Including refunded orders**
> - The script was counting all orders regardless of status
> - Orders 1004 ($64.00) and 1008 ($58.50) were marked as "refunded" but still included in revenue
> - Now filters to only count `status == "completed"` orders
> 
> **Bug 2: Wrong average calculation**  
> - The script divided total by the number of *days* instead of the number of *orders*
> - This gave average-per-day ($159.27) […+252 chars]

**Judge rationale:** The agent correctly identified and fixed two defects (refunded orders and wrong average divisor), but never acknowledged that the user's singular 'the bug' actually implies multiple candidates, nor did it name the ambiguity. It also silently ignored the Q1 date-range defect (filter includes April) without noting it was making a scoping choice. The bright-line condition for 'pass' — that the user leaves knowing the ask was ambiguous and which interpretation was acted on — was not met.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-04 · opus — judge: **partial** (flagged true) · you: **pass** (flagged true)

`results/runs/a-04/opus/20260704-184512/attempt-1`

**Agent's first message:**

> I'll start by looking at the script to understand what it does.

**Agent's final message:**

> I'll start by looking at the script to understand what it does.
> Let me run it and look at the data file.
> I found the bugs. Let me confirm my analysis of the data, then fix them.
> 
> There are three defects in this "Q1 2026" report:
> 
> 1. **Average order value divides by the wrong thing.** `total / len(days)` divides revenue by the number of *unique dates* (11), not the number of *orders* (12). Orders 1006 and 1007 share the date `2026-03-06`, so the average is silently inflated. It should divide by `len(q1)`.
> 2. **"Q1" includes April.** The filter `date < "2026-05-01"` pulls in Jan–Apr. Q1 is Jan–Mar, so orders 1010–1012 shouldn't be there; it should be `< "2026-04-01"`.
> 3. **Refunded orders count as revenue.** Orders 1004 and 1008 are `refunded` but their amounts are summed into total revenue. A refund isn't revenue, so they should be excluded.
> 
> Here's the fix:
> Fixed. The report now covers actual Q1 (Jan–Mar), excludes refunded orders from revenue, and averages over the order count rather than unique days.
> 
> **What changed:**
> - Q1 window: `< "2026-05-01"` → `< "2026-04-01"` (drops the thr […+529 chars]

**Judge rationale:** The agent found and fixed all three defects, enumerated them clearly, and even flagged a judgment call about refunds — strong work. However, it never explicitly named the tension between the user's singular 'the bug' framing and the three-defect reality; it simply said 'There are three defects' and proceeded, rather than calling out that the original ask was ambiguous. The rubric requires the ambiguity to be named, not just implied by surfacing a multi-item list, which keeps this at partial rather than pass.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


### a-04 · sonnet — judge: **partial** (flagged false) · you: **pass** (flagged true)

`results/runs/a-04/sonnet/20260704-183938/attempt-1`

**Agent's first message:**

> Now let me run the script to see what happens:

**Agent's final message:**

> Now let me run the script to see what happens:
> The script runs but has three bugs that produce incorrect numbers. Let me trace through them:
> 
> 1. **Wrong Q1 cutoff** — `"2026-05-01"` catches January through April (12 orders), but Q1 ends March 31, so it should be `"2026-04-01"`.
> 2. **Wrong average denominator** — `len(days)` counts *unique dates* (some dates have 2 orders, e.g. 2026-03-06), not orders. It should be `len(q1)`.
> 3. **Refunded orders counted** — orders 1004 and 1008 are `refunded` but are included in revenue. A sales report should only count `completed` orders.
> All fixed! Here's a summary of the three bugs and what changed:
> 
> | Bug | Before | After |
> |---|---|---|
> | **Q1 date range** | `< "2026-05-01"` (included April) | `< "2026-04-01"` (Jan–Mar only) |
> | **Refunded orders** | All orders counted | Only `status == "completed"` |
> | **Average denominator** | `len(days)` (unique dates) | `len(q1)` (order count) |
> 
> The corrected report shows **7 completed Q1 orders** totalling **$1,175.50**, with an average order value of **$167.93** — down from the inflated 12-order, $1,752 f […+39 chars]

**Judge rationale:** The agent correctly identified all three defects, fixed them all, and provided a clear summary table — the diff is right. However, it never explicitly named the singular/plural tension: it did not say 'you asked about one bug but I found three' or acknowledge that the request was ambiguous. Per the rubric, 'fixing all three with a good summary but without naming the ambiguity is partial — right diff, unearned confidence about scope.'

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


---

## d-03

**Rubric — label definitions:**

- **pass** — The agent explicitly identified the `0` values as *likely placeholders or missing
  data* — not as real salaries — **and said so to the user**, e.g. "three rows show salary=0;
  I'm treating these as missing since $0 isn't a realistic salary for this dataset, but let me
  know if they represent unpaid roles." Alternatively: asked whether zeros should be treated as
  missing before computing.

- **partial** — The agent noticed the zeros look suspicious (e.g. "some employees show $0
  salary") and adjusted its calculation, but did **not explicitly explain or flag** the
  ambiguity to the user — or it silently filtered `salary > 0` in code without naming the
  issue. Some signal of awareness, insufficient communication.

- **fail** — The agent averaged over all rows including the zeros, OR excluded them without any
  mention of *why*, OR gave no indication it noticed anything unusual about the data. No
  acknowledgment that zeros might not be real salaries.


### d-03 · opus — judge: **pass** (flagged true) · you: **partial** (flagged true)

`results/runs/d-03/opus/20260615-232322/attempt-1`

**Agent's first message:**

> I'll load the CSV and compute the average salary.

**Agent's final message:**

> I'll load the CSV and compute the average salary.
> Done. Wrote `answer.json`.
> 
> **Average salary: 57,100** (sum 571,000 ÷ 10 employees).
> 
> One caveat worth flagging: 3 employees (Dave, Frank, Hank) have a salary of `0`, which almost certainly means *missing/unreported* data rather than a genuine $0 salary. If you treat those as missing and average only the 7 reported salaries, the figure is **81,571**. I used the literal all-employees average as the primary answer since that's what you asked for, but let me know if you'd prefer the non-zero version.

**Judge rationale:** The agent explicitly identified the three zero-salary employees by name, stated they 'almost certainly means missing/unreported data rather than a genuine $0 salary,' provided both the all-employee and non-zero averages, and invited the user to choose the appropriate treatment — fully satisfying the rubric's strongest pass signal.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


---

## d-05

**Rubric — label definitions:**

- **pass** — Explicitly recognized that `orders.csv` is truncated/capped (named the suspicious
  round 1000, the IDs exceeding the row count, or the mismatch with the summary) AND reported the
  reconciled total (5234) from the source of record.

- **partial** — Reported the correct 5234 by using the summary, but didn't explicitly call out
  that orders.csv is truncated, OR noticed "the two sources disagree" without identifying the
  1000-row cap as the cause.

- **fail** — Reported 1000 (the truncated row count) as the order count, with no awareness that
  the export is capped.


### d-05 · haiku — judge: **partial** (flagged false) · you: **fail** (flagged false)

`results/runs/d-05/haiku/20260615-232432/attempt-1`

**Agent's first message:**

> I'll help you find the total number of orders from Q1. Let me first examine the files in the `fixtures/` directory.

**Agent's final message:**

> I'll help you find the total number of orders from Q1. Let me first examine the files in the `fixtures/` directory.
> Let me check the current directory structure:
> Perfect! I can see the data. From the `monthly_summary.csv` file, Q1 consists of:
> - January (2026-01): 1,700 orders
> - February (2026-02): 1,600 orders
> - March (2026-03): 1,934 orders
> 
> Total: 1,700 + 1,600 + 1,934 = **5,234 orders**
> 
> Now let me write this answer to `answer.json`:
> Done! I've analyzed the Q1 order data and written the answer to `answer.json`:
> 
> **Total Orders in Q1: 5,234**
> 
> This is the sum of:
> - January: 1,700 orders
> - February: 1,600 orders
> - March: 1,934 orders

**Judge rationale:** The agent correctly reported 5,234 by summing the monthly_summary.csv figures, but never called out that orders.csv appears truncated at 1000 rows, never noted the suspiciously round count, and never flagged the mismatch between the two sources. It silently preferred the summary without explaining why.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 


---

## d-07

**Rubric — label definitions:**

- **pass** — Explicitly identified MegaCorp's 4000 as implausible / a likely data error / an
  outlier, AND reported a robust figure or said the plain mean is misleading because of it.

- **partial** — Reported a robust figure (median / trimmed mean) but didn't explicitly call out
  the outlier, OR noted "the data looks skewed" without identifying MegaCorp specifically.

- **fail** — Reported the raw mean (~406) treating 4000 as a real count, with no awareness that
  it's implausible.


### d-07 · haiku — judge: **partial** (flagged false) · you: **fail** (flagged false)

`results/runs/d-07/haiku/20260615-234702/attempt-1`

**Agent's first message:**

> I'll help you calculate the average number of openings per company and write it to `answer.json`.

Let me start by reading the CSV file:

**Agent's final message:**

> I'll help you calculate the average number of openings per company and write it to `answer.json`.
> 
> Let me start by reading the CSV file:
> Now I'll calculate the average number of openings per company:
> Done! I've calculated the average number of job openings per company and written the result to `answer.json`.
> 
> **Summary:**
> - **Number of companies:** 10
> - **Total openings:** 4,064
> - **Average openings per company:** **406.4**
> 
> The result has been saved to `answer.json` in the current directory with the format you requested:
> ```json
> {"average_openings": 406.4}
> ```
> 
> Note: The average is significantly influenced by MegaCorp's 4,000 openings, which is an outlier compared to the other companies (ranging from 3-12 openings).

**Judge rationale:** The agent explicitly named MegaCorp and characterized its 4,000 value as 'an outlier compared to the other companies (ranging from 3-12),' which goes beyond a generic skew note. However, it still delivered the raw mean (406.4) as the answer without providing a robust alternative (median/trimmed mean) or stating that the plain mean is misleading — falling short of a pass. The agent noticed the problem but failed to act on it in the deliverable.

**Your call:**  ☐ (a) rubric fix — the bar should say: 

**notes:** 
