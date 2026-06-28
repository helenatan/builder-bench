"""Builder-Bench runner — the neutral headless agent loop.

Usage:
    python -m harness.runner --task b-01 --model opus-4.6 [options]

End to end it: resolves the task, builds an isolated sandbox from the task's fixed starting
state, runs the model through the task's prompt steps in one continuous session, logs the
full trajectory, grades it programmatically, computes metrics, and writes a result row to
results/leaderboard.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adapters import get_adapter, resolve_model
from .metrics import aggregate
from .sandbox import docker_available, get_sandbox

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
RESULTS_DIR = REPO_ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
LEADERBOARD = RESULTS_DIR / "leaderboard.json"

# Vars a Claude Desktop / Claude Code *host* injects to broker its own auth. When the harness
# spawns a fresh `claude` subprocess inside such a session, these hijack authentication and the
# child 401s — even with a valid key — because host auth is brokered for the parent only. The
# harness runs its own neutral session, so we strip them (the SDK re-adds what it needs) and let
# the configured credential take over. Credential vars are deliberately NOT in this list.
_HOST_BROKER_VARS = {
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_EXECPATH",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH",
    "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH",
    "CLAUDE_CODE_ENABLE_ASK_USER_QUESTION_TOOL",
    "CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES",
    "CLAUDE_CODE_DISABLE_CRON",
    "CLAUDE_AGENT_SDK_VERSION",
    "AI_AGENT",
    "CLAUDE_EFFORT",
}
_CREDENTIAL_VARS = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN")

# Credentials that bill OUTSIDE the Claude subscription (pay-per-use API / gateway). v1 is
# subscription-only, so these are stripped by default — billing then falls through to the
# subscription login (`claude setup-token` / `claude login`). Override with --allow-api.
_API_BILLING_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def sanitize_host_env() -> list[str]:
    """Remove host-brokering vars from this process's env so the child `claude` authenticates
    with the configured credential. Returns the names removed."""
    removed = [k for k in list(os.environ) if k in _HOST_BROKER_VARS]
    for k in removed:
        os.environ.pop(k, None)
    return removed


def has_credential() -> str | None:
    for k in _CREDENTIAL_VARS:
        if os.environ.get(k):
            return k
    return None


def enforce_subscription_billing() -> list[str]:
    """Strip pay-per-use API credentials from this process's env so the child `claude` bills the
    Claude subscription, not the API. Returns the names removed. The subscription login itself
    (`claude setup-token` / `claude login`) lives in the CLI's credential store and is unaffected."""
    removed = [k for k in _API_BILLING_VARS if os.environ.get(k)]
    for k in removed:
        os.environ.pop(k, None)
    return removed


# --------------------------------------------------------------------------- task loading
def resolve_task_dir(task_id: str) -> Path:
    """Match 'b-01' to tasks/b-01-dedup-survives/ (prefix match), or an exact dir name."""
    exact = TASKS_DIR / task_id
    if exact.is_dir():
        return exact
    matches = sorted(p for p in TASKS_DIR.iterdir() if p.is_dir() and p.name.startswith(task_id))
    if not matches:
        raise SystemExit(f"No task matching '{task_id}' under {TASKS_DIR}")
    if len(matches) > 1:
        raise SystemExit(f"Ambiguous task '{task_id}': {[m.name for m in matches]}")
    return matches[0]


def load_task(task_dir: Path) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    spec = task_dir / "success.yaml"
    if spec.is_file():
        if yaml is None:
            raise SystemExit("pyyaml is required to read success.yaml: pip install pyyaml")
        cfg = yaml.safe_load(spec.read_text()) or {}

    # Resolve the ordered prompt steps.
    steps = cfg.get("steps")
    if steps:
        prompt_files = [task_dir / s for s in steps]
    else:
        multi = sorted(task_dir.glob("prompt_step*.md"))
        prompt_files = multi if multi else [task_dir / "prompt.md"]
    missing = [str(p) for p in prompt_files if not p.is_file()]
    if missing:
        raise SystemExit(f"Task '{task_dir.name}' is missing prompt files: {missing}")

    cfg["_dir"] = task_dir
    cfg["_prompts"] = [p.read_text() for p in prompt_files]
    cfg["_prompt_files"] = [p.name for p in prompt_files]
    cfg.setdefault("id", task_dir.name)
    cfg.setdefault("category", "?")
    cfg.setdefault("pass_threshold", 1.0)
    cfg.setdefault("grader", "grader.py")
    return cfg


