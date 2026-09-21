"""Scheduling services for dashboard timelines and task planning."""

from datetime import date, datetime, timedelta
from typing import Any

from backend.app.repositories.task_repository import (
    fetch_tasks_by_user_id,
    update_task_schedule_fields,
    fetch_total_hours_by_user_and_date,
)
from backend.app.utils.db import row_get
from backend.app.utils.timezone import get_ist_now, get_ist_today, make_ist_datetime

DEFAULT_DAY_START_HOUR = 9
DEFAULT_DAILY_AVAILABLE_HOURS = 4


def _parse_iso_date(date_value):
    """Parse an ISO date string into a ``date`` object."""
    if not date_value:
        return None
    try:
        return datetime.strptime(date_value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _task_priority_score(task_row, today):
    """Return a deterministic scheduling priority for a task row."""
    due_date = _parse_iso_date(row_get(task_row, "due_date"))
    status = row_get(task_row, "status") or "todo"
    estimated_hours = row_get(task_row, "estimated_hours")
    if estimated_hours is None:
        estimated_hours = row_get(task_row, "duration", 0)

    score = 0
    if due_date:
        days_until_due = (due_date - today).days
        if days_until_due <= 1:
            score += 5
        elif days_until_due <= 3:
            score += 4
        elif days_until_due <= 7:
            score += 3
        else:
            score += 1

    if status == "in-progress":
        score += 2

    if estimated_hours >= 4:
        score += 3
    elif estimated_hours >= 2:
        score += 2
    else:
        score += 1

    return score


def generate_schedule(tasks, target_date=None):
    """Build the visual day timeline for a specific date."""
    schedule = []

    # Default to today if no target_date provided
    if target_date is None:
        target_date = get_ist_today().isoformat()

    current_time = make_ist_datetime(date.fromisoformat(target_date), DEFAULT_DAY_START_HOUR)

    # Filter tasks by scheduled_date and exclude completed tasks
    daily_tasks = []
    for task in tasks:
        # NOTE: sqlite3.Row requires key lookup via row_get; the `in`
        # operator on a Row tests VALUES, not column names.
        scheduled_date = row_get(task, "scheduled_date")
        status = row_get(task, "status") or "todo"

        if scheduled_date == target_date and status != "done":
            daily_tasks.append(task)

    # Sort by priority score or estimated hours (since they are already persisted)
    # Using a simple sort by ID or original order for stability
    sorted_tasks = sorted(daily_tasks, key=lambda x: x["id"])

    for task in sorted_tasks:
        estimated = row_get(task, "estimated_hours")
        duration = float(estimated if estimated is not None else row_get(task, "duration", 0))
        start_time = current_time
        end_time = start_time + timedelta(hours=duration)

        schedule.append(
            {
                "task": task["task_name"],
                "category": task["category"],
                "start_time": start_time,
                "end_time": end_time,
                "duration_hours": duration,
                "due_date": row_get(task, "due_date"),
                "status": row_get(task, "status") or "todo",
            }
        )
        current_time = end_time

    return schedule


def build_study_schedule(tasks, user_id, daily_available_hours=DEFAULT_DAILY_AVAILABLE_HOURS):
    """Create a day-wise study plan without exceeding daily capacity."""
    # Guard against infinite loops/zero capacity
    if daily_available_hours < 0.1:
        daily_available_hours = DEFAULT_DAILY_AVAILABLE_HOURS

    today = get_ist_today()
    pending_tasks = []

    for row in tasks:
        status = row_get(row, "status") or "todo"
        if status == "done":
            continue

        estimated_hours = row_get(row, "estimated_hours")
        if estimated_hours is None:
            estimated_hours = row_get(row, "duration")
        try:
            estimated_hours = float(estimated_hours)
            if estimated_hours <= 0:
                raise ValueError("Duration must be positive.")
        except (ValueError, TypeError):
            # Skip tasks with invalid/legacy durations instead of aborting the
            # whole scheduling run (a single bad row must not break creation,
            # deletion or status updates elsewhere in the app).
            continue
        due_date = _parse_iso_date(row_get(row, "due_date"))

        pending_tasks.append(
            {
                "id": row["id"],
                "task_name": row["task_name"],
                "category": row["category"],
                "due_date": due_date,
                "estimated_hours": estimated_hours,
                "priority_score": _task_priority_score(row, today),
            }
        )

    pending_tasks.sort(
        key=lambda task: (
            task["due_date"] is None,
            task["due_date"] or date.max,
            -task["priority_score"],
            -task["estimated_hours"],
            task["id"],
        )
    )

    day_capacity: dict[date, float] = {}
    schedule_sessions: list[dict[str, Any]] = []
    assignments = {}

    # Smart Study Calendar: Start scheduling from today.
    # We allow scheduling for today to ensure new tasks appear immediately if capacity allows.
    cursor_day = today
    max_iterations = 365 # Safety guard: don't schedule beyond 1 year

    for task in pending_tasks:
        remaining_hours = task["estimated_hours"]
        current_day = cursor_day
        first_scheduled_day = None
        deadline_day = task["due_date"]
        iteration_count = 0

        while remaining_hours > 0 and iteration_count < max_iterations:
            iteration_count += 1
            if deadline_day and current_day > deadline_day:
                deadline_day = None

            if current_day not in day_capacity:
                # DB-Aware Capacity: Subtract hours already spent on this day
                existing_hours = fetch_total_hours_by_user_and_date(user_id, current_day.isoformat())
                day_capacity[current_day] = float(daily_available_hours) - existing_hours

            available_hours = day_capacity[current_day]
            if available_hours <= 0:
                current_day += timedelta(days=1)
                continue

            allocated_hours = min(remaining_hours, available_hours)
            day_capacity[current_day] -= allocated_hours
            remaining_hours -= allocated_hours

            if first_scheduled_day is None:
                first_scheduled_day = current_day

            schedule_sessions.append(
                {
                    "task_id": task["id"],
                    "task": task["task_name"],
                    "category": task["category"],
                    "date": current_day.isoformat(),
                    "hours": allocated_hours,
                    "priority_score": task["priority_score"],
                }
            )

            if remaining_hours > 0:
                current_day += timedelta(days=1)
                # Ensure we don't schedule past the due date
                if deadline_day and current_day > deadline_day:
                    # If we've exceeded the deadline but still have hours, we must stop.
                    # The task is partially scheduled, but the remainder is unschedulable.
                    remaining_hours = 0
                    break

        assignments[task["id"]] = (
            first_scheduled_day.isoformat() if first_scheduled_day else (today + timedelta(days=1)).isoformat()
        )

    for row in tasks:
        if row["id"] not in assignments:
            assignments[row["id"]] = row_get(row, "scheduled_date") or None

    return {"sessions": schedule_sessions, "assignments": assignments}


def schedule_user_tasks(user_id, daily_available_hours=DEFAULT_DAILY_AVAILABLE_HOURS):
    """Persist auto-scheduled dates for a user's current task list."""
    tasks = fetch_tasks_by_user_id(user_id)
    schedule_result = build_study_schedule(tasks, user_id=user_id, daily_available_hours=daily_available_hours)

    for task_row in tasks:
        task_id = task_row["id"]
        estimated_hours = row_get(task_row, "estimated_hours")
        if estimated_hours is None:
            estimated_hours = row_get(task_row, "duration")
        scheduled_date = schedule_result["assignments"].get(task_id)
        update_task_schedule_fields(task_id, user_id, estimated_hours, scheduled_date)

    return schedule_result
