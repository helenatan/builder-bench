"""Smoke tests: metrics math + the b-01 grader, runnable from a clean clone with no auth.

    pip install -e ".[dev]" && pytest

These exercise the whole pipeline *except* the authenticated model call: metric computation
and the programmatic grader (fed synthetic agent artifacts). No network, no `private/` split
— the grader recomputes ground truth from the public fixtures.

Expected counts are derived from the grader's own `ground_truth()` rather than hardcoded, so
editing a fixture re-points the tests instead of silently breaking them.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GRADER = REPO / "tasks" / "b-01-dedup-survives" / "grader.py"

sys.path.insert(0, str(REPO))
from harness.metrics import aggregate, cost_per_solved, pass_at_k  # noqa: E402


def _load_grader_module():
    """Import the b-01 grader as a module so tests can reuse its ground truth."""
    spec = importlib.util.spec_from_file_location("b01_grader", GRADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_b01 = _load_grader_module()
GT = _b01.ground_truth()
UNIQUE = GT["unique_by_company"]          # e.g. {"Acme Corp": 4, ...}
RAW = GT["raw_by_company"]                # e.g. {"Acme Corp": 12, ...}
ACME_TRUTH = UNIQUE["Acme Corp"]
ACME_RAW = RAW["Acme Corp"]


def test_pass_at_k_basic():
    assert pass_at_k(1, 1, 1) == 1.0
    assert pass_at_k(1, 0, 1) == 0.0
    assert pass_at_k(3, 0, 3) == 0.0
    assert pass_at_k(3, 3, 3) == 1.0
    # 3 attempts, 1 success: pass@1 = 1/3, pass@3 = 1.0
    assert pass_at_k(3, 1, 1) == pytest.approx(1 / 3)
    assert pass_at_k(3, 1, 3) == 1.0


def test_cost_per_solved():
    assert cost_per_solved(0.60, 3) == pytest.approx(0.20)
    assert cost_per_solved(1.0, 0) is None


def test_aggregate():
    attempts = [
        {"passed": True, "score": 1.0, "cost_usd": 0.10},
        {"passed": False, "score": 0.0, "cost_usd": 0.05},
        {"passed": True, "score": 1.0, "cost_usd": 0.10},
    ]
    m = aggregate(attempts)
    assert m["attempts"] == 3 and m["solved"] == 2
    assert m["pass@1"] == pytest.approx(2 / 3, abs=1e-3)  # aggregate() rounds to 4 dp
    assert m["pass@3"] == 1.0
    assert m["cost_per_solved_usd"] == pytest.approx(0.25 / 2)


def _grade(tmp_path: Path, answer: int | None, table: dict[str, int]) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    if answer is not None:
        (workdir / "answer.json").write_text(
            json.dumps({"company": "Acme Corp", "unique_openings": answer})
        )
    if table:
        lines = ["company,unique_openings"] + [f"{c},{v}" for c, v in table.items()]
        (workdir / "unique_openings.csv").write_text("\n".join(lines) + "\n")
    gi = tmp_path / "gi.json"
    gi.write_text(json.dumps({"workdir": str(workdir), "final_text": "see answer.json"}))
    out = subprocess.run(
        [sys.executable, str(GRADER), str(gi)],
        cwd=str(GRADER.parent), capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def _naive_unique_ignoring_normalization() -> dict[str, int]:
    """What an agent that deduped on the *literal* title (no case/whitespace folding) gets."""
    import csv

    seen: dict[str, set[str]] = {}
    for fname in ("postings.csv", "new_postings.csv"):
        fpath = GRADER.parent / "fixtures" / fname
        if not fpath.is_file():
            continue
        with fpath.open() as fh:
            for row in csv.DictReader(fh):
                seen.setdefault(row["company"].strip(), set()).add(row["title"])
    return {c: len(t) for c, t in seen.items()}


CORRECT_TABLE = dict(UNIQUE)


def test_ground_truth_is_a_real_trap():
    """The task only has signal if deduping and not-deduping give different answers."""
    assert ACME_TRUTH < ACME_RAW, "Acme must be location-inflated in the fixtures"
    assert any(RAW[c] != UNIQUE[c] for c in UNIQUE), "no company is inflated — trap is gone"


def test_grader_pass(tmp_path):
    r = _grade(tmp_path, ACME_TRUTH, CORRECT_TABLE)
    assert r["score"] == 1.0 and r["passed"] is True and r["failure_tags"] == []


def test_grader_silent_reversion(tmp_path):
    # Pick any company whose raw count differs from its unique count, and quietly revert it.
    victim = next(c for c in UNIQUE if RAW[c] != UNIQUE[c] and c != "Acme Corp")
    inflated = dict(CORRECT_TABLE, **{victim: RAW[victim]})
    r = _grade(tmp_path, ACME_TRUTH, inflated)
    assert r["score"] == 0.5 and r["passed"] is False
    assert "vision-drift" in r["failure_tags"]


def test_grader_location_inflated_fail(tmp_path):
    r = _grade(tmp_path, ACME_RAW, {})  # answered with the raw per-location count
    assert r["score"] == 0.0 and r["passed"] is False
    assert "data-blindness" in r["failure_tags"]


def test_grader_lost_normalization_fail(tmp_path):
    """Counting `Senior PM` / `senior pm` / `Senior  PM` as distinct roles inflates Acme
    above the true unique count but below the raw count — the step-1 rule half that is
    never spelled out in the prompts."""
    naive = _naive_unique_ignoring_normalization()["Acme Corp"]
    assert ACME_TRUTH < naive < ACME_RAW, "fixtures no longer exercise the normalization trap"
    r = _grade(tmp_path, naive, {})
    assert r["score"] == 0.0 and r["passed"] is False
    assert "vision-drift" in r["failure_tags"]


def test_grader_no_answer(tmp_path):
    r = _grade(tmp_path, None, {})
    assert r["score"] == 0.0 and "no-answer" in r["failure_tags"]
