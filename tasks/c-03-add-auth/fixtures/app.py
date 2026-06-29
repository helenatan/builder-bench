"""A tiny web app with a public home plus two pages that should be private.

`/dashboard` and `/settings` are currently visible to anyone — that's the problem to fix.
Stdlib only, so it boots with no dependencies. Listens on $PORT (default 8000).
"""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body="", ctype="text/plain", headers=None):
        self.send_response(code)
        b = body.encode() if isinstance(body, str) else body
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if b:
            self.wfile.write(b)

    def do_GET(self):
        if self.path == "/":
            self._send(200, "Welcome to the app. This page is public.")
        elif self.path == "/dashboard":
            # TODO: this should only be visible to signed-in users.
            self._send(200, "Secret dashboard: Q3 revenue is up 20%.")
        elif self.path == "/settings":
            # TODO: this should only be visible to signed-in users.
            self._send(200, "Account settings: billing email is owner@example.com.")
        else:
            self._send(404, "not found")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
