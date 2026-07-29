"""Human labeling UI for judge validation (PRD §6).

Serves a local web app for hand-grading judged transcripts one by one. Labels are written
straight into labels.csv (the same file `validate collect` and `validate kappa` use), so the
flow composes in any order — collect preserves human labels keyed by run_path:

    python -m judge.validation.review          # label the core set (attempt-1 per task x model)
    python -m judge.validation.review --all    # label every fresh judged transcript
    python -m judge.validation.validate kappa  # then: judge-vs-human agreement

Blind protocol: the judge's label and rationale are HIDDEN while you label. Seeing the judge's
verdict first anchors the human and inflates kappa; the reveal happens only after your label is
saved, side by side, so disagreements are honest ones. Grade from the rubric, not the judge.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import sys
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from judge.validation.validate import LABELS_CSV, LABEL_FIELDS, REPO_ROOT, find_transcripts

RUBRIC_DIRS = ("private/rubrics", "judge/rubrics")
LABEL_CHOICES = ("pass", "partial", "fail")


# --------------------------------------------------------------------------- state
class Store:
    """Discovered transcripts merged with labels.csv, written back atomically on save."""

    def __init__(self, core_only: bool) -> None:
        items = find_transcripts()
        if core_only:
            # One transcript per (task, tier): attempt-1 of the most recent run. Keeps the
            # labeling session at PRD scale (~25-40) while covering every judged task x tier.
            # Model dirs name the same tier two ways across run eras ("haiku-4.5" vs "haiku"),
            # so key on the tier prefix and break ties by run timestamp.
            latest: dict[tuple[str, str], dict] = {}
            for it in items:
                if it["attempt"] != "attempt-1":
                    continue
                key = (it["task_id"], it["model"].split("-")[0])
                ts = Path(it["run_path"]).parts[-2]
                if key not in latest or ts > Path(latest[key]["run_path"]).parts[-2]:
                    latest[key] = it
            items = sorted(latest.values(), key=lambda i: i["run_path"])
        self.items = items
        self.by_run = {i["run_path"]: i for i in items}
        self.rows: dict[str, dict] = {}      # run_path -> labels.csv row (discovered or not)
        if LABELS_CSV.is_file():
            with LABELS_CSV.open() as f:
                for row in csv.DictReader(f):
                    self.rows[row["run_path"]] = {k: row.get(k, "") for k in LABEL_FIELDS}
        for it in items:
            self.rows.setdefault(it["run_path"], self._blank(it))

    @staticmethod
    def _blank(it: dict) -> dict:
        row = {k: "" for k in LABEL_FIELDS}
        row.update(run_path=it["run_path"], task_id=it["task_id"],
                   model=it["model"], attempt=it["attempt"])
        return row

    def queue(self) -> list[dict]:
        """Discovered rows, unlabeled first, stable task/model/attempt order."""
        rows = [self.rows[i["run_path"]] for i in self.items]
        return sorted(rows, key=lambda r: (bool(r["human_label"].strip()),
                                           r["task_id"], r["model"], r["attempt"]))

    def next_unlabeled(self, after: str | None = None) -> dict | None:
        ordered = [self.rows[i["run_path"]] for i in self.items]
        if after and any(r["run_path"] == after for r in ordered):
            k = next(i for i, r in enumerate(ordered) if r["run_path"] == after)
            ordered = ordered[k + 1:] + ordered[:k]
        return next((r for r in ordered if not r["human_label"].strip()), None)

    def save(self, run_path: str, label: str, flagged: str, note: str) -> None:
        row = self.rows[run_path]
        row["human_label"] = label
        row["human_flagged"] = flagged
        row["human_note"] = note.replace("\n", " ").strip()
        # Atomic rewrite; keep rows for runs not in the current filter/discovery untouched.
        ordered = list(self.rows.values())
        fd, tmp = tempfile.mkstemp(dir=LABELS_CSV.parent, suffix=".csv")
        with os.fdopen(fd, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
            w.writeheader()
            w.writerows(ordered)
        os.replace(tmp, LABELS_CSV)


def load_rubric(task_id: str) -> str:
    for base in RUBRIC_DIRS:
        p = REPO_ROOT / base / f"{task_id}.md"
        if p.is_file():
            return p.read_text()
    return "(no rubric file found for this task)"


# --------------------------------------------------------------------------- rendering
def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def _clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + f"\n… [+{len(s) - n} chars truncated]"


def _tool_use_html(block: dict) -> str:
    name = block.get("name", "?")
    inp = block.get("input") or {}
    if isinstance(inp, dict):
        gist = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
        rest = {k: v for k, v in inp.items() if k not in ("command", "content", "description")}
        detail = json.dumps(inp, indent=2)[:2000]
    else:
        gist, detail = str(inp)[:200], str(inp)[:2000]
    return (f'<details class="tool"><summary>&#128295; <b>{esc(name)}</b> '
            f'<code>{esc(_clip(str(gist), 160))}</code></summary>'
            f'<pre>{esc(detail)}</pre></details>')


def _tool_result_html(block: dict) -> str:
    content = block.get("content", "")
    if isinstance(content, list):
        content = "\n".join(str(c.get("text", c)) if isinstance(c, dict) else str(c)
                            for c in content)
    err = ' class="err"' if block.get("is_error") else ""
    return (f'<details{err}><summary>result{" (error)" if block.get("is_error") else ""}'
            f'</summary><pre>{esc(_clip(str(content), 3000))}</pre></details>')


def render_transcript(t: dict) -> str:
    out: list[str] = []
    for step in t.get("steps", []):
        out.append(f'<h3>Step {esc(step.get("step", "?"))} — prompt</h3>'
                   f'<pre class="prompt">{esc(step.get("prompt", ""))}</pre>')
        for m in step.get("messages", []):
            content = m.get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                kind = b.get("block")
                if kind == "text":
                    out.append(f'<div class="say">{esc(b.get("text", ""))}</div>')
                elif kind == "ThinkingBlock":
                    think = (b.get("data") or {}).get("thinking", "")
                    out.append(f'<details class="think"><summary>thinking</summary>'
                               f'<pre>{esc(_clip(think, 2500))}</pre></details>')
                elif kind == "tool_use":
                    out.append(_tool_use_html(b))
                elif kind == "tool_result":
                    out.append(_tool_result_html(b))
        final = step.get("final_text")
        if final:
            out.append(f'<h4>Final message (step {esc(step.get("step", "?"))})</h4>'
                       f'<div class="final">{esc(final)}</div>')
    return "\n".join(out)


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
 body {{ font: 15px/1.5 -apple-system, sans-serif; margin: 0; color: #1a1a1a; }}
 .wrap {{ max-width: 900px; margin: 0 auto; padding: 24px 20px 40vh; }}
 h1 {{ font-size: 20px; }} h3 {{ margin-top: 28px; }}
 pre {{ background: #f6f6f4; padding: 10px 12px; border-radius: 6px; overflow-x: auto;
       white-space: pre-wrap; font-size: 13px; }}
 pre.prompt {{ background: #eef3fb; border-left: 3px solid #4a7dcf; }}
 .say {{ white-space: pre-wrap; margin: 10px 0; }}
 .final {{ white-space: pre-wrap; background: #f2f8ef; border-left: 3px solid #6aa84f;
          padding: 10px 12px; border-radius: 6px; }}
 details {{ margin: 6px 0; }} details > summary {{ cursor: pointer; color: #666; font-size: 13px; }}
 details.think > summary {{ color: #9a7db0; }}
 details.err > summary {{ color: #c0392b; }}
 .rubric {{ background: #fdf6e3; border: 1px solid #e8d9a0; padding: 4px 16px;
           border-radius: 8px; }}
 .bar {{ position: fixed; bottom: 0; left: 0; right: 0; background: #fff;
        border-top: 2px solid #ddd; padding: 12px 20px; box-shadow: 0 -4px 16px rgba(0,0,0,.07); }}
 .bar .inner {{ max-width: 900px; margin: 0 auto; display: flex; gap: 18px;
               align-items: center; flex-wrap: wrap; }}
 .bar label {{ margin-right: 8px; }}
 .bar input[type=text] {{ flex: 1; min-width: 200px; padding: 6px; }}
 button {{ padding: 8px 22px; font-size: 15px; cursor: pointer; }}
 .pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; }}
 .pass {{ background: #d8f0d0; }} .partial {{ background: #fdeeba; }} .fail {{ background: #f6d3cd; }}
 .none {{ background: #eee; color: #888; }}
 table {{ border-collapse: collapse; width: 100%; }} td, th {{ padding: 5px 10px;
        border-bottom: 1px solid #eee; text-align: left; font-size: 14px; }}
 .agree {{ color: #3c763d; }} .disagree {{ color: #c0392b; font-weight: 600; }}
 .meta {{ color: #777; font-size: 13px; }}
 .compare {{ display: flex; gap: 24px; margin: 20px 0; }}
 .compare > div {{ flex: 1; border: 1px solid #ddd; border-radius: 8px; padding: 14px 16px; }}
 kbd {{ background: #eee; border-radius: 3px; padding: 0 5px; font-size: 12px; }}
</style></head><body><div class="wrap">{body}</div>{bar}
<script>{script}</script></body></html>"""

