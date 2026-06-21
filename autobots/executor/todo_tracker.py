"""Visual todo tracker for active phase tasks with milestone updates."""

from __future__ import annotations

import datetime
import enum
import os
import threading
from pathlib import Path

try:
    import msvcrt  # type: ignore[import-untyped]  # Windows
except ImportError:
    msvcrt = None  # type: ignore[assignment]

try:
    import fcntl  # type: ignore[import-untyped]  # Unix
except ImportError:
    fcntl = None  # type: ignore[assignment]


class TaskState(enum.Enum):
    """State of a task in the todo tracker."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


_SYMBOLS = {
    TaskState.COMPLETED: "[OK]",
    TaskState.ACTIVE: "[>>]",
    TaskState.PENDING: "[ ]",
}


class _FileLock:
    """Cross-platform exclusive file lock."""

    def __init__(self, path: str):
        self._path = path
        self._fd: int | None = None

    def __enter__(self):
        self._fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
        if msvcrt is not None:
            msvcrt.locking(self._fd, msvcrt.LK_LOCK, 1)  # type: ignore[union-attr]
        elif fcntl is not None:
            fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            try:
                if msvcrt is not None:
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)  # type: ignore[union-attr]
                elif fcntl is not None:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None
        return False


class TodoTracker:
    """
    Manages a visual todo list for phase tasks.

    Display format:
        # Todos

        [✓] Completed task description
        [•] Active task description (in progress)
        [ ] Pending task description
    """

    def __init__(self, phase_name: str, tasks: list[str]):
        self.phase_name = phase_name
        self.tasks = list(tasks)
        self._states: dict[str, TaskState] = {task: TaskState.PENDING for task in tasks}

    def mark_active(self, task: str) -> None:
        """Mark a task as actively being worked on."""
        if task in self._states:
            self._states[task] = TaskState.ACTIVE

    def mark_complete(self, task: str) -> None:
        """Mark a task as completed."""
        if task in self._states:
            self._states[task] = TaskState.COMPLETED

    def get_state(self, task: str) -> TaskState:
        """Get the current state of a task."""
        return self._states.get(task, TaskState.PENDING)

    def render(self) -> str:
        """
        Render the todo list in visual format.

        Returns:
            Formatted string like:
                # Todos

                [✓] Completed task
                [•] Active task
                [ ] Pending task
        """
        lines = ["# Todos", ""]
        for task in self.tasks:
            state = self._states.get(task, TaskState.PENDING)
            symbol = _SYMBOLS[state]
            lines.append(f"{symbol} {task}")
        return "\n".join(lines)

    def get_completed_count(self) -> int:
        """Return the number of completed tasks."""
        return sum(1 for s in self._states.values() if s == TaskState.COMPLETED)

    def get_total_count(self) -> int:
        """Return the total number of tasks."""
        return len(self.tasks)

    def is_all_complete(self) -> bool:
        """Return True if all tasks are completed."""
        return all(s == TaskState.COMPLETED for s in self._states.values())


def render_phase_todo(phase_name: str, tasks: list[str], states: dict[str, TaskState] | None = None) -> str:
    """Convenience function to render a phase todo list."""
    tracker = TodoTracker(phase_name, tasks)
    if states:
        for task, state in states.items():
            if state == TaskState.COMPLETED:
                tracker.mark_complete(task)
            elif state == TaskState.ACTIVE:
                tracker.mark_active(task)
    return tracker.render()


def append_milestone(
    progress_path: str,
    phase_name: str,
    task: str,
    result: str,
    todo_snapshot: str,
) -> None:
    """
    Append a milestone block to progress-tracker.md that includes:
    1. The task completion result
    2. A snapshot of the current todo state
    """
    lock_path = progress_path + ".lock"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"\n## {phase_name} \u2014 {task}\n"
        f"> Completed: {timestamp}\n\n"
        f"{result}\n\n"
        f"### Progress\n\n"
        f"{todo_snapshot}\n\n"
        f"---\n"
    )

    with _FileLock(lock_path):
        with open(progress_path, "a", encoding="utf-8") as fh:
            fh.write(block)


def update_phase_status(
    progress_path: str,
    phase_id: str,
    status: str,
) -> None:
    """
    Update a phase's status marker in progress-tracker.md.
    Supports PENDING ([ ]), IN_PROGRESS ([~]), COMPLETE ([x]).
    """
    import re

    lock_path = progress_path + ".lock"
    path = Path(progress_path)
    if not path.exists():
        return

    with _FileLock(lock_path):
        content = path.read_text(encoding="utf-8-sig")
        lines = content.splitlines()
        updated = False

        for i, line in enumerate(lines):
            if phase_id not in line:
                continue

            marker_map = {
                "PENDING": "[ ]",
                "IN_PROGRESS": "[~]",
                "COMPLETE": "[x]",
            }
            new_marker = marker_map.get(status)
            if not new_marker:
                continue

            if "[x]" in line or "[ ]" in line or "[~]" in line:
                import re as _re
                lines[i] = _re.sub(r"\[[ x~]\]", new_marker, line, count=1)
                updated = True
                break

        if updated:
            path.write_text("\n".join(lines) + ("\n" if content.endswith("\n") else ""), encoding="utf-8")
