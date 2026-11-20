"""Task and user statistics, plus the plain-text report files."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .models import Task

TASK_REPORT = "task_overview.txt"
USER_REPORT = "user_overview.txt"


def _pct(part: int, whole: int) -> float:
    return part / whole * 100 if whole else 0.0


@dataclass(frozen=True)
class TaskOverview:
    total: int
    completed: int
    uncompleted: int
    overdue: int

    @property
    def pct_incomplete(self) -> float:
        return _pct(self.uncompleted, self.total)

    @property
    def pct_overdue(self) -> float:
        return _pct(self.overdue, self.total)


@dataclass(frozen=True)
class UserOverview:
    username: str
    total: int
    completed: int
    overdue: int  # incomplete and past due
    all_tasks: int  # total tasks across all users

    @property
    def incomplete(self) -> int:
        return self.total - self.completed

    @property
    def pct_of_all(self) -> float:
        return _pct(self.total, self.all_tasks)

    @property
    def pct_completed(self) -> float:
        return _pct(self.completed, self.total)

    @property
    def pct_incomplete(self) -> float:
        return _pct(self.incomplete, self.total)

    @property
    def pct_incomplete_overdue(self) -> float:
        return _pct(self.overdue, self.total)


def task_overview(tasks: Sequence[Task], today: dt.date) -> TaskOverview:
    completed = sum(1 for task in tasks if task.completed)
    overdue = sum(1 for task in tasks if task.is_overdue(today))
    return TaskOverview(
        total=len(tasks),
        completed=completed,
        uncompleted=len(tasks) - completed,
        overdue=overdue,
    )


def user_overviews(
    usernames: Iterable[str], tasks: Sequence[Task], today: dt.date
) -> list[UserOverview]:
    overviews = []
    for username in usernames:
        mine = [task for task in tasks if task.assignee == username]
        overviews.append(
            UserOverview(
                username=username,
                total=len(mine),
                completed=sum(1 for task in mine if task.completed),
                overdue=sum(1 for task in mine if task.is_overdue(today)),
                all_tasks=len(tasks),
            )
        )
    return overviews


def render_task_overview(overview: TaskOverview) -> str:
    return (
        f"Total number of tasks: {overview.total}\n"
        f"Total number of completed tasks: {overview.completed}\n"
        f"Total number of uncompleted tasks: {overview.uncompleted}\n"
        f"Total number of overdue tasks: {overview.overdue}\n"
        f"Percentage of tasks that are incomplete: {overview.pct_incomplete:.2f}%\n"
        f"Percentage of tasks that are overdue: {overview.pct_overdue:.2f}%\n"
    )


def render_user_overview(overviews: Sequence[UserOverview], total_tasks: int) -> str:
    lines = [
        f"Total number of users: {len(overviews)}",
        f"Total number of tasks: {total_tasks}",
        "",
    ]
    for item in overviews:
        lines += [
            f"User: {item.username}",
            f"Total tasks assigned: {item.total}",
            f"Percentage of total tasks assigned: {item.pct_of_all:.2f}%",
            f"Percentage of tasks completed: {item.pct_completed:.2f}%",
            f"Percentage of tasks still incomplete: {item.pct_incomplete:.2f}%",
            f"Percentage of tasks incomplete and overdue: {item.pct_incomplete_overdue:.2f}%",
            "",
        ]
    return "\n".join(lines) + "\n"


def write_reports(
    data_dir: str | Path,
    usernames: Iterable[str],
    tasks: Sequence[Task],
    today: dt.date,
) -> tuple[Path, Path]:
    """(Re)write both report files and return their paths."""
    data_dir = Path(data_dir)
    task_path = data_dir / TASK_REPORT
    user_path = data_dir / USER_REPORT
    task_path.write_text(render_task_overview(task_overview(tasks, today)), encoding="utf-8")
    user_path.write_text(
        render_user_overview(user_overviews(usernames, tasks, today), len(tasks)),
        encoding="utf-8",
    )
    return task_path, user_path
