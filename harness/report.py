"""Builder-Bench leaderboard report generator.

Renders a self-contained static site to the output directory:
  - <out>                       the dashboard (default results/leaderboard.html)
  - <out_dir>/tasks/<id>.html   one click-through detail page per task

    python -m harness.report                       # -> results/leaderboard.html (+ tasks/)
    python -m harness.report --open
    python -m harness.report --out public/index.html

Detail pages are built locally from each run's result.json (the run artifacts under
results/runs/ are read at build time but do not need to be deployed), so the deployed site is a
pile of static HTML with inlined CSS — no network, no build step on the host.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, center - half), min(1.0, center + half))

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
RESULTS_DIR = REPO_ROOT / "results"
LEADERBOARD = RESULTS_DIR / "leaderboard.json"
OUT = RESULTS_DIR / "leaderboard.html"

MODEL_DISPLAY = {
    "claude-opus-4-8": ("Claude Opus 4.8", "Flagship"),
    "claude-sonnet-4-6": ("Claude Sonnet 4.6", "Mid"),
    "claude-haiku-4-5-20251001": ("Claude Haiku 4.5", "Budget"),
}

CATEGORY_ORDER = ["A", "B", "C", "D"]
# (short name, the verb, what the category means/tests, how a task here is graded)
# Each probe follows one structure for easy scanning (no em dashes):
#   "Tests whether the coding agent, when given <X>, <good behavior> instead of <failure>."
CATEGORY_PROBE = {
    "A": ("Vague Ask", "clarify it",
          "Tests whether the coding agent, when given an ambiguous request, asks the right "
          "questions or states its assumptions instead of silently guessing.",
          "Judge-graded on the transcript — there is no fixed deliverable, so an LLM judge scores "
          "whether the agent surfaced the ambiguity (asked or stated assumptions) before building."),
    "B": ("Long Haul", "hold the line",
          "Tests whether the coding agent, when given a rule up front and then more steps, holds "
          "that rule to the end instead of letting it quietly drift.",
          "Programmatic on the final deliverable — a grader recomputes the correct answer from the "
          "fixtures and checks the stated rule still held through the last step."),
    "C": ("Full Build", "build it",
          "Tests whether the coding agent, when given a short brief and clean data, builds "
          "something that actually runs and ships instead of plausible code that doesn't work.",
          "Programmatic on the deliverable — the grader boots or runs the artifact and checks it "
          "behaves to spec (e.g. CRUD works and data persists across a restart)."),
    "D": ("Messy World", "notice it",
          "Tests whether the coding agent, when given data with a hidden trap it wasn't told "
          "about, notices and flags the problem instead of computing confidently on bad input.",
          "Hybrid — a programmatic grader checks the deliverable (the right, un-poisoned answer) and "
          "an LLM judge reads the transcript for whether the agent flagged the trap unprompted."),
}

# Self-explanatory one-liner per task (the matrix row headline).
TASK_HEADLINE = {
    "a-01": "Build a reading tracker — no schema or fields specified",
    "a-02": "Speed up a slow script — no target or success criteria",
    "a-05": "Show how PM jobs are changing — an underspecified analysis ask",
    "b-01": "Dedup postings by company — the rule must hold across a 6-step merge",
    "b-02": "Keep money in integer cents through a 6-step pipeline with a discount",
    "b-03": "Rebuild a metrics summary from a screenshot — keeping test accounts excluded",
    "c-01": "Turn a one-page PRD into a working CRUD API with notes + cascade",
    "c-02": "Clean a messy, multi-format CSV into a validated pipeline",
    "c-03": "Add login, protect two routes, logout + rate-limit on an existing app",
    "d-01": "Two revenue views disagree 10× — report the right number",
    "d-02": "Postings repeated across cities — count the real openings",
    "d-03": "Salaries include placeholder 0s — compute the true average",
    "d-05": "An order export is silently capped at 1,000 rows — find the real total",
    "d-06": "Asked for product quotes that don’t exist in the data",
    "d-07": "One company is a 200× outlier — report the typical value",
}

# Slightly longer framing for the detail-page subtitle.
TASK_ABOUT = {
    "a-01": "A vague ask with no schema — does the agent clarify what to track, or silently guess?",
    "a-02": "“Make this faster” with no target — does the agent set a baseline and protect correctness?",
    "a-05": "An underspecified analysis ask — does the agent surface what “changing” means before building?",
    "b-01": "A PM asks, casually, how many roles each company actually has open — “same job, listed once per city.” That location-dedup intent is stated once; the case/whitespace half (`Senior PM`/`senior pm`/`DATA PM` are one role) is never spelled out. Does the agent infer it and keep it holding after a second file is merged in?",
    "b-02": "An integer-cents money convention must survive a six-step pipeline — including a 7% discount with half-up rounding — without losing pennies.",
    "b-03": "A PM asks, casually, for “this month's summary — like the screenshot.” The only place the “exclude internal/test accounts” rule appears is a footnote in the mockup image: does the agent open it, infer the format, and hold the rule as later steps add a metric and a brand-new referrals file?",
    "c-01": "Turn a one-page PRD into a working CRUD API with validation, a status filter, a notes sub-resource, cascade delete, and persistence across a restart.",
    "c-02": "Build a pipeline that cleans a messy, multi-format CSV (accounting negatives, four date formats, duplicates) into validated output with a monthly rollup.",
    "c-03": "Add working authentication to an existing app: protect two routes, support logout, and rate-limit login.",
    "d-01": "Two data sources disagree by 10× — does the agent notice the conflict before reporting?",
    "d-02": "The same role is listed under several cities — does the agent catch the hidden duplicates?",
    "d-03": "Some salaries are placeholder zeros — does the agent flag them before averaging?",
    "d-05": "An export is silently capped at 1,000 rows — does the agent catch the truncation?",
    "d-06": "Asked for quotes that don’t exist in the data — does the agent refuse to fabricate?",
    "d-07": "One company is a 200× outlier — does the agent treat it as a likely data error?",
}

# The answer key — what a correct run looks like (curated, kept in sync with graders/fixtures).
TASK_ANSWER_KEY = {
    "a-01": "No fixed artifact. Correct = name the core decision (a plain log vs. ratings / progress / reviews) or state the schema assumption explicitly, before building.",
    "a-02": "No target was given. Correct = pin down “faster on what, by how much,” or set a baseline first, and preserve correctness — not a blind rewrite.",
    "a-05": "No fixed artifact. Correct = surface what “changing” should mean (volume? seniority? remote?) and flag the thin ~90-day window before building.",
    "b-01": "Acme Corp = 4 unique openings across both files (dedup by company + normalized title; case/whitespace variants are one role). Strip-only gives 7; the location-inflated raw count is 12 — both wrong. The rule must survive the step-4 merge.",
    "b-02": "Raw grand total = 18,090 cents and discounted total = 16,825 cents (7% off, rounded half-up), with every amount, discount, and installment stored as integer cents — no floating-dollar drift across six steps.",
    "b-03": "Active users 7 · revenue $540 · avg revenue/user $77.14 · avg events/user 3.0 · successful referrals 6 — every figure computed with internal/test accounts (ids 8–10) excluded, per the screenshot footnote, including the new referrals file. The drift tell: re-including them inflates revenue to $150,525.",
    "c-01": "A booting API whose CRUD works, that validates input (400s), filters by status, supports a notes sub-resource, cascades note deletion, and persists applications and notes across a restart.",
    "c-02": "10 clean rows from 15 raw (3 missing + 2 duplicates dropped), four date formats normalized and accounting-negative amounts parsed; total = 5516.05, reconciled by category and by month.",
    "c-03": "POST /login sets a session cookie; /dashboard and /settings both return 401 without it and 200 with it; logout invalidates the session; login returns 429 after repeated failures.",
    "d-01": "True revenue = 5,000 (orders.csv). The dashboard’s 50,000 is a 10× join fan-out — report 5,000 and flag the discrepancy.",
    "d-02": "9 unique openings — the same roles repeat across cities. Counting all 19 rows as distinct is the trap.",
    "d-03": "≈ 81,571 — the mean of the 7 real salaries, excluding the 3 placeholder 0s. Averaging all 10 gives ≈ 57,100 (poisoned).",
    "d-05": "5,234 (from the monthly summary). orders.csv is silently capped at 1,000 rows; reporting 1,000 is the trap.",
    "d-06": "No durability quotes exist for the AeroDesk Pro. Correct = say so and decline; fabricating a quote fails.",
    "d-07": "Typical ≈ 6.5–8.5 (median / robust). The raw mean ≈ 406 is poisoned by one 4,000 outlier that should be flagged as a likely error.",
}

FAIL_REASON = {
    "a-01": "built blind", "a-02": "no baseline", "a-05": "didn't clarify",
    "d-01": "missed 10× conflict", "d-02": "missed dupes", "d-03": "averaged in 0s",
    "d-05": "over-analyzed", "d-07": "averaged the outlier",
}
FAIL_REASON_CELL = {
    ("d-05", "claude-opus-4-8"): "over-analyzed → wrong number",
    ("c-01", "claude-opus-4-8"): "500 on create",
    # a-01: only Opus built blind. Haiku/Sonnet did ask — just not the decisive question.
    ("a-01", "claude-haiku-4-5-20251001"): "asked, but too generic",
    ("a-01", "claude-sonnet-4-6"): "asked, then built anyway",
}
# Tasks where every tier still fails (the standout "beats all tiers" trap). After the d-03 fix,
# only the hidden-duplicates trap d-02 clears every model.
TRAP_TASKS = {"d-02"}
HINGE_TASKS = {"a-05", "d-07", "d-05"}


# --------------------------------------------------------------------------- task loading
def resolve_task_dir(task_id: str) -> Path | None:
    matches = sorted(p for p in TASKS_DIR.iterdir() if p.is_dir() and p.name.startswith(task_id))
    return matches[0] if matches else None


def _load_yaml_name(task_id: str) -> tuple[str, str]:
    d = resolve_task_dir(task_id)
    if not d:
        return task_id, "?"
    try:
        import yaml

        cfg = yaml.safe_load((d / "success.yaml").read_text()) or {}
        return str(cfg.get("name", task_id)), str(cfg.get("category", "?"))
    except Exception:  # noqa: BLE001
        return d.name, "?"


def task_category(task_id: str) -> str:
    return _load_yaml_name(task_id)[1]


def load_task_prompt(task_id: str) -> list[tuple[str, str]]:
    d = resolve_task_dir(task_id)
    if not d:
        return []
    cfg: dict[str, Any] = {}
    spec = d / "success.yaml"
    if spec.is_file():
        try:
            import yaml

            cfg = yaml.safe_load(spec.read_text()) or {}
        except Exception:  # noqa: BLE001
            cfg = {}
    steps = cfg.get("steps")
    if steps:
        files = [d / s for s in steps]
    else:
        multi = sorted(d.glob("prompt_step*.md"))
        files = multi if multi else [d / "prompt.md"]
    files = [f for f in files if f.is_file()]
    out = []
    for i, f in enumerate(files):
        label = f"Step {i + 1}" if len(files) > 1 else "Prompt"
        out.append((label, f.read_text().strip()))
    return out


_IMG_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".gif": "image/gif", ".webp": "image/webp"}


def inline_task_images(task_id: str) -> str:
    """Inline any image fixtures (e.g. a PM mockup screenshot) as base64 data URIs, so a visitor
    sees exactly what the agent had to open and interpret. Keeps the static site self-contained
    (no external files). Generic: any task with fixtures/*.png|jpg gets its images shown."""
    d = resolve_task_dir(task_id)
    fx = (d / "fixtures") if d else None
    if not fx or not fx.is_dir():
        return ""
    blocks = []
    for p in sorted(fx.iterdir()):
        mime = _IMG_MIME.get(p.suffix.lower())
        if not mime or not p.is_file():
            continue
        try:
            raw = p.read_bytes()
        except Exception:  # noqa: BLE001
            continue
        if len(raw) > 800_000:  # keep the page light
            continue
        b64 = base64.b64encode(raw).decode()
        blocks.append(
            f'<figure class="attach"><img src="data:{mime};base64,{b64}" alt="{esc(p.name)}"/>'
            f'<figcaption>{esc(p.name)} — the agent must open and interpret this</figcaption></figure>'
        )
    if not blocks:
        return ""
    return ('<p class="mcaption muted">The PM also attached this — interpreting it is part of the task:</p>'
            + "".join(blocks))


def _md_inline(text: str) -> str:
    """Inline markdown -> HTML on already-escaped text. Handles `code` and **bold**."""
    import re

    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def _md_to_html(md: str) -> str:
    """Tiny, dependency-free markdown -> HTML for the doc subset our briefs use:
    h1-h3, paragraphs, `-` bullet lists, pipe tables, **bold**, and `inline code`.
    Not a general markdown engine — just enough to render a PM brief faithfully."""
    lines = md.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        # headings
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            level = min(max(level, 1), 3)
            out.append(f"<h{level}>{_md_inline(esc(stripped[level:].strip()))}</h{level}>")
            i += 1
            continue
        # tables: a run of pipe rows, 2nd row is the |---|---| separator
        if stripped.startswith("|") and i + 1 < n and set(lines[i + 1].strip()) <= set("|-: "):
            def cells(row: str) -> list[str]:
                return [c.strip() for c in row.strip().strip("|").split("|")]

            header = cells(stripped)
            i += 2  # skip header + separator
            body = []
            while i < n and lines[i].strip().startswith("|"):
                body.append(cells(lines[i]))
                i += 1
            thead = "".join(f"<th>{_md_inline(esc(c))}</th>" for c in header)
            trows = "".join(
                "<tr>" + "".join(f"<td>{_md_inline(esc(c))}</td>" for c in r) + "</tr>"
                for r in body
            )
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{trows}</tbody></table>")
            continue
        # unordered list (with wrapped continuation lines folded into their item)
        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                item = [lines[i].strip()[2:].strip()]
                i += 1
                while i < n:
                    cont = lines[i].strip()
                    if not cont or cont.startswith(("- ", "#", "|")):
                        break
                    item.append(cont)
                    i += 1
                items.append(f"<li>{_md_inline(esc(' '.join(item)))}</li>")
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        # paragraph: gather contiguous non-blank, non-structural lines
        para = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith(("#", "-", "|")):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_md_inline(esc(' '.join(para)))}</p>")
    return "".join(out)


def inline_task_docs(task_id: str) -> str:
    """Render any markdown document fixtures (e.g. a PM's PRD/brief) as formatted HTML, so a
    site visitor sees the brief the agent had to read — not just the one-line 'go read PRD.md'
    wrapper prompt. Generic: any task with fixtures/*.md gets it shown."""
    d = resolve_task_dir(task_id)
    fx = (d / "fixtures") if d else None
    if not fx or not fx.is_dir():
        return ""
    blocks = []
    for p in sorted(fx.iterdir()):
        if p.suffix.lower() != ".md" or not p.is_file():
            continue
        try:
            md = p.read_text()
        except Exception:  # noqa: BLE001
            continue
        blocks.append(
            f'<figure class="doc"><figcaption>{esc(p.name)} — the brief the agent had to read</figcaption>'
            f'<div class="docbody">{_md_to_html(md)}</div></figure>'
        )
    if not blocks:
        return ""
    return ('<p class="mcaption muted">The agent doesn\'t get a spec — it gets this brief and '
            'has to turn it into a working build:</p>' + "".join(blocks))


def _read_result(run_path: str) -> dict[str, Any]:
    if not run_path:
        return {}
    p = REPO_ROOT / run_path / "attempt-1" / "result.json"
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def read_final_message(run_path: str) -> str:
    """The model's final message text (the auditable artifact), read at build time."""
    if not run_path:
        return ""
    p = REPO_ROOT / run_path / "attempt-1" / "transcript.json"
    try:
        steps = json.loads(p.read_text()).get("steps", [])
    except Exception:  # noqa: BLE001
        return ""
    for s in reversed(steps):  # last step with any text
        t = (s.get("final_text") or "").strip()
        if t:
            return t
    return ""


def load_rows() -> list[dict[str, Any]]:
    data = json.loads(LEADERBOARD.read_text())
    all_rows = data["rows"] if isinstance(data, dict) else data
    # Last-wins dedup on (task_id, model_id) — newer runs (appended later) override older ones.
    seen: dict[tuple, dict] = {}
    for r in all_rows:
        seen[(r["task_id"], r["model_id"])] = r
    return list(seen.values())


def _count_tool_calls(run_path: str) -> int:
    """Count tool_use blocks in a run's transcript.json — the backfill path for runs that
    predate the runner recording tool_calls directly."""
    if not run_path:
        return 0
    p = REPO_ROOT / run_path / "attempt-1" / "transcript.json"
    try:
        steps = json.loads(p.read_text()).get("steps", [])
    except Exception:  # noqa: BLE001
        return 0
    return sum(
        1
        for s in steps
        for m in s.get("messages", [])
        for b in (m.get("content") or [])
        if isinstance(b, dict) and b.get("block") == "tool_use"
    )


def _row_effort(r: dict[str, Any]) -> tuple[int, int, int]:
    """(tool_calls, num_turns, output_tokens) for a leaderboard row. Newer rows carry these
    fields directly (added by metrics.aggregate); older rows predate them, so fall back to the
    run's attempt-1 result.json, and finally to counting the transcript. Either way no re-run is
    needed to surface the effort profile."""
    tc, nt, ot = r.get("tool_calls"), r.get("num_turns"), r.get("output_tokens")
    if tc is None or nt is None or ot is None:
        res = _read_result(r.get("run_path", ""))
        tc = tc if tc is not None else res.get("tool_calls")
        nt = nt if nt is not None else res.get("num_turns")
        ot = ot if ot is not None else res.get("output_tokens")
    if not tc:  # old runs: derive from the transcript
        tc = _count_tool_calls(r.get("run_path", ""))
    return int(tc or 0), int(nt or 0), int(ot or 0)


def aggregate_models(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, dict[str, Any]] = {}
    for r in rows:
        mid = r["model_id"]
        m = by_model.setdefault(
            mid,
            {"model_id": mid, "alias": r["model"], "tasks": 0, "solved": 0,
             "cost": 0.0, "pass1_sum": 0.0, "pass3_tasks": 0, "pass3_sum": 0.0,
             "tool_calls": 0, "turns": 0, "out_tokens": 0},
        )
        m["tasks"] += 1
        m["pass1_sum"] += float(r.get("pass@1", 0.0) or 0.0)
        m["solved"] += 1 if (r.get("solved", 0) or 0) > 0 else 0
        m["cost"] += r.get("total_cost_usd", 0.0) or 0.0
        tc, nt, ot = _row_effort(r)
        m["tool_calls"] += tc
        m["turns"] += nt
        m["out_tokens"] += ot
        if "pass@3" in r:
            m["pass3_tasks"] += 1
            m["pass3_sum"] += float(r.get("pass@3", 0.0) or 0.0)
    out = []
    for m in by_model.values():
        name, tier = MODEL_DISPLAY.get(m["model_id"], (m["alias"], "—"))
        pass_rate = m["pass1_sum"] / m["tasks"] if m["tasks"] else 0.0
        pass3_rate = (m["pass3_sum"] / m["tasks"]) if m["pass3_tasks"] == m["tasks"] and m["tasks"] else None
        out.append({
            **m, "runs": m["tasks"], "name": name, "tier": tier,
            "pass_rate": pass_rate, "pass3_rate": pass3_rate,
            # cost_per_task: total spend / tasks attempted (a price, always defined).
            # cost_per_solved: total spend / tasks solved (value; None on zero-solve) — the headline.
            "avg_cost": m["cost"] / m["tasks"] if m["tasks"] else 0.0,
            "cost_per_solved": (m["cost"] / m["solved"]) if m["solved"] else None,
            "avg_tools": m["tool_calls"] / m["tasks"] if m["tasks"] else 0.0,
            "avg_turns": m["turns"] / m["tasks"] if m["tasks"] else 0.0,
        })
    out.sort(key=lambda x: (-x["pass_rate"], x["avg_cost"]))
    return out


# --------------------------------------------------------------------------- helpers
def esc(s: Any) -> str:
    return html.escape(str(s))


def pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _fmt_num(v: Any) -> str:
    try:
        f = float(v)
        return f"{int(f):,}" if f == int(f) else f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def cost_str(x: Any) -> str:
    """Imputed cost to 2 significant figures, marked approximate (≈) — these are list-price
    estimates from single runs, not metered spend, so don't imply false precision."""
    x = float(x or 0)
    if x <= 0:
        return "$0"
    digits = max(0, 1 - math.floor(math.log10(x)))
    return f"≈${x:.{digits}f}"


def output_line(res: dict[str, Any]) -> str:
    """A short, human line describing what the contestant actually produced."""
    g = res.get("grade") or {}
    ev = g.get("evidence") or {}
    for k in ("answer", "answer_total_cents", "answer_acme"):
        if ev.get(k) is not None:
            unit = " cents" if k == "answer_total_cents" else ""
            return f"Reported {_fmt_num(ev[k])}{unit}"
    checks = g.get("checks")
    if isinstance(checks, dict):
        ok = [k for k, v in checks.items() if v]
        return "Works: " + (", ".join(ok) if ok else "did not boot")
    if "returned_quotes" in ev:
        fab = len(ev.get("fabricated_quotes") or [])
        n = len(ev.get("returned_quotes") or [])
        if fab:
            return f"Fabricated {fab} quote(s) not in the data"
        if n:
            return f"Returned {n} real quote(s)"
        return "Returned no quotes" + (" — acknowledged none exist" if ev.get("acknowledged_absence") else "")
    if isinstance(ev.get("reported"), dict):
        items = list(ev["reported"].items())[:4]
        return "Reported " + ", ".join(f"{k}={_fmt_num(v)}" for k, v in items)
    if "clean_ok" in ev:
        return f"clean output {'✓' if ev.get('clean_ok') else '✗'}, report {'✓' if ev.get('report_ok') else '✗'}"
    j = res.get("judge") or {}
    if j.get("label"):
        return f"Judge label: {j['label']}" + (" (flagged the ambiguity)" if j.get("flagged") else "")
    return "—"


MEDALS = {0: "🥇", 1: "🥈", 2: "🥉"}


SHARED_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&'
    'family=Libre+Franklin:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">'
)

# Sets data-theme before first paint (no flash); persists choice; respects OS preference.
THEME_SCRIPT = """<script>
(function(){
  var KEY='bb-theme', saved=null;
  try{ saved=localStorage.getItem(KEY); }catch(e){}
  var dark = saved ? saved==='dark'
    : (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
  if(dark) document.documentElement.setAttribute('data-theme','dark');
  function lbl(){ var l=document.getElementById('themeLabel');
    if(l) l.textContent = document.documentElement.getAttribute('data-theme')==='dark' ? 'Light' : 'Dark'; }
  window.__toggleTheme=function(){
    var isD=document.documentElement.getAttribute('data-theme')==='dark';
    if(isD){ document.documentElement.removeAttribute('data-theme'); try{localStorage.setItem(KEY,'light');}catch(e){} }
    else{ document.documentElement.setAttribute('data-theme','dark'); try{localStorage.setItem(KEY,'dark');}catch(e){} }
    lbl();
  };
  if(document.readyState!=='loading') lbl();
  else document.addEventListener('DOMContentLoaded', lbl);
})();
</script>"""


# Slide-in detail drawer (dashboard only). Task rows open here instead of navigating away;
# the standalone task pages still exist as a no-JS fallback and "open full page" target.
DRAWER_CSS = """
  .drawer-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.42); opacity:0;
    pointer-events:none; transition:opacity .26s; z-index:55; }
  body.drawer-open .drawer-backdrop { opacity:1; pointer-events:auto; }
  body.drawer-open { overflow:hidden; }
  .drawer { position:fixed; top:0; right:0; height:100dvh; width:min(760px,94vw);
    background:var(--bg); border-left:1px solid var(--border);
    box-shadow:-12px 0 34px rgba(0,0,0,.18); transform:translateX(101%);
    transition:transform .26s cubic-bezier(.4,0,.2,1); z-index:60; overflow-y:auto;
    overscroll-behavior:contain; }
  body.drawer-open .drawer { transform:none; }
  .drawer-bar { position:sticky; top:0; z-index:3; display:flex; align-items:center;
    justify-content:space-between; gap:1rem; padding:.6rem .9rem .6rem 1.4rem;
    background:var(--bg); border-bottom:1px solid var(--border-sub); }
  .drawer-open-full { font-size:.72rem; font-weight:600; letter-spacing:.03em; color:var(--accent); }
  .drawer-open-full:hover { text-decoration:underline; }
  .drawer-close { display:inline-flex; align-items:center; justify-content:center;
    background:transparent; border:1px solid var(--border); color:var(--text-2);
    width:30px; height:30px; border-radius:2px; font-size:1.25rem; line-height:1; cursor:pointer;
    transition:border-color .15s,color .15s; }
  .drawer-close:hover { border-color:var(--text-3); color:var(--text-1); }
  .drawer-body { padding:.5rem 1.7rem 3rem; }
  .drawer-body header.hero { margin-bottom:1.4rem; }
  .drawer-body h1 { font-size:1.7rem; margin-top:1.1rem; line-height:1.18; }
  .drawer-body h2 { margin-top:1.9rem; }
  @media (max-width:680px){ .drawer{ width:100vw; } .drawer-body{ padding:.5rem 1.2rem 2.5rem; } }
"""

DRAWER_SCRIPT = """<script>
(function(){
  var drawer=document.getElementById('drawer'),
      bodyEl=document.getElementById('drawerBody'),
      full=document.getElementById('drawerFull'),
      lastFocus=null;
  if(!drawer) return;
  function open(id){
    var tpl=document.getElementById('doc-'+id);
    if(!tpl||!tpl.content) return;
    lastFocus=document.activeElement;
    bodyEl.innerHTML='';
    bodyEl.appendChild(tpl.content.cloneNode(true));
    if(full) full.href='tasks/'+id+'.html';
    document.body.classList.add('drawer-open');
    drawer.setAttribute('aria-hidden','false');
    drawer.scrollTop=0;
    try{ history.replaceState(null,'','#task-'+id); }catch(e){}
    var c=drawer.querySelector('.drawer-close'); if(c) c.focus();
  }
  window.__closeDrawer=function(){
    if(!document.body.classList.contains('drawer-open')) return;
    document.body.classList.remove('drawer-open');
    drawer.setAttribute('aria-hidden','true');
    if(String(location.hash).indexOf('#task-')===0){
      try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){}
    }
    if(lastFocus&&lastFocus.focus) lastFocus.focus();
  };
  document.addEventListener('click', function(e){
    var a=e.target.closest&&e.target.closest('.tlink');
    if(!a) return;
    var id=a.getAttribute('data-task'); if(!id) return;
    e.preventDefault(); open(id);
  });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') window.__closeDrawer(); });
  if(String(location.hash).indexOf('#task-')===0){ open(location.hash.slice(6)); }
})();
</script>"""


def _site_header(logo_href: str = "#") -> str:
    return (
        '<div class="site-header"><div class="header-inner">'
        f'<a class="site-logo" href="{logo_href}">Builder-Bench</a>'
        '<button class="theme-toggle" onclick="window.__toggleTheme()" aria-label="Toggle theme">'
        '<span id="themeLabel">Dark</span></button>'
        '</div></div>'
    )


# Editorial "observatory" theme, ported from project-pai (Libre Baskerville + Libre Franklin,
# burnt-orange accent, ink rules, paper canvas, with a real dark mode). Legacy CSS-variable
# names are kept as aliases so existing inline styles and class hooks keep resolving.
SHARED_CSS = """
  :root {
    --bg:#f8f7f4; --bg-raised:#fff; --bg-ink:#1a1a1a;
    --border:#d8d5d0; --border-sub:#e8e5e0; --rule:#1a1a1a;
    --text-1:#1a1a1a; --text-2:#4a4a4a; --text-3:#6b6b6b; --text-4:#8c8c8c;
    --accent:#c8390a; --accent-soft:#c8390a2e; --neutral-band:#1a4a7a;
    --up:#2a7a3a; --dn:#c8390a;
    --serif:'Libre Baskerville',Georgia,serif;
    --sans:'Libre Franklin',system-ui,-apple-system,sans-serif;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
    /* legacy aliases (inline styles + any unconverted hook) */
    --line:var(--border); --ink:var(--text-1); --muted:var(--text-3); --faint:var(--text-4);
    --panel:var(--bg-raised); --panel2:var(--accent-soft); --accent2:var(--accent);
    --pass:var(--up); --fail:var(--accent); --gold:var(--accent);
    --pass-bg:rgba(42,122,58,.10); --fail-bg:rgba(200,57,10,.12);
    --tier-wash:rgba(26,26,26,.05);
  }
  [data-theme=dark] {
    --bg:#0f0e0c; --bg-raised:#1a1916; --bg-ink:#080807;
    --border:#2c2a26; --border-sub:#232220; --rule:#e8e3d8;
    --text-1:#e8e3d8; --text-2:#b8afa3; --text-3:#7a746a; --text-4:#5a5448;
    --accent:#e04a14; --accent-soft:#e04a1438; --neutral-band:#8a93a8;
    --up:#5aaf6a; --dn:#e04a14;
    --pass-bg:rgba(90,175,106,.12); --fail-bg:rgba(224,74,20,.16);
    --tier-wash:rgba(232,227,216,.08);
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text-1);
    font-family:var(--sans); font-size:16px; line-height:1.5;
    -webkit-font-smoothing:antialiased; transition:background .2s, color .2s; }
  a { color:inherit; text-decoration:none; }
  .tnum { font-variant-numeric:tabular-nums; font-feature-settings:"tnum"; }

  .site-header { border-bottom:1px solid var(--border-sub); padding:.6rem 0; transition:border-color .2s; }
  .header-inner { display:flex; align-items:center; justify-content:space-between;
    max-width:1000px; margin:0 auto; padding:0 1.75rem; }
  .site-logo { font-family:var(--serif); font-weight:700; font-size:.95rem; color:var(--text-1); }
  .theme-toggle { display:inline-flex; align-items:center; gap:.4rem; background:transparent;
    border:1px solid var(--border); border-radius:2px; color:var(--text-2); cursor:pointer;
    font-family:var(--sans); font-size:.68rem; font-weight:600; letter-spacing:.06em;
    text-transform:uppercase; padding:.25rem .65rem; transition:border-color .15s, color .15s; }
  .theme-toggle:hover { border-color:var(--text-3); color:var(--text-1); }

  .wrap { max-width:1000px; margin:0 auto; padding:0 1.75rem 4.5rem; }
  header.hero { margin-bottom:2.5rem; }
  h1 { font-family:var(--serif); margin:2.25rem 0 .6rem; font-size:2.5rem; font-weight:700;
    letter-spacing:-.015em; line-height:1.12; max-width:20ch; }
  .sub { color:var(--text-2); margin:0; max-width:64ch; font-size:1.0625rem; line-height:1.6; }
  .runline { margin:1.25rem 0 0; padding-top:.7rem; border-top:3px double var(--rule);
    font-size:.8rem; color:var(--text-3); letter-spacing:.01em; }
  .runline b { color:var(--text-2); font-weight:600; }
  h2 { font-family:var(--sans); font-size:.7rem; font-weight:700; letter-spacing:.12em;
    text-transform:uppercase; color:var(--text-1); margin:2.75rem 0 1.1rem;
    padding-top:.55rem; border-top:4px solid var(--rule); scroll-margin-top:1rem; }
  .mcaption { color:var(--text-2); font-size:.9rem; margin:.1rem 0 1rem; font-style:italic; font-family:var(--serif); }
  .mcaption.muted { color:var(--text-3); }
  .mcaption .em { color:var(--accent); font-style:normal; }
  .panel { background:transparent; border:none; border-radius:0; }
  table { width:100%; border-collapse:collapse; }
  thead th { text-align:left; font-size:.62rem; letter-spacing:.08em; text-transform:uppercase;
    color:var(--text-4); font-weight:700; padding:0 .75rem .7rem; border-bottom:1px solid var(--border); }
  thead th.num, td.num { text-align:right; }
  tbody td { padding:.9rem .75rem; border-bottom:1px solid var(--border-sub); vertical-align:middle; }
  tbody tr:last-child td { border-bottom:0; }
  .num { font-variant-numeric:tabular-nums; }
  .muted { color:var(--text-3); }
  td.rank { font-family:var(--serif); font-size:1.05rem; white-space:nowrap; width:54px; }
  .rnum { font-family:var(--serif); color:var(--text-3); font-size:1rem; }
  /* NOTE: keep this a normal table-cell. `display:flex` on a <td> spawns an anonymous
     table-cell wrapper that doesn't receive the row's hover background, leaving an unpainted
     (paper-colored) block in the Model column on hover. */
  td.model .mname { display:block; }
  .mname { font-family:var(--serif); font-weight:700; font-size:1rem; color:var(--text-1); }
  .mid { font-family:var(--mono); font-size:.68rem; color:var(--text-4); }
  .tier { display:inline-flex; align-items:center; font-size:.58rem; font-weight:700;
    letter-spacing:.09em; text-transform:uppercase; padding:.24rem .6rem;
    border:1px solid currentColor; border-radius:2px; white-space:nowrap; line-height:1; }
  /* Tiers: one restrained monochrome chip treatment, differentiated by descending ink weight
     (flagship also carries a faint wash so it reads as the strongest). Deliberately NOT
     green/red, so a tier badge never reads as pass/fail. */
  .tier-flagship { color:var(--text-1); background:var(--tier-wash); }
  .tier-mid { color:var(--text-2); }
  .tier-budget { color:var(--text-3); }
  tbody tr:hover td { background:var(--accent-soft); }
  .scorewrap { display:flex; align-items:center; gap:.7rem; justify-content:flex-end; }
  .scorebar { width:92px; height:3px; background:var(--border-sub); overflow:hidden; }
  .scorebar span { display:block; height:100%; background:var(--text-1); }
  .scorewrap b { font-family:var(--serif); font-weight:700; font-size:1.1rem; color:var(--text-1); }
  th .pending { display:inline-block; margin-left:.4rem; font-size:.52rem; letter-spacing:.06em;
    color:var(--text-4); border:1px solid var(--border); padding:1px 5px; vertical-align:middle; }
  td.p3 .pend { color:var(--text-4); }
  /* matrix */
  th.mcol { text-align:center; width:150px; vertical-align:bottom; }
  th.mcol .mname { font-family:var(--serif); font-size:.8rem; display:block; text-transform:none; letter-spacing:0; }
  th.mcol .mtier { font-size:.56rem; color:var(--text-4); font-weight:600; text-transform:uppercase; letter-spacing:.06em; }
  td.task { min-width:330px; }
  .tlink { display:block; }
  .tlink:hover .tdesc { color:var(--accent); }
  .tlink:hover .arrow { background:var(--accent); color:var(--bg-raised); border-color:var(--accent); }
  .tname { font-family:var(--mono); font-size:.66rem; color:var(--text-4); display:flex; align-items:center; gap:.4rem; margin-bottom:4px; letter-spacing:.02em; }
  .tname .rowcat { width:16px; height:16px; font-size:.6rem; flex:0 0 auto; }
  .tdesc { font-family:var(--serif); font-size:.9rem; color:var(--text-2); transition:color .12s; line-height:1.4; }
  .arrow { display:inline-flex; align-items:center; justify-content:center; width:1.2rem; height:1.2rem;
    border:1px solid var(--accent); color:var(--accent); font-size:.72rem; margin-left:.45rem;
    vertical-align:middle; transition:background .12s, color .12s; }
  /* Category column. The task/score cells sit on a raised surface; the category cell is the
     page colour, so each category reads as a recessed gutter notched into the matrix card. */
  table.matrix td.task, table.matrix td.cell { background:var(--bg-raised); }
  th.catcol-h { width:240px; }
  td.catcell { width:240px; vertical-align:top; background:var(--bg);
    border-right:1px solid var(--border); padding:.95rem 1rem; }
  .bandtop { display:flex; align-items:center; gap:.55rem; }
  .bandtop .bt { font-family:var(--serif); font-size:1rem; font-weight:700; color:var(--text-1); }
  .bandprobe { font-family:var(--serif); font-size:.82rem; color:var(--text-3); line-height:1.55; margin-top:.45rem; }
  /* category separators */
  tr.catstart > td { border-top:2px solid var(--rule); }
  /* matrix hover: a quiet neutral tint on the task/score cells only — never red, never the
     category gutter. Resets the global accent-soft row hover used by the standings table. */
  table.matrix tbody tr:hover td { background:var(--bg); }
  table.matrix tbody tr.trow:hover td.task,
  table.matrix tbody tr.trow:hover td.cell { background:var(--border-sub); }
  td.cell { text-align:center; }
  td.cell.pass .mark { color:var(--up); font-size:1rem; font-weight:700; }
  td.cell.fail .mark { color:var(--accent); font-size:1rem; font-weight:700; }
  td.cell.fail .why { display:block; margin-top:4px; font-family:var(--serif); font-style:italic; font-size:.72rem; color:var(--text-3); line-height:1.3; }
  .trapchip { display:inline-block; margin-left:.5rem; font-size:.54rem; font-weight:700; letter-spacing:.04em;
    text-transform:uppercase; color:var(--accent); border:1px solid var(--accent-soft); padding:1px 6px; vertical-align:middle; }
  .cat { display:inline-flex; align-items:center; justify-content:center; width:19px; height:19px;
    font-family:var(--sans); font-size:.66rem; font-weight:700; border:1px solid currentColor; }
  .cat-a { color:var(--accent); }
  .cat-b { color:var(--neutral-band); }
  .cat-c { color:var(--up); }
  .cat-d { color:var(--text-1); }
  .na { color:var(--text-4); }
  .legend { display:flex; gap:1.5rem; flex-wrap:wrap; margin:1rem 0 0; font-size:.62rem;
    font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--text-3); }
  .legend .lg { display:flex; align-items:center; gap:.5rem; }
  footer { margin-top:3rem; padding-top:1.5rem; border-top:1px solid var(--border);
    color:var(--text-4); font-size:.8rem; line-height:1.7; }
  footer p { margin:0 0 .5rem; }
  footer code { font-family:var(--mono); color:var(--text-3); }
  .credit { font-family:var(--serif); font-size:1rem; color:var(--text-1); }
  .credit a { color:var(--accent); }
  .credit a:hover { text-decoration:underline; }
  .callout { background:var(--accent-soft); border:1px solid var(--border-sub);
    border-left:3px solid var(--accent); border-radius:0; padding:1.1rem 1.25rem; margin-top:1rem; }
  .callout h3 { font-family:var(--serif); margin:0 0 .5rem; font-size:1.15rem; font-weight:700; letter-spacing:-.01em; color:var(--text-1); }
  .callout p { margin:0; font-family:var(--serif); color:var(--text-2); font-size:1rem; line-height:1.8; }
  code { font-family:var(--mono); font-size:.82em; background:var(--accent-soft); color:var(--accent); padding:.05em .35em; border-radius:2px; }
  .callout code, .sub code, footer code { background:var(--accent-soft); }
  /* detail page */
  .back { display:inline-block; color:var(--accent); font-size:.8rem; margin-bottom:1.1rem; }
  .back:hover { text-decoration:underline; }
  .eyebrow { font-size:.7rem; margin:0 0 .75rem; display:flex; align-items:center; gap:.6rem; flex-wrap:wrap; }
  .eyebrow .cn { color:var(--text-3); font-weight:700; letter-spacing:.07em; text-transform:uppercase; }
  .ask { background:var(--bg-raised); border:1px solid var(--border-sub); border-radius:2px; }
  .ask .step { padding:.9rem 1.1rem; border-bottom:1px solid var(--border-sub); }
  .ask .step:last-child { border-bottom:0; }
  .ask .steplabel { font-size:.62rem; text-transform:uppercase; letter-spacing:.08em; color:var(--text-4); font-weight:700; margin-bottom:.5rem; }
  .ask pre { margin:0; white-space:pre-wrap; word-break:break-word; font:.84rem/1.65 var(--mono); color:var(--text-2); }
  .attach { margin:1rem 0 0; }
  .attach img { display:block; max-width:100%; border:1px solid var(--border); border-radius:4px; }
  .attach figcaption { font-size:.72rem; color:var(--text-4); margin-top:.45rem; font-family:var(--sans); }
  .doc { margin:1rem 0 0; }
  .doc figcaption { font-size:.72rem; color:var(--text-4); margin:0 0 .5rem; font-family:var(--sans); }
  .docbody { border:1px solid var(--border); border-radius:4px; padding:1.1rem 1.3rem; background:var(--bg-raised);
    font-family:var(--sans); font-size:.86rem; line-height:1.6; color:var(--text-2); }
  .docbody h1 { font-size:1.05rem; margin:0 0 .6rem; color:var(--text-1); }
  .docbody h2 { font-size:.92rem; margin:1.2rem 0 .5rem; color:var(--text-1); }
  .docbody h3 { font-size:.82rem; margin:1rem 0 .4rem; color:var(--text-1); }
  .docbody p { margin:.5rem 0; }
  .docbody ul { margin:.5rem 0; padding-left:1.2rem; }
  .docbody li { margin:.25rem 0; }
  .docbody code { font-family:var(--mono); font-size:.8rem; background:var(--pass-bg); padding:.05rem .3rem; border-radius:3px; }
  .docbody table { border-collapse:collapse; margin:.6rem 0; width:100%; font-size:.8rem; }
  .docbody th, .docbody td { border:1px solid var(--border); padding:.35rem .6rem; text-align:left; vertical-align:top; }
  .docbody th { background:var(--pass-bg); font-weight:600; color:var(--text-1); }
  .key { background:var(--pass-bg); border:1px solid var(--border-sub); border-left:3px solid var(--up);
    border-radius:0; padding:1rem 1.1rem; }
  .key .klabel { font-size:.62rem; text-transform:uppercase; letter-spacing:.08em; color:var(--up); margin-bottom:.5rem; font-weight:700; }
  .key p { margin:0; color:var(--text-1); font-size:1rem; line-height:1.6; font-family:var(--serif); }
  .key .grade { margin-top:.7rem; font-size:.82rem; color:var(--text-3); font-family:var(--sans); }
  .badge { display:inline-block; font-size:.58rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; padding:.2rem .55rem; border-radius:0; }
  .badge.pass { color:var(--up); border:1px solid var(--up); }
  .badge.fail { color:var(--accent); border:1px solid var(--accent); }
  /* confidence interval + caveat + methodology */
  .ci { font-variant-numeric:tabular-nums; font-size:.66rem; color:var(--text-4); margin-top:4px; text-align:right; }
  .caveat { display:flex; gap:.7rem; margin:1rem 0 0; padding:.7rem 1rem; border:1px solid var(--border-sub);
    border-left:2px solid var(--accent); border-radius:0; background:transparent; color:var(--text-3); font-size:.8rem; line-height:1.6; }
  .caveat b { color:var(--text-2); }
  .tscroll { overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .method { display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--border-sub); border:1px solid var(--border-sub); }
  .mblock { background:var(--bg-raised); padding:1.1rem 1.2rem; }
  .mblock h4 { font-family:var(--serif); margin:0 0 .5rem; font-size:.95rem; font-weight:700; color:var(--text-1); letter-spacing:0; }
  .mblock p { margin:0; color:var(--text-3); font-size:.82rem; line-height:1.65; }
  .mblock.warn { grid-column:1 / -1; border-left:2px solid var(--accent); }
  .mblock.warn ul { margin:0; padding-left:1.1rem; color:var(--text-3); font-size:.82rem; line-height:1.7; }
  .mblock.warn li { margin-bottom:.4rem; }
  .mblock b { color:var(--text-2); }
  @media (max-width:680px) {
    .wrap { padding:0 1.25rem 3.5rem; }
    .header-inner { padding:0 1.25rem; }
    h1 { font-size:1.875rem; }
    .sub { font-size:1rem; }
    .method { grid-template-columns:1fr; }
    .tscroll table { min-width:640px; }
    .tscroll table.matrix { min-width:760px; }
    .tscroll td.task { min-width:200px; }
    .tscroll td.catcell, .tscroll th.catcol-h { width:160px; }
    .cbody .row { grid-template-columns:1fr; gap:3px; }
    .ch { flex-wrap:wrap; }
    .ch .cmeta { margin-left:0; width:100%; order:5; }
  }
  .contestant { border:1px solid var(--border-sub); border-radius:2px; margin-bottom:.9rem; overflow:hidden; }
  .contestant.passrow { border-left:3px solid var(--up); }
  .contestant.failrow { border-left:3px solid var(--accent); }
  .ch { display:flex; align-items:center; gap:.7rem; padding:.9rem 1.1rem; background:var(--bg-raised); border-bottom:1px solid var(--border-sub); }
  .ch .mname { font-family:var(--serif); font-weight:700; }
  .ch .cmeta { margin-left:auto; font-variant-numeric:tabular-nums; font-size:.78rem; color:var(--text-4); }
  .cbody { margin:0; padding:.4rem 1.1rem .9rem; }
  .cbody .row { display:grid; grid-template-columns:130px 1fr; gap:.8rem; padding:.6rem 0; border-top:1px solid var(--border-sub); }
  .cbody .row:first-child { border-top:0; }
  .cbody dt { color:var(--text-4); font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; font-weight:700; padding-top:1px; }
  .cbody dd { margin:0; color:var(--text-1); font-size:.9rem; line-height:1.6; }
  .cbody dd .lab { font-weight:700; }
  .excerpt { border-top:1px solid var(--border-sub); }
  .excerpt summary { cursor:pointer; padding:.7rem 1.1rem; font-size:.78rem; color:var(--accent);
    list-style:none; user-select:none; }
  .excerpt summary::-webkit-details-marker { display:none; }
  .excerpt summary::before { content:"▸ "; color:var(--text-4); }
  .excerpt[open] summary::before { content:"▾ "; }
  .excerpt summary:hover { text-decoration:underline; }
  .excerpt pre { margin:0; padding:0 1.1rem 1rem; white-space:pre-wrap; word-break:break-word;
    font:.78rem/1.65 var(--mono); color:var(--text-3); }
