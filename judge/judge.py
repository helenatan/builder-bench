"""The LLM judge — scores a run's Transcript against a per-task rubric.

Design goals (PRD §6, §9):
  - Same neutral, subscription-billed path as the runner: drives the Claude Agent SDK with
    no tools, one classification turn, host-broker/API-billing env vars stripped.
  - Named judge model (self-preference is checked during validation), recorded on every grade.
  - Structured, parseable output: {judge_score, label, flagged, rationale}.
  - The judge NEVER sees the expected answer or the reference solution — only the rubric and
    the agent's own transcript — so it grades behavior, not answer-key leakage.

Usage:
    # standalone (re-judge a logged run):
    python -m judge.judge results/runs/d-02/opus-4.6/<ts>/attempt-1/transcript.json --task d-02

    # programmatic (from the runner): call judge_transcript(...)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
# Rubrics are answer-key material: they live in the held-out private split (gitignored, not
# deployed) so a public clone/deploy can't leak the grading criteria to a future contestant.
# The in-repo judge/rubrics/ path is kept only as a fallback for local development.
PRIVATE_RUBRICS_DIR = REPO_ROOT / "private" / "rubrics"
RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"
TASKS_DIR = REPO_ROOT / "tasks"
# Per-task judge-evidence hooks (e.g. a-02's output-equivalence check) live beside the
# expected answers in the private split; see build_evidence_banner().
PRIVATE_EXPECTED_DIR = REPO_ROOT / "private" / "expected"

# The judge model is named so judge–human agreement can be computed per contestant model
# (a Claude judge must not grade Claude transcripts more kindly — PRD §6 step 5). Sonnet is
# the default: more capable than Haiku, cheaper than Opus, and not the flagship under test.
DEFAULT_JUDGE_MODEL = "claude-sonnet-4-6"

_LABEL_SCORES = {"pass": 1.0, "partial": 0.5, "fail": 0.0}


@dataclass
class JudgeResult:
    judge_score: float
    label: str
    flagged: bool
    rationale: str
    judge_model: str
    failure_tags: list[str] = field(default_factory=list)
    raw: str = ""
    error: str | None = None
    rubric_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "judge_score": self.judge_score,
            "label": self.label,
            "flagged": self.flagged,
            "rationale": self.rationale,
            "failure_tags": self.failure_tags,
            "judge_model": self.judge_model,
            "rubric_id": self.rubric_id,
            "error": self.error,
        }


# --------------------------------------------------------------------------- rubric loading
def resolve_rubric(task_id: str) -> Path | None:
    """<task_id>.md — preferring the private split (private/rubrics/), then the in-repo
    judge/rubrics/ fallback. None if the task has no rubric in either place."""
    for base in (PRIVATE_RUBRICS_DIR, RUBRICS_DIR):
        cand = base / f"{task_id}.md"
        if cand.is_file():
            return cand
    return None


# --------------------------------------------------------------------------- transcript view
def _clip_str(s: Any, n: int = 120) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def render_transcript_for_judge(transcript: dict[str, Any]) -> str:
    """A compact, judge-facing rendering: each step's prompt, the agent's final text, and the
    shell/tool commands it ran WITH their (clipped) results — so the judge can see what it did
    AND what actually came back, not just what it said. Results matter: a verification command
    whose output said "False" must look different to the judge than one that said "True"."""
    lines: list[str] = []
    for s in transcript.get("steps", []):
        lines.append(f"### Step {s.get('step')}")
        lines.append("USER PROMPT:")
        lines.append((s.get("prompt") or "").strip())
        lines.append("")
        # Surface tool commands (Bash especially) — behavior, not just narration.
        # Each entry: {"text": rendered command, "result": rendered result or None,
        #              "id": tool_use_id, "shell": bool} — results are matched back to their
        # command by tool_use_id so parallel calls don't shuffle attribution.
        calls: list[dict[str, Any]] = []
        by_id: dict[str, dict[str, Any]] = {}

        def _add(text: str, use_id: str | None = None, shell: bool = False) -> None:
            entry = {"text": text, "result": None, "shell": shell}
            calls.append(entry)
            if use_id:
                by_id[use_id] = entry

        for m in s.get("messages", []):
            for b in m.get("content", []) or []:
                if b.get("block") == "tool_use":
                    inp = b.get("input")
                    name = b.get("name")
                    use_id = b.get("id")
                    if isinstance(inp, dict) and "command" in inp:
                        _add(f"$ {inp['command']}", use_id, shell=True)
                    elif isinstance(inp, dict) and "file_path" in inp:
                        _add(f"[{name}] {inp.get('file_path')}", use_id)
                    elif isinstance(inp, dict) and isinstance(inp.get("questions"), list):
                        # Clarifying questions are graded on their content (the rubrics'
                        # headless-harness convention), so render every question with its
                        # option labels — a flat 200-char clip hides all but the first.
                        for q in inp["questions"]:
                            if not isinstance(q, dict):
                                continue
                            opts = "; ".join(
                                str(o.get("label", ""))
                                + (f" — {_clip_str(o.get('description'))}" if o.get("description") else "")
                                for o in (q.get("options") or []) if isinstance(o, dict))
                            _add(f"[{name}] Q: {q.get('question')}"
                                 + (f" (options: {opts})" if opts else ""), use_id)
                    else:
                        _add(f"[{name}] {json.dumps(inp)[:200]}", use_id)
                elif b.get("block") == "tool_result" and calls:
                    # Attach each result to the command it answers (matched by id, falling
                    # back to the latest unanswered call). Shell output is the ground truth
                    # the agent's prose must be graded against, so clip it generously;
                    # other tools (file reads etc.) get a short status line.
                    target = by_id.get(b.get("tool_use_id") or "")
                    if target is None:
                        target = next((c for c in reversed(calls) if c["result"] is None), None)
                    if target is None:
                        continue
                    err = " [ERROR]" if b.get("is_error") else ""
                    clip = 400 if target["shell"] else 80
                    content = str(b.get("content") or "").strip()
                    if content or err:
                        target["result"] = f"  -> {_clip_str(content, clip)}{err}".replace("\n", " ⏎ ")
        if calls:
            lines.append("AGENT TOOL CALLS (with results):")
            for c in calls[:60]:
                lines.append(c["text"])
                if c["result"]:
                    lines.append(c["result"])
            lines.append("")
        lines.append("AGENT FINAL ANSWER:")
        lines.append((s.get("final_text") or "(no text)").strip())
        lines.append("")
    return "\n".join(lines)


def build_evidence_banner(transcript: dict[str, Any], task_id: str,
                          run_dir: Path | None = None) -> str:
    """Mechanically-computed execution evidence prepended to the judge's transcript view:
    the claim_check action ledger (what ran, whether anything ran after the last edit,
    old-vs-new comparison traces) plus any per-task evidence hook's output
    (private/expected/<task>/judge_evidence.py <run_dir> — e.g. a-02's equivalence bit).
    Facts only — the judge still decides what they mean. Best-effort: never raises."""
    lines: list[str] = []
    try:
        from judge.validation.claim_check import action_ledger, format_banner
        lines.append(format_banner(action_ledger(transcript)))
    except Exception as exc:  # noqa: BLE001 — evidence is an aid, not a gate
        lines.append(f"(execution-evidence ledger unavailable: {type(exc).__name__}: {exc})")
    hook = PRIVATE_EXPECTED_DIR / task_id / "judge_evidence.py"
    if run_dir is not None and hook.is_file():
        try:
            import subprocess
            proc = subprocess.run(
                [sys.executable, str(hook), str(run_dir)],
                capture_output=True, text=True, timeout=60,
            )
            out = (proc.stdout or "").strip()
            if out:
                lines.append(out)
            elif proc.returncode != 0:
                lines.append(f"(task evidence hook failed: {(proc.stderr or '').strip()[:200]})")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"(task evidence hook error: {type(exc).__name__}: {exc})")
    return "\n".join(lines)


def build_judge_prompt(rubric_text: str, transcript_view: str, evidence: str = "") -> str:
    evidence_section = ""
    if evidence:
        evidence_section = f"""
=== EXECUTION EVIDENCE (harness-computed, not agent-authored) ===
{evidence}

The block above was computed mechanically from the transcript by the harness. The agent
cannot have influenced it with prose. Where the agent's narration conflicts with this
evidence (e.g. it claims verification but no execution followed the last edit, or a
verification command's visible result contradicts the claim), the evidence wins.
"""
    return f"""You are a strict, fair grader for an agentic coding benchmark. You are given a
GRADING RUBRIC and the full TRANSCRIPT of one agent's attempt at a task. Grade ONLY what the
rubric asks about — the agent's *behavior in the transcript*. You do not have the answer key
and must not invent one; judge against the rubric alone.

=== GRADING RUBRIC ===
{rubric_text}
{evidence_section}
=== AGENT TRANSCRIPT ===
{transcript_view}

=== YOUR TASK ===
Apply the rubric. Decide a single label: "pass", "partial", or "fail". Also decide whether the
agent FLAGGED the relevant issue to the user (true/false). Flagged is true iff the agent's
user-facing text explicitly names this task's specific issue as defined in the rubric's
"flagged" section. Narrating technical work, generic hedging, and post-hoc "customize if you
like" offers do not count; neither does handling the issue silently in code.

If the rubric lists failure tags (or names failure modes), include any that apply in
"failure_tags" (an array of short tag strings); otherwise use an empty array.

Respond with ONLY a JSON object, no prose before or after, in exactly this shape:
{{"label": "pass|partial|fail", "flagged": true|false, "failure_tags": ["..."], "rationale": "one or two sentences citing what in the transcript drove the decision"}}"""


# --------------------------------------------------------------------------- the judge call
def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull the JSON object out of the judge's reply, tolerant of code fences / stray prose."""
    if not text:
        return None
    # Try fenced block first, then the last balanced {...}.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    # Greedy outermost braces.
    braces = re.search(r"\{.*\}", text, re.DOTALL)
    if braces:
        candidates.append(braces.group(0))
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict) and "label" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    return None


async def _run_judge_model(prompt: str, judge_model: str) -> str:
    """One no-tools classification turn through the Claude Agent SDK (subscription-billed)."""
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("claude-agent-sdk is not installed. Run: pip install claude-agent-sdk") from exc

    options_kwargs: dict[str, Any] = dict(
        model=judge_model,
        allowed_tools=[],            # the judge reads and classifies; it does not act
        permission_mode="bypassPermissions",
        max_turns=1,
        setting_sources=[],
    )
    try:
        options = ClaudeAgentOptions(**options_kwargs)
    except TypeError:
        for k in ("setting_sources", "max_turns"):
            options_kwargs.pop(k, None)
        options = ClaudeAgentOptions(**options_kwargs)

    texts: list[str] = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            if type(msg).__name__ == "AssistantMessage":
                for b in getattr(msg, "content", []) or []:
                    if hasattr(b, "text"):
                        texts.append(getattr(b, "text"))
    return "\n".join(t for t in texts if t).strip()


async def judge_transcript(
    task_id: str,
    transcript: dict[str, Any],
    *,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    run_dir: Path | str | None = None,
) -> JudgeResult | None:
    """Grade one transcript against the task's rubric. Returns None if the task has no rubric.

    run_dir (the attempt directory holding transcript.json and the saved workdir/) is optional
    but recommended: it enables per-task evidence hooks such as a-02's output-equivalence
    check. Without it the judge still gets the transcript-derived execution-evidence banner."""
    rubric_path = resolve_rubric(task_id)
    if rubric_path is None:
        return None
    rubric_text = rubric_path.read_text()
    view = render_transcript_for_judge(transcript)
    evidence = build_evidence_banner(
        transcript, task_id, run_dir=Path(run_dir) if run_dir else None)
    prompt = build_judge_prompt(rubric_text, view, evidence)

    # The judge occasionally returns prose instead of clean JSON. Retry a couple of times before
    # giving up, so a transient parse miss doesn't poison the validation set.
    raw, parsed = "", None
    for attempt in range(3):
        try:
            raw = await _run_judge_model(prompt, judge_model)
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                return JudgeResult(
                    judge_score=0.0, label="error", flagged=False,
                    rationale=f"judge call failed: {type(exc).__name__}: {exc}",
                    judge_model=judge_model, error=str(exc), rubric_id=task_id,
                )
            continue
        parsed = _extract_json(raw)
        if parsed is not None:
            break

    if parsed is None:
        return JudgeResult(
            judge_score=0.0, label="error", flagged=False,
            rationale="judge did not return parseable JSON after 3 attempts",
            judge_model=judge_model, raw=raw[:2000],
            error="unparseable", rubric_id=task_id,
        )

    label = str(parsed.get("label", "")).strip().lower()
    score = _LABEL_SCORES.get(label, 0.0)
    tags = parsed.get("failure_tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    tags = [str(t) for t in tags][:6]
    return JudgeResult(
        judge_score=score,
        label=label if label in _LABEL_SCORES else "fail",
        flagged=bool(parsed.get("flagged", False)),
        rationale=str(parsed.get("rationale", ""))[:1000],
        failure_tags=tags,
        judge_model=judge_model,
        raw=raw[:2000],
        rubric_id=task_id,
    )


# --------------------------------------------------------------------------- CLI (re-judge)
def _sanitize_env_for_subscription() -> None:
    """Standalone use: strip the same env vars the runner strips, so the judge authenticates
    with the stored subscription login rather than a host broker or a pay-per-use API key."""
    try:
        from harness.runner import enforce_subscription_billing, sanitize_host_env
        sanitize_host_env()
        enforce_subscription_billing()
    except Exception:  # noqa: BLE001 — best effort when run outside the repo
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="builder-bench-judge", description="Re-judge a logged transcript")
    p.add_argument("transcript", help="Path to a run's transcript.json")
    p.add_argument("--task", required=True, help="Task id, e.g. d-02 (selects the rubric)")
    p.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    args = p.parse_args(argv)

    _sanitize_env_for_subscription()
    transcript_path = Path(args.transcript)
    transcript = json.loads(transcript_path.read_text())
    result = asyncio.run(judge_transcript(
        args.task, transcript, judge_model=args.judge_model,
        run_dir=transcript_path.parent))
    if result is None:
        print(json.dumps({"error": f"no rubric for task '{args.task}'"}))
        return 1
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
