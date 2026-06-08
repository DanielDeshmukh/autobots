"""Execution engine for autobots plan."""

from __future__ import annotations

from pathlib import Path


def plan_phase(target_root: str) -> dict | None:
    """
    Plan the next incomplete phase:
    1. Parse roadmap.md (read-only)
    2. Find first incomplete phase
    3. Create tasks with IDs in task-registry.json
    4. Return the phase info (tasks are NOT executed yet)
    """
    from ..planning.core import parse_roadmap
    from .task_registry import create_tasks_from_phase, get_phase_status, get_all_tasks

    context_dir = Path(target_root) / "context"
    roadmap_path = str(context_dir / "roadmap.md")

    phases = parse_roadmap(roadmap_path)
    if not phases:
        return None

    existing_tasks = get_all_tasks(target_root)

    for phase in phases:
        phase_id = phase.get("phase_id", "P0")
        phase_name = phase["phase"]
        tasks = phase["tasks"]

        if not tasks:
            continue

        if phase["complete"]:
            continue

        phase_tasks = [t for t in existing_tasks.values() if t["phase_id"] == phase_id]
        if phase_tasks:
            all_done = all(
                t["status"] in ("completed", "failed")
                for t in phase_tasks
            )
            if all_done:
                continue

            return {
                "phase_id": phase_id,
                "phase_name": phase_name,
                "tasks": [
                    {"task_id": t["task_id"], "description": t["description"], "status": t["status"]}
                    for t in sorted(phase_tasks, key=lambda x: x["task_id"])
                ],
                "already_planned": True,
            }

        task_ids = create_tasks_from_phase(target_root, phase_id, phase_name, tasks)
        planned_tasks = []
        for tid, desc in zip(task_ids, tasks):
            planned_tasks.append({"task_id": tid, "description": desc})

        return {
            "phase_id": phase_id,
            "phase_name": phase_name,
            "tasks": planned_tasks,
            "already_planned": False,
        }

    return None


def run_task(target_root: str, task_id: str, mode: str = "supervised") -> dict:
    """
    Execute a single task by ID.
    Modes: supervised, autonomous, milestone
    """
    from .task_registry import get_task, start_task, complete_task, fail_task
    from ..planning.core import build_cluster_dispatch
    from ..router.planning import dispatch_phase
    from .queue_writer import append_result
    from .todo_tracker import TodoTracker, append_milestone, update_phase_status

    task = get_task(target_root, task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    if task["status"] == "task_registry.COMPLETED":
        return {"error": f"Task {task_id} already completed"}

    context_dir = Path(target_root) / "context"
    progress_path = str(context_dir / "progress-tracker.md")

    try:
        start_task(target_root, task_id)

        phases = [{"phase": task["phase_name"], "tasks": [task["description"]], "complete": False}]
        cluster_map = build_cluster_dispatch(phases)

        tracker = TodoTracker(task["phase_name"], [task["description"]])
        tracker.mark_active(task["description"])

        results = asyncio.run(dispatch_phase([task["description"]], cluster_map))
        result = results[0] if results else {}

        cluster = result.get("cluster", "")
        tracker.mark_complete(task["description"])

        todo_snapshot = tracker.render()
        append_milestone(progress_path, task["phase_name"], task["description"], cluster, todo_snapshot)

        complete_task(target_root, task_id, result=cluster, cluster=cluster)

        from .task_registry import get_phase_status
        phase_status = get_phase_status(target_root, task["phase_id"])
        if phase_status["completed"] == phase_status["total"]:
            update_phase_status(progress_path, task["phase_id"], "COMPLETE")

        return {"task_id": task_id, "status": "completed", "cluster": cluster}

    except Exception as exc:
        fail_task(target_root, task_id, error=str(exc))
        return {"task_id": task_id, "status": "failed", "error": str(exc)}


import asyncio
