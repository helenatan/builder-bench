"""Smoke tests: metrics math + the D-01 grader, runnable from a clean clone with no auth.

    pip install -e ".[dev]" && pytest

These exercise everything in the M0 pipeline *except* the authenticated model call: metric
computation and the programmatic grader (fed synthetic agent artifacts).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GRADER = REPO / "tasks" / "d-01-dedup-survives" / "grader.py"

sys.path.insert(0, str(REPO))
from harness.metrics import aggregate, cost_per_solved, pass_at_k  # noqa: E402


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


CORRECT_TABLE = {"Acme Corp": 3, "Globex": 2, "Initech": 1, "Umbrella": 2, "Stark Industries": 1}


def test_grader_pass(tmp_path):
    r = _grade(tmp_path, 3, CORRECT_TABLE)
    assert r["score"] == 1.0 and r["passed"] is True and r["failure_tags"] == []


def test_grader_silent_reversion(tmp_path):
    inflated = dict(CORRECT_TABLE, **{"Stark Industries": 4})  # 4 == Stark raw count
    r = _grade(tmp_path, 3, inflated)
    assert r["score"] == 0.5 and r["passed"] is False
    assert "vision-drift" in r["failure_tags"]


def test_grader_location_inflated_fail(tmp_path):
    r = _grade(tmp_path, 7, {})  # 7 == Acme raw count
    assert r["score"] == 0.0 and r["passed"] is False
    assert "data-blindness" in r["failure_tags"]


def test_grader_no_answer(tmp_path):
    r = _grade(tmp_path, None, {})
    assert r["score"] == 0.0 and "no-answer" in r["failure_tags"]
