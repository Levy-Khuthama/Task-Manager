"""Drive the interactive menu with scripted keyboard input."""

import datetime as dt

import pytest

from taskmanager import cli
from taskmanager.cli import CLI, format_task, main
from taskmanager.core import TaskManager
from taskmanager.demo import DEMO_PASSWORD
from taskmanager.models import Task
from taskmanager.storage import Storage

FUTURE = "2026-06-20"


@pytest.fixture
def drive(monkeypatch, capsys, tmp_path):
    """Return run(manager, inputs, secrets) -> (exit code, printed output)."""

    def run(manager, inputs, secrets=()):
        typed = iter(inputs)
        hidden = iter(secrets)

        def fake_input(prompt=""):
            try:
                return next(typed)
            except StopIteration:
                raise AssertionError(f"Script ran out of input at prompt: {prompt!r}") from None

        def fake_secret(prompt=""):
            try:
                return next(hidden)
            except StopIteration:
                raise AssertionError(f"Script ran out of secrets at prompt: {prompt!r}") from None

        monkeypatch.setattr("builtins.input", fake_input)
        monkeypatch.setattr(cli, "read_secret", fake_secret)
        code = CLI(manager, tmp_path).run()
        return code, capsys.readouterr().out

    return run


def login_as(user):
    passwords = {"admin": "admin-pass-1", "alice": "alice-pass-1", "bob": "bob-pass-12"}
    return [user], [passwords[user]]


def add_task(manager, assignee="alice", title="Write docs", due=dt.date(2026, 6, 20)):
    return manager.add_task(assignee, title, "Some details", due)


# ------------------------------------------------------------------ login


def test_login_then_exit(drive, populated):
    code, out = drive(populated, ["alice", "e"], ["alice-pass-1"])
    assert code == 0
    assert "Login successful!" in out
    assert "Goodbye!" in out


def test_three_wrong_logins_end_the_session(drive, populated):
    code, out = drive(populated, ["alice"] * 3, ["bad"] * 3)
    assert code == 1
    assert out.count("Invalid username or password.") == 3
    assert "Too many failed attempts" in out


def test_first_run_creates_the_admin_account(drive, manager):
    code, out = drive(
        manager,
        ["admin", "e"],
        ["first-admin-pw", "first-admin-pw", "first-admin-pw"],
    )
    assert code == 0
    assert "Admin account created." in out
    assert manager.authenticate("admin", "first-admin-pw")


def test_first_run_reprompts_on_mismatch_and_weak_password(drive, manager):
    code, out = drive(
        manager,
        ["admin", "e"],
        [
            "aaaaaaaa",
            "bbbbbbbb",
            "short",
            "short",
            "good-admin-pw",
            "good-admin-pw",
            "good-admin-pw",
        ],
    )
    assert code == 0
    assert "Passwords do not match" in out
    assert "at least 8" in out
    assert manager.authenticate("admin", "good-admin-pw")


# ------------------------------------------------------------------- menu


def test_invalid_menu_choice(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["zzz", "e"], secrets)
    assert "invalid input" in out


def test_regular_users_cannot_use_admin_options(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["r", "vc", "del", "e"], secrets)
    assert out.count("Unauthorised access") == 3
    assert populated.tasks == [task]


def test_register_user_as_admin(drive, populated):
    users, secrets = login_as("admin")
    code, out = drive(
        populated,
        users + ["r", "carol", "e"],
        secrets + ["carol-pass-1", "carol-pass-1"],
    )
    assert "User successfully registered!" in out
    assert populated.authenticate("carol", "carol-pass-1")


def test_register_user_rejects_duplicate_and_mismatch(drive, populated):
    users, secrets = login_as("admin")
    _, out = drive(
        populated,
        users + ["r", "alice", "r", "carol", "e"],
        secrets + ["some-new-pass", "some-new-pass", "first-pass-1", "other-pass-1"],
    )
    assert "already exists" in out
    assert "Passwords do not match" in out
    assert "carol" not in populated.users


