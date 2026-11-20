"""Data model and date helpers."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

# Formats accepted when a user types a date.
DATE_INPUT_FORMATS = ("%Y-%m-%d", "%d %b %Y", "%d %B %Y")
# Format used whenever a date is shown to the user.
DISPLAY_FORMAT = "%d %b %Y"


def parse_date(text: str) -> dt.date | None:
    """Parse ``2026-06-03``, ``03 Jun 2026`` or ``03 June 2026``.

    Returns ``None`` if the text matches none of the accepted formats.
    """
    text = text.strip()
    for fmt in DATE_INPUT_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_date(value: dt.date) -> str:
    """Format a date for display, e.g. ``03 Jun 2026``."""
    return value.strftime(DISPLAY_FORMAT)


@dataclass
class Task:
    """A single task assigned to one user."""

    id: int
    assignee: str
    title: str
    description: str
    date_assigned: dt.date
    due_date: dt.date
    completed: bool = False

    def is_overdue(self, today: dt.date | None = None) -> bool:
        """A task is overdue when it is incomplete and its due date has passed.

        A task due *today* is not overdue yet.
        """
        today = today or dt.date.today()
        return not self.completed and self.due_date < today

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "assignee": self.assignee,
            "title": self.title,
            "description": self.description,
            "date_assigned": self.date_assigned.isoformat(),
            "due_date": self.due_date.isoformat(),
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=int(data["id"]),
            assignee=str(data["assignee"]),
            title=str(data["title"]),
            description=str(data["description"]),
            date_assigned=dt.date.fromisoformat(data["date_assigned"]),
            due_date=dt.date.fromisoformat(data["due_date"]),
            completed=bool(data["completed"]),
        )
