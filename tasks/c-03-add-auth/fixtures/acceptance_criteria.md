# Login — acceptance criteria (what QA will check)

These are the black-box HTTP checks I'll run against the app once it's started with
`bash run.sh` (it should keep listening on the `PORT` env var, default `8000`). All of them
need to pass.

**Home page stays public**
- `GET /` → `200`.

**The two pages require a session**
- `GET /dashboard` and `GET /settings` *without* a valid session → `401`. A `302`/redirect to a
  login page is also acceptable, as long as the protected content itself isn't returned in the
  response.

**Login**
- `POST /login` accepts a JSON body `{"username": "...", "password": "..."}`.
- Correct credentials (`admin` / `secret`) → `200` and a session cookie (a `Set-Cookie` header).
- Wrong credentials → `401`.
- With that valid session cookie, `GET /dashboard` and `GET /settings` → `200` and show their
  content.

**Logout actually logs out**
- `POST /logout` ends the current session. Reusing the same cookie afterward must no longer
  grant access — a later `GET /dashboard` with it → `401` (or a redirect). Clearing the cookie
  on the client side only isn't enough; the session has to be dead server-side, because I'll
  replay the old cookie.

**Brute-force protection**
- After `5` failed login attempts, further login attempts → `429` (Too Many Requests), so the
  one account can't be brute-forced.
