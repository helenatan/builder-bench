"""Judge validation harness (PRD §6).

The judge is itself a model, so its grades do not count until they are shown to match human
judgment. This script runs the two halves of that protocol:

    # 1. COLLECT — batch-judge every logged transcript for judged tasks, emit a labeling sheet
    python -m judge.validation.validate collect

    # ... a human fills the `human_label` / `human_flagged` columns in labels.csv ...

    # 2. KAPPA — compute judge-vs-human agreement (overall + per contestant model)
    python -m judge.validation.validate kappa

`kappa` reports Cohen's kappa and exact-agreement %. The PRD bar is κ ≥ 0.7. It also breaks
agreement down per contestant model — a Claude judge must not grade Claude transcripts more
kindly (the self-preference check). On a miss, the fix is the *rubric*, not the judge.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = REPO_ROOT / "results" / "runs"
TASKS_DIR = REPO_ROOT / "tasks"
LABELS_CSV = Path(__file__).resolve().parent / "labels.csv"
GOLD_CSV = Path(__file__).resolve().parent / "gold_set.csv"

LABEL_FIELDS = [
    "run_path", "task_id", "model", "attempt",
    "judge_label", "judge_flagged",
    "human_label", "human_flagged", "human_note",  # filled by the human (see review.py)
    "judge_rationale",
]


# --------------------------------------------------------------------------- discovery
def _needs_judge(task_id: str) -> bool:
    """Read success.yaml for the task to see if it carries a rubric."""
    try:
        import yaml
    except ImportError:
        # Fall back to: does a rubric file exist? (private split first, then in-repo.)
        return any(
            (REPO_ROOT / base / f"{task_id}.md").is_file()
            for base in ("private/rubrics", "judge/rubrics")
        )
    for d in TASKS_DIR.iterdir():
        if d.is_dir() and d.name.startswith(task_id):
            spec = d / "success.yaml"
            if spec.is_file():
                cfg = yaml.safe_load(spec.read_text()) or {}
                return bool(cfg.get("needs_judge"))
    return False


def find_transcripts() -> list[dict]:
    """Every attempt transcript under results/runs for tasks that need a judge.

    Skips STALE attempts — runs stamped with a task_version that no longer matches the task
    folder (harness/taskhash.py). A transcript of an old task version must never reach human
    labeling: there is no right label for a transcript graded against a rubric it never saw."""
    current: dict[str, str] = {}
    try:
        from harness.taskhash import current_hashes
        current = current_hashes()
    except Exception:  # noqa: BLE001 — best effort when run outside the repo
        pass

    found: list[dict] = []
    stale: list[str] = []
    if not RUNS_DIR.is_dir():
        return found
    for transcript in sorted(RUNS_DIR.glob("*/*/*/attempt-*/transcript.json")):
        # path: runs/<task>/<model>/<ts>/attempt-N/transcript.json
        parts = transcript.relative_to(RUNS_DIR).parts
        task_id, model = parts[0], parts[1]
        attempt = parts[3]
        if not _needs_judge(task_id):
            continue
        then = None
        try:
            then = json.loads((transcript.parent / "result.json").read_text()).get("task_version")
        except Exception:  # noqa: BLE001
            pass
        now = current.get(task_id)
        if then and now and then != now:
            stale.append(f"{transcript.parent.relative_to(REPO_ROOT)} (ran {then}, task is now {now})")
            continue
        found.append({
            "task_id": task_id, "model": model, "attempt": attempt,
            "path": transcript,
            "run_path": str(transcript.parent.relative_to(REPO_ROOT)),
        })
    if stale:
        print(f"[validate] skipping {len(stale)} stale transcript(s) — task changed since the "
              "run; archive and re-run:", file=sys.stderr)
        for s in stale:
            print(f"  {s}", file=sys.stderr)
    return found


# --------------------------------------------------------------------------- collect
def _sanitize_env() -> None:
    try:
        from harness.runner import enforce_subscription_billing, sanitize_host_env
        sanitize_host_env()
        enforce_subscription_billing()
    except Exception:  # noqa: BLE001
        pass


async def _collect(judge_model: str, labeled_only: bool = False,
                   tasks: set[str] | None = None, missing_only: bool = False) -> None:
    from judge import judge_transcript

    items = find_transcripts()
    if not items:
        print("No transcripts found for judged tasks. Run some tasks with needs_judge: true first.")
        return

    # Preserve any human labels already entered, keyed by run_path.
    prior: dict[str, dict] = {}
    if LABELS_CSV.is_file():
        with LABELS_CSV.open() as f:
            for row in csv.DictReader(f):
                prior[row["run_path"]] = row

    def _needs_run(it: dict) -> bool:
        prev = prior.get(it["run_path"], {})
        if tasks is not None and it["task_id"] not in tasks:
            return False
        if missing_only and prev.get("judge_label", "").strip():
            return False
        if labeled_only:
            return bool(prev.get("human_label", "").strip())
        return True

    todo = [it for it in items if _needs_run(it)]
    if labeled_only or tasks is not None or missing_only:
        scope = " + ".join(filter(None, [
            "human-labeled" if labeled_only else "",
            "missing judge label" if missing_only else "",
            f"tasks {sorted(tasks)}" if tasks is not None else "",
        ]))
        print(f"[collect] judging {len(todo)}/{len(items)} transcripts ({scope}); "
              "others keep their existing judge columns.", file=sys.stderr)

    rows: list[dict] = []
    done = 0
    for it in items:
        prev = prior.get(it["run_path"], {})
        if it in todo:
            transcript = json.loads(it["path"].read_text())
            done += 1
            print(f"  [{done}/{len(todo)}] judging {it['run_path']} ...", file=sys.stderr)
            res = await judge_transcript(it["task_id"], transcript, judge_model=judge_model,
                                         run_dir=it["path"].parent)
            judge_label = res.label if res else ""
            judge_flagged = str(res.flagged).lower() if res else ""
            judge_rationale = (res.rationale if res else "").replace("\n", " ")
        else:  # skipped this round — carry forward whatever judge columns it had
            judge_label = prev.get("judge_label", "")
            judge_flagged = prev.get("judge_flagged", "")
            judge_rationale = prev.get("judge_rationale", "")
        rows.append({
            "run_path": it["run_path"],
            "task_id": it["task_id"],
            "model": it["model"],
            "attempt": it["attempt"],
            "judge_label": judge_label,
            "judge_flagged": judge_flagged,
            "human_label": prev.get("human_label", ""),       # keep prior human work
            "human_flagged": prev.get("human_flagged", ""),
            "human_note": prev.get("human_note", ""),
            "judge_rationale": judge_rationale,
        })

    with LABELS_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
        w.writeheader()
        w.writerows(rows)

    n_human = sum(1 for r in rows if r["human_label"])
    print(f"\nWrote {len(rows)} judged rows -> {LABELS_CSV.relative_to(REPO_ROOT)}")
    print(f"  (judge model: {judge_model}; {n_human} already have human labels)")
    print("Next: open labels.csv and fill the `human_label` (pass/partial/fail) and "
          "`human_flagged` (true/false) columns, then run: validate kappa")


# --------------------------------------------------------------------------- kappa
def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa for two equal-length lists of categorical labels."""
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b))
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    m = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        m[idx[x]][idx[y]] += 1
    po = sum(m[i][i] for i in range(k)) / n
    row = [sum(m[i]) for i in range(k)]
    col = [sum(m[i][j] for i in range(k)) for j in range(k)]
    pe = sum((row[i] / n) * (col[i] / n) for i in range(k))
    if pe == 1.0:
        return 1.0  # perfect, degenerate agreement
    return (po - pe) / (1 - pe)


