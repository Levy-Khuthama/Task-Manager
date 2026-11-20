import datetime as dt

from taskmanager.demo import DEMO_PASSWORD, DEMO_USERS, seed_demo
from taskmanager.reports import task_overview

TODAY = dt.date(2026, 6, 10)


def test_demo_creates_users_who_can_log_in(tmp_path):
    manager = seed_demo(tmp_path, today=TODAY)
    assert set(manager.users) == set(DEMO_USERS)
    assert all(manager.authenticate(name, DEMO_PASSWORD) for name in DEMO_USERS)


def test_demo_tasks_mix_overdue_upcoming_and_completed(tmp_path):
    manager = seed_demo(tmp_path, today=TODAY)
    overview = task_overview(manager.tasks, TODAY)
    assert overview.total == 7
    assert overview.completed == 2
    assert overview.overdue == 2


def test_reseeding_resets_the_data_but_keeps_other_files(tmp_path):
    seed_demo(tmp_path, today=TODAY).add_task("alice", "Extra", "Extra task", TODAY)
    (tmp_path / "notes.txt").write_text("keep me", encoding="utf-8")
    manager = seed_demo(tmp_path, today=TODAY)
    assert len(manager.tasks) == 7
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "keep me"
