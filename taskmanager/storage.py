"""JSON file storage for users and tasks."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Task


class StorageError(Exception):
    """Raised when a data file cannot be read or is corrupt."""


class Storage:
    """Reads and writes ``users.json`` and ``tasks.json`` in a data directory."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def users_path(self) -> Path:
        return self.data_dir / "users.json"

    @property
    def tasks_path(self) -> Path:
        return self.data_dir / "tasks.json"

    # ---- users: {username: encoded password hash} ----

    def load_users(self) -> dict[str, str]:
        data = self._read_json(self.users_path, default={})
        if not isinstance(data, dict):
            raise StorageError(f"{self.users_path} is corrupt: expected a JSON object.")
        return {str(name): str(hashed) for name, hashed in data.items()}

    def save_users(self, users: dict[str, str]) -> None:
        self._write_json(self.users_path, users, private=True)

    # ---- tasks ----

    def load_tasks(self) -> list[Task]:
        data = self._read_json(self.tasks_path, default=[])
        if not isinstance(data, list):
            raise StorageError(f"{self.tasks_path} is corrupt: expected a JSON list.")
        try:
            return [Task.from_dict(item) for item in data]
        except (KeyError, TypeError, ValueError) as exc:
            raise StorageError(f"{self.tasks_path} contains an invalid task: {exc!r}") from exc

    def save_tasks(self, tasks: list[Task]) -> None:
        self._write_json(self.tasks_path, [task.to_dict() for task in tasks])

    # ---- helpers ----

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            raise StorageError(f"{path} is not valid JSON: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"Could not read {path}: {exc}") from exc

    @staticmethod
    def _write_json(path: Path, payload: Any, private: bool = False) -> None:
        """Write atomically so a crash mid-write never leaves a half-written file."""
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if private:
                try:
                    os.chmod(tmp_name, 0o600)
                except OSError:
                    pass  # e.g. filesystems without POSIX permissions
            os.replace(tmp_name, path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
