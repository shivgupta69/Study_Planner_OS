"""Task repository for database operations."""

from typing import List, Optional, Set, Tuple, Any
from contextlib import contextmanager

from backend.app.utils.db import get_db


@contextmanager
def db_session():
    """Context manager for database connections to prevent leaks."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def fetch_total_hours_by_user_and_date(user_id: int, target_date: str) -> float:
    """
    Fetch the total estimated hours already scheduled for a user on a specific date.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(estimated_hours) FROM tasks WHERE user_id=? AND scheduled_date=? AND status <> 'done'",
            (user_id, target_date),
        )
        row = cursor.fetchone()
        total = row[0] if row and row[0] is not None else 0.0
        return float(total)


def fetch_tasks_by_user_id(user_id: int) -> List[Tuple]:
    """
    Fetch all tasks for a user ordered by ID descending.

    Args:
        user_id: User's ID.

    Returns:
        List of task rows.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC", (user_id,))
        return cursor.fetchall()


def fetch_task_by_id_for_user(task_id: int, user_id: int) -> Optional[Tuple]:
    """
    Fetch a specific task by ID for a user.

    Args:
        task_id: Task's ID.
        user_id: User's ID for ownership verification.

    Returns:
        Task row or None if not found.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
        return cursor.fetchone()


def fetch_filtered_tasks(
    user_id: int,
    search: str = "",
    category: str = "",
    status: str = "",
    due_filter: str = ""
) -> List[Tuple]:
    """
    Fetch tasks with optional filters.

    Args:
        user_id: User's ID.
        search: Search term for task name/category.
        category: Filter by category.
        status: Filter by status (todo, in-progress, done).
        due_filter: Filter by due date (today, this-week, overdue).

    Returns:
        List of filtered task rows.
    """
    with db_session() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM tasks WHERE user_id=?"
        params = [user_id]

        if search:
            query += " AND (task_name LIKE ? OR category LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        if category:
            query += " AND category=?"
            params.append(category)

        if status:
            query += " AND status=?"
            params.append(status)

        if due_filter == "today":
            query += " AND due_date = date('now', 'localtime')"
        elif due_filter == "this-week":
            query += (
                " AND due_date BETWEEN date('now', 'weekday 1', '-7 days') "
                "AND date('now', 'weekday 0')"
            )
        elif due_filter == "overdue":
            query += (
                " AND due_date IS NOT NULL AND due_date <> '' "
                "AND due_date < date('now', 'localtime') AND status <> 'done'"
            )

        query += " ORDER BY id DESC"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()


def fetch_distinct_categories(user_id: int) -> List[Tuple]:
    """
    Fetch distinct categories for a user.

    Args:
        user_id: User's ID.

    Returns:
        List of category names.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT TRIM(category) AS category
            FROM tasks
            WHERE user_id=?
              AND category IS NOT NULL
              AND TRIM(category) <> ''
            ORDER BY category ASC
            """,
            (user_id,),
        )
        return cursor.fetchall()


def fetch_category_counts(user_id: int) -> List[Tuple]:
    """
    Fetch task count per category for a user.

    Args:
        user_id: User's ID.

    Returns:
        List of (category, count) tuples.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TRIM(category) AS category, COUNT(*) AS total
            FROM tasks
            WHERE user_id=?
              AND category IS NOT NULL
              AND TRIM(category) <> ''
            GROUP BY TRIM(category)
            ORDER BY category ASC
            """,
            (user_id,),
        )
        return cursor.fetchall()


def fetch_stats_by_category(user_id: int) -> List[Tuple]:
    """
    Fetch total duration per category for a user.

    Args:
        user_id: User's ID.

    Returns:
        List of (category, total_duration) tuples.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT category, SUM(duration) AS total_duration FROM tasks WHERE user_id=? GROUP BY category",
            (user_id,),
        )
        return cursor.fetchall()


def fetch_task_columns() -> Set[str]:
    """
    Fetch column names from tasks table.

    Returns:
        Set of column names.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        rows = cursor.fetchall()
        return {row[1] for row in rows}