def _report(pairs: list[tuple[str, str]], title: str) -> None:
    if not pairs:
        print(f"  {title}: no labeled rows")
        return
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]
    exact = sum(1 for x, y in pairs if x == y) / len(pairs)
    kappa = cohens_kappa(a, b)
    bar = "✓ ≥0.7" if kappa >= 0.7 else "✗ <0.7 — tighten the rubric (PRD §6.4)"
    print(f"  {title}: n={len(pairs)}  exact={exact:.0%}  κ={kappa:.3f}  {bar}")


def _kappa(fresh_only: bool = False) -> int:
    if not LABELS_CSV.is_file():
        print(f"No {LABELS_CSV.name}. Run: validate collect", file=sys.stderr)
        return 1
    rows = list(csv.DictReader(LABELS_CSV.open()))
    if fresh_only:
        gold = set()
        if GOLD_CSV.is_file():
            gold = {r["run_path"] for r in csv.DictReader(GOLD_CSV.open())}
        rows = [r for r in rows if r["run_path"] not in gold]
        print(f"[kappa] --fresh-only: excluding {len(gold)} gold-set (reconciled) rows — "
              "this kappa is measured on blind labels only.\n")
    human_only = [r for r in rows if r.get("human_label", "").strip()]
    if not human_only:
        print("No human labels yet. Fill human_label in labels.csv, then re-run.", file=sys.stderr)
        return 1
    labeled = [r for r in human_only if r.get("judge_label", "").strip()]
    if len(labeled) < len(human_only):
        print(f"[kappa] {len(human_only) - len(labeled)} human-labeled row(s) have no judge label "
              "yet — excluded; run `validate collect` to judge them.", file=sys.stderr)
    if not labeled:
        return 1

    print(f"Judge-vs-human agreement on {len(labeled)}/{len(rows)} labeled transcripts")
    print("(judge label is the LLM judge; human label is the reference. PRD bar: κ ≥ 0.7)\n")

    overall = [(r["judge_label"], r["human_label"].strip().lower()) for r in labeled]
    _report(overall, "OVERALL")

    print("\nPer contestant model (self-preference check — PRD §6.5):")
    by_model: dict[str, list[tuple[str, str]]] = {}
    for r in labeled:
        by_model.setdefault(r["model"], []).append(
            (r["judge_label"], r["human_label"].strip().lower())
        )
    for model in sorted(by_model):
        _report(by_model[model], f"  {model}")

    flagged = [
        (r["judge_flagged"].strip().lower(), r["human_flagged"].strip().lower())
        for r in labeled
        if r.get("judge_flagged", "").strip() and r.get("human_flagged", "").strip()
    ]
    if flagged:
        print("\nFlagged-the-issue agreement (true/false, hybrid-gate tasks):")
        _report(flagged, "FLAGGED")

    disagreements = [
        r for r in labeled
        if r["judge_label"].strip() and r["judge_label"].strip().lower() != r["human_label"].strip().lower()
    ]
    if disagreements:
        print(f"\n{len(disagreements)} label disagreement(s) — rubric-fix candidates (PRD §6.4):")
        for r in disagreements:
            note = f"  note: {r['human_note']}" if r.get("human_note", "").strip() else ""
            print(f"  {r['run_path']}: judge={r['judge_label']} human={r['human_label']}{note}")

    return 0


# --------------------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="judge-validate")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="batch-judge all logged transcripts -> labels.csv")
    c.add_argument("--judge-model", default="claude-sonnet-4-6")
    c.add_argument("--labeled-only", action="store_true",
                   help="only judge transcripts that already have a human label")
    c.add_argument("--tasks", help="comma-separated task ids to re-judge (e.g. after a "
                   "rubric edit); others keep their existing judge labels")
    c.add_argument("--missing-only", action="store_true",
                   help="skip rows that already have a judge label (judge only new rows)")
    k = sub.add_parser("kappa", help="compute judge-vs-human agreement from labels.csv")
    k.add_argument("--fresh-only", action="store_true",
                   help="exclude gold_set.csv rows (already reconciled) — report kappa on "
                        "blind labels only")
    args = p.parse_args(argv)

    if args.cmd == "collect":
        _sanitize_env()
        tasks = {t.strip() for t in args.tasks.split(",") if t.strip()} if args.tasks else None
        asyncio.run(_collect(args.judge_model, labeled_only=args.labeled_only, tasks=tasks,
                             missing_only=args.missing_only))
        return 0
    if args.cmd == "kappa":
        return _kappa(fresh_only=args.fresh_only)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
