import datetime as dt
import os
import stat

import pytest

from taskmanager.models import Task
from taskmanager.storage import Storage, StorageError


def sample_task(task_id=1):
    return Task(
        id=task_id,
        assignee="alice",
        title="Title",
        description="Has a comma, and more",
        date_assigned=dt.date(2026, 6, 1),
        due_date=dt.date(2026, 6, 10),
    )


def test_missing_files_load_as_empty(tmp_path):
    storage = Storage(tmp_path)
    assert storage.load_users() == {}
    assert storage.load_tasks() == []


def test_creates_the_data_directory(tmp_path):
    target = tmp_path / "nested" / "data"
    Storage(target)
    assert target.is_dir()


def test_users_round_trip(tmp_path):
    storage = Storage(tmp_path)
    storage.save_users({"alice": "hash-a", "bob": "hash-b"})
    assert storage.load_users() == {"alice": "hash-a", "bob": "hash-b"}


def test_tasks_round_trip_including_commas_in_text(tmp_path):
    storage = Storage(tmp_path)
    storage.save_tasks([sample_task(1), sample_task(2)])
    assert storage.load_tasks() == [sample_task(1), sample_task(2)]


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_users_file_is_private(tmp_path):
    storage = Storage(tmp_path)
    storage.save_users({"alice": "hash"})
    mode = stat.S_IMODE(storage.users_path.stat().st_mode)
    assert mode == 0o600


def test_saving_leaves_no_temp_files_behind(tmp_path):
    storage = Storage(tmp_path)
    storage.save_users({"alice": "hash"})
    storage.save_tasks([sample_task()])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tasks.json", "users.json"]


def test_invalid_json_raises_storage_error(tmp_path):
    storage = Storage(tmp_path)
    storage.users_path.write_text("{not json", encoding="utf-8")
    storage.tasks_path.write_text("[oops", encoding="utf-8")
    with pytest.raises(StorageError, match="not valid JSON"):
        storage.load_users()
    with pytest.raises(StorageError, match="not valid JSON"):
        storage.load_tasks()


def test_wrong_top_level_type_raises_storage_error(tmp_path):
    storage = Storage(tmp_path)
    storage.users_path.write_text("[]", encoding="utf-8")
    storage.tasks_path.write_text("{}", encoding="utf-8")
    with pytest.raises(StorageError):
        storage.load_users()
    with pytest.raises(StorageError):
        storage.load_tasks()


def test_task_with_missing_field_raises_storage_error(tmp_path):
    storage = Storage(tmp_path)
    storage.tasks_path.write_text('[{"id": 1, "assignee": "alice"}]', encoding="utf-8")
    with pytest.raises(StorageError, match="invalid task"):
        storage.load_tasks()