# --------------------------------------------------------------------------- logging
def render_transcript_md(session: Any, task_cfg: dict[str, Any]) -> str:
    lines = [f"# Transcript — task `{task_cfg['id']}` — model `{session.model}` ({session.model_id})", ""]
    if session.error:
        lines += [f"> **session error:** {session.error}", ""]
    for s in session.steps:
        lines += [f"## Step {s.index}", "", "**Prompt:**", "", "```", s.prompt.strip(), "```", ""]
        lines += ["**Final answer:**", "", s.final_text or "_(no text)_", ""]
        tool_calls = [
            b for m in s.messages for b in m.get("content", []) if b.get("block") == "tool_use"
        ]
        if tool_calls:
            lines.append(f"<details><summary>{len(tool_calls)} tool call(s)</summary>\n")
            for t in tool_calls:
                lines.append(f"- `{t.get('name')}` {json.dumps(t.get('input'))[:300]}")
            lines.append("\n</details>\n")
    return "\n".join(lines)


def run_grader(task_cfg: dict[str, Any], session: Any, attempt_dir: Path, workdir: Path) -> dict[str, Any]:
    grader = task_cfg["_dir"] / "grader.py"
    if not grader.is_file():
        return {"score": 0.0, "passed": False, "failure_tags": ["no-grader"], "details": "grader.py missing"}

    payload = {
        "task_id": task_cfg["id"],
        "task_dir": str(task_cfg["_dir"]),
        "workdir": str(workdir),
        "attempt_dir": str(attempt_dir),
        "transcript": session.transcript_steps(),
        "final_text": session.final_text,
    }
    grade_input = attempt_dir / "grade_input.json"
    grade_input.write_text(json.dumps(payload, indent=2))

    proc = subprocess.run(
        [sys.executable, str(grader), str(grade_input)],
        cwd=str(task_cfg["_dir"]),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return {
            "score": 0.0, "passed": False, "failure_tags": ["grader-error"],
            "details": f"grader exited {proc.returncode}", "stderr": proc.stderr[-2000:],
        }
    # Grader prints a single JSON object on stdout. Be tolerant of trailing noise.
    out = proc.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {
            "score": 0.0, "passed": False, "failure_tags": ["grader-bad-output"],
            "details": "grader did not emit JSON", "stdout": out[-2000:],
        }


async def run_judge(task_cfg: dict[str, Any], session: Any, attempt_dir: Path, judge_model: str) -> dict[str, Any] | None:
    """Invoke the LLM judge on this attempt's transcript. Returns the judge block (or an error
    block) and writes judge.json. None if the judge package/rubric is unavailable."""
    try:
        from judge import judge_transcript
    except Exception as exc:  # noqa: BLE001
        return {"error": f"judge unavailable: {type(exc).__name__}: {exc}"}

    transcript = session.to_dict()
    try:
        result = await judge_transcript(task_cfg["id"], transcript, judge_model=judge_model)
    except Exception as exc:  # noqa: BLE001 — never let the judge crash a run
        return {"error": f"judge raised: {type(exc).__name__}: {exc}"}
    if result is None:
        return {"error": f"no rubric for task '{task_cfg['id']}'"}

    block = result.to_dict()
    (attempt_dir / "judge.json").write_text(json.dumps(block, indent=2))
    return block


def update_leaderboard(row: dict[str, Any]) -> None:
    data = {"rows": []}
    if LEADERBOARD.is_file():
        try:
            data = json.loads(LEADERBOARD.read_text())
        except json.JSONDecodeError:
            pass
    data.setdefault("rows", []).append(row)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    LEADERBOARD.write_text(json.dumps(data, indent=2))


# --------------------------------------------------------------------------- run loop
async def run_attempt(task_cfg, model, sandbox_kind, attempt_dir, budget_usd, max_turns, judge_model) -> dict[str, Any]:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    sandbox = get_sandbox(sandbox_kind, task_cfg["_dir"], attempt_dir)
    workdir = sandbox.setup()
    print(f"  [sandbox:{sandbox.kind}] workdir = {workdir}")

    adapter = get_adapter(
        model, workdir,
        budget_usd=budget_usd,
        max_turns=max_turns,
        system_prompt=task_cfg.get("system_prompt"),
    )
    print(f"  [model] {model} -> {adapter.model_id}; running {len(task_cfg['_prompts'])} step(s)...")
    session = await adapter.run_session(task_cfg["_prompts"])

    (attempt_dir / "transcript.json").write_text(json.dumps(session.to_dict(), indent=2))
    (attempt_dir / "transcript.md").write_text(render_transcript_md(session, task_cfg))

    has_grader = (task_cfg["_dir"] / task_cfg.get("grader", "grader.py")).is_file()
    grade = run_grader(task_cfg, session, attempt_dir, workdir) if has_grader else None
    if grade is not None and "passed" not in grade:
        grade["passed"] = float(grade.get("score", 0.0)) >= float(task_cfg["pass_threshold"])

    # Behavioral grading via the LLM judge against a per-task rubric (Messy World, Vague Ask).
    judge_block = None
    if task_cfg.get("needs_judge"):
        judge_block = await run_judge(task_cfg, session, attempt_dir, judge_model)

    # How the final score is decided:
    #   programmatic  — the grader gates pass/fail; the judge (if any) is REPORTED alongside but
    #                   does not move the score until judge–human agreement is validated (PRD §6).
    #                   This covers Full Build, Long Haul, and (for now) hybrid Messy World.
    #   judge         — Vague Ask: there is no deliverable to check, so the judge IS the score.
    grade_with = task_cfg.get("grade_with") or ("programmatic" if has_grader else "judge")
    threshold = float(task_cfg["pass_threshold"])
    if grade_with == "judge":
        jscore = float((judge_block or {}).get("judge_score", 0.0))
        score, passed = jscore, jscore >= threshold
        tags = (judge_block or {}).get("failure_tags", []) or []
        details = (judge_block or {}).get("rationale", "") or "judge produced no rationale"
    elif grade_with == "hybrid_gate":
        # Both programmatic AND judge must clear their respective thresholds.
        # judge_pass_threshold defaults to 0.8 so only a clean "pass" label (1.0) qualifies.
        judge_thresh = float(task_cfg.get("judge_pass_threshold", 0.8))
        grade = grade or {"score": 0.0, "passed": False, "failure_tags": ["no-grader"],
                          "details": "no grader.py"}
        prog_score = float(grade.get("score", 0.0))
        prog_passed = prog_score >= threshold
        jscore = float((judge_block or {}).get("judge_score", 0.0))
        judge_passed = jscore >= judge_thresh
        score = prog_score
        passed = prog_passed and judge_passed
        tags = list(grade.get("failure_tags", []) or [])
        if not judge_passed:
            jtags = list((judge_block or {}).get("failure_tags", []) or [])
            tags = list(dict.fromkeys(tags + jtags + ["weak-self-verification"]))
        prog_status = "OK" if prog_passed else f"FAIL (score={prog_score:.2f})"
        judge_status = "OK" if judge_passed else f"FAIL (score={jscore:.1f} < {judge_thresh:.1f})"
        details = (grade.get("details", "") or "") + f" | judge gate: {judge_status}"
    else:
        grade = grade or {"score": 0.0, "passed": False, "failure_tags": ["no-grader"],
                          "details": "no grader.py and grade_with is not 'judge'"}
        score, passed = float(grade.get("score", 0.0)), bool(grade.get("passed"))
        tags, details = grade.get("failure_tags", []), grade.get("details", "")

    result = {
        "score": score,
        "passed": passed,
        "grade_with": grade_with,
        "failure_tags": tags,
        "details": details,
        "cost_usd": session.cost_usd,
        "input_tokens": session.input_tokens,
        "output_tokens": session.output_tokens,
        "num_turns": session.num_turns,
        "tool_calls": sum(
            1
            for s in session.steps
            for m in s.messages
            for b in m.get("content", [])
            if b.get("block") == "tool_use"
        ),
        "session_error": session.error,
        "grade": grade,
        "judge": judge_block,
    }
    (attempt_dir / "result.json").write_text(json.dumps(result, indent=2))
    sandbox.teardown()
    verdict = "PASS" if result["passed"] else "FAIL"
    print(
        f"  [grade] {verdict} score={result['score']:.2f} "
        f"cost=${session.cost_usd:.4f} tags={result['failure_tags']}"
    )
    return result


async def run_task(args: argparse.Namespace) -> int:
    task_dir = resolve_task_dir(args.task)
    task_cfg = load_task(task_dir)
    provider, model_id = resolve_model(args.model)

    if not args.keep_host_env:
        removed = sanitize_host_env()
        if removed:
            print(f"[builder-bench] sanitized host-brokering env vars: {sorted(removed)}")
    if not args.allow_api:
        stripped = enforce_subscription_billing()
        if stripped:
            print(
                f"[builder-bench] subscription-only mode: stripped {sorted(stripped)} so runs "
                "bill to your Claude subscription, not the pay-per-use API. Use --allow-api to "
                "permit API billing."
            )
    cred = has_credential()
    if cred:
        billing = "API (pay-per-use)" if cred == "ANTHROPIC_API_KEY" else "subscription / OAuth"
        print(f"[builder-bench] using credential from ${cred} -> {billing}")
    else:
        print(
            "[builder-bench] no credential env var set; the child `claude` will use your stored "
            "login (subscription) if present. If you have not run `claude setup-token` / "
            "`claude login`, the agent will 401.",
            file=sys.stderr,
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_slug = args.model.replace("/", "_")
    run_root = RUNS_DIR / task_cfg["id"] / model_slug / stamp
    run_root.mkdir(parents=True, exist_ok=True)

    sandbox_kind = args.sandbox
    if sandbox_kind == "auto":
        eff = "docker" if docker_available() else "local"
        print(f"[builder-bench] sandbox=auto -> {eff}")
    else:
        eff = sandbox_kind

    print(f"[builder-bench] task={task_cfg['id']} (cat {task_cfg['category']}) "
          f"model={args.model} attempts={args.attempts}")

    attempts: list[dict[str, Any]] = []
    for i in range(1, args.attempts + 1):
        print(f"\n--- attempt {i}/{args.attempts} ---")
        try:
            res = await run_attempt(
                task_cfg, args.model, sandbox_kind,
                run_root / f"attempt-{i}", args.budget_usd, args.max_turns,
                args.judge_model,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] attempt {i} crashed: {type(exc).__name__}: {exc}", file=sys.stderr)
            res = {"score": 0.0, "passed": False, "failure_tags": ["harness-error"],
                   "details": str(exc), "cost_usd": 0.0}
        attempts.append(res)

    metrics = aggregate(attempts)
    summary = {
        "task_id": task_cfg["id"],
        "category": task_cfg["category"],
        "model": args.model,
        "model_id": model_id,
        "provider": provider,
        "sandbox": eff,
        "timestamp": stamp,
        "metrics": metrics,
        "attempts": attempts,
        "run_path": str(run_root.relative_to(REPO_ROOT)),
    }
    (run_root / "summary.json").write_text(json.dumps(summary, indent=2))

    update_leaderboard({
        "task_id": task_cfg["id"], "category": task_cfg["category"],
        "model": args.model, "model_id": model_id, "provider": provider,
        "sandbox": eff, "timestamp": stamp, **metrics,
        "run_path": str(run_root.relative_to(REPO_ROOT)),
    })

    print("\n[builder-bench] ===== summary =====")
    print(json.dumps(metrics, indent=2))
    print(f"[builder-bench] artifacts: {run_root}")
    print(f"[builder-bench] leaderboard row appended -> {LEADERBOARD.relative_to(REPO_ROOT)}")
    return 0 if metrics.get("solved", 0) > 0 else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="builder-bench", description="Builder-Bench neutral runner")
    p.add_argument("--task", required=True, help="Task id or prefix, e.g. b-01")
    p.add_argument("--model", required=True, help="Model alias, e.g. opus-4.6, sonnet, haiku")
    p.add_argument("--attempts", type=int, default=1, help="Attempts for pass@k (default 1)")
    p.add_argument("--sandbox", choices=["auto", "docker", "local"], default="auto",
                   help="Sandbox backend (default auto: docker if available, else local)")
    p.add_argument("--budget-usd", type=float, default=2.0,
                   help="Per-attempt spend cap in USD (default 2.0)")
    p.add_argument("--max-turns", type=int, default=40, help="Max agent turns per attempt")
    p.add_argument(
        "--judge-model", default="claude-sonnet-4-6",
        help="Model the LLM judge uses to grade transcripts on tasks with needs_judge: true "
             "(default claude-sonnet-4-6). Named so judge-vs-human agreement can be checked "
             "per contestant model (PRD §6).",
    )
    p.add_argument(
        "--keep-host-env", action="store_true",
        help="Do NOT strip host (Claude Desktop/Code) auth-brokering env vars. Off by default; "
             "stripping lets the child agent authenticate with your own credential.",
    )
    p.add_argument(
        "--allow-api", action="store_true",
        help="Permit pay-per-use Anthropic API billing. Off by default (subscription-only): "
             "ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN are stripped so runs bill to your Claude "
             "subscription (claude setup-token / login).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(run_task(args))


if __name__ == "__main__":
    raise SystemExit(main())
