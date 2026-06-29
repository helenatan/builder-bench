#!/usr/bin/env python3
"""Grader for task c-03 (add auth to a small app).

Programmatic, black-box. Boots the agent's `run.sh` and checks the auth contract over HTTP —
framework-agnostic, never reads the source. Hardened beyond the original single-route gate:

  - TWO routes must be protected (`/dashboard` AND `/settings`),
  - `POST /logout` must actually invalidate the session,
  - login must rate-limit (429) after repeated failures.

    python grader.py <grade_input.json>

Scoring (sums to 1.0; pass_threshold 1.0):
    boots 0.10 · public 0.10 · dashboard_protected 0.20 · settings_protected 0.15 ·
    login_access 0.20 · logout 0.15 · lockout 0.10
The protected-route weights are the security crux: a UI-only gate that still serves the content
to an unauthenticated client fails them.
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
    "boots": 0.10, "public": 0.10, "dashboard_protected": 0.20, "settings_protected": 0.15,
    "login_access": 0.20, "logout": 0.15, "lockout": 0.10,
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # don't follow — we need to SEE the 3xx


_opener = urllib.request.build_opener(_NoRedirect)


def _req(method, url, body=None, cookie=None):
    """Return (status, set_cookie, text). status 0 = connection failure. Redirects NOT followed."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with _opener.open(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.status, resp.headers.get("Set-Cookie"), resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Set-Cookie"), e.read().decode(errors="replace")
    except (urllib.error.URLError, ConnectionError, socket.timeout, OSError):
        return 0, None, ""


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _cookie_pair(set_cookie: str | None) -> str | None:
    if not set_cookie:
        return None
    first = set_cookie.split(",")[0].split(";")[0].strip()
    return first if "=" in first else None


def _protected(status: int, body: str, leak_token: str) -> bool:
    """A route is protected if an unauthenticated GET is 401/403, or a redirect that does NOT
    leak the protected content."""
    leaked = leak_token in body.lower()
    return status in (401, 403) or (status in (302, 303, 307) and not leaked)


def boot(workdir: Path, port: int, log: Path):
    env = dict(os.environ); env["PORT"] = str(port); env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(["bash", "run.sh"], cwd=str(workdir),
                            env=env, stdout=log.open("ab"), stderr=subprocess.STDOUT,
                            start_new_session=True)
    ports = [port] if port == FALLBACK_PORT else [port, FALLBACK_PORT]
    deadline = time.time() + BOOT_TIMEOUT
    while time.time() < deadline:
        if proc.poll() is not None:
            for p in ports:
                if _req("GET", f"http://127.0.0.1:{p}/")[0]:
                    return proc, f"http://127.0.0.1:{p}"
            return proc, None
        for p in ports:
            if _req("GET", f"http://127.0.0.1:{p}/")[0]:
                return proc, f"http://127.0.0.1:{p}"
        time.sleep(1.0)
    return proc, None


def stop(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)
    except (ProcessLookupError, PermissionError):
        pass
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text())
    workdir = Path(payload["workdir"])
    attempt_dir = Path(payload.get("attempt_dir", workdir))
    checks = {k: False for k in WEIGHTS}
    notes: list[str] = []
    tags: list[str] = []

    if not (workdir / "run.sh").is_file():
        print(json.dumps({"score": 0.0, "passed": False,
                          "failure_tags": ["weak-self-verification", "no-run-script"],
                          "details": "no run.sh at project root", "checks": checks}))
        return 0

    port = _free_port()
    proc, base = boot(workdir, port, attempt_dir / "server.log")
    try:
        if not base:
            notes.append("server did not boot within timeout")
            tags.append("weak-self-verification")
        else:
            checks["boots"] = True

            # public home still works
            sc, _, _ = _req("GET", f"{base}/")
            checks["public"] = sc == 200
            if not checks["public"]:
                notes.append(f"GET / returned {sc}, expected 200")

            # both protected without a session
            dc, _, dbody = _req("GET", f"{base}/dashboard")
            checks["dashboard_protected"] = _protected(dc, dbody, "revenue")
            if not checks["dashboard_protected"]:
                tags.append("weak-self-verification")
                notes.append(f"GET /dashboard unauth returned {dc} (leaked={'revenue' in dbody.lower()}); expected 401/redirect")

            stc, _, sbody = _req("GET", f"{base}/settings")
            checks["settings_protected"] = _protected(stc, sbody, "billing")
            if not checks["settings_protected"]:
                tags.append("weak-self-verification")
                notes.append(f"GET /settings unauth returned {stc} (leaked={'billing' in sbody.lower()}); expected 401/redirect")

            # login with valid creds -> 200 + cookie; both routes reachable with it
            lc, setck, _ = _req("POST", f"{base}/login", {"username": "admin", "password": "secret"})
            cookie = _cookie_pair(setck)
            if lc == 200 and cookie:
                ac, _, abody = _req("GET", f"{base}/dashboard", cookie=cookie)
                sc2, _, s2body = _req("GET", f"{base}/settings", cookie=cookie)
                dash_ok = ac == 200 and "revenue" in abody.lower()
                set_ok = sc2 == 200 and "billing" in s2body.lower()
                checks["login_access"] = bool(dash_ok and set_ok)
                if not checks["login_access"]:
                    notes.append(f"authed access: dashboard={ac}(ok={dash_ok}), settings={sc2}(ok={set_ok})")
            else:
                notes.append(f"POST /login (admin/secret) returned {lc}, cookie_set={bool(cookie)}; expected 200 + Set-Cookie")

            # logout invalidates the session: dashboard with the old cookie -> 401/redirect
            if checks["login_access"] and cookie:
                oc, _, _ = _req("POST", f"{base}/logout", {}, cookie=cookie)
                ad, _, adbody = _req("GET", f"{base}/dashboard", cookie=cookie)
                checks["logout"] = oc in (200, 204) and _protected(ad, adbody, "revenue")
                if not checks["logout"]:
                    notes.append(f"logout: POST /logout returned {oc}; dashboard with old cookie returned {ad} "
                                 f"(leaked={'revenue' in adbody.lower()}); expected logout 200 then 401")
            else:
                notes.append("logout: skipped (login_access did not pass)")

            # rate-limit: repeated wrong-password logins must start returning 429
            wrong_codes = []
            for _ in range(6):
                wc, _, _ = _req("POST", f"{base}/login", {"username": "admin", "password": "WRONG"})
                wrong_codes.append(wc)
            checks["lockout"] = 429 in wrong_codes
            if not checks["lockout"]:
                notes.append(f"lockout: 6 wrong-password attempts returned {wrong_codes}; expected a 429 after 5 failures")
            elif not all(c in (401, 429) for c in wrong_codes):
                notes.append(f"warning: wrong-password attempts returned unexpected codes {wrong_codes}")
    finally:
        stop(proc)

    score = round(sum(w for k, w in WEIGHTS.items() if checks[k]), 4)
    passed = score >= 1.0
    if not checks["boots"]:
        details = "app did not boot via run.sh; " + "; ".join(notes)
    elif passed:
        details = ("auth enforced: /dashboard and /settings are 401 without a session and 200 with one; "
                   "logout invalidates the session; login rate-limits after repeated failures; / stays public")
    else:
        details = f"partial: failed {[k for k in checks if not checks[k]]}. " + "; ".join(notes)

    print(json.dumps({
        "score": score, "passed": passed,
        "failure_tags": list(dict.fromkeys(tags)),
        "details": details, "checks": checks,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
