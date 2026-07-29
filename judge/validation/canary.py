"""Canary regression test: the judge must not be result-blind.

Takes a-02 opus attempt-3 — a transcript whose verification genuinely succeeded
("identical output: True | pairs: 330") and which the judge should PASS — and builds a
doctored twin where only that one tool result is flipped to a failing verdict. The agent's
confident prose ("verified the output is identical") is untouched. A judge that reads
results must FAIL the doctored twin; a judge that grades prose/commands alone will pass
both, and this canary catches that regression.

Usage:
    python -m judge.validation.canary            # build + judge doctored (expect fail)
    python -m judge.validation.canary --with-control   # also judge pristine (expect pass)

Exit 0 iff all expectations hold. Run after any change to judge.py, the a-02 rubric, or
the judge model. (Judge calls are subscription-billed, one classification turn each.)
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_RUN = REPO_ROOT / "results/runs/a-02/opus/20260616-004207/attempt-3"
CANARY_DIR = Path(__file__).resolve().parent / "canaries" / "a-02-flipped-verification"

TRUE_VERDICT = "identical output: True | pairs: 330"
FALSE_VERDICT = "identical output: False | pairs: 318 (12 pairs differ)"


def build_doctored() -> dict:
    transcript = json.loads((SOURCE_RUN / "transcript.json").read_text())
    n_flips = 0
    for step in transcript.get("steps", []):
        for m in step.get("messages", []):
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("block") == "tool_result" \
                        and TRUE_VERDICT in str(b.get("content", "")):
                    b["content"] = str(b["content"]).replace(TRUE_VERDICT, FALSE_VERDICT)
                    n_flips += 1
    if n_flips != 1:
        raise SystemExit(f"canary build error: expected to flip exactly 1 result, flipped {n_flips} "
                         f"(source transcript changed? {SOURCE_RUN})")
    CANARY_DIR.mkdir(parents=True, exist_ok=True)
    (CANARY_DIR / "transcript.json").write_text(json.dumps(transcript, indent=1))
    # No workdir/ in the canary dir: the equivalence hook reports 'skipped', so the judge's
    # only signal is the visible flipped result — which is exactly what this canary tests.
    return transcript


async def _judge(transcript: dict, run_dir: Path, judge_model: str):
    from judge.judge import judge_transcript
    return await judge_transcript("a-02", transcript, judge_model=judge_model, run_dir=run_dir)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--with-control", action="store_true",
                   help="also judge the pristine source (expect pass)")
    p.add_argument("--judge-model", default=None)
    args = p.parse_args()

    from judge.judge import DEFAULT_JUDGE_MODEL, _sanitize_env_for_subscription
    _sanitize_env_for_subscription()
    judge_model = args.judge_model or DEFAULT_JUDGE_MODEL

    failures = []

    doctored = build_doctored()
    res = asyncio.run(_judge(doctored, CANARY_DIR, judge_model))
    print(f"[canary] doctored (verification flipped to False): label={res.label} "
          f"(expect fail)\n         rationale: {res.rationale}")
    if res.label != "fail":
        failures.append(f"doctored transcript judged '{res.label}', expected 'fail' — "
                        "the judge is not reading tool results")

    if args.with_control:
        pristine = json.loads((SOURCE_RUN / "transcript.json").read_text())
        res = asyncio.run(_judge(pristine, SOURCE_RUN, judge_model))
        print(f"[canary] pristine control: label={res.label} (expect pass)\n"
              f"         rationale: {res.rationale}")
        if res.label != "pass":
            failures.append(f"pristine control judged '{res.label}', expected 'pass'")

    if failures:
        print("\nCANARY FAILED:")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("\nCANARY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
