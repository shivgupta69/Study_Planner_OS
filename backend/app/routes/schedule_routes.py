from flask import Blueprint, jsonify, render_template, request, session
from datetime import date

from backend.app.services.schedule_service import generate_schedule
from backend.app.services.task_service import get_user_task_rows
from backend.app.utils.db import row_get
from backend.app.utils.helpers import handle_route_errors, login_required
from backend.app.utils.timezone import IST, ensure_ist, get_ist_today


schedule_bp = Blueprint("schedule", __name__)


def _build_schedule_context(user_id, target_date=None):
    """Shared scheduling logic for the HTML view and the JSON API."""
    tasks = get_user_task_rows(user_id)
    today = get_ist_today()

    if target_date:
        # Ignore malformed ?date= values instead of crashing the page.
        try:
            date.fromisoformat(target_date)
        except ValueError:
            target_date = today.isoformat()
    else:
        target_date = today.isoformat()

    schedule = generate_schedule(tasks, target_date=target_date)

    for item in schedule:
        item["start_time"] = ensure_ist(item.get("start_time"))
        item["end_time"] = ensure_ist(item.get("end_time"))

    # Find all dates that have at least one task scheduled.
    # NOTE: use row_get -- `"col" in row` tests VALUES on sqlite3.Row, not keys.
    scheduled_dates = sorted(
        {d for d in (row_get(t, "scheduled_date") for t in tasks) if d}
    )

    return tasks, today, target_date, schedule, scheduled_dates


@schedule_bp.route("/schedule")
@handle_route_errors
@login_required
def schedule_view():
    user_id = session["user_id"]

    # Get target date from query param, default to today
    target_date = (request.args.get("date") or "")[:20]

    _, today, target_date, schedule, scheduled_dates = _build_schedule_context(
        user_id, target_date
    )

    # Today's schedule is possible since scheduling starts from today.
    # Show the hint only when the schedule is empty AND it's the today view.
    schedule_is_empty = len(schedule) == 0
    is_today_view = (target_date == today.isoformat())
    today_hint = None
    if schedule_is_empty and is_today_view:
        today_hint = "No tasks scheduled for today. Add some tasks on the dashboard to get started!"

    return render_template(
        "schedule.html",
        schedule=schedule,
        timezone_label=IST.zone,
        selected_date=target_date,
        today=today.isoformat(),
        scheduled_dates=scheduled_dates,
        today_hint=today_hint
    )


@schedule_bp.route("/api/schedule/today")
@handle_route_errors
@login_required
def schedule_today_api():
    """JSON timeline for a day (defaults to today in IST).

    Documented API: GET /api/schedule/today[?date=YYYY-MM-DD]
    """
    user_id = session["user_id"]
    target_date = (request.args.get("date") or "")[:20]

    _, today, target_date, schedule, _ = _build_schedule_context(user_id, target_date)

    return jsonify(
        {
            "success": True,
            "date": target_date,
            "is_today": target_date == today.isoformat(),
            "timezone": IST.zone,
            "schedule": [
                {
                    "task": item["task"],
                    "category": item["category"],
                    "start_time": item["start_time"].isoformat()
                    if item.get("start_time")
                    else None,
                    "end_time": item["end_time"].isoformat()
                    if item.get("end_time")
                    else None,
                    "duration_hours": item["duration_hours"],
                    "due_date": item.get("due_date"),
                    "status": item.get("status"),
                }
                for item in schedule
            ],
        }
    )