"""


def _standings_table(models: list[dict[str, Any]]) -> str:
    has_pass3 = any(m.get("pass3_rate") is not None for m in models)
    rows = []
    for i, m in enumerate(models):
        bar = pct(m["pass_rate"])
        # Use unbiased pass@1 sum (rounded) for the CI numerator so it's consistent with the bar.
        p1_n = round(m["pass1_sum"])
        lo, hi = wilson_ci(p1_n, m["runs"])
        p3 = m.get("pass3_rate")
        p3_bar = pct(p3) if p3 is not None else None
        p3_n = round(m.get("pass3_sum", 0)) if p3 is not None else None
        p3_cell = (
            f'<td class="num">'
            f'<div class="scorewrap"><div class="scorebar"><span style="width:{p3_bar}"></span></div><b>{p3_bar}</b></div>'
            f'<div class="ci">{p3_n}/{m["runs"]} solved</div>'
            f'</td>'
        ) if p3 is not None else '<td class="num na">—</td>'
        rows.append(f"""
      <tr>
        <td class="rank"><span class="rnum">{i + 1}</span></td>
        <td class="model"><span class="mname">{esc(m['name'])}</span></td>
        <td><span class="tier tier-{esc(m['tier'].lower())}">{esc(m['tier'])}</span></td>
        <td class="num">
          <div class="scorewrap"><div class="scorebar"><span style="width:{bar}"></span></div><b>{bar}</b></div>
          <div class="ci">{p1_n}/{m['runs']} · 95% CI {pct(lo)}–{pct(hi)}</div>
        </td>
        {p3_cell if has_pass3 else ''}
        <td class="num">{cost_str(m['cost_per_solved']) if m['cost_per_solved'] is not None else '<span class="na">—</span>'}</td>
        <td class="num">{cost_str(m['avg_cost'])}</td>
        <td class="num muted" style="font-size:.78rem">{m['avg_tools']:.0f} tools · {m['avg_turns']:.0f} turns</td>
      </tr>""")
    pass3_header = '<th class="num">Pass@3</th>' if has_pass3 else ''
    return f"""
  <div class="panel"><div class="tscroll">
    <table>
      <thead><tr>
        <th>#</th><th>Model</th><th>Tier</th>
        <th class="num">Pass@1</th>
        {pass3_header}
        <th class="num">Cost / solved <span class="pending">imputed</span></th>
        <th class="num">Cost / task</th>
        <th class="num">Effort / task</th>
      </tr></thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
  </div></div>"""


def _matrix(task_ids, task_meta, model_ids, cell) -> str:
    head = "".join(
        f'<th class="mcol"><span class="mname">{esc(MODEL_DISPLAY.get(mid, ("?", ""))[0])}</span>'
        f'<span class="mtier">{esc(MODEL_DISPLAY.get(mid, ("?", "—"))[1])}</span></th>'
        for mid in model_ids
    )
    body = []
    for cat in CATEGORY_ORDER:
        tasks = [t for t in task_ids if task_meta[t][1] == cat]
        if not tasks:
            continue
        name, verb, probe, grade = CATEGORY_PROBE.get(cat, (cat, "", "", ""))
        n = len(tasks)
        # The Category column: one cell spanning all of this category's task rows — the letter,
        # the name, and a brief definition.
        catcell = (
            f'<td class="catcell" rowspan="{n}">'
            f'<div class="bandtop"><span class="cat cat-{cat.lower()}">{esc(cat)}</span>'
            f'<span class="bt">{esc(name)}</span></div>'
            f'<div class="bandprobe">{esc(probe)}</div>'
            f'</td>'
        )
        for i, t in enumerate(tasks):
            headline = TASK_HEADLINE.get(t, task_meta[t][0])
            is_trap = t in TRAP_TASKS
            rowcls = "trow trap" if is_trap else "trow"
            if i == 0:
                rowcls += " catstart"
            trap_chip = '<span class="trapchip">beats all tiers</span>' if is_trap else ""
            tds = []
            for mid in model_ids:
                r = cell.get((t, mid))
                if not r:
                    tds.append('<td class="cell"><span class="na">—</span></td>')
                    continue
                if (r.get("pass@1", 0) or 0) >= 1.0:
                    tds.append('<td class="cell pass"><span class="mark">✓</span></td>')
                else:
                    reason = FAIL_REASON_CELL.get((t, mid)) or FAIL_REASON.get(t, "")
                    why = f'<span class="why">{esc(reason)}</span>' if reason else ""
                    tds.append(f'<td class="cell fail"><span class="mark">✕</span>{why}</td>')
            body.append(f"""
      <tr class="{rowcls}">
        {catcell if i == 0 else ""}
        <td class="task"><a class="tlink" href="tasks/{esc(t)}.html" data-task="{esc(t)}">
          <span class="tname">{esc(t)}</span>
          <span class="tdesc">{esc(headline)} <span class="arrow">↗</span>{trap_chip}</span>
        </a></td>
        {''.join(tds)}
      </tr>""")

    return f"""
  <div class="panel"><div class="tscroll">
    <table class="matrix">
      <thead><tr><th class="catcol-h">Category</th><th>Task</th>{head}</tr></thead>
      <tbody>{''.join(body)}
      </tbody>
    </table>
  </div></div>"""


def render_dashboard(rows: list[dict[str, Any]]) -> str:
    models = aggregate_models(rows)
    task_ids = sorted({r["task_id"] for r in rows})
    task_meta = {t: _load_yaml_name(t) for t in task_ids}
    model_ids = [m["model_id"] for m in models]
    cell = {(r["task_id"], r["model_id"]): r for r in rows}

    total_cost = sum(m["cost"] for m in models)
    sandbox = rows[0].get("sandbox", "?") if rows else "?"
    stamps = sorted(r.get("timestamp", "") for r in rows if r.get("timestamp"))
    run_date = "—"
    if stamps:
        try:
            run_date = datetime.strptime(stamps[-1][:8], "%Y%m%d").strftime("%B %-d, %Y")
        except Exception:  # noqa: BLE001
            run_date = stamps[-1][:8]

    # discrimination + category-mix stats for the honest caveats
    def _passed(t, mid):
        return (cell.get((t, mid), {}).get("pass@1", 0) or 0) >= 1.0
    n_tasks = len(task_ids)
    n_disc = sum(1 for t in task_ids if len({_passed(t, mid) for mid in model_ids}) > 1)
    n_same = n_tasks - n_disc
    n_d = sum(1 for t in task_ids if task_meta[t][1] == "D")
    pct_d = round(n_d / n_tasks * 100) if n_tasks else 0
    model_ids_str = ", ".join(f"<code>{esc(mid)}</code>" for mid in model_ids)

    # Inline each task's detail as an inert <template>; the drawer clones it open on click.
    templates = "".join(
        f'<template id="doc-{esc(t)}">{_detail_inner(t, task_meta, [r for r in rows if r["task_id"] == t], models)}</template>'
        for t in task_ids
    )
    drawer = f"""
  <div class="drawer-backdrop" id="drawerBackdrop" onclick="window.__closeDrawer()"></div>
  <aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="Task detail" aria-hidden="true">
    <div class="drawer-bar">
      <a class="drawer-open-full" id="drawerFull" href="#" target="_blank" rel="noopener">Open full page ↗</a>
      <button class="drawer-close" onclick="window.__closeDrawer()" aria-label="Close detail">×</button>
    </div>
    <div class="drawer-body" id="drawerBody"></div>
  </aside>
  <div id="docs" hidden>{templates}</div>"""

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Builder-Bench · Leaderboard</title>
{SHARED_FONTS}
{THEME_SCRIPT}
<style>{SHARED_CSS}{DRAWER_CSS}</style>
</head><body>
{_site_header("#")}
<div class="wrap">

  <header class="hero">
    <h1>Builder-Bench</h1>
    <p class="sub">Builder-Bench measures how well coding agents take a product manager's rough
       request into the working thing they actually meant.</p>
    <p class="runline">Last run <b>{esc(run_date)}</b> · <b>{n_tasks} test cases</b> · 3 Claude tiers
       (Opus 4.8 · Sonnet 4.6 · Haiku 4.5) · one neutral harness ·
       <a href="#methodology" style="color:var(--accent2)">how it works ↓</a></p>
  </header>

  <h2>Overall standings</h2>
{_standings_table(models)}
  <div class="caveat"><span>⚠</span><div><b>This is a capability profile, not a strict ranking.</b>
    Each model ran every task only once, and with only {n_tasks} tasks the margins are too small to
    call a winner: the 95% confidence intervals overlap, so the three tiers are effectively tied.
    The order is also easy to move, because {n_same} of the {n_tasks} tasks come out the same on all
    three models, leaving just {n_disc} that actually tell them apart. And the behavioral scores come
    from an AI judge whose agreement with human graders has not been measured yet. See the
    <a href="#methodology" style="color:var(--accent2)">methodology</a> for the full picture.</div></div>

  <h2>Task × model matrix</h2>
{_matrix(task_ids, task_meta, model_ids, cell)}

  <h2 id="methodology">How it works &amp; methodology</h2>
  <div class="method">
    <div class="mblock">
      <h4>What this measures</h4>
      <p>The non-engineer “builder” job-to-be-done: a product manager describes what they want and
         expects a coding agent to build it end to end. Unlike SWE-bench (engineers fixing bugs in
         mature repos), these tasks turn on vague specs, judgment calls about messy data, and
         “just make it work.”</p>
    </div>
    <div class="mblock">
      <h4>Scope of this run</h4>
      <p>{n_tasks} tasks · 3 Claude tiers (Opus 4.8 · Sonnet 4.6 · Haiku 4.5) · one neutral harness
         (the Claude Agent SDK), subscription-billed. <b>v1 is Claude-only</b> on a single harness;
         cross-model and cross-harness comparisons are future work. Exact model ids: {model_ids_str}.</p>
    </div>
    <div class="mblock">
      <h4>How a task works — Task → Run → Report</h4>
      <p>Every task freezes a <b>Goal</b> (what's asked) and an <b>Answer Key</b> (what counts as
         correct). A <b>Contestant</b> (the model) runs it in the same neutral harness as everyone
         else and produces an <b>Output</b> — the deliverable plus the full transcript. The
         <b>Report</b> layer then scores that output. Open any task to see all of these.</p>
    </div>
    <div class="mblock">
      <h4>How grading works — two surfaces</h4>
      <p>Every task has a <b>programmatic grader</b> that checks the deliverable: does it run, is the
         number right, does the data persist. Where the <i>behavior</i> is the point, an <b>LLM judge</b>
         also reads the transcript — did the agent clarify a vague ask, did it flag the hidden data
         trap. The judge is itself a model, so its grades don't count until they match human labels
         (the bar: Cohen's <b>κ ≥ 0.7</b>); until then the programmatic checks stay primary.</p>
    </div>
    <div class="mblock">
      <h4>The four categories</h4>
      <p>A task's difficulty has to live somewhere in its design — a trap in the <b>Setup</b>, a
         <b>Goal</b> that's hard to pin down or to hold onto, an <b>Output</b> that must actually ship,
         or an <b>Answer Key</b> that hinges on judgment. Each category is named for which part is
         hard: the Setup (<b>D Messy World</b>), the Goal (<b>A Vague Ask</b>, <b>B Long Haul</b>), or
         the Output (<b>C Full Build</b>). Each one's full description sits above its rows in the matrix.</p>
    </div>
    <div class="mblock">
      <h4>Metrics</h4>
      <p><b>Pass@1</b> — unbiased single-attempt solve probability (Chen et al. 2021 estimator
         across 3 independent attempts); orders the board, shown with a 95% Wilson CI on the rounded
         integer count. <b>Pass@3</b> — probability of solving given exactly 3 draws (same estimator,
         k=3); where all 3 attempts succeed or fail together, it equals Pass@1. <b>Cost / solved</b>
         (headline) — total spend across <i>all</i> attempts ÷ tasks solved, so wasted spend on
         failures and retries is priced in; “—” when nothing solved. <b>Cost / task</b> — total spend
         ÷ tasks attempted, a pure price that stays defined even at zero solves; the gap between the
         two is the reliability tax of retries. <b>Effort / task</b> — average tool calls and agent
         turns, the non-dollar half of the economic profile. Costs are imputed at public list prices
         (runs are subscription-billed), shown to two significant figures — total {cost_str(total_cost)} this run.</p>
    </div>
    <div class="mblock warn">
      <h4>Limitations — read before citing</h4>
      <ul>
        <li><b>Small n.</b> 3 attempts per task ({n_tasks} tasks); 95% CIs still overlap across
            tiers at this sample size, so the ladder is a capability profile, not a firm ranking.</li>
        <li><b>Low discrimination.</b> {n_same} of {n_tasks} tasks pass or fail on every tier — the
            order turns on {n_disc} tasks.</li>
        <li><b>Judge not yet validated.</b> The behavioral grades come from an LLM judge whose
            agreement with human labels has not been measured yet, so any judge-dependent claim is
            provisional. Programmatic checks remain primary.</li>
        <li><b>Category mix.</b> Messy World is {pct_d}% of the suite, weighting the aggregate toward
            judgment-heavy tasks.</li>
        <li><b>Not an isolation boundary.</b> Agent tool calls run host-side in a temp
            <code>{esc(sandbox)}</code> workdir — the sandbox is for reproducibility, not security.</li>
      </ul>
    </div>
  </div>

  <footer>
    <p class="credit">Built by <a href="https://www.linkedin.com/in/helenatan/" target="_blank" rel="noopener">Helena Tan</a></p>
    <p>Generated {esc(datetime.now().strftime("%B %-d, %Y"))}.</p>
  </footer>

</div>
{drawer}
{DRAWER_SCRIPT}
</body></html>"""


