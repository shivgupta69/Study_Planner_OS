"""Task model definition."""

from dataclasses import dataclass
from typing import Optional

from backend.app.utils.db import row_get


@dataclass
class Task:
    """
    Task data model.

    Attributes:
        id: Task's unique identifier.
        user_id: Owner's user ID.
        task_name: Task title/description.
        category: Task category (e.g., Math, Science).
        duration: Estimated duration in hours.
        due_date: Optional due date (ISO format).
        status: Task status (todo, in-progress, done).
        estimated_hours: Scheduled study hours.
        scheduled_date: Assigned study date (ISO format).
    """
    id: int
    user_id: int
    task_name: str
    category: str
    duration: int
    due_date: Optional[str] = None
    status: str = "todo"
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[str] = None

    @classmethod
    def from_row(cls, row):
        """Create Task instance from database row."""
        if not row:
            return None
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            task_name=row["task_name"],
            category=row["category"],
            duration=row["duration"],
            due_date=row_get(row, "due_date"),
            status=row_get(row, "status") or "todo",
            estimated_hours=row_get(row, "estimated_hours"),
            scheduled_date=row_get(row, "scheduled_date"),
        )
