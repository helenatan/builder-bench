"""Cross-cutting dimension scorer — grade a run's *process* and *craft*, not its answer.

The per-task judge (judge/judge.py) scores task-specific behavior against a task rubric. This
module scores **cross-cutting dimensions** that apply to every run regardless of task:

  - **planning**  (judge/rubrics/_planning.md)        — decomposition, ordering, self-validation
  - **product_quality** (judge/rubrics/_product_quality.md) — maintainability / readability / docs

Both reuse the existing judge plumbing (transcript rendering, prompt, model call, JSON parse), so
the grading contract and subscription-billing rules are identical. Planning is scored from the
transcript and so can be run **retroactively over the existing run archive** — no re-run of the
contestants needed (review feedback #3). Product quality benefits from seeing the built files; it
reads an optional deliverable snapshot when present (see --include-deliverable).

    # retroactive planning pass over everything already run (needs subscription auth for the judge)
    python -m judge.dimensions --dimension planning
    python -m judge.dimensions --dimension planning --task d-02 --model opus
    python -m judge.dimensions --dimension planning --dry-run     # render + count, no model calls
    python -m judge.dimensions --dimension product_quality --category C --include-deliverable

Each scored attempt gets a sidecar `attempt-N/dimension-<name>.json`. A summary prints per-model
averages. Re-running skips attempts already scored unless --force.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Reuse the judge's plumbing verbatim so dimensions grade on the same contract.
from judge.judge import (  # noqa: E402
    DEFAULT_JUDGE_MODEL,
    _LABEL_SCORES,
    _extract_json,
    _run_judge_model,
    _sanitize_env_for_subscription,
    build_judge_prompt,
    render_transcript_for_judge,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"
LEADERBOARD = REPO_ROOT / "results" / "leaderboard.json"

# Text-ish files worth showing the product-quality judge; capped so the prompt stays bounded.
_SNAPSHOT_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb", ".rs", ".java", ".sh",
                  ".sql", ".html", ".css", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"}
_SNAPSHOT_MAX_FILES = 25
_SNAPSHOT_MAX_BYTES = 4000


def _load_rows() -> list[dict[str, Any]]:
    data = json.loads(LEADERBOARD.read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    seen: dict[tuple, dict] = {}
    for r in rows:
        seen[(r["task_id"], r["model_id"])] = r
    return list(seen.values())


def _deliverable_view(attempt_dir: Path) -> str:
    """Render an optional captured deliverable snapshot (attempt-N/deliverable/) for the judge.
    Returns '' when no snapshot exists — older runs simply won't have one."""
    snap = attempt_dir / "deliverable"
    if not snap.is_dir():
        return ""
    files = [p for p in sorted(snap.rglob("*"))
             if p.is_file() and p.suffix.lower() in _SNAPSHOT_EXTS]
    if not files:
        return ""
    out = ["", "=== BUILT DELIVERABLE (captured files) ==="]
    for p in files[:_SNAPSHOT_MAX_FILES]:
        rel = p.relative_to(snap)
        try:
            body = p.read_text(errors="replace")[:_SNAPSHOT_MAX_BYTES]
        except Exception:  # noqa: BLE001
            continue
        out += [f"\n--- {rel} ---", body]
    return "\n".join(out)


def _iter_attempts(rows, task=None, model=None, category=None):
    for r in rows:
        if task and not r["task_id"].startswith(task):
            continue
        if category and r.get("category") != category:
            continue
        if model and model not in (r.get("model", ""), r.get("model_id", "")):
            continue
        base = REPO_ROOT / r.get("run_path", "")
        for ad in sorted(base.glob("attempt-*")):
            if (ad / "transcript.json").is_file():
                yield r, ad


def _build_prompt(rubric_text: str, attempt_dir: Path, include_deliverable: bool) -> str | None:
    try:
        transcript = json.loads((attempt_dir / "transcript.json").read_text())
    except Exception:  # noqa: BLE001
        return None
    view = render_transcript_for_judge(transcript)
    if include_deliverable:
        view += _deliverable_view(attempt_dir)
    return build_judge_prompt(rubric_text, view)


async def score(args) -> int:
    rubric_path = RUBRICS_DIR / f"_{args.dimension}.md"
    if not rubric_path.is_file():
        print(f"No rubric at {rubric_path}", file=sys.stderr)
        return 2
    rubric_text = rubric_path.read_text()
    rows = _load_rows()
    targets = list(_iter_attempts(rows, args.task, args.model, args.category))
    if not targets:
        print("No matching attempts.")
        return 0

    sidecar = f"dimension-{args.dimension}.json"
    if args.dry_run:
        print(f"[dry-run] dimension={args.dimension}: {len(targets)} attempt(s) would be scored "
              f"against {rubric_path.name}. No model calls made.")
        return 0

    _sanitize_env_for_subscription()
    by_model: dict[str, list[float]] = {}
    scored = skipped = 0
    for r, ad in targets:
        out_path = ad / sidecar
        if out_path.is_file() and not args.force:
            try:
                prev = json.loads(out_path.read_text())
                by_model.setdefault(r["model_id"], []).append(float(prev.get("score", 0.0)))
                skipped += 1
                continue
            except Exception:  # noqa: BLE001
                pass
        prompt = _build_prompt(rubric_text, ad, args.include_deliverable)
        if prompt is None:
            continue
        raw, parsed = "", None
        for _ in range(3):
            try:
                raw = await _run_judge_model(prompt, args.judge_model)
            except Exception as exc:  # noqa: BLE001
                print(f"  [error] {r['task_id']}/{r['model_id']}: {exc}", file=sys.stderr)
                break
            parsed = _extract_json(raw)
            if parsed is not None:
                break
        if parsed is None:
            continue
        label = str(parsed.get("label", "")).strip().lower()
        sc = _LABEL_SCORES.get(label, 0.0)
        rec = {
            "dimension": args.dimension,
            "label": label if label in _LABEL_SCORES else "fail",
            "score": sc,
            "rationale": str(parsed.get("rationale", ""))[:1000],
            "failure_tags": [str(t) for t in (parsed.get("failure_tags") or [])][:6],
            "judge_model": args.judge_model,
            "rubric": rubric_path.name,
        }
        out_path.write_text(json.dumps(rec, indent=2))
        by_model.setdefault(r["model_id"], []).append(sc)
        scored += 1
        print(f"  {r['task_id']:6} {r['model_id']:26} {rec['label']:>7}  {rec['rationale'][:80]}")

    print(f"\n[{args.dimension}] scored {scored}, reused {skipped} cached\n")
    print(f"  {'Model':26} {'Avg ' + args.dimension:>16} {'n':>4}")
    print("  " + "-" * 50)
    for mid, vals in sorted(by_model.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print(f"  {mid:26} {sum(vals)/len(vals)*100:>14.0f}% {len(vals):>4}")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="builder-bench-dimensions",
                                description="Score cross-cutting dimensions over runs")
    p.add_argument("--dimension", required=True, choices=["planning", "product_quality"])
    p.add_argument("--task", help="task-id prefix filter (e.g. d-02, c-)")
    p.add_argument("--model", help="model alias or id filter")
    p.add_argument("--category", help="category filter (A/B/C/D)")
    p.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    p.add_argument("--include-deliverable", action="store_true",
                   help="append the captured deliverable snapshot to the judge view")
    p.add_argument("--force", action="store_true", help="re-score attempts that already have a sidecar")
    p.add_argument("--dry-run", action="store_true", help="render + count, make no model calls")
    args = p.parse_args(argv)
    return asyncio.run(score(args))


if __name__ == "__main__":
    raise SystemExit(main())