def insert_task(
    user_id: int,
    task_name: str,
    category: str,
    duration: int,
    due_date: Optional[str] = None,
    status: Optional[str] = None,
    estimated_hours: Optional[float] = None,
    scheduled_date: Optional[str] = None,
) -> int:
    """
    Insert a new task into the database.

    Handles schema migrations for legacy databases with fewer columns.

    Args:
        user_id: User's ID.
        task_name: Task name/description.
        category: Task category.
        duration: Duration in hours.
        due_date: Optional due date.
        status: Task status (default: todo).
        estimated_hours: Estimated study hours.
        scheduled_date: Scheduled study date.

    Returns:
        ID of the newly created task.
    """
    # Removed redundant fetch_task_columns() call from here
    # and used a safer approach within the transaction
    with db_session() as conn:
        cursor = conn.cursor()
        task_columns = {row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()}

        if {
            "due_date",
            "status",
            "estimated_hours",
            "scheduled_date",
        }.issubset(task_columns):
            cursor.execute(
                "INSERT INTO tasks (user_id, task_name, category, duration, due_date, status, estimated_hours, scheduled_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    task_name,
                    category,
                    duration,
                    due_date,
                    status or "todo",
                    estimated_hours if estimated_hours is not None else duration,
                    scheduled_date,
                ),
            )
        elif "due_date" in task_columns and "status" in task_columns:
            cursor.execute(
                "INSERT INTO tasks (user_id, task_name, category, duration, due_date, status) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, task_name, category, duration, due_date, status or "todo"),
            )
        else:
            cursor.execute(
                "INSERT INTO tasks (user_id, task_name, category, duration) VALUES (?, ?, ?, ?)",
                (user_id, task_name, category, duration),
            )

        task_id = cursor.lastrowid
        conn.commit()
        return task_id


def delete_task_for_user(task_id: int, user_id: int) -> int:
    """
    Delete a task by ID for a user.

    Args:
        task_id: Task's ID.
        user_id: User's ID for ownership verification.

    Returns:
        Number of rows deleted (0 or 1).
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
        conn.commit()
        return cursor.rowcount


def update_task_status_for_user(task_id: int, user_id: int, status: str) -> int:
    """
    Update task status for a user's task.

    Args:
        task_id: Task's ID.
        user_id: User's ID for ownership verification.
        status: New status value.

    Returns:
        Number of rows updated (0 or 1).
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status=? WHERE id=? AND user_id=?",
            (status, task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount


def update_task_schedule_fields(
    task_id: int,
    user_id: int,
    estimated_hours: float,
    scheduled_date: str
) -> int:
    """
    Update task scheduling fields.

    Args:
        task_id: Task's ID.
        user_id: User's ID.
        estimated_hours: Updated estimated hours.
        scheduled_date: Updated scheduled date.

    Returns:
        Number of rows updated, or 0 if columns don't exist.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        task_columns = {row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()}
        if not {"estimated_hours", "scheduled_date"}.issubset(task_columns):
            return 0

        cursor.execute(
            "UPDATE tasks SET estimated_hours=?, scheduled_date=? WHERE id=? AND user_id=?",
            (estimated_hours, scheduled_date, task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount


def fetch_weekly_analytics(user_id: int) -> Optional[Tuple]:
    """
    Fetch weekly analytics for a user (tasks due within the next 7 days).

    Args:
        user_id: User's ID.

    Returns:
        Tuple of (total_duration, completed_tasks, total_tasks) or None.
    """
    from backend.app.utils.timezone import get_ist_today
    from datetime import timedelta
    
    today = get_ist_today().isoformat()
    next_week = (get_ist_today() + timedelta(days=7)).isoformat()
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(duration), 0),
                COALESCE(SUM(CASE WHEN status='done' THEN 1 ELSE 0 END), 0),
                COUNT(*)
            FROM tasks
            WHERE user_id=?
              AND due_date IS NOT NULL
              AND due_date BETWEEN ? AND ?
            """,
            (user_id, today, next_week),
        )
        return cursor.fetchone()


def fetch_sessions_by_user_and_date(user_id: int, target_date: str) -> List[Tuple]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.*, t.task_name, t.category, t.due_date, t.status
            FROM task_schedule_sessions s
            JOIN tasks t ON s.task_id = t.id
            WHERE s.user_id = ? AND s.scheduled_date = ? AND t.status <> 'done'
            ORDER BY s.id ASC
            """,
            (user_id, target_date),
        )
        return cursor.fetchall()

def replace_user_sessions(user_id: int, sessions: List[dict]) -> None:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM task_schedule_sessions WHERE user_id = ?", (user_id,))
        if sessions:
            cursor.executemany(
                "INSERT INTO task_schedule_sessions (task_id, user_id, scheduled_date, allocated_hours) VALUES (?, ?, ?, ?)",
                [(s["task_id"], user_id, s["date"], s["hours"]) for s in sessions]
            )
        conn.commit()

def fetch_all_session_dates(user_id: int) -> List[str]:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT scheduled_date FROM task_schedule_sessions WHERE user_id = ? ORDER BY scheduled_date ASC",
            (user_id,),
        )
        return [row[0] for row in cursor.fetchall()]
