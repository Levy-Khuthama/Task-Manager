import datetime as dt

import pytest

from taskmanager import auth
from taskmanager.core import TaskManager
from taskmanager.storage import Storage

TODAY = dt.date(2026, 6, 10)


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    """Use few PBKDF2 iterations in tests so the suite stays fast."""
    monkeypatch.setattr(auth, "ITERATIONS", 1_000)


@pytest.fixture
def today():
    return TODAY


@pytest.fixture
def manager(tmp_path):
    """An empty manager with a fixed 'today' so date logic is deterministic."""
    return TaskManager(Storage(tmp_path), clock=lambda: TODAY)


@pytest.fixture
def populated(manager):
    """A manager with three users and no tasks."""
    manager.register_user("admin", "admin-pass-1")
    manager.register_user("alice", "alice-pass-1")
    manager.register_user("bob", "bob-pass-12")
    return manager