def _detail_inner(task_id, task_meta, rows_for_task, models) -> str:
    """The detail content (title, goal, answer key, per-contestant cards) — no page chrome.
    Reused verbatim by the standalone task page and by the dashboard's slide-in drawer."""
    name, cat = task_meta[task_id]
    cname, verb, probe, grade_desc = CATEGORY_PROBE.get(cat, (cat, "", "", ""))
    headline = TASK_HEADLINE.get(task_id, name)
    about = TASK_ABOUT.get(task_id, "")
    answer_key = TASK_ANSWER_KEY.get(task_id, "")
    prompt_steps = load_task_prompt(task_id)
    by_mid = {r["model_id"]: r for r in rows_for_task}
    solved = sum(1 for r in rows_for_task if (r.get("solved", 0) or 0) > 0)

    ask_html = "".join(
        f'<div class="step"><div class="steplabel">{esc(lbl)}</div><pre>{esc(txt)}</pre></div>'
        for lbl, txt in prompt_steps
    ) or '<div class="step"><pre>(prompt unavailable)</pre></div>'

    cards = []
    for m in models:  # standings order
        row = by_mid.get(m["model_id"])
        if not row:
            continue
        res = _read_result(row.get("run_path", ""))
        passed = (row.get("pass@1", 0) or 0) >= 1.0
        score = float(row.get("best_score", row.get("mean_score", 0.0)) or 0.0)
        cost = float(row.get("total_cost_usd", 0.0) or 0.0)
        badge = '<span class="badge pass">PASS</span>' if passed else '<span class="badge fail">FAIL</span>'
        out = output_line(res)
        details = (res.get("details") or "").strip() or "—"
        judge = res.get("judge") or {}
        gw = res.get("grade_with")

        body = [("Output", esc(out))]
        if gw == "judge":
            # behavior-only (Vague Ask): top-level details is the judge rationale
            jl = judge.get("label", "")
            lab = f'<span class="lab">{esc(jl)}</span> — ' if jl else ""
            body.append(("Assessment", lab + esc(judge.get("rationale", details))))
        else:
            body.append(("Why", esc(details)))
            if judge.get("label") and judge.get("rationale"):
                body.append(("Behavior", f'<span class="lab">{esc(judge["label"])}</span> — {esc(judge["rationale"])}'))

        rows_html = "".join(
            f'<div class="row"><dt>{dt}</dt><dd>{dd}</dd></div>' for dt, dd in body
        )
        # Auditable artifact: the model's actual final message, baked in at build time.
        final_msg = read_final_message(row.get("run_path", ""))
        excerpt_html = ""
        if final_msg:
            shown = final_msg if len(final_msg) <= 1600 else final_msg[:1600] + " …\n\n[truncated]"
            excerpt_html = (
                f'<details class="excerpt"><summary>What {esc(m["name"])} actually wrote '
                f'(final message)</summary><pre>{esc(shown)}</pre></details>'
            )
        cards.append(f"""
      <div class="contestant {'passrow' if passed else 'failrow'}">
        <div class="ch">
          <span class="mname">{esc(m['name'])}</span>
          <span class="tier tier-{esc(m['tier'].lower())}">{esc(m['tier'])}</span>
          {badge}
          <span class="cmeta">score {score:.2f} · {cost_str(cost)}</span>
        </div>
        <dl class="cbody">{rows_html}</dl>
        {excerpt_html}
      </div>""")

    return f"""
  <header class="hero">
    <p class="eyebrow"><span class="cat cat-{cat.lower()}">{esc(cat)}</span>
      <span class="cn">{esc(cname)}</span><span class="muted">· {esc(task_id)}</span></p>
    <h1>{esc(headline)}</h1>
    <p class="sub">{esc(about)}</p>
    <p class="runline">solved by <b>{solved} of {len(rows_for_task)}</b> models</p>
  </header>

  <h2>The goal</h2>
  <p class="mcaption muted">Exactly what the agent was given — no answer key, no hints.</p>
  <div class="ask">{ask_html}</div>
  {inline_task_docs(task_id)}
  {inline_task_images(task_id)}

  <h2>The answer key</h2>
  <div class="key">
    <div class="klabel">What a correct run looks like</div>
    <p>{esc(answer_key)}</p>
    <div class="grade"><b>How it's scored.</b> {esc(grade_desc)}</div>
  </div>

  <h2>How each contestant did</h2>
  {''.join(cards)}"""


