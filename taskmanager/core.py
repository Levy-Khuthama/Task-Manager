"""Business rules: users, authentication, permissions and task changes.

Nothing in this module prints or prompts, which keeps it easy to test.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable

from . import auth
from .models import Task
from .storage import Storage

ADMIN = "admin"
MIN_PASSWORD_LENGTH = 8
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class TaskManagerError(Exception):
    """A user-facing error: bad input, missing record or not allowed."""


class TaskManager:
    def __init__(self, storage: Storage, clock: Callable[[], dt.date] = dt.date.today):
        self.storage = storage
        self._clock = clock
        self.users = storage.load_users()
        self.tasks = storage.load_tasks()

    def today(self) -> dt.date:
        return self._clock()

    # ---------------------------------------------------------------- users

    def register_user(self, username: str, password: str, *, enforce_policy: bool = True) -> None:
        """Add a user. ``enforce_policy=False`` is only for importing legacy data."""
        username = username.strip()
        if not USERNAME_PATTERN.match(username):
            raise TaskManagerError(
                "Username must be 3-32 characters: letters, digits, '_', '.' or '-'."
            )
        if username in self.users:
            raise TaskManagerError(f"Username '{username}' already exists.")
        if not password:
            raise TaskManagerError("Password cannot be empty.")
        if enforce_policy and len(password) < MIN_PASSWORD_LENGTH:
            raise TaskManagerError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
            )
        self.users[username] = auth.hash_password(password)
        self.storage.save_users(self.users)

    def authenticate(self, username: str, password: str) -> bool:
        encoded = self.users.get(username.strip())
        return encoded is not None and auth.verify_password(password, encoded)

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        if not self.authenticate(username, old_password):
            raise TaskManagerError("Current password is incorrect.")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise TaskManagerError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
            )
        self.users[username] = auth.hash_password(new_password)
        self.storage.save_users(self.users)

    def require_user(self, username: str) -> str:
        if username not in self.users:
            raise TaskManagerError(
                f"'{username}' is not a registered user. "
                f"Registered users: {', '.join(sorted(self.users))}"
            )
        return username

    # ---------------------------------------------------------------- tasks

    def validate_due_date(self, due_date: dt.date) -> None:
        if due_date < self.today():
            raise TaskManagerError("The due date cannot be in the past.")

    def add_task(self, assignee: str, title: str, description: str, due_date: dt.date) -> Task:
        self.require_user(assignee)
        title, description = title.strip(), description.strip()
        if not title:
            raise TaskManagerError("The task title cannot be empty.")
        if not description:
            raise TaskManagerError("The task description cannot be empty.")
        self.validate_due_date(due_date)
        return self._append(assignee, title, description, self.today(), due_date, False)

    def import_task(
        self,
        assignee: str,
        title: str,
        description: str,
        date_assigned: dt.date,
        due_date: dt.date,
        completed: bool,
    ) -> Task:
        """Add a task as-is, skipping the "due date in the past" rule.

        Used for legacy imports and demo data, where past dates are expected.
        """
        self.require_user(assignee)
        return self._append(assignee, title, description, date_assigned, due_date, completed)

    def get_task(self, task_id: int) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise TaskManagerError(f"There is no task with ID {task_id}.")

    def tasks_for(self, username: str) -> list[Task]:
        return [task for task in self.tasks if task.assignee == username]

    def completed_tasks(self) -> list[Task]:
        return [task for task in self.tasks if task.completed]

    def mark_complete(self, task_id: int, acting_user: str) -> Task:
        task = self._modifiable(task_id, acting_user)
        task.completed = True
        self.storage.save_tasks(self.tasks)
        return task

    def edit_task(
        self,
        task_id: int,
        acting_user: str,
        *,
        assignee: str | None = None,
        due_date: dt.date | None = None,
    ) -> Task:
        """Change the assignee, the due date, or both."""
        if assignee is None and due_date is None:
            raise TaskManagerError("Nothing to change.")
        task = self._modifiable(task_id, acting_user)
        # Validate everything before changing anything.
        if assignee is not None:
            self.require_user(assignee)
        if due_date is not None:
            self.validate_due_date(due_date)
        if assignee is not None:
            task.assignee = assignee
        if due_date is not None:
            task.due_date = due_date
        self.storage.save_tasks(self.tasks)
        return task

    def delete_task(self, task_id: int, acting_user: str) -> Task:
        if acting_user != ADMIN:
            raise TaskManagerError("Only the admin can delete tasks.")
        task = self.get_task(task_id)
        self.tasks.remove(task)
        self.storage.save_tasks(self.tasks)
        return task

    # -------------------------------------------------------------- helpers

    def _modifiable(self, task_id: int, acting_user: str) -> Task:
        task = self.get_task(task_id)
        if acting_user not in (task.assignee, ADMIN):
            raise TaskManagerError("You can only change tasks assigned to you.")
        if task.completed:
            raise TaskManagerError("This task is already complete and cannot be changed.")
        return task

    def _append(
        self,
        assignee: str,
        title: str,
        description: str,
        date_assigned: dt.date,
        due_date: dt.date,
        completed: bool,
    ) -> Task:
        task = Task(
            id=max((t.id for t in self.tasks), default=0) + 1,
            assignee=assignee,
            title=title,
            description=description,
            date_assigned=date_assigned,
            due_date=due_date,
            completed=completed,
        )
        self.tasks.append(task)
        self.storage.save_tasks(self.tasks)
        return task