def test_change_password(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(
        populated,
        users + ["p", "e"],
        secrets + ["alice-pass-1", "a-better-pass", "a-better-pass"],
    )
    assert "Password changed." in out
    assert populated.authenticate("alice", "a-better-pass")


def test_change_password_with_wrong_current_password(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(
        populated,
        users + ["p", "e"],
        secrets + ["not-my-password", "a-better-pass", "a-better-pass"],
    )
    assert "Current password is incorrect" in out
    assert populated.authenticate("alice", "alice-pass-1")


# ----------------------------------------------------------------- adding


def test_add_task(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(
        populated,
        users + ["a", "bob", "Fix bug", "Crash on login", FUTURE, "e"],
        secrets,
    )
    assert "Task #1 successfully added!" in out
    task = populated.tasks[0]
    assert (task.assignee, task.title, task.due_date) == ("bob", "Fix bug", dt.date(2026, 6, 20))
    assert task.date_assigned == dt.date(2026, 6, 10)


def test_add_task_reprompts_on_bad_user_date_and_past_date(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(
        populated,
        users
        + ["a", "ghost", "bob", "Title", "Details", "next week", "2026-06-01", "20 Jun 2026", "e"],
        secrets,
    )
    assert "not a registered user" in out
    assert "not a valid date" in out
    assert "cannot be in the past" in out
    assert populated.tasks[0].due_date == dt.date(2026, 6, 20)


# ---------------------------------------------------------------- viewing


def test_view_all_and_completed(drive, populated):
    add_task(populated, "alice", "Open task")
    done = add_task(populated, "bob", "Finished task")
    populated.mark_complete(done.id, "bob")
    users, secrets = login_as("admin")
    _, out = drive(populated, users + ["va", "vc", "e"], secrets)
    assert out.count("Open task") == 1
    assert out.count("Finished task") == 2  # in "all" and in "completed"


def test_view_all_with_no_tasks(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["va", "e"], secrets)
    assert "No tasks found." in out


def test_view_mine_with_no_tasks(drive, populated):
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["vm", "e"], secrets)
    assert "You have no tasks." in out


def test_format_task_flags_overdue(today):
    task = Task(1, "alice", "Late", "Desc", dt.date(2026, 6, 1), dt.date(2026, 6, 5))
    assert "(OVERDUE)" in format_task(task, today)
    task.completed = True
    assert "(OVERDUE)" not in format_task(task, today)


# ----------------------------------------------------- completing / editing


def test_complete_my_task(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["vm", str(task.id), "c", "-1", "e"], secrets)
    assert "Task marked as complete!" in out
    assert task.completed


def test_cannot_pick_someone_elses_or_a_missing_task(drive, populated):
    theirs = add_task(populated, "bob")
    users, secrets = login_as("alice")
    mine = add_task(populated, "alice")
    _, out = drive(
        populated,
        users + ["vm", str(theirs.id), "abc", "99", "-1", "e"],
        secrets,
    )
    assert out.count("Please enter the ID of one of your tasks") == 3
    assert not theirs.completed and not mine.completed


def test_completed_task_cannot_be_picked_again(drive, populated):
    task = add_task(populated)
    populated.mark_complete(task.id, "alice")
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["vm", str(task.id), "-1", "e"], secrets)
    assert "already complete" in out


def test_edit_assignee(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["vm", str(task.id), "e", "a", "bob", "e"], secrets)
    assert "Task details updated!" in out
    assert task.assignee == "bob"
    assert task.due_date == dt.date(2026, 6, 20)


def test_edit_due_date(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(
        populated, users + ["vm", str(task.id), "e", "d", "2026-07-01", "-1", "e"], secrets
    )
    assert "Task details updated!" in out
    assert (task.assignee, task.due_date) == ("alice", dt.date(2026, 7, 1))


def test_edit_both(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(
        populated, users + ["vm", str(task.id), "e", "b", "bob", "01 Jul 2026", "e"], secrets
    )
    assert "Task details updated!" in out
    assert (task.assignee, task.due_date) == ("bob", dt.date(2026, 7, 1))


def test_edit_with_unknown_assignee_reprompts_and_can_be_cancelled(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(
        populated,
        users + ["vm", str(task.id), "e", "a", "ghost", "-1", "-1", "e"],
        secrets,
    )
    assert "not a registered user" in out
    assert "Edit cancelled." in out
    assert task.assignee == "alice"


def test_edit_menu_cancel_and_invalid_choices(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(
        populated,
        users
        + ["vm", str(task.id), "e", "n", str(task.id), "x", str(task.id), "e", "q", "-1", "e"],
        secrets,
    )
    assert out.count("Invalid choice") == 2
    assert (task.assignee, task.completed) == ("alice", False)


# --------------------------------------------------------------- deleting


def test_admin_deletes_a_task_after_confirming(drive, populated):
    keep = add_task(populated, title="Keep me")
    remove = add_task(populated, title="Remove me")
    users, secrets = login_as("admin")
    _, out = drive(populated, users + ["del", str(remove.id), "y", "e"], secrets)
    assert "Task successfully deleted!" in out
    assert populated.tasks == [keep]


def test_declining_the_confirmation_keeps_the_task(drive, populated):
    task = add_task(populated)
    users, secrets = login_as("admin")
    _, out = drive(populated, users + ["del", str(task.id), "n", "e"], secrets)
    assert "Task not deleted." in out
    assert populated.tasks == [task]


def test_delete_with_bad_ids(drive, populated):
    users, secrets = login_as("admin")
    _, out = drive(populated, users + ["del", "abc", "del", "42", "e"], secrets)
    assert "whole number" in out
    assert "no task with ID 42" in out


# ---------------------------------------------------------------- reports


def test_statistics_are_regenerated_each_time(drive, populated, tmp_path):
    users, secrets = login_as("alice")
    _, first = drive(populated, users + ["ds", "e"], secrets)
    assert "Total number of tasks: 0" in first

    add_task(populated)
    _, second = drive(populated, users + ["ds", "e"], secrets)
    assert "Total number of tasks: 1" in second  # not the stale report from before


def test_generate_reports_writes_files(drive, populated, tmp_path):
    add_task(populated)
    users, secrets = login_as("alice")
    _, out = drive(populated, users + ["gr", "e"], secrets)
    assert (tmp_path / "task_overview.txt").exists()
    assert (tmp_path / "user_overview.txt").exists()
    assert "Task overview saved to" in out


# ------------------------------------------------------------------- main


def test_main_demo_mode_runs_end_to_end(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    typed = iter(["alice", "vm", "-1", "e"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setattr(cli, "read_secret", lambda prompt="": DEMO_PASSWORD)
    assert main(["--demo"]) == 0
    out = capsys.readouterr().out
    assert "Demo data created" in out
    assert "Write project README" in out
    assert (tmp_path / "demo_data" / "tasks.json").exists()


def test_main_rejects_demo_with_data_dir(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--demo", "--data-dir", str(tmp_path)])
    assert exc.value.code == 2


def test_main_imports_legacy_files_then_exits(capsys, tmp_path):
    users = tmp_path / "user.txt"
    tasks = tmp_path / "tasks.txt"
    users.write_text("alice, alice-pass-1\n", encoding="utf-8")
    tasks.write_text("alice, Old task, Done, 01 Jun 2026, 02 Jun 2026, Yes\n", encoding="utf-8")
    data = tmp_path / "data"
    code = main(
        ["--data-dir", str(data), "--import-users", str(users), "--import-tasks", str(tasks)]
    )
    assert code == 0
    assert "Imported 1 user(s) and 1 task(s)." in capsys.readouterr().out
    reloaded = TaskManager(Storage(data))
    assert reloaded.authenticate("alice", "alice-pass-1")
    assert reloaded.tasks[0].completed


def test_main_reports_corrupt_data_files(capsys, tmp_path):
    (tmp_path / "users.json").write_text("{broken", encoding="utf-8")
    assert main(["--data-dir", str(tmp_path)]) == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_main_exits_cleanly_when_input_ends(monkeypatch, capsys, tmp_path):
    def end_of_input(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", end_of_input)
    TaskManager(Storage(tmp_path)).register_user("alice", "alice-pass-1")
    assert main(["--data-dir", str(tmp_path)]) == 130
    assert "Goodbye!" in capsys.readouterr().out