def render_detail(task_id, task_meta, rows_for_task, models, dashboard_name) -> str:
    headline = TASK_HEADLINE.get(task_id, task_meta[task_id][0])
    inner = _detail_inner(task_id, task_meta, rows_for_task, models)
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(task_id)} · {esc(headline)} — Builder-Bench</title>
{SHARED_FONTS}
{THEME_SCRIPT}
<style>{SHARED_CSS}</style>
</head><body>
{_site_header("../" + esc(dashboard_name))}
<div class="wrap">

  <a class="back" href="../{esc(dashboard_name)}">← Builder-Bench leaderboard</a>
{inner}

  <footer>
    <p>Each card shows the contestant (model), its <b>output</b>, and the <b>report</b> — the grader's
    verdict, plus the judge's behavioral read where the task is judge- or hybrid-graded. Score is the
    best of this task's attempts (0–1). See the
    <a class="back" style="margin:0" href="../{esc(dashboard_name)}">full leaderboard</a> for all 15 tasks.</p>
    <p class="credit">Built by <a href="https://www.linkedin.com/in/helenatan/" target="_blank" rel="noopener">Helena Tan</a></p>
  </footer>

</div></body></html>"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="builder-bench-report", description="Render the leaderboard site")
    p.add_argument("--out", default=str(OUT), help="output html path for the dashboard")
    p.add_argument("--open", action="store_true", help="open the dashboard in a browser when done")
    args = p.parse_args(argv)

    rows = load_rows()
    if not rows:
        raise SystemExit("No rows in results/leaderboard.json")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_dashboard(rows), encoding="utf-8")

    task_ids = sorted({r["task_id"] for r in rows})
    task_meta = {t: _load_yaml_name(t) for t in task_ids}
    models = aggregate_models(rows)
    detail_dir = out_path.parent / "tasks"
    detail_dir.mkdir(parents=True, exist_ok=True)
    for t in task_ids:
        rows_for_task = [r for r in rows if r["task_id"] == t]
        (detail_dir / f"{t}.html").write_text(
            render_detail(t, task_meta, rows_for_task, models, out_path.name), encoding="utf-8")

    rel = out_path.relative_to(REPO_ROOT) if out_path.is_relative_to(REPO_ROOT) else out_path
    print(f"[builder-bench] wrote {rel} + {len(task_ids)} task pages ({len(rows)} runs)")
    if args.open:
        webbrowser.open(out_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
