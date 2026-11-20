"""Import data from the original plain-text ``user.txt`` and ``tasks.txt`` files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from .core import MIN_PASSWORD_LENGTH, TaskManager, TaskManagerError
from .models import parse_date

PathLike = Union[str, Path]


@dataclass
class ImportResult:
    users_imported: int = 0
    tasks_imported: int = 0
    warnings: list[str] = field(default_factory=list)


def import_legacy(
    manager: TaskManager,
    users_file: PathLike | None = None,
    tasks_file: PathLike | None = None,
) -> ImportResult:
    """Import users first (so tasks can reference them), then tasks.

    Plain-text passwords are hashed on the way in. Problem lines are skipped
    and reported in ``ImportResult.warnings`` rather than aborting the import.
    """
    result = ImportResult()
    if users_file:
        _import_users(manager, Path(users_file), result)
    if tasks_file:
        _import_tasks(manager, Path(tasks_file), result)
    return result


def _lines(path: Path):
    with open(path, encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if line:
                yield number, line


def _import_users(manager: TaskManager, path: Path, result: ImportResult) -> None:
    for number, line in _lines(path):
        parts = line.split(", ", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            result.warnings.append(
                f"{path.name} line {number}: skipped (expected 'username, password')."
            )
            continue
        username, password = parts
        try:
            manager.register_user(username, password, enforce_policy=False)
        except TaskManagerError as exc:
            result.warnings.append(f"{path.name} line {number}: skipped ({exc})")
            continue
        result.users_imported += 1
        if len(password) < MIN_PASSWORD_LENGTH:
            result.warnings.append(
                f"User '{username.strip()}' has a short legacy password; "
                "change it from the menu after logging in."
            )


def _import_tasks(manager: TaskManager, path: Path, result: ImportResult) -> None:
    for number, line in _lines(path):
        parts = line.split(", ")
        # assignee, title, description (may itself contain ", "), assigned, due, status
        if len(parts) < 6:
            result.warnings.append(f"{path.name} line {number}: skipped (expected 6 fields).")
            continue
        assignee, title = parts[0], parts[1]
        description = ", ".join(parts[2:-3])
        assigned_text, due_text, status = parts[-3], parts[-2], parts[-1]

        due_date = parse_date(due_text)
        if due_date is None:
            result.warnings.append(
                f"{path.name} line {number}: skipped (unreadable due date '{due_text}')."
            )
            continue
        if status.lower() not in ("yes", "no"):
            result.warnings.append(
                f"{path.name} line {number}: skipped (status must be Yes or No, got '{status}')."
            )
            continue
        date_assigned = parse_date(assigned_text)
        if date_assigned is None:
            date_assigned = manager.today()
            result.warnings.append(
                f"{path.name} line {number}: unreadable assigned date '{assigned_text}'; "
                "used today's date."
            )
        try:
            manager.import_task(
                assignee, title, description, date_assigned, due_date, status.lower() == "yes"
            )
        except TaskManagerError as exc:
            result.warnings.append(f"{path.name} line {number}: skipped ({exc})")
            continue
        result.tasks_imported += 1
