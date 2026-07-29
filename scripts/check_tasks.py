#!/usr/bin/env python3
"""Validate every task folder against the schema in tasks/README.md.

    python scripts/check_tasks.py

Runs in CI on every PR. This is the guard that lets us take task contributions from
strangers: it checks the manifest is well-formed and self-consistent, that every file
the manifest names actually exists, and that nothing references the private/ split
(which no public clone has). It does NOT run any model.

Exit 0 if every task is valid, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TASKS = REPO / "tasks"

REQUIRED = {"id", "category", "name", "derived_from", "needs_judge", "mode",
            "steps", "pass_threshold", "failure_tags_possible"}
OPTIONAL = {"grader", "grade_with", "multimodal", "judge_pass_threshold"}

CATEGORIES = {"A", "B", "C", "D", "E"}
MODES = {"single", "multi_step"}
# How the final score is decided (harness/runner.py::run_attempt):
#   programmatic — the grader gates pass/fail; the judge, if any, is reported alongside
#   judge        — no fixed deliverable; the judge label is the score
#   hybrid_gate  — programmatic AND judge must both pass
GRADE_WITH = {"judge", "programmatic", "hybrid_gate"}

# The seven builder-persona failure modes (README "Failure taxonomy"). A task may only
# declare tags from this list — an unrecognized tag never shows up in the report.
TAXONOMY = {
    "premature-implementation", "vision-drift", "silent-assumptions",
    "weak-self-verification", "data-blindness", "over-eagerness", "fabricated-data",
}


def check_task(folder: Path) -> list[str]:
    """Return a list of human-readable problems with this task folder (empty == valid)."""
    errs: list[str] = []
    rel = folder.relative_to(REPO)

    manifest = folder / "success.yaml"
    if not manifest.is_file():
        return [f"{rel}: no success.yaml"]

    try:
        cfg = yaml.safe_load(manifest.read_text())
    except yaml.YAMLError as exc:
        return [f"{rel}/success.yaml: not parseable — {exc}"]
    if not isinstance(cfg, dict):
        return [f"{rel}/success.yaml: expected a mapping at the top level"]

    missing = REQUIRED - cfg.keys()
    if missing:
        errs.append(f"{rel}/success.yaml: missing required key(s): {', '.join(sorted(missing))}")
    unknown = cfg.keys() - REQUIRED - OPTIONAL
    if unknown:
        errs.append(f"{rel}/success.yaml: unrecognized key(s): {', '.join(sorted(unknown))}")

    # id must match the folder name's prefix, so results/ paths and task ids line up.
    task_id = cfg.get("id")
    if task_id and not folder.name.startswith(f"{task_id}-"):
        errs.append(f"{rel}: id '{task_id}' does not match folder name '{folder.name}'")

    if (cat := cfg.get("category")) not in CATEGORIES:
        errs.append(f"{rel}: category '{cat}' not in {sorted(CATEGORIES)}")
    if task_id and cat and not str(task_id).lower().startswith(str(cat).lower()):
        errs.append(f"{rel}: id '{task_id}' does not sit in its declared category '{cat}'")

    if (mode := cfg.get("mode")) not in MODES:
        errs.append(f"{rel}: mode '{mode}' not in {sorted(MODES)}")
    if (gw := cfg.get("grade_with")) is not None and gw not in GRADE_WITH:
        errs.append(f"{rel}: grade_with '{gw}' not in {sorted(GRADE_WITH)}")

    threshold = cfg.get("pass_threshold")
    if not isinstance(threshold, (int, float)) or not 0 < threshold <= 1:
        errs.append(f"{rel}: pass_threshold must be a number in (0, 1], got {threshold!r}")

    tags = cfg.get("failure_tags_possible") or []
    if not isinstance(tags, list) or not tags:
        errs.append(f"{rel}: failure_tags_possible must be a non-empty list")
    else:
        for tag in set(tags) - TAXONOMY:
            errs.append(f"{rel}: failure tag '{tag}' is not in the taxonomy")

    # Every prompt step the manifest names must exist, in order.
    steps = cfg.get("steps") or []
    if not isinstance(steps, list) or not steps:
        errs.append(f"{rel}: steps must be a non-empty list")
    else:
        for step in steps:
            if not (folder / str(step)).is_file():
                errs.append(f"{rel}: steps names '{step}', which does not exist")
        if mode == "single" and len(steps) != 1:
            errs.append(f"{rel}: mode 'single' must declare exactly one step, got {len(steps)}")
        if mode == "multi_step" and len(steps) < 2:
            errs.append(f"{rel}: mode 'multi_step' needs 2+ steps, got {len(steps)}")

    if not (folder / "setup.sh").is_file():
        errs.append(f"{rel}: no setup.sh")

    # A task is graded programmatically, by judge, or both — but it must be graded somehow.
    grader = cfg.get("grader")
    if grader and not (folder / str(grader)).is_file():
        errs.append(f"{rel}: grader '{grader}' does not exist")
    if not grader and not cfg.get("needs_judge"):
        errs.append(f"{rel}: no grader and needs_judge is false — nothing would score this task")

    for src in folder.glob("*.py"):
        errs.extend(check_no_hard_private_dep(src, rel))

    return errs


def check_no_hard_private_dep(src: Path, rel: Path) -> list[str]:
    """No grader may *require* the held-out split — a public clone doesn't have it.

    Looking for it and falling back is fine, and is the documented `_load_expected`
    pattern (private/expected -> tasks/<id>/expected -> None). We inspect string
    constants via the AST so prose in docstrings and comments doesn't trip the check.
    """
    import ast

    try:
        tree = ast.parse(src.read_text())
    except SyntaxError as exc:
        return [f"{rel}/{src.name}: does not parse — {exc}"]

    # Every string constant that is a docstring, so we can ignore those.
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))

    # Functions allowed to name the private split, because falling back is their job.
    allowed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_load_expected":
            allowed.update(id(n) for n in ast.walk(node))

    errs = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings or id(node) in allowed:
            continue
        if "private" in node.value:
            errs.append(
                f"{rel}/{src.name}:{node.lineno}: names the held-out split outside "
                f"_load_expected — a public clone has no private/"
            )
    return errs


def main() -> int:
    folders = sorted(p for p in TASKS.iterdir() if p.is_dir() and (p / "success.yaml").is_file())
    if not folders:
        print("no task folders found", file=sys.stderr)
        return 1

    all_errs: list[str] = []
    seen_ids: dict[str, Path] = {}
    for folder in folders:
        all_errs.extend(check_task(folder))
        try:
            cfg = yaml.safe_load((folder / "success.yaml").read_text()) or {}
        except yaml.YAMLError:
            continue
        if (tid := cfg.get("id")) in seen_ids:
            all_errs.append(f"duplicate task id '{tid}': {seen_ids[tid].name} and {folder.name}")
        elif tid:
            seen_ids[tid] = folder

    if all_errs:
        print(f"✗ {len(all_errs)} problem(s) across {len(folders)} task(s):\n")
        for err in all_errs:
            print(f"  - {err}")
        return 1

    print(f"✓ {len(folders)} task manifests valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
