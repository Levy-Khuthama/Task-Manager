import datetime as dt

import pytest

from taskmanager.core import TaskManager, TaskManagerError
from taskmanager.storage import Storage

FUTURE = dt.date(2026, 6, 20)
PAST = dt.date(2026, 6, 1)


def add(manager, assignee="alice", title="Title", description="Details", due=FUTURE):
    return manager.add_task(assignee, title, description, due)


# ----------------------------------------------------------------- users


@pytest.mark.parametrize("username", ["ab", "has space", "bad/name", "x" * 33, ""])
def test_register_rejects_invalid_usernames(manager, username):
    with pytest.raises(TaskManagerError, match="Username must be"):
        manager.register_user(username, "long-enough-pw")


def test_register_rejects_short_and_empty_passwords(manager):
    with pytest.raises(TaskManagerError, match="at least 8"):
        manager.register_user("alice", "short")
    with pytest.raises(TaskManagerError, match="cannot be empty"):
        manager.register_user("alice", "")
    assert manager.users == {}


def test_register_rejects_duplicates(populated):
    with pytest.raises(TaskManagerError, match="already exists"):
        populated.register_user("alice", "another-pass-1")


def test_passwords_are_stored_hashed(populated):
    assert populated.users["alice"].startswith("pbkdf2_sha256$")
    assert "alice-pass-1" not in populated.users["alice"]


def test_users_persist_between_sessions(populated, tmp_path):
    reloaded = TaskManager(Storage(tmp_path))
    assert set(reloaded.users) == {"admin", "alice", "bob"}
    assert reloaded.authenticate("alice", "alice-pass-1")


def test_authenticate(populated):
    assert populated.authenticate("alice", "alice-pass-1")
    assert populated.authenticate("  alice  ", "alice-pass-1")
    assert not populated.authenticate("alice", "wrong-password")
    assert not populated.authenticate("nobody", "alice-pass-1")
    assert not populated.authenticate("alice", "")


def test_change_password(populated):
    populated.change_password("alice", "alice-pass-1", "brand-new-pass")
    assert populated.authenticate("alice", "brand-new-pass")
    assert not populated.authenticate("alice", "alice-pass-1")


def test_change_password_needs_correct_current_password_and_a_long_new_one(populated):
    with pytest.raises(TaskManagerError, match="incorrect"):
        populated.change_password("alice", "not-it", "brand-new-pass")
    with pytest.raises(TaskManagerError, match="at least 8"):
        populated.change_password("alice", "alice-pass-1", "short")
    assert populated.authenticate("alice", "alice-pass-1")


# ----------------------------------------------------------------- adding


def test_add_task_sets_id_and_assigned_date(populated):
    first = add(populated)
    second = add(populated, title="Second")
    assert (first.id, second.id) == (1, 2)
    assert first.date_assigned == dt.date(2026, 6, 10)
    assert first.completed is False


def test_add_task_validates_input(populated):
    with pytest.raises(TaskManagerError, match="not a registered user"):
        add(populated, assignee="ghost")
    with pytest.raises(TaskManagerError, match="title"):
        add(populated, title="   ")
    with pytest.raises(TaskManagerError, match="description"):
        add(populated, description="")
    with pytest.raises(TaskManagerError, match="past"):
        add(populated, due=PAST)
    assert populated.tasks == []


def test_task_due_today_is_allowed(populated):
    assert add(populated, due=dt.date(2026, 6, 10)).due_date == dt.date(2026, 6, 10)


def test_tasks_persist_between_sessions(populated, tmp_path):
    add(populated, description="Contains, commas, here")
    reloaded = TaskManager(Storage(tmp_path), clock=lambda: dt.date(2026, 6, 10))
    assert [t.description for t in reloaded.tasks] == ["Contains, commas, here"]


def test_import_task_allows_past_dates_and_completed(populated):
    task = populated.import_task("alice", "Old", "Done long ago", PAST, PAST, True)
    assert task.completed and task.due_date == PAST