SHORTCUTS = """
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  const pick = v => { const el = document.querySelector(`input[name=label][value=${v}]`);
                      if (el) el.checked = true; };
  if (e.key === '1') pick('pass');
  if (e.key === '2') pick('partial');
  if (e.key === '3') pick('fail');
  if (e.key === 'f') { const el = document.querySelector('input[name=flagged][value=true]');
                       if (el) el.checked = !el.checked ||
                         (document.querySelector('input[name=flagged][value=false]').checked = false, true); }
  if (e.key === 'Enter') { const f = document.getElementById('labelform'); if (f) f.requestSubmit(); }
  if (e.key === 'n') { const a = document.getElementById('nextlink'); if (a) a.click(); }
});"""


def pill(label: str) -> str:
    l = (label or "").strip().lower()
    cls = l if l in LABEL_CHOICES else "none"
    return f'<span class="pill {cls}">{esc(l or "—")}</span>'


# --------------------------------------------------------------------------- handler
def make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, body: str, code: int = 200) -> None:
            data = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _redirect(self, to: str) -> None:
            self.send_response(303)
            self.send_header("Location", to)
            self.end_headers()

        # ------------------------------------------------------------- pages
        def page_index(self) -> None:
            rows = store.queue()
            done = [r for r in rows if r["human_label"].strip()]
            both = [r for r in done if r["judge_label"].strip()]
            agree = sum(1 for r in both
                        if r["judge_label"].strip().lower() == r["human_label"].strip().lower())
            nxt = store.next_unlabeled()
            head = (f"<h1>Human labeling — judge validation</h1>"
                    f"<p><b>{len(done)}/{len(rows)}</b> labeled"
                    + (f" &middot; agreement so far: <b>{agree}/{len(both)}</b>"
                       f" (run <code>validate kappa</code> for &kappa;)" if both else "")
                    + ".</p>")
            if nxt:
                head += (f'<p><a id="nextlink" href="/review?run={urllib.parse.quote(nxt["run_path"])}">'
                         f'<button>Label next: {esc(nxt["task_id"])} / {esc(nxt["model"])} / '
                         f'{esc(nxt["attempt"])}</button></a> <span class="meta">(<kbd>n</kbd>)</span></p>')
            else:
                head += ('<p><b>All labeled 🎉</b> — run '
                         '<code>python -m judge.validation.validate kappa</code></p>')
            body = [head, "<table><tr><th>task</th><th>model</th><th>attempt</th>"
                          "<th>human</th><th>judge</th><th></th></tr>"]
            for r in rows:
                h, j = r["human_label"].strip().lower(), r["judge_label"].strip().lower()
                verdict = ""
                if h and j:
                    verdict = ('<span class="agree">agree</span>' if h == j
                               else '<span class="disagree">disagree</span>')
                link = f'/review?run={urllib.parse.quote(r["run_path"])}'
                body.append(f'<tr><td><a href="{link}">{esc(r["task_id"])}</a></td>'
                            f'<td>{esc(r["model"])}</td><td>{esc(r["attempt"])}</td>'
                            f'<td>{pill(h)}</td><td>{pill(j) if h else "<span class=meta>hidden until labeled</span>"}</td>'
                            f'<td>{verdict}</td></tr>')
            body.append("</table>")
            self._send(PAGE.format(title="labeling", body="".join(body), bar="", script=SHORTCUTS))

        def page_review(self, run_path: str) -> None:
            it = store.by_run.get(run_path)
            row = store.rows.get(run_path)
            if not it or not row:
                return self._send("<p>Unknown run.</p>", 404)
            transcript = json.loads(it["path"].read_text())
            relabel = bool(row["human_label"].strip())
            queue = store.queue()
            pos = sum(1 for r in queue if r["human_label"].strip())
            body = f"""
<p class="meta"><a href="/">&larr; dashboard</a> &middot; {pos}/{len(queue)} labeled</p>
<h1>{esc(row['task_id'])} &middot; {esc(row['model'])} &middot; {esc(row['attempt'])}</h1>
{'<p class="meta">already labeled ' + pill(row['human_label']) + ' — submitting overwrites</p>' if relabel else ''}
<details class="rubric" open><summary><b>Rubric</b> (grade from this, not from vibes)</summary>
<pre>{esc(load_rubric(row['task_id']))}</pre></details>
{render_transcript(transcript)}
"""
            flagged_now = row["human_flagged"].strip().lower()
            bar = f"""<div class="bar"><form id="labelform" method="post" action="/label"><div class="inner">
<input type="hidden" name="run" value="{esc(run_path)}">
<span><label><input type="radio" name="label" value="pass" {'checked' if row['human_label'] == 'pass' else ''}> pass <kbd>1</kbd></label>
<label><input type="radio" name="label" value="partial" {'checked' if row['human_label'] == 'partial' else ''}> partial <kbd>2</kbd></label>
<label><input type="radio" name="label" value="fail" {'checked' if row['human_label'] == 'fail' else ''}> fail <kbd>3</kbd></label></span>
<span>flagged the issue? <label><input type="radio" name="flagged" value="true" {'checked' if flagged_now == 'true' else ''}> yes <kbd>f</kbd></label>
<label><input type="radio" name="flagged" value="false" {'checked' if flagged_now != 'true' else ''}> no</label></span>
<input type="text" name="note" placeholder="optional note (why, edge cases — feeds rubric fixes)" value="{esc(row.get('human_note', ''))}">
<button type="submit">Save &amp; reveal judge <kbd>&#9166;</kbd></button>
</div></form></div>"""
            self._send(PAGE.format(title=row["task_id"], body=body, bar=bar, script=SHORTCUTS))

        def page_reveal(self, run_path: str) -> None:
            row = store.rows.get(run_path)
            if not row:
                return self._send("<p>Unknown run.</p>", 404)
            h, j = row["human_label"].strip().lower(), row["judge_label"].strip().lower()
            verdict = ""
            if j:
                verdict = ("<p class='agree'><b>Judge agrees with you.</b></p>" if h == j else
                           "<p class='disagree'><b>Disagreement</b> — if the judge is wrong, the fix "
                           "is the <i>rubric</i>, not the judge (PRD §6.4). Note it and move on.</p>")
            else:
                verdict = ("<p class='meta'>No judge label yet for this run — "
                           "<code>validate collect</code> will add one and keep your label.</p>")
            nxt = store.next_unlabeled(after=run_path)
            nav = (f'<a id="nextlink" href="/review?run={urllib.parse.quote(nxt["run_path"])}">'
                   f'<button>Next unlabeled <kbd>n</kbd></button></a>' if nxt
                   else '<a href="/"><button>Dashboard — all labeled 🎉</button></a>')
            body = f"""
<p class="meta"><a href="/">&larr; dashboard</a></p>
<h1>Saved: {esc(row['task_id'])} &middot; {esc(row['model'])} &middot; {esc(row['attempt'])}</h1>
{verdict}
<div class="compare">
 <div><h3>You</h3>{pill(h)} &middot; flagged: <b>{esc(row['human_flagged'] or '—')}</b>
   <p class="meta">{esc(row.get('human_note', ''))}</p></div>
 <div><h3>Judge</h3>{pill(j)} &middot; flagged: <b>{esc(row['judge_flagged'] or '—')}</b>
   <p class="meta">{esc(row['judge_rationale'])}</p></div>
</div>
<p>{nav} &nbsp; <a href="/review?run={urllib.parse.quote(run_path)}">relabel this one</a></p>
"""
            self._send(PAGE.format(title="saved", body=body, bar="", script=SHORTCUTS))

        # ------------------------------------------------------------- routing
        def do_GET(self) -> None:
            url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(url.query)
            if url.path == "/":
                return self.page_index()
            if url.path == "/review" and q.get("run"):
                return self.page_review(q["run"][0])
            if url.path == "/reveal" and q.get("run"):
                return self.page_reveal(q["run"][0])
            self._send("<p>Not found.</p>", 404)

        def do_POST(self) -> None:
            if self.path != "/label":
                return self._send("<p>Not found.</p>", 404)
            length = int(self.headers.get("Content-Length", 0))
            form = urllib.parse.parse_qs(self.rfile.read(length).decode())
            run = form.get("run", [""])[0]
            label = form.get("label", [""])[0]
            if run not in store.rows or label not in LABEL_CHOICES:
                return self._send("<p>Pick pass / partial / fail before saving.</p>", 400)
            store.save(run, label, form.get("flagged", ["false"])[0],
                       form.get("note", [""])[0])
            self._redirect(f"/reveal?run={urllib.parse.quote(run)}")

    return Handler


# --------------------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="judge-review", description=__doc__)
    p.add_argument("--all", action="store_true",
                   help="label every fresh transcript (default: core set = attempt-1 only)")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)

    store = Store(core_only=not args.all)
    if not store.items:
        print("No fresh judged transcripts found under results/runs.", file=sys.stderr)
        return 1
    n_done = sum(1 for i in store.items if store.rows[i["run_path"]]["human_label"].strip())
    scope = "ALL transcripts" if args.all else "core set (attempt-1 per task x model; --all for everything)"
    print(f"Labeling {scope}: {len(store.items)} transcripts, {n_done} already labeled.")
    print(f"Open http://localhost:{args.port}  (Ctrl-C to stop; labels save to "
          f"{LABELS_CSV.relative_to(REPO_ROOT)} on every submit)")
    server = HTTPServer(("127.0.0.1", args.port), make_handler(store))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Next: python -m judge.validation.validate kappa")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
