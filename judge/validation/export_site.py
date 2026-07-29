"""Export the human-labeling exercise as a self-contained static website (PRD §6).

Builds a single-page labeling app plus an ENCRYPTED data payload, so the bundle can sit on any
public static host (the Vercel site, GitHub Pages, a file share) without leaking the private
rubrics — the answer-key split stays private; labelers unlock the payload with a passphrase you
share directly. Labels persist in the labeler's browser (localStorage) and export as a CSV they
send back; merge it with:

    python -m judge.validation.export_site --passphrase "..."   # build private/labeling-site/
    python -m judge.validation.import_labels <exported.csv>     # merge labels back in

Same blind protocol as review.py: the judge's verdict ships inside the encrypted payload but the
app hides it until the human's label is saved.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
from pathlib import Path

from judge.validation.review import Store, load_rubric, _clip
from judge.validation.validate import REPO_ROOT

DEFAULT_OUT = REPO_ROOT / "private" / "labeling-site"
PBKDF2_ITERS = 310_000


# --------------------------------------------------------------------------- payload
def _flag_definition(rubric_text: str) -> str:
    """The rubric's '## flagged' section (canonical definition + per-task instantiation),
    surfaced next to the flagged toggle so labelers apply the strict reading."""
    lines, capture = [], False
    for line in rubric_text.splitlines():
        if line.strip().lower().startswith("## flagged"):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            lines.append(line)
    return "\n".join(lines).strip()


def _simplify_transcript(t: dict) -> list[dict]:
    """Flatten a transcript into render-ready events (mirrors review.py's HTML renderer)."""
    steps: list[dict] = []
    for step in t.get("steps", []):
        events: list[dict] = []
        for m in step.get("messages", []):
            content = m.get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                kind = b.get("block")
                if kind == "text":
                    events.append({"k": "say", "t": b.get("text", "")})
                elif kind == "ThinkingBlock":
                    events.append({"k": "think",
                                   "t": _clip((b.get("data") or {}).get("thinking", ""), 2500)})
                elif kind == "tool_use":
                    inp = b.get("input") or {}
                    if isinstance(inp, dict):
                        gist = str(inp.get("command") or inp.get("file_path")
                                   or inp.get("pattern") or "")
                        detail = json.dumps(inp, indent=2)
                    else:
                        gist, detail = str(inp), str(inp)
                    events.append({"k": "tool", "name": b.get("name", "?"),
                                   "gist": _clip(gist, 160), "detail": _clip(detail, 2000)})
                elif kind == "tool_result":
                    c = b.get("content", "")
                    if isinstance(c, list):
                        c = "\n".join(str(x.get("text", x)) if isinstance(x, dict) else str(x)
                                      for x in c)
                    events.append({"k": "res", "t": _clip(str(c), 3000),
                                   "err": bool(b.get("is_error"))})
        steps.append({"step": step.get("step"), "prompt": step.get("prompt", ""),
                      "final": step.get("final_text", ""), "events": events})
    return steps


def _fresh_batch(store: Store) -> list[dict]:
    """One not-yet-labeled transcript per (task, tier) for a clean blind κ measurement:
    attempt-2 of the latest run, falling back to attempt-3, then any unlabeled attempt.
    Excludes anything with a human label (the reconciled gold set must not be re-labeled)."""
    labeled = {rp for rp, row in store.rows.items() if row.get("human_label", "").strip()}
    by_cell: dict[tuple[str, str], list[dict]] = {}
    for it in store.items:
        if it["run_path"] in labeled:
            continue
        by_cell.setdefault((it["task_id"], it["model"].split("-")[0]), []).append(it)
    picked = []
    for cell, cands in sorted(by_cell.items()):
        cands.sort(key=lambda i: (Path(i["run_path"]).parts[-2], i["attempt"]), reverse=True)
        for pref in ("attempt-2", "attempt-3"):
            hit = next((c for c in cands if c["attempt"] == pref), None)
            if hit:
                break
        picked.append(hit or cands[0])
    return picked


# Tasks whose label turns on what the agent actually *ran* (not what it said): the site
# auto-expands tool events for these and shows the execution-evidence banner prominently.
# Context: the a-02 round-2/3 human slips were prose-salience — the fabricated claim was
# front and center while the (absent) verification hid behind collapsed 🔧 toggles.
BEHAVIOR_KEYED_TASKS = {"a-02"}


def build_payload(batch: str) -> dict:
    store = Store(core_only=False)
    items_src = _fresh_batch(store) if batch == "fresh" else Store(core_only=True).items
    items = []
    for it in items_src:
        row = store.rows.get(it["run_path"], {})
        rubric = load_rubric(it["task_id"])
        transcript = json.loads(it["path"].read_text())
        # Same mechanically-computed evidence banner the judge sees (claim_check ledger +
        # per-task hooks like a-02's equivalence bit) — labelers grade with equal footing.
        try:
            from judge.judge import build_evidence_banner
            evidence = build_evidence_banner(transcript, it["task_id"],
                                             run_dir=it["path"].parent)
        except Exception:  # noqa: BLE001 — the site still works without the banner
            evidence = ""
        items.append({
            "run_path": it["run_path"],
            "task_id": it["task_id"],
            "model": it["model"],
            "attempt": it["attempt"],
            "judge_label": row.get("judge_label", ""),
            "judge_flagged": row.get("judge_flagged", ""),
            "judge_rationale": row.get("judge_rationale", ""),
            "rubric": rubric,
            "flag_def": _flag_definition(rubric),
            "evidence": evidence,
            "expand_tools": it["task_id"] in BEHAVIOR_KEYED_TASKS,
            "steps": _simplify_transcript(transcript),
        })
    return {"batch": batch, "items": items}


def encrypt(payload: dict, passphrase: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=PBKDF2_ITERS).derive(passphrase.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(payload).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return {"kdf": "PBKDF2-SHA256", "iters": PBKDF2_ITERS,
            "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


# --------------------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="export-labeling-site", description=__doc__)
    p.add_argument("--passphrase", help="payload passphrase (default: generate one)")
    p.add_argument("--batch", choices=("core", "fresh"), default="core",
                   help="core = attempt-1 of latest run per task x tier; "
                        "fresh = one NOT-yet-labeled transcript per task x tier "
                        "(prefers attempt-2) for a clean blind kappa measurement")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)

    passphrase = args.passphrase or "-".join(secrets.token_hex(2) for _ in range(3))
    payload = build_payload(batch=args.batch)
    if not payload["items"]:
        print("No transcripts to export for this batch.", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "payload.enc").write_text(json.dumps(encrypt(payload, passphrase)))
    app = (Path(__file__).parent / "site_app.html").read_text()
    (args.out / "index.html").write_text(app)

    raw_kb = len(json.dumps(payload)) // 1024
    print(f"Built labeling site -> {args.out.relative_to(REPO_ROOT)}/")
    print(f"  {len(payload['items'])} transcripts "
          f"({args.batch} batch), payload {raw_kb} KB (encrypted at rest)")
    print(f"  passphrase: {passphrase}")
    print("Share the URL + passphrase with each labeler. They export a CSV when done;")
    print("merge with: python -m judge.validation.import_labels <file.csv>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
