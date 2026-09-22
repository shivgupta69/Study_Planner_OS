# Study Planner OS - Full Stack Project

LINK : https://study-planner-os.onrender.com

Study Planner OS is a Flask-based personal study management application built for task tracking, progress monitoring, and smart study planning. The system combines a Python backend with server-rendered Jinja templates, a SQLite database, and lightweight analytics to help users stay organized and improve study consistency.

The project is organized into clearly separated layers:
- **Backend logic** for routing, validation, business services, and data access
- **Frontend templates** and partials for a responsive, modern UI
- **SQLite persistence** for user accounts, tasks, and analytics history
- **Robust Connection Management**: Utilizes context managers for database sessions to ensure stability and prevent connection leaks.
- **Production-Ready Security**: Implements environment-based secret management for sensitive configurations, replacing hardcoded defaults for production environments.

---

## 1. Project Overview

This application allows a user to:
- **Manage Accounts**: Register and log in to a personal account with secure password hashing.
- **Task Management**: Create, update, filter, and delete study tasks with categories and durations.
- **Smart Study Calendar**: 
    - **Future-Only Due Dates**: Enforces a strict rule where due dates must be tomorrow or later to prevent unrealistic same-day overloading.
    - **Auto-Distribution**: Automatically distributes tasks across available future dates based on a daily study capacity (default 4 hours).
    - **Task Splitting**: Automatically splits long tasks (exceeding daily capacity) across multiple days.
    - **Deadline Respect**: Ensures no task is scheduled beyond its designated due date.
    - **Timeline Generation**: Generates a visual daily timeline starting at 9:00 AM IST.
    - **Date Navigation**: Easily jump between different scheduled days to see planned work.
- **Progress Tracking**: Track task status (To Do, In Progress, Done) and view dashboard summaries.
- **Study Analytics**: Review study activity and completion rates via an analytics dashboard using a delta-based logging system.
- **Enhanced UX**: Features a refined dashboard UI for better task visibility and corrected date validation to ensure schedule integrity.
- **Global Error Handling**: A comprehensive error management system provides graceful, user-friendly feedback across both web templates and API responses.
- **Hybrid Interface**: Interact through a polished browser UI or JSON-based API endpoints.

The application follows a clean layered design:
```text
Browser / User
    |
    v
Flask routes (controllers)
    |
    v
Services (business logic)
    |
    v
Repositories (SQLite queries)
    |
    v
SQLite database
```

---

## 2. Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, Flask |
| Template engine | Jinja2 |
| Database | SQLite |
| Authentication | Flask sessions, password hashing, timed auth tokens |
| Password security | Werkzeug bcrypt support via werkzeug.security and bcrypt |
| Frontend | HTML, Tailwind CSS via CDN, JavaScript (AJAX) |
| Verification | Python compile checks and Flask test-client smoke flows |
| Runtime | Python 3.11+ |

---

## 3. Project Structure

```text
.
├── README.md
├── backend/
│   ├── __init__.py
│   ├── requirements.txt
│   ├── run.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task_model.py
│   │   │   └── user_model.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── analytics_repository.py
│   │   │   ├── task_repository.py
│   │   │   └── user_repository.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── analytics_routes.py
│   │   │   ├── auth_routes.py
│   │   │   ├── schedule_routes.py
│   │   │   └── task_routes.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── analytics_service.py
│   │   │   ├── auth_service.py
│   │   │   ├── schedule_service.py
│   │   │   └── task_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── auth_tokens.py
│   │       ├── db.py
│   │       ├── helpers.py
│   │       ├── security.py
│   │       └── timezone.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── init_db.py
│   └── .gitignore
├── frontend/
│   ├── static/
│   └── templates/
│       ├── analytics.html
│       ├── base.html
│       ├── dashboard.html
│       ├── login.html
│       ├── register.html
│       ├── schedule.html
│       ├── components/
│       │   ├── navbar.html
│       │   ├── progress_bar.html
│       │   ├── sidebar.html
│       │   └── task_card.html
│       ├── macros/
│       │   ├── badge.html
│       │   ├── button.html
│       │   ├── card.html
│       │   ├── input.html
│       │   ├── modal.html
│       │   ├── progress.html
│       │   └── toast.html
│       └── partials/
│           ├── dashboard_filters.html
│           ├── dashboard_metrics.html
│           ├── dashboard_sidebar.html
│           └── dashboard_task_list.html
```

---

## 4. Backend Architecture

### 4.1 App Bootstrap
- **backend/run.py**: Entry point that creates the Flask app and runs it on the configured port.
- **backend/app/__init__.py**: Application factory that registers blueprints (`auth`, `tasks`, `schedule`, `analytics`) and initializes the DB.

