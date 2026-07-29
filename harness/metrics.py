"""Metrics: pass@1, pass@3, cost-per-solved-task.

`pass@k` uses the standard unbiased estimator from Chen et al. (2021): given `n` attempts of
which `c` passed, the probability that a random size-k subset contains at least one pass is

    pass@k = 1 - C(n - c, k) / C(n, k)

For the common M0 case (n = 1), pass@1 is simply 1.0 if the single attempt passed else 0.0.
Cost-per-solved-task is the headline metric the PRD elevates above raw token price: total
dollars spent across all attempts divided by the number of attempts that solved the task.
"""

from __future__ import annotations

from math import comb
from typing import Any


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k for n attempts with c successes."""
    if n <= 0:
        return 0.0
    k = min(k, n)
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def cost_per_solved(total_cost_usd: float, num_solved: int) -> float | None:
    """Dollars per solved task. None when nothing solved (undefined, not zero)."""
    if num_solved <= 0:
        return None
    return total_cost_usd / num_solved


def cost_per_task(total_cost_usd: float, num_attempts: int) -> float | None:
    """Dollars per attempt — a pure *price* number, always defined when any attempt ran.

    Distinct from cost_per_solved: cost_per_solved folds in reliability (failed/retried spend
    lands in the numerator, only successes in the denominator) and is the headline; cost_per_task
    is the stable-denominator companion that still reports a number on zero-solve cells. Their
    ratio (cost_per_solved / cost_per_task) approximates the "reliability tax" of retries and
    dead ends. See docs/v2-plan.md Phase 0."""
    if num_attempts <= 0:
        return None
    return total_cost_usd / num_attempts


def aggregate(attempts: list[dict[str, Any]], ks: tuple[int, ...] = (1, 3)) -> dict[str, Any]:
    """Roll up a list of attempt results into reportable metrics.

    Each attempt dict needs at least: {"passed": bool, "score": float, "cost_usd": float}.
    pass@k is only reported for k <= number of attempts actually run.
    """
    n = len(attempts)
    c = sum(1 for a in attempts if a.get("passed"))
    total_cost = sum(float(a.get("cost_usd", 0.0)) for a in attempts)
    scores = [float(a.get("score", 0.0)) for a in attempts]

    def _isum(key: str) -> int:
        return sum(int(a.get(key, 0) or 0) for a in attempts)

    pass_at: dict[str, float] = {}
    for k in ks:
        if k <= n:
            pass_at[f"pass@{k}"] = round(pass_at_k(n, c, k), 4)

    cps = cost_per_solved(total_cost, c)
    cpt = cost_per_task(total_cost, n)
    # Effort signals (summed across all attempts) — the raw material for the economic profile
    # (PRD §7-adjacent / docs/v2-plan.md Phase 0). tool_calls is added by the runner per attempt.
    return {
        "attempts": n,
        "solved": c,
        **pass_at,
        "mean_score": round(sum(scores) / n, 4) if n else 0.0,
        "best_score": round(max(scores), 4) if n else 0.0,
        "total_cost_usd": round(total_cost, 6),
        "cost_per_solved_usd": round(cps, 6) if cps is not None else None,
        "cost_per_task_usd": round(cpt, 6) if cpt is not None else None,
        "input_tokens": _isum("input_tokens"),
        "output_tokens": _isum("output_tokens"),
        "num_turns": _isum("num_turns"),
        "tool_calls": _isum("tool_calls"),
    }
