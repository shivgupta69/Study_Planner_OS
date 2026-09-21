# Bug Fixes — Study Planner OS (Render 500 / redirect loop)

Date: 2026-09-21 · Verified locally under gunicorn with the full user flow.

## 🔴 Critical bugs fixed

### 1. Dashboard crashed for every logged-in user (infinite redirect loop)
- **File:** `frontend/templates/dashboard.html` (line 5)
- **Bug:** An orphaned `{% endblock %}` with no opening `{% block %}` → Jinja2
  `TemplateSyntaxError: Encountered unknown tag 'endblock'` on every render.
  The error handler flashed + redirected to `/`, which crashed again → loop.
- **Fix:** Removed the stray tag.

### 2. `POST /api/tasks` returned a raw HTML 500 (your "Internal Server Error")
Two stacked bugs:
- **File:** `backend/app/utils/helpers.py` → `sanitize_input()`
  **Bug:** Crashed with `AttributeError: 'int' object has no attribute 'strip'`
  whenever JSON sent a numeric value (e.g. `"duration": 2`).
  **Fix:** Coerce any value to `str` first; `None` → `""`.
- **File:** `backend/app/utils/helpers.py` → `handle_route_errors()`
  **Bug A:** Referenced `logging.PRODUCTION`, which does not exist → the error
  handler itself raised `AttributeError`, escaping as a raw HTML 500 instead of
  the intended JSON error. **Fix:** use the app's `debug` flag instead.
  **Bug B:** `accepts.get("text/html", -1)` — werkzeug 3.x `MIMEAccept` has no
  `.get()` → another handler crash for `Accept: application/json` requests
  (exactly what the dashboard's fragment refresh sends). **Fix:** `accepts["text/html"]`.
  **Bug C:** Browser errors redirected to `/` even when `/` was the failing
  page → redirect loop. **Fix:** never redirect back to the same path.

### 3. `sqlite3.Row` column checks were all silently False
- **Files:** `schedule_service.py`, `task_model.py`, `task_service.py`, `task_routes.py`
- **Bug:** `"scheduled_date" in row` on a `sqlite3.Row` tests the row's VALUES,
  not column names — it is always False. Consequences:
  - `generate_schedule()` never saw `scheduled_date` → **the schedule timeline
    was ALWAYS empty** (the app's headline feature).
  - `build_study_schedule()` never saw `status`/`due_date` → done tasks were
    re-scheduled forever; deadlines ignored.
  - `Task.from_row()` nulled out `due_date`, `estimated_hours`, `scheduled_date`
    → API responses returned `"due_date": null` for real dates.
  - Dashboard chart labels showed "Cat 0", "Cat 1" instead of categories.
- **Fix:** New `row_get(row, key, default)` helper in `utils/db.py` that checks
  `row.keys()`; applied everywhere the broken pattern existed. SQL aliases
  aligned (`SUM(duration) AS total_duration`).

### 4. Analytics crashed once any task was completed
- **File:** `backend/app/repositories/analytics_repository.py`
- **Bug:** SQL returned columns aliased `hours_total`/`tasks_total`, but
  `analytics_service` reads `row["hours_studied"]`/`row["tasks_completed"]`
  → `IndexError` on any non-empty analytics data → (via bug 2C) redirect loop.
- **Fix:** Aliases renamed to match the service.

### 5. Insecure fallback SECRET_KEY in production
- **File:** `backend/config/config.py`
- **Bug:** Missing `SECRET_KEY` only warned and fell back to a constant that is
  public in the repo → anyone could forge session cookies (sessions literally
  contain `user_id`).
- **Fix:** On Render (`RENDER`/`RENDER_SERVICE_ID` env detected) the app now
  **refuses to boot** without `SECRET_KEY`; `SESSION_COOKIE_SECURE` defaults
  to `1` there. Local dev keeps the warning + fallback.

## 🟡 Robustness / contract fixes
- `GET /api/schedule/today` (documented in README) returned 404 → implemented
  as a proper JSON endpoint (`?date=` supported), sharing logic with `/schedule`.
- `/add` and `/api/tasks` now accept `task` **or** `task_name` (README documents
  `task_name`; the JS sends `task`).
- `?date=garbage` on `/schedule` no longer crashes (falls back to today).
- `build_study_schedule` skips legacy rows with invalid durations instead of
  aborting the whole scheduling run.
- New `render.yaml` blueprint: correct `$PORT` start command, auto-generated
  `SECRET_KEY`, `/login` health check, optional 1 GB disk for SQLite persistence.
- README deployment section rewritten for Render (env vars table, warnings).

## ⚙️ Required Render settings (do this even with the fixed code!)
1. **Environment → add `SECRET_KEY`** (the app now fails fast without it):
   `python3 -c "import secrets; print(secrets.token_hex(32))"`
2. **Start command:**
   `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 backend.run:app`
3. **Health check path:** `/login`
4. Optional but recommended: attach a **Disk** mounted at
   `/opt/render/project/src/backend/instance` — otherwise SQLite is wiped on
   every deploy (see `render.yaml` comments).
5. After deploying with a new SECRET_KEY, all users must log in again
   (old signed cookies/tokens become invalid — this is expected and good).

## ✅ Verification performed
- 26-check flow under Flask test client: register → login → dashboard renders →
  API task create (int & string payloads, `task`/`task_name` aliases) → graceful
  JSON 400s → schedule distribution across days (4h/day capacity respected,
  deadlines respected) → status done removes task from timeline → analytics
  renders with completion data → fragments JSON → logged-out redirects.
- Full HTTP-level rerun under `gunicorn` (2 workers) with the exact payloads the
  dashboard JS sends — all green.
