# Application Tracker — product brief

I'm deep in a job search and I've lost the plot. Which companies did I apply to, for what
role, and where does each one stand right now? My spreadsheet is a mess and I keep
double-applying. I want a small service of my own — something my scripts and tools can talk
to — so nothing falls through the cracks.

It's just me using it. No UI needed, no one else logs in. I just want a reliable place to put
this stuff and get it back.

## What I'm tracking

Each thing I track is one **application**: the company and the role I applied for. Every
application starts life as *just applied* and moves through stages as things progress —
**applied → interviewing → offer → rejected**. Those four are the only stages that are real
to me. When I add one, it should land in *applied* unless I say otherwise.

I also want to jot **notes** on any application — little reminders like "recruiter called" or
"take-home due Friday." A note is just some text, and it always belongs to one specific
application.

## What I need to do

- **Add** an application (company + role), and **see** everything I've applied to, or pull up
  any single one on its own.
- **Filter** the list down to just the ones at a given stage — e.g. show me only what I'm
  interviewing for right now.
- **Move** an application to a new stage as things change.
- **Remove** an application I want to forget about entirely.
- **Add** a note to a specific application, and **read back** all the notes on it.

## What matters most

- **My data has to stick around.** If I close my laptop and come back tomorrow, every
  application *and* every note I entered is still there exactly as I left it. Losing data is a
  dealbreaker. And coming back shouldn't quietly reset or re-seed anything either — restarting
  the service must leave my existing data untouched, not wipe it or refill it with samples.
- **Don't let me save junk.** An application with no company, or no role, is useless to me —
  don't save it, tell me it was bad input. Same if something tries to set a stage that isn't
  one of the four real ones.
- **When I delete an application, its notes go with it.** I don't want orphaned notes for a
  company I've stopped tracking — once the application is gone, its notes should be gone too.

## What "done" feels like

So we're agreed on the parts that are easy to get subtly wrong, here's the behavior my scripts
expect. It's a JSON-over-HTTP service, and they hit these routes:

- **`POST /applications`** — add one. Comes back as **201** with the new record: a
  server-assigned unique `id`, the `company` and `role` I sent, a `status` (defaulting to
  `applied`), and a server-set `created_at` timestamp (ISO 8601). Missing `company`, missing
  `role`, or a stage outside the four → client error **400**, and nothing gets saved.
- **`GET /applications`** — list, **200** with a JSON array. Accepts an optional
  `?status=<stage>` filter that returns only applications at that stage.
- **`GET /applications/{id}`** — fetch one, **200**, or **404** if there's no such application.
- **`PATCH /applications/{id}`** — change just the fields I send (usually the stage), **200**
  with the updated record, or **404** if it doesn't exist. A stage outside the four → **400**.
- **`DELETE /applications/{id}`** — remove it. Returns success-with-no-content (**204**);
  fetching that application afterward returns **404**, and so do (or empty-out) its notes.
- **`POST /applications/{id}/notes`** — add a note. **201** with the created note (its own
  `id` plus the `application_id` it belongs to). No `text` → **400**; unknown application →
  **404**.
- **`GET /applications/{id}/notes`** — list an application's notes, **200** with an array;
  unknown application → **404**.

Resources and the shapes I expect back:

| Application field | Notes |
|-------|-------|
| `id` | server-assigned, unique |
| `company` | required |
| `role` | required |
| `status` | one of `applied`, `interviewing`, `offer`, `rejected`; defaults to `applied` |
| `created_at` | server-set, ISO 8601 |

| Note field | Notes |
|-------|-------|
| `id` | server-assigned, unique |
| `application_id` | the parent application's id |
| `text` | required |
| `created_at` | server-set, ISO 8601 |

## A couple of practical things

- The service should listen on the port in the `PORT` environment variable, defaulting to
  **8000**.
- Give me a `run.sh` at the project root that installs whatever it needs and starts the
  service in the foreground — `bash run.sh` should be all it takes. Use whatever storage makes
  sense to you; I care that the data survives, not how.

## Out of scope

Authentication, pagination, a web UI, multiple users. Keep it small and correct.
