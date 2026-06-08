"""Append-only queue writer for progress-tracker.md."""

from __future__ import annotations

import datetime
import os
import threading

try:
    import msvcrt  # type: ignore[import-untyped]  # Windows
except ImportError:
    msvcrt = None  # type: ignore[assignment]

try:
    import fcntl  # type: ignore[import-untyped]  # Unix
except ImportError:
    fcntl = None  # type: ignore[assignment]

_lock_path = threading.local()


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


def append_result(path: str, phase: str, task: str, result: str) -> None:
    """
    Acquires an exclusive lock, appends a formatted result block,
    releases the lock. Safe to call from concurrent asyncio tasks
    via loop.run_in_executor.
    """
    lock_path = path + ".lock"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"\n## {phase} \u2014 {task}\n"
        f"> Completed: {timestamp}\n\n"
        f"{result}\n\n"
        f"---\n"
    )

    with _FileLock(lock_path):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(block)
