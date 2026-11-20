# Task Manager

A command-line app for assigning and tracking team tasks. Users log in, create and assign tasks, mark them complete, and generate progress reports. It has no third-party runtime dependencies and ships with a test suite and CI.

Built in Python as part of my software development training, then reworked from a single script into a tested, installable package.

## Highlights

- **Secure logins**: passwords are hashed with salted PBKDF2-HMAC-SHA256 (standard library only), never stored in plain text. The user file is written with owner-only permissions.
- **Role-based access**: the `admin` user can register users, delete tasks and view completed tasks. Everyone else gets a smaller menu, and permissions are enforced in the core logic, not just hidden in the menu.
- **Safe editing**: a task can be completed or edited only by its assignee or the admin. Edits are validated before anything is changed, so a failed edit never leaves a task half-updated.
- **Reports**: task and per-user statistics (completion rate, overdue rate, share of workload) written to text files.
- **Reliable storage**: data lives in JSON files, written atomically so a crash mid-save cannot corrupt them.
- **Tested**: 116 tests, including a test for every bug fixed from the original script. Lint and tests run on Python 3.10 to 3.14 in GitHub Actions.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone <your-repo-url>
cd task-manager
python -m pip install -e .
task-manager --demo
```

`--demo` creates sample users and tasks in `./demo_data` and prints the login details (`admin`, `alice` and `bob`, all with the password `demo-pass-123`). Demo data is for trying the app only.

To start with your own data instead, run `task-manager`. On first run it asks you to choose an admin password. Data is stored in `./data`, or in the folder you pass with `--data-dir`. You can also run it without installing, using `python -m taskmanager`.

## Menu

| Option | Action | Who |
|--------|--------|-----|
| `a`   | Add a task | everyone |
| `va`  | View all tasks | everyone |
| `vm`  | View my tasks, then complete or edit one | everyone |
| `ds`  | Display statistics | everyone |
| `gr`  | Generate report files | everyone |
| `p`   | Change my password | everyone |
| `r`   | Register a user | admin |
| `vc`  | View completed tasks | admin |
| `del` | Delete a task (with confirmation) | admin |
| `e`   | Exit | everyone |

Dates can be typed as `2026-12-31`, `31 Dec 2026` or `31 December 2026`. Due dates cannot be in the past. Overdue incomplete tasks are flagged when viewed.

## Reports

`ds` and `gr` write two files into the data folder:

- `task_overview.txt`: total, completed, uncompleted and overdue tasks, plus the incomplete and overdue percentages.
- `user_overview.txt`: for each user, tasks assigned, share of all tasks, and the percentages completed, incomplete, and incomplete and overdue.

A task due today is not overdue until the day after, and completed tasks are never overdue.

## Importing data from the original version

The first version stored everything in plain-text `user.txt` and `tasks.txt`. To bring that data across (passwords are hashed on the way in):

```bash
task-manager --import-users user.txt --import-tasks tasks.txt
```

Problem lines are skipped and reported rather than stopping the import. Descriptions that contain commas are handled correctly.

## Project layout

```
taskmanager/
  models.py    Task dataclass and date parsing
  auth.py      Password hashing and verification
  storage.py   Atomic JSON reading and writing
  core.py      Business rules: users, permissions, task changes
  reports.py   Statistics and report files
  legacy.py    Import from the original text files
  demo.py      Sample data
  cli.py       Interactive menu and command-line options
tests/         pytest suite
.github/       CI workflow
```

The core logic never prints or prompts, so it can be tested directly. The menu in `cli.py` only handles input and output.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

## What changed from the original script

The first version was a single script with the logic spread through module-level code. Reworking it fixed several bugs:

- Editing a task's assignee crashed with a `NameError`, and editing the due date never asked for a new date. Editing now supports assignee, due date or both.
- Reassigning a task asked for the new assignee twice.
- Statistics could show stale numbers from an old report file. They are now regenerated every time.
- Tasks were identified by title, so deleting one title removed every task that shared it. Tasks now have unique IDs.
- Every task line was split on `", "`, so a comma in a description broke the record. JSON storage removes that problem.
- Passwords were stored and compared in plain text.

## Limitations

This is a single-user-at-a-time tool with file-based storage. It is not designed for several people editing the same data folder at once, and it has no password recovery. Ideas for the future include a SQLite backend, search and filtering, and a web interface.

## Author

Karabo Levy Khuthama

## Licence

MIT. See [LICENSE](LICENSE).
