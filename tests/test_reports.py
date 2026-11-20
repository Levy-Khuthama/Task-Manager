import datetime as dt

from taskmanager.models import Task
from taskmanager.reports import (
    TASK_REPORT,
    USER_REPORT,
    render_task_overview,
    render_user_overview,
    task_overview,
    user_overviews,
    write_reports,
)

TODAY = dt.date(2026, 6, 10)


def task(task_id, assignee, due, completed):
    return Task(
        id=task_id,
        assignee=assignee,
        title=f"Task {task_id}",
        description="d",
        date_assigned=dt.date(2026, 6, 1),
        due_date=due,
        completed=completed,
    )


# The same five tasks that produced the reports in the original project:
# two completed, three incomplete and past due.
ORIGINAL_TASKS = [
    task(1, "admin", dt.date(2026, 6, 4), True),
    task(2, "admin", dt.date(2026, 6, 4), False),
    task(3, "Karabo", dt.date(2026, 6, 2), True),
    task(4, "Karabo", dt.date(2026, 6, 2), False),
    task(5, "Karabo", dt.date(2026, 6, 4), False),
]
ORIGINAL_USERS = ["admin", "Levy", "Karabo"]

ORIGINAL_TASK_REPORT = """\
Total number of tasks: 5
Total number of completed tasks: 2
Total number of uncompleted tasks: 3
Total number of overdue tasks: 3
Percentage of tasks that are incomplete: 60.00%
Percentage of tasks that are overdue: 60.00%
"""

ORIGINAL_USER_REPORT = """\
Total number of users: 3
Total number of tasks: 5

User: admin
Total tasks assigned: 2
Percentage of total tasks assigned: 40.00%
Percentage of tasks completed: 50.00%
Percentage of tasks still incomplete: 50.00%
Percentage of tasks incomplete and overdue: 50.00%

User: Levy
Total tasks assigned: 0
Percentage of total tasks assigned: 0.00%
Percentage of tasks completed: 0.00%
Percentage of tasks still incomplete: 0.00%
Percentage of tasks incomplete and overdue: 0.00%

User: Karabo
Total tasks assigned: 3
Percentage of total tasks assigned: 60.00%
Percentage of tasks completed: 33.33%
Percentage of tasks still incomplete: 66.67%
Percentage of tasks incomplete and overdue: 66.67%

"""


def test_task_report_matches_the_original_format_and_numbers():
    assert render_task_overview(task_overview(ORIGINAL_TASKS, TODAY)) == ORIGINAL_TASK_REPORT


def test_user_report_matches_the_original_format_and_numbers():
    overviews = user_overviews(ORIGINAL_USERS, ORIGINAL_TASKS, TODAY)
    assert render_user_overview(overviews, len(ORIGINAL_TASKS)) == ORIGINAL_USER_REPORT


def test_task_due_today_is_not_counted_overdue():
    overview = task_overview([task(1, "alice", TODAY, False)], TODAY)
    assert overview.overdue == 0


def test_completed_tasks_are_not_counted_overdue():
    overview = task_overview([task(1, "alice", dt.date(2020, 1, 1), True)], TODAY)
    assert overview.overdue == 0


def test_no_tasks_gives_zeros_instead_of_dividing_by_zero():
    overview = task_overview([], TODAY)
    assert (overview.total, overview.pct_incomplete, overview.pct_overdue) == (0, 0.0, 0.0)
    users = user_overviews(["alice"], [], TODAY)
    assert users[0].pct_of_all == 0.0
    assert "Percentage of tasks completed: 0.00%" in render_user_overview(users, 0)


def test_write_reports_creates_both_files(tmp_path):
    task_path, user_path = write_reports(tmp_path, ORIGINAL_USERS, ORIGINAL_TASKS, TODAY)
    assert (task_path.name, user_path.name) == (TASK_REPORT, USER_REPORT)
    assert task_path.read_text(encoding="utf-8") == ORIGINAL_TASK_REPORT
    assert user_path.read_text(encoding="utf-8") == ORIGINAL_USER_REPORT


def test_write_reports_overwrites_stale_files(tmp_path):
    write_reports(tmp_path, ORIGINAL_USERS, ORIGINAL_TASKS, TODAY)
    write_reports(tmp_path, ORIGINAL_USERS, [], TODAY)
    assert "Total number of tasks: 0" in (tmp_path / TASK_REPORT).read_text(encoding="utf-8")
