"""Interactive command-line interface."""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import sys
from pathlib import Path

from . import __version__
from .core import ADMIN, MIN_PASSWORD_LENGTH, TaskManager, TaskManagerError
from .demo import DEMO_PASSWORD, DEMO_USERS, seed_demo
from .legacy import import_legacy
from .models import Task, format_date, parse_date
from .reports import write_reports
from .storage import Storage, StorageError

MAX_LOGIN_ATTEMPTS = 3
DIVIDER = "=" * 35
DEFAULT_DATA_DIR = "data"
DEMO_DATA_DIR = "demo_data"

ADMIN_MENU = """
Select one of the following options:
    r   - register a user
    a   - add task
    va  - view all tasks
    vm  - view my tasks
    vc  - view completed tasks
    del - delete a task
    ds  - display statistics
    gr  - generate reports
    p   - change my password
    e   - exit
: """

USER_MENU = """
Select one of the following options:
    a   - add task
    va  - view all tasks
    vm  - view my tasks
    ds  - display statistics
    gr  - generate reports
    p   - change my password
    e   - exit
: """

ADMIN_ONLY = {"r", "vc", "del"}


def read_secret(prompt: str) -> str:
    """Read a password without echoing it. A separate function so tests can replace it."""
    return getpass.getpass(prompt)


def ask_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty. Please try again.")


def format_task(task: Task, today: dt.date) -> str:
    overdue = " (OVERDUE)" if task.is_overdue(today) else ""
    return (
        f"#{task.id}  {task.title}\n"
        f"   Assigned to:   {task.assignee}\n"
        f"   Date assigned: {format_date(task.date_assigned)}\n"
        f"   Due date:      {format_date(task.due_date)}{overdue}\n"
        f"   Completed:     {'Yes' if task.completed else 'No'}\n"
        f"   Description:   {task.description}\n"
        f"{DIVIDER}"
    )


