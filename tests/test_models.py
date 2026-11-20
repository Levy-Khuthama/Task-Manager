import datetime as dt

import pytest

from taskmanager.models import Task, format_date, parse_date


def make_task(**overrides):
    values = dict(
        id=1,
        assignee="alice",
        title="Write tests",
        description="Cover the core logic",
        date_assigned=dt.date(2026, 6, 1),
        due_date=dt.date(2026, 6, 10),
        completed=False,
    )
    values.update(overrides)
    return Task(**values)


def test_parse_date_accepts_all_documented_formats():
    expected = dt.date(2026, 6, 3)
    for text in ("2026-06-03", "03 Jun 2026", "03 June 2026", "  2026-06-03  "):
        assert parse_date(text) == expected


@pytest.mark.parametrize("text", ["", "2026", "31 Feb 2026", "tomorrow", "2026/06/03"])
def test_parse_date_rejects_invalid_text(text):
    assert parse_date(text) is None


def test_format_date_uses_day_short_month_year():
    assert format_date(dt.date(2026, 6, 3)) == "03 Jun 2026"


def test_incomplete_task_is_overdue_only_after_its_due_date():
    task = make_task(due_date=dt.date(2026, 6, 10))
    assert not task.is_overdue(today=dt.date(2026, 6, 9))
    assert not task.is_overdue(today=dt.date(2026, 6, 10))  # due today is not overdue yet
    assert task.is_overdue(today=dt.date(2026, 6, 11))


def test_completed_task_is_never_overdue():
    task = make_task(completed=True, due_date=dt.date(2020, 1, 1))
    assert not task.is_overdue(today=dt.date(2026, 6, 11))


def test_task_survives_a_dict_round_trip():
    task = make_task(completed=True)
    assert Task.from_dict(task.to_dict()) == task


def test_task_dict_uses_iso_dates():
    data = make_task().to_dict()
    assert data["date_assigned"] == "2026-06-01"
    assert data["due_date"] == "2026-06-10"
