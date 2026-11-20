"""Sample data so anyone can try the app without setting anything up."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .core import ADMIN, TaskManager
from .reports import TASK_REPORT, USER_REPORT
from .storage import Storage

DEMO_PASSWORD = "demo-pass-123"
DEMO_USERS = (ADMIN, "alice", "bob")

# (assignee, title, description, days assigned ago, due in N days, completed)
_DEMO_TASKS = (
    (
        "admin",
        "Onboard new team members",
        "Create accounts and walk everyone through the app.",
        10,
        5,
        False,
    ),
    ("alice", "Set up CI pipeline", "Run the tests on every push.", 20, -10, True),
    ("alice", "Write project README", "Document features and how to run the app.", 14, -3, False),
    ("alice", "Review pull requests", "Review the two open pull requests.", 5, 2, False),
    ("bob", "Prepare sprint demo", "Slides and a short live demo.", 12, -4, True),
    ("bob", "Fix login bug", "Users are locked out after one wrong password.", 7, -1, False),
    ("bob", "Update documentation", "Add screenshots to the user guide.", 3, 7, False),
)


def seed_demo(data_dir: str | Path, today: dt.date | None = None) -> TaskManager:
    """Create fresh demo users and tasks in ``data_dir``.

    Only the app's own data files are removed first, never the whole folder.
    Dates are relative to today so the reports always show a mix of overdue,
    upcoming and completed tasks.
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("users.json", "tasks.json", TASK_REPORT, USER_REPORT):
        (data_dir / name).unlink(missing_ok=True)

    today = today or dt.date.today()
    manager = TaskManager(Storage(data_dir), clock=lambda: today)
    for username in DEMO_USERS:
        manager.register_user(username, DEMO_PASSWORD)
    for assignee, title, description, assigned_ago, due_in, done in _DEMO_TASKS:
        manager.import_task(
            assignee,
            title,
            description,
            today - dt.timedelta(days=assigned_ago),
            today + dt.timedelta(days=due_in),
            done,
        )
    return manager
