"""Builder-Bench LLM judge.

The judge grades the *Transcript* surface for tasks that carry a behavioral rubric
(Messy World's "did it flag the data issue?", Vague Ask's "did it ask the right
question?"). It is the subjective counterpart to the programmatic `grader.py`, which
grades the *Deliverable*.

Per PRD §6 the judge's grades do not count until validated against human labels
(Cohen's kappa ≥ 0.7). Until then the programmatic check stays the pass/fail gate and
the judge score is *reported alongside*, not folded into pass/fail.
"""

from .judge import DEFAULT_JUDGE_MODEL, JudgeResult, judge_transcript

__all__ = ["DEFAULT_JUDGE_MODEL", "JudgeResult", "judge_transcript"]