### 4.2 Core Logic Layers
- **Models**: Dataclasses for `User` and `Task` to ensure type safety across the app.
- **Repositories**: Direct SQLite query interfaces for users, tasks, and study logs.
- **Services**: Business logic layer.
    - `auth_service`: Handles registration, login, and password security.
    - `task_service`: Manages task lifecycle, validation, and dashboard metrics.
    - `schedule_service`: **The Smart Engine**. Calculates priority scores, manages daily capacity (4h limit), and distributes tasks across available dates starting from today.
    - `analytics_service`: Tracks study hours and completion deltas.
- **Routes**: Flask endpoints mapping URLs to service calls.

### 4.3 Utilities
- **timezone.py**: Ensures all scheduling and analytics are handled consistently in IST (Asia/Kolkata).
- **db.py**: Manages connection pooling and schema initialization.
- **security.py**: Implements bcrypt-based password hashing.

---

## 5. Frontend & UI Documentation

The UI is built with **Tailwind CSS** for a modern, responsive look and **Jinja2** for dynamic content.

- **Dashboard**: The primary workspace featuring AJAX-powered "Fast Add" for tasks and real-time fragment refreshes.
- **Smart Calendar**: A date-aware timeline view that displays scheduled blocks of time, distinguishing between when a task is *scheduled* vs when it is *due*.
- **Analytics**: A visualization page for tracking study hours and task completion rates using delta-based logs.
- **Components**: Uses a library of reusable macros (`card`, `button`, `input`, `toast`) to maintain visual consistency.

---

## 6. Database Schema

The application uses SQLite with three main tables:

### users
`id` (PK), `username` (Unique), `password` (Hashed).

### tasks
`id` (PK), `user_id` (FK), `task_name`, `category`, `duration`, `due_date` (ISO), `status` (todo/in-progress/done), `estimated_hours`, `scheduled_date` (ISO).

### study_logs
`id` (PK), `user_id` (FK), `log_date` (ISO), `hours_studied`, `tasks_completed`, `created_at`.

---

## 7. API Reference

### Task Operations
- `POST /add`: Create task via form.
- `POST /api/tasks`: Create task via JSON.
- `DELETE /api/tasks/<id>`: Remove task.
- `PUT /api/tasks/<id>/status`: Update status.

### Schedule & Analytics
- `GET /schedule`: Main calendar view (supports `?date=YYYY-MM-DD`).
- `GET /api/schedule/today`: JSON response of today's timeline.
- `GET /analytics`: Performance dashboard.

---

## 8. Local Setup & Installation

### Prerequisites
- Python 3.11 or newer
- pip

### Installation
```bash
cd /path/to/project
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Database Initialization
```bash
python backend/scripts/init_db.py
```

### Running the App
```bash
python backend/run.py
```
Access the app at: `http://localhost:5081`

### Production Deployment (Render)
For production, use a WSGI server like Gunicorn instead of the built-in Flask development server. This is essential for concurrency and stability. A ready-made `render.yaml` blueprint is included in the repository root.

**Start command** (must bind to Render's injected `$PORT`, never a hardcoded port):
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 backend.run:app
```

**Required environment variables** (Render dashboard → Environment):

| Variable | Value | Why |
| --- | --- | --- |
| `SECRET_KEY` | random string, e.g. output of `python -c "import secrets; print(secrets.token_hex(32))"` | Session signing. The app refuses to boot on Render without it. |
| `SESSION_COOKIE_SECURE` | `1` | HTTPS-only cookies (defaults to `1` on Render automatically). |
| `DATABASE_PATH` | absolute path to the SQLite file | Defaults to `backend/instance/study.db`. Point it at a mounted disk to persist data. |

**Health check path**: `/login` (lightweight, no auth required).

**Database initialization** happens automatically at startup (`init_db` runs inside the app factory), so no separate build step is needed. `python backend/scripts/init_db.py` remains available for local resets.

> ⚠️ **Persistence warning**: Render's filesystem is ephemeral — the SQLite database is wiped on every deploy/restart unless you attach a Render Disk (see the commented `disk:` block in `render.yaml`) and keep `DATABASE_PATH` inside its `mountPath`.


---

## 9. Verification
**Smoke Test Flow:**
1. Register a new user.
2. Create a task with a future due date.
3. Navigate to `/schedule` and verify the task is automatically scheduled for today (if capacity exists) or a future date.
4. Check that tasks are distributed across multiple days if they exceed 4 hours.
5. Mark a task as `done` and verify that it is removed from the active schedule and recorded in `/analytics`.
