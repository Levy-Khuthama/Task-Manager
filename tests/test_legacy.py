import datetime as dt

import pytest

from taskmanager.legacy import import_legacy


@pytest.fixture
def write(tmp_path):
    def _write(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    return _write


def test_users_are_imported_and_hashed(manager, write, tmp_path):
    users = write("user.txt", "admin, long-admin-pass\nalice, alice-pass-1\n")
    result = import_legacy(manager, users_file=users)
    assert result.users_imported == 2
    assert manager.authenticate("alice", "alice-pass-1")
    assert "alice-pass-1" not in (tmp_path / "users.json").read_text(encoding="utf-8")


def test_short_legacy_passwords_are_imported_with_a_warning(manager, write):
    users = write("user.txt", "admin, adm1n\n")
    result = import_legacy(manager, users_file=users)
    assert manager.authenticate("admin", "adm1n")
    assert any("short legacy password" in w for w in result.warnings)


def test_bad_and_duplicate_user_lines_are_skipped_with_warnings(manager, write):
    users = write(
        "user.txt",
        "alice, alice-pass-1\n\njust-a-name\nalice, another-pass\nx, short-name-pw\n",
    )
    result = import_legacy(manager, users_file=users)
    assert result.users_imported == 1
    assert len(result.warnings) == 3


def test_tasks_are_imported_with_their_status_and_dates(manager, write):
    manager.register_user("alice", "alice-pass-1")
    tasks = write(
        "tasks.txt",
        "alice, Finish capstone, Wrap up the final project, 01 Jun 2026, 02 Jun 2026, Yes\n"
        "alice, Review, Check the code, 2026-06-03, 04 Jun 2026, no\n",
    )
    result = import_legacy(manager, tasks_file=tasks)
    assert result.tasks_imported == 2
    first, second = manager.tasks
    assert first.completed and first.due_date == dt.date(2026, 6, 2)
    assert first.date_assigned == dt.date(2026, 6, 1)
    assert not second.completed
    assert [t.id for t in manager.tasks] == [1, 2]


def test_descriptions_containing_commas_are_kept_whole(manager, write):
    manager.register_user("alice", "alice-pass-1")
    tasks = write(
        "tasks.txt",
        "alice, Plan, Buy milk, eggs, and bread, 01 Jun 2026, 02 Jun 2026, No\n",
    )
    import_legacy(manager, tasks_file=tasks)
    assert manager.tasks[0].description == "Buy milk, eggs, and bread"


def test_unreadable_assigned_date_falls_back_to_today(manager, write):
    manager.register_user("alice", "alice-pass-1")
    tasks = write("tasks.txt", "alice, Test, testing, 2026, 02 Jun 2026, No\n")
    result = import_legacy(manager, tasks_file=tasks)
    assert manager.tasks[0].date_assigned == manager.today()
    assert any("assigned date" in w for w in result.warnings)


def test_problem_task_lines_are_skipped_with_warnings(manager, write):
    manager.register_user("alice", "alice-pass-1")
    tasks = write(
        "tasks.txt",
        "alice, Too, few\n"
        "alice, Bad due, desc, 01 Jun 2026, someday, No\n"
        "alice, Bad status, desc, 01 Jun 2026, 02 Jun 2026, Maybe\n"
        "ghost, Unknown user, desc, 01 Jun 2026, 02 Jun 2026, No\n"
        "alice, Good, desc, 01 Jun 2026, 02 Jun 2026, No\n",
    )
    result = import_legacy(manager, tasks_file=tasks)
    assert result.tasks_imported == 1
    assert len(result.warnings) == 4
    assert [t.title for t in manager.tasks] == ["Good"]


def test_importing_nothing_is_fine(manager):
    result = import_legacy(manager)
    assert (result.users_imported, result.tasks_imported, result.warnings) == (0, 0, [])