class CLI:
    def __init__(self, manager: TaskManager, data_dir: Path):
        self.manager = manager
        self.data_dir = Path(data_dir)
        self.username = ""
        self.actions = {
            "r": self.register_user,
            "a": self.add_task,
            "va": self.view_all,
            "vm": self.view_mine,
            "vc": self.view_completed,
            "del": self.delete_task,
            "ds": self.display_statistics,
            "gr": self.generate_reports,
            "p": self.change_password,
        }

    @property
    def is_admin(self) -> bool:
        return self.username == ADMIN

    # ---------------------------------------------------------- entry points

    def run(self) -> int:
        if not self.manager.users:
            self.first_run_setup()
        if not self.login():
            return 1

        while True:
            choice = input(ADMIN_MENU if self.is_admin else USER_MENU).strip().lower()
            if choice == "e":
                print("Goodbye!")
                return 0
            handler = self.actions.get(choice)
            if handler is None:
                print("You have entered an invalid input. Please try again.")
            elif choice in ADMIN_ONLY and not self.is_admin:
                print("Unauthorised access. That option is for the admin only.")
            else:
                try:
                    handler()
                except TaskManagerError as exc:
                    print(f"Error: {exc}")

    def first_run_setup(self) -> None:
        print("No users found. Let's create the admin account.")
        while True:
            password = read_secret(
                f"Choose an admin password (min {MIN_PASSWORD_LENGTH} characters): "
            )
            if password != read_secret("Confirm the password: "):
                print("Passwords do not match. Please try again.")
                continue
            try:
                self.manager.register_user(ADMIN, password)
            except TaskManagerError as exc:
                print(f"Error: {exc}")
                continue
            print("Admin account created.")
            return

    def login(self) -> bool:
        for _ in range(MAX_LOGIN_ATTEMPTS):
            username = input("Enter your username: ").strip()
            password = read_secret("Enter your password: ")
            if self.manager.authenticate(username, password):
                self.username = username
                print("Login successful!")
                return True
            print("Invalid username or password.")
        print("Too many failed attempts. Exiting.")
        return False

    # -------------------------------------------------------------- prompts

    def ask_registered_user(self, prompt: str, allow_cancel: bool = False) -> str | None:
        suffix = " (or '-1' to cancel)" if allow_cancel else ""
        while True:
            name = ask_non_empty(f"{prompt}{suffix}: ")
            if allow_cancel and name == "-1":
                return None
            try:
                return self.manager.require_user(name)
            except TaskManagerError as exc:
                print(f"Error: {exc}")

    def ask_due_date(self, prompt: str) -> dt.date:
        while True:
            text = input(f"{prompt} (e.g. 2026-12-31 or 31 Dec 2026): ").strip()
            parsed = parse_date(text)
            if parsed is None:
                print(f"Error: '{text}' is not a valid date. Try '2026-12-31' or '31 Dec 2026'.")
                continue
            try:
                self.manager.validate_due_date(parsed)
            except TaskManagerError as exc:
                print(f"Error: {exc}")
                continue
            return parsed

    def ask_new_password(self) -> str | None:
        password = read_secret(f"Enter a new password (min {MIN_PASSWORD_LENGTH} characters): ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"Error: Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
            return None
        if password != read_secret("Confirm the password: "):
            print("Passwords do not match.")
            return None
        return password

    # -------------------------------------------------------------- actions

    def register_user(self) -> None:
        username = ask_non_empty("Enter a new username: ")
        password = self.ask_new_password()
        if password is None:
            return
        self.manager.register_user(username, password)
        print("User successfully registered!")

    def change_password(self) -> None:
        current = read_secret("Enter your current password: ")
        new_password = self.ask_new_password()
        if new_password is None:
            return
        self.manager.change_password(self.username, current, new_password)
        print("Password changed.")

    def add_task(self) -> None:
        assignee = self.ask_registered_user(
            "Enter the username of the person the task is assigned to"
        )
        title = ask_non_empty("Enter the title of the task: ")
        description = ask_non_empty("Enter the description of the task: ")
        due_date = self.ask_due_date("Enter the due date of the task")
        task = self.manager.add_task(assignee, title, description, due_date)
        print(f"Task #{task.id} successfully added!")

    def view_all(self) -> None:
        self._print_tasks(self.manager.tasks, "No tasks found.")

    def view_completed(self) -> None:
        self._print_tasks(self.manager.completed_tasks(), "There are no completed tasks.")

    def view_mine(self) -> None:
        """Show my tasks, then let me complete or edit one."""
        while True:
            mine = self.manager.tasks_for(self.username)
            if not mine:
                print("You have no tasks.")
                return
            self._print_tasks(mine, "")

            raw = input("Enter a task ID to complete or edit (or '-1' to go back): ").strip()
            if raw == "-1":
                return
            task = next((t for t in mine if raw.isdigit() and t.id == int(raw)), None)
            if task is None:
                print("Error: Please enter the ID of one of your tasks, or '-1' to go back.")
                continue
            if task.completed:
                print("This task is already complete and cannot be changed.")
                continue

            action = input("Enter 'c' to mark it complete, 'e' to edit it, or 'n' to go back: ")
            action = action.strip().lower()
            if action == "c":
                self.manager.mark_complete(task.id, self.username)
                print("Task marked as complete!")
            elif action == "e":
                self._edit(task)
            elif action != "n":
                print("Invalid choice. Please try again.")

    def _edit(self, task: Task) -> None:
        choice = (
            input(
                "Enter 'a' to change the assignee, 'd' to change the due date, "
                "'b' to change both, or 'n' to cancel: "
            )
            .strip()
            .lower()
        )
        if choice not in ("a", "d", "b"):
            if choice != "n":
                print("Invalid choice. Please try again.")
            return

        new_assignee = None
        new_due_date = None
        if choice in ("a", "b"):
            new_assignee = self.ask_registered_user("Enter the new assignee", allow_cancel=True)
            if new_assignee is None:
                print("Edit cancelled.")
                return
        if choice in ("d", "b"):
            new_due_date = self.ask_due_date("Enter the new due date")

        try:
            self.manager.edit_task(
                task.id, self.username, assignee=new_assignee, due_date=new_due_date
            )
        except TaskManagerError as exc:
            print(f"Error: {exc}")
            return
        print("Task details updated!")

    def delete_task(self) -> None:
        raw = ask_non_empty("Enter the ID of the task you want to delete: ")
        if not raw.isdigit():
            print("Error: A task ID is a whole number.")
            return
        task = self.manager.get_task(int(raw))
        print(format_task(task, self.manager.today()))
        if input("Delete this task? (y/n): ").strip().lower() != "y":
            print("Task not deleted.")
            return
        self.manager.delete_task(task.id, self.username)
        print("Task successfully deleted!")

    def generate_reports(self) -> None:
        task_path, user_path = write_reports(
            self.data_dir, self.manager.users, self.manager.tasks, self.manager.today()
        )
        print(f"Task overview saved to {task_path}")
        print(f"User overview saved to {user_path}")

    def display_statistics(self) -> None:
        # Always regenerate so the numbers reflect the current tasks, not a stale file.
        task_path, user_path = write_reports(
            self.data_dir, self.manager.users, self.manager.tasks, self.manager.today()
        )
        for title, path in (("Task Overview", task_path), ("User Overview", user_path)):
            print("\n" + "=" * 50)
            print(title.upper())
            print("=" * 50)
            print(path.read_text(encoding="utf-8").rstrip())
        print("=" * 50)

    # -------------------------------------------------------------- helpers

    def _print_tasks(self, tasks: list[Task], empty_message: str) -> None:
        if not tasks:
            print(empty_message)
            return
        print(DIVIDER)
        today = self.manager.today()
        for task in tasks:
            print(format_task(task, today))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-manager",
        description="Assign and track team tasks from the command line.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--data-dir",
        default=None,
        help=f"folder for users, tasks and reports (default: ./{DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help=f"reset ./{DEMO_DATA_DIR} with sample users and tasks, then start the app",
    )
    parser.add_argument(
        "--import-users", metavar="FILE", help="import a legacy user.txt, then exit"
    )
    parser.add_argument(
        "--import-tasks", metavar="FILE", help="import a legacy tasks.txt, then exit"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.demo and args.data_dir:
        parser.error("--demo and --data-dir cannot be used together.")
    if args.demo and (args.import_users or args.import_tasks):
        parser.error("--demo cannot be combined with an import.")

    data_dir = Path(DEMO_DATA_DIR if args.demo else (args.data_dir or DEFAULT_DATA_DIR))

    try:
        if args.demo:
            manager = seed_demo(data_dir)
            print("Demo data created. Log in as one of these users:")
            print(f"  {', '.join(DEMO_USERS)}  (password for all: {DEMO_PASSWORD})")
        else:
            manager = TaskManager(Storage(data_dir))

        if args.import_users or args.import_tasks:
            result = import_legacy(manager, args.import_users, args.import_tasks)
            print(f"Imported {result.users_imported} user(s) and {result.tasks_imported} task(s).")
            for warning in result.warnings:
                print(f"  warning: {warning}")
            return 0

        return CLI(manager, data_dir).run()
    except StorageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
