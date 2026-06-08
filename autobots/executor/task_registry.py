"""Task registry with ID system and process task JSON for tracking."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any

try:
    import msvcrt  # type: ignore[import-untyped]  # Windows
except ImportError:
    msvcrt = None  # type: ignore[assignment]

try:
    import fcntl  # type: ignore[import-untyped]  # Unix
except ImportError:
    fcntl = None  # type: ignore[assignment]


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


class TaskStatus:
    """Task status constants."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


def _now_iso() -> str:
    """Return current time as ISO string."""
    return datetime.datetime.now().isoformat()


def get_registry_path(target_root: str) -> str:
    """Get path to task-registry.json in target project."""
    return str(Path(target_root) / ".autobots-state" / "task-registry.json")


def _load_registry(registry_path: str) -> dict[str, Any]:
    """Load the task registry from JSON."""
    path = Path(registry_path)
    if not path.exists():
        return {"tasks": {}, "next_task_index": 1}
    try:
        content = path.read_text(encoding="utf-8-sig")
        data = json.loads(content)
        if "tasks" not in data:
            data["tasks"] = {}
        if "next_task_index" not in data:
            data["next_task_index"] = max(
                (int(k.split("-")[-1]) for k in data["tasks"] if "-" in k),
                default=0,
            ) + 1
        return data
    except (json.JSONDecodeError, ValueError):
        return {"tasks": {}, "next_task_index": 1}


def _save_registry(registry_path: str, data: dict[str, Any]) -> None:
    """Save the task registry to JSON with file locking."""
    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry_path + ".lock"

    with _FileLock(lock_path):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def create_tasks_from_phase(
    target_root: str,
    phase_id: str,
    phase_name: str,
    tasks: list[str],
) -> list[str]:
    """
    Create task entries for a phase and return their task IDs.

    Each task gets an ID like: P1-T1, P1-T2, etc.
    """
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)
    task_ids: list[str] = []

    for i, task_desc in enumerate(tasks, start=1):
        task_id = f"{phase_id}-T{i}"
        task_ids.append(task_id)

        data["tasks"][task_id] = {
            "task_id": task_id,
            "phase_id": phase_id,
            "phase_name": phase_name,
            "description": task_desc,
            "status": TaskStatus.PENDING,
            "created_at": _now_iso(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "cluster": None,
        }

    _save_registry(registry_path, data)
    return task_ids


def get_task(target_root: str, task_id: str) -> dict[str, Any] | None:
    """Get a task by ID."""
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)
    return data["tasks"].get(task_id)


def get_phase_tasks(target_root: str, phase_id: str) -> list[dict[str, Any]]:
    """Get all tasks for a phase, ordered by task number."""
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)

    phase_tasks = [
        t for t in data["tasks"].values()
        if t["phase_id"] == phase_id
    ]
    phase_tasks.sort(key=lambda t: t["task_id"])
    return phase_tasks


def get_all_tasks(target_root: str) -> dict[str, dict[str, Any]]:
    """Get all tasks grouped by phase."""
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)
    return data["tasks"]


def get_next_pending_task(target_root: str, phase_id: str) -> dict[str, Any] | None:
    """Get the next pending task for a phase."""
    tasks = get_phase_tasks(target_root, phase_id)
    for task in tasks:
        if task["status"] == TaskStatus.PENDING:
            return task
    return None


def start_task(target_root: str, task_id: str) -> dict[str, Any]:
    """Mark a task as active."""
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)

    if task_id not in data["tasks"]:
        raise ValueError(f"Task {task_id} not found")

    data["tasks"][task_id]["status"] = TaskStatus.ACTIVE
    data["tasks"][task_id]["started_at"] = _now_iso()

    _save_registry(registry_path, data)
    return data["tasks"][task_id]


def complete_task(
    target_root: str,
    task_id: str,
    result: str | None = None,
    cluster: str | None = None,
) -> dict[str, Any]:
    """Mark a task as completed."""
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)

    if task_id not in data["tasks"]:
        raise ValueError(f"Task {task_id} not found")

    data["tasks"][task_id]["status"] = TaskStatus.COMPLETED
    data["tasks"][task_id]["completed_at"] = _now_iso()
    data["tasks"][task_id]["result"] = result
    data["tasks"][task_id]["cluster"] = cluster

    _save_registry(registry_path, data)
    return data["tasks"][task_id]


def fail_task(target_root: str, task_id: str, error: str) -> dict[str, Any]:
    """Mark a task as failed."""
    registry_path = get_registry_path(target_root)
    data = _load_registry(registry_path)

    if task_id not in data["tasks"]:
        raise ValueError(f"Task {task_id} not found")

    data["tasks"][task_id]["status"] = TaskStatus.FAILED
    data["tasks"][task_id]["completed_at"] = _now_iso()
    data["tasks"][task_id]["error"] = error

    _save_registry(registry_path, data)
    return data["tasks"][task_id]


def get_phase_status(target_root: str, phase_id: str) -> dict[str, Any]:
    """Get status summary for a phase."""
    tasks = get_phase_tasks(target_root, phase_id)
    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED)
    failed = sum(1 for t in tasks if t["status"] == TaskStatus.FAILED)
    active = sum(1 for t in tasks if t["status"] == TaskStatus.ACTIVE)
    pending = sum(1 for t in tasks if t["status"] == TaskStatus.PENDING)

    if total == 0:
        status = "empty"
    elif completed == total:
        status = "complete"
    elif failed > 0:
        status = "failed"
    elif active > 0 or (completed > 0 and completed < total):
        status = "in_progress"
    else:
        status = "pending"

    return {
        "phase_id": phase_id,
        "status": status,
        "total": total,
        "completed": completed,
        "failed": failed,
        "active": active,
        "pending": pending,
        "tasks": tasks,
    }


def get_all_phases_status(target_root: str) -> list[dict[str, Any]]:
    """Get status for all phases."""
    all_tasks = get_all_tasks(target_root)
    phases: dict[str, list[dict]] = {}
    for task in all_tasks.values():
        pid = task["phase_id"]
        if pid not in phases:
            phases[pid] = []
        phases[pid].append(task)

    result = []
    for phase_id in sorted(phases.keys()):
        tasks = phases[phase_id]
        total = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t["status"] == TaskStatus.FAILED)
        active = sum(1 for t in tasks if t["status"] == TaskStatus.ACTIVE)
        pending = sum(1 for t in tasks if t["status"] == TaskStatus.PENDING)

        if completed == total:
            status = "complete"
        elif failed > 0:
            status = "failed"
        elif active > 0:
            status = "in_progress"
        else:
            status = "pending"

        result.append({
            "phase_id": phase_id,
            "phase_name": tasks[0]["phase_name"] if tasks else "",
            "status": status,
            "total": total,
            "completed": completed,
            "failed": failed,
            "active": active,
            "pending": pending,
        })

    return result
