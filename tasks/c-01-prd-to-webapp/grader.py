#!/usr/bin/env python3
"""Grader for task c-01 (PRD -> web app with a database).

Programmatic, black-box. The grader never reads the agent's source — it boots the app the
agent built (`bash run.sh`) and tests its *running behavior* against the PRD's HTTP contract,
so it is language/framework-agnostic.

Hardened contract (vs. the original plain CRUD): input validation (400s), a `?status=` list
filter, a **notes** sub-resource, **cascade** delete of notes with their application, and
persistence of BOTH applications and notes across a restart.

    python grader.py <grade_input.json>

Scoring (sums to 1.0; pass_threshold 1.0 requires the whole contract):
    boots 0.10 · create 0.10 · read 0.10 · update 0.10 · validation 0.10 · filter 0.10 ·
    notes 0.10 · persistence 0.15 · delete 0.10 · cascade 0.05
If the server never boots, score is 0 and everything downstream is skipped.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

BOOT_TIMEOUT = 90
REQUEST_TIMEOUT = 5
FALLBACK_PORT = 8000

WEIGHTS = {
    "boots": 0.10, "create": 0.10, "read": 0.10, "update": 0.10, "validation": 0.10,
    "filter": 0.10, "notes": 0.10, "persistence": 0.15, "delete": 0.10, "cascade": 0.05,
}


# --------------------------------------------------------------------------- HTTP helpers
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode(errors="replace")
            try:
                return resp.status, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return e.code, raw
    except (urllib.error.URLError, ConnectionError, socket.timeout, OSError):
        return 0, None


def _short(obj: object) -> str:
    s = json.dumps(obj) if not isinstance(obj, str) else obj
    return s[:200]


# --------------------------------------------------------------------------- server lifecycle
class Server:
    def __init__(self, workdir: Path, port: int, log_path: Path):
        self.workdir = workdir
        self.port = port
        self.log_path = log_path
        self.proc: subprocess.Popen | None = None
        self.base: str | None = None

    def start(self) -> str | None:
        env = dict(os.environ)
        env["PORT"] = str(self.port)
        env["PYTHONUNBUFFERED"] = "1"
        log = self.log_path.open("ab")
        self.proc = subprocess.Popen(
            ["bash", "run.sh"], cwd=str(self.workdir), env=env,
            stdout=log, stderr=log, start_new_session=True,
        )
        deadline = time.time() + BOOT_TIMEOUT
        ports = [self.port] if self.port == FALLBACK_PORT else [self.port, FALLBACK_PORT]
        while time.time() < deadline:
            if self.proc.poll() is not None:
                for p in ports:
                    code, _ = _request("GET", f"http://127.0.0.1:{p}/applications")
                    if code:
                        self.base = f"http://127.0.0.1:{p}"
                        return self.base
                return None
            for p in ports:
                code, _ = _request("GET", f"http://127.0.0.1:{p}/applications")
                if code:
                    self.base = f"http://127.0.0.1:{p}"
                    return self.base
            time.sleep(1.0)
        return None

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        self.proc = None


# --------------------------------------------------------------------------- the contract test
def grade(workdir: Path, attempt_dir: Path) -> dict:
    checks: dict[str, bool] = {k: False for k in WEIGHTS}
    notes: list[str] = []
    tags: list[str] = []

    if not (workdir / "run.sh").is_file():
        return {
            "score": 0.0, "passed": False,
            "failure_tags": ["weak-self-verification", "no-run-script"],
            "details": "no run.sh at project root — the PRD requires one to start the app",
            "checks": checks,
        }

    port = _free_port()
    log1 = attempt_dir / "server_run1.log"
    log2 = attempt_dir / "server_run2.log"

    # ---- Run 1: boot + create/read/update/validation/filter/notes -----------------------
    srv = Server(workdir, port, log1)
    base = srv.start()
    app_id = note_made = second_id = None
    try:
        if not base:
            notes.append("server did not respond on any port within the boot timeout")
            tags.append("weak-self-verification")
            srv.stop()
            return _result(checks, notes, tags)
        checks["boots"] = True

        # CREATE
        code, obj = _request("POST", f"{base}/applications", {"company": "Acme Corp", "role": "Senior PM"})
        if code == 201 and isinstance(obj, dict) and "id" in obj \
                and obj.get("company") == "Acme Corp" and obj.get("role") == "Senior PM":
            checks["create"] = True
            app_id = obj["id"]
            if obj.get("status") not in (None, "applied"):
                notes.append(f"create: status defaulted to {obj.get('status')!r}, expected 'applied'")
        else:
            notes.append(f"create: POST returned {code}, body={_short(obj)}")

        # READ (list + by id)
        if app_id is not None:
            lc, lobj = _request("GET", f"{base}/applications")
            gc, gobj = _request("GET", f"{base}/applications/{app_id}")
            list_ok = lc == 200 and isinstance(lobj, list) and any(
                isinstance(x, dict) and x.get("id") == app_id for x in lobj
            )
            get_ok = gc == 200 and isinstance(gobj, dict) and gobj.get("id") == app_id
            checks["read"] = bool(list_ok and get_ok)
            if not checks["read"]:
                notes.append(f"read: list={lc}(match={list_ok}) get={gc}(match={get_ok})")

            # UPDATE
            uc, uobj = _request("PATCH", f"{base}/applications/{app_id}", {"status": "interviewing"})
            checks["update"] = uc == 200 and isinstance(uobj, dict) and uobj.get("status") == "interviewing"
            if not checks["update"]:
                notes.append(f"update: PATCH returned {uc}, body={_short(uobj)}")

        # VALIDATION: missing required field -> 400; bad status -> 400
        mc, _ = _request("POST", f"{base}/applications", {"company": "NoRole Inc"})
        bc, _ = _request("POST", f"{base}/applications", {"company": "X", "role": "Y", "status": "banana"})
        checks["validation"] = mc == 400 and bc == 400
        if not checks["validation"]:
            notes.append(f"validation: missing-field returned {mc} (want 400), bad-status returned {bc} (want 400)")

        # FILTER: a second app stays 'applied'; query each status partitions correctly
        c2, o2 = _request("POST", f"{base}/applications", {"company": "Globex", "role": "Data PM"})
        if c2 == 201 and isinstance(o2, dict):
            second_id = o2.get("id")
        if app_id is not None and second_id is not None:
            fa_c, fa = _request("GET", f"{base}/applications?status=applied")
            fi_c, fi = _request("GET", f"{base}/applications?status=interviewing")
            def ids(x):
                return {r.get("id") for r in x if isinstance(r, dict)} if isinstance(x, list) else set()
            applied_ok = fa_c == 200 and second_id in ids(fa) and app_id not in ids(fa)
            interviewing_ok = fi_c == 200 and app_id in ids(fi) and second_id not in ids(fi)
            checks["filter"] = bool(applied_ok and interviewing_ok)
            if not checks["filter"]:
                notes.append(f"filter: ?status=applied ok={applied_ok}, ?status=interviewing ok={interviewing_ok}")

        # NOTES: create a note on app_id, then list it
        if app_id is not None:
            nc, nobj = _request("POST", f"{base}/applications/{app_id}/notes", {"text": "called recruiter"})
            note_ok = nc == 201 and isinstance(nobj, dict) and "id" in nobj
            gnc, gn = _request("GET", f"{base}/applications/{app_id}/notes")
            list_ok = gnc == 200 and isinstance(gn, list) and any(
                isinstance(x, dict) and x.get("text") == "called recruiter" for x in gn
            )
            checks["notes"] = bool(note_ok and list_ok)
            note_made = note_ok
            if not checks["notes"]:
                notes.append(f"notes: POST returned {nc} (body={_short(nobj)}), GET list returned {gnc}(match={list_ok})")
    finally:
        srv.stop()

    # ---- Run 2: restart -> persistence (app + note + status), delete, cascade -----------
    if app_id is not None and checks["boots"]:
        srv2 = Server(workdir, port, log2)
        base2 = srv2.start()
        try:
            if not base2:
                notes.append("server failed to restart for the persistence check")
            else:
                pc, pobj = _request("GET", f"{base2}/applications/{app_id}")
                app_survived = pc == 200 and isinstance(pobj, dict) and pobj.get("id") == app_id
                status_survived = isinstance(pobj, dict) and pobj.get("status") == "interviewing"
                gnc, gn = _request("GET", f"{base2}/applications/{app_id}/notes")
                note_survived = gnc == 200 and isinstance(gn, list) and any(
                    isinstance(x, dict) and x.get("text") == "called recruiter" for x in gn
                )
                # persistence requires the application to survive; note survival required only if a note was made
                checks["persistence"] = bool(app_survived and (note_survived or not note_made))
                if not checks["persistence"]:
                    tags.append("weak-self-verification")
                    notes.append(f"persistence: app_survived={app_survived}, note_survived={note_survived} (GET {pc})")
                elif checks["update"] and not status_survived:
                    notes.append("persistence: record survived but the status update did not")

                # DELETE (+ 404 after)
                dc, _ = _request("DELETE", f"{base2}/applications/{app_id}")
                ac, _ = _request("GET", f"{base2}/applications/{app_id}")
                checks["delete"] = dc in (200, 204) and ac == 404
                if not checks["delete"]:
                    notes.append(f"delete: DELETE returned {dc}, follow-up GET returned {ac} (expected 204 then 404)")

                # CASCADE: notes for the deleted app must be gone (404 parent, or empty list)
                cnc, cn = _request("GET", f"{base2}/applications/{app_id}/notes")
                checks["cascade"] = (cnc == 404) or (cnc == 200 and isinstance(cn, list) and len(cn) == 0)
                if not checks["cascade"]:
                    notes.append(f"cascade: GET notes after delete returned {cnc} body={_short(cn)} (expected 404 or empty list)")
        finally:
            srv2.stop()

    return _result(checks, notes, tags)


def _result(checks: dict, notes: list[str], tags: list[str]) -> dict:
    score = round(sum(WEIGHTS[k] for k, ok in checks.items() if ok), 4)
    passed = score >= 1.0
    if not checks["boots"]:
        tags = list(dict.fromkeys(tags + ["weak-self-verification"]))
        details = "app did not boot via run.sh; " + "; ".join(notes)
    elif passed:
        details = "boots; full CRUD + validation + filter + notes; cascade + persistence across restart all hold"
    else:
        failed = [k for k, ok in checks.items() if not ok]
        details = f"partial: failed {failed}. " + "; ".join(notes)
    return {
        "score": score, "passed": passed,
        "failure_tags": list(dict.fromkeys(tags)),
        "details": details, "checks": checks,
    }


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    attempt_dir = Path(payload.get("attempt_dir", workdir))
    result = grade(workdir, attempt_dir)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