def test_tasks_for_and_completed_tasks(populated):
    add(populated, "alice")
    add(populated, "bob")
    done = add(populated, "alice", title="Done")
    populated.mark_complete(done.id, "alice")
    assert [t.assignee for t in populated.tasks_for("alice")] == ["alice", "alice"]
    assert [t.id for t in populated.completed_tasks()] == [done.id]


# ----------------------------------------------------------- completing


def test_assignee_can_complete_their_task(populated):
    task = add(populated)
    populated.mark_complete(task.id, "alice")
    assert populated.get_task(task.id).completed


def test_admin_can_complete_any_task(populated):
    task = add(populated)
    populated.mark_complete(task.id, "admin")
    assert task.completed


def test_other_users_cannot_complete_a_task(populated):
    task = add(populated)
    with pytest.raises(TaskManagerError, match="assigned to you"):
        populated.mark_complete(task.id, "bob")
    assert not task.completed


def test_completed_task_cannot_be_completed_or_edited_again(populated):
    task = add(populated)
    populated.mark_complete(task.id, "alice")
    with pytest.raises(TaskManagerError, match="already complete"):
        populated.mark_complete(task.id, "alice")
    with pytest.raises(TaskManagerError, match="already complete"):
        populated.edit_task(task.id, "alice", assignee="bob")


def test_unknown_task_id(populated):
    with pytest.raises(TaskManagerError, match="no task with ID 99"):
        populated.mark_complete(99, "alice")


# -------------------------------------------------------------- editing
# The original script crashed (NameError) when editing the assignee or both
# fields, and never asked for the new due date. These cover each path.


def test_edit_assignee_only(populated):
    task = add(populated)
    populated.edit_task(task.id, "alice", assignee="bob")
    assert (task.assignee, task.due_date) == ("bob", FUTURE)


def test_edit_due_date_only(populated):
    task = add(populated)
    new_due = dt.date(2026, 7, 1)
    populated.edit_task(task.id, "alice", due_date=new_due)
    assert (task.assignee, task.due_date) == ("alice", new_due)


def test_edit_both(populated):
    task = add(populated)
    new_due = dt.date(2026, 7, 1)
    populated.edit_task(task.id, "alice", assignee="bob", due_date=new_due)
    assert (task.assignee, task.due_date) == ("bob", new_due)


def test_edit_requires_something_to_change(populated):
    task = add(populated)
    with pytest.raises(TaskManagerError, match="Nothing to change"):
        populated.edit_task(task.id, "alice")


def test_failed_edit_changes_nothing(populated):
    task = add(populated)
    with pytest.raises(TaskManagerError, match="past"):
        populated.edit_task(task.id, "alice", assignee="bob", due_date=PAST)
    with pytest.raises(TaskManagerError, match="not a registered user"):
        populated.edit_task(task.id, "alice", assignee="ghost", due_date=dt.date(2026, 7, 1))
    assert (task.assignee, task.due_date) == ("alice", FUTURE)


def test_edits_are_saved(populated, tmp_path):
    task = add(populated)
    populated.edit_task(task.id, "alice", assignee="bob")
    reloaded = TaskManager(Storage(tmp_path))
    assert reloaded.get_task(task.id).assignee == "bob"


def test_only_assignee_or_admin_can_edit(populated):
    task = add(populated)
    with pytest.raises(TaskManagerError, match="assigned to you"):
        populated.edit_task(task.id, "bob", due_date=dt.date(2026, 7, 1))
    populated.edit_task(task.id, "admin", due_date=dt.date(2026, 7, 1))
    assert task.due_date == dt.date(2026, 7, 1)


# ------------------------------------------------------------- deleting


def test_admin_can_delete_by_id_and_only_that_task(populated):
    keep = add(populated, title="Same title")
    remove = add(populated, title="Same title")
    populated.delete_task(remove.id, "admin")
    assert populated.tasks == [keep]


def test_non_admin_cannot_delete(populated):
    task = add(populated)
    with pytest.raises(TaskManagerError, match="Only the admin"):
        populated.delete_task(task.id, "alice")
    assert populated.tasks == [task]


def test_delete_unknown_id(populated):
    with pytest.raises(TaskManagerError, match="no task with ID"):
        populated.delete_task(5, "admin")
