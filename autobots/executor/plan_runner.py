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
    from .task_registry import get_task, start_task, complete_task, fail_task, get_phase_status
    from ..router import AutobotRouter, PhaseRecord
    from ..workspace import TargetProjectWorkspace

    task = get_task(target_root, task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    if task["status"] == "completed":
        return {"error": f"Task {task_id} already completed"}

    context_dir = Path(target_root) / "context"
    roadmap_path = str(context_dir / "roadmap.md")
    progress_path = str(context_dir / "progress-tracker.md")

    try:
        start_task(target_root, task_id)

        workspace = TargetProjectWorkspace(target_root)
        router = AutobotRouter()

        healthy = router.catalog.probe_models(timeout=15.0)
        if healthy:
            router.catalog.filter_to_healthy_models(healthy)

        roadmap_text = workspace.read_context_file("roadmap.md")
        progress_text = workspace.read_context_file("progress-tracker.md")

        phase = router.find_next_phase(progress_text)
        if not phase:
            return {"error": f"No pending phase found in progress-tracker.md"}

        result = router.execute_phase(
            workspace=workspace,
            phase=phase,
            roadmap_text=roadmap_text,
            progress_text=progress_text,
        )

        updated_progress = router.complete_phase(workspace, phase, progress_text, result.plan)

        files = result.files_written or []
        complete_task(
            target_root,
            task_id,
            result=f"Generated {len(files)} files: {', '.join(files[:5])}",
            cluster=result.cluster_name,
        )

        phase_status = get_phase_status(target_root, task["phase_id"])
        if phase_status["completed"] == phase_status["total"]:
            from .todo_tracker import update_phase_status
            update_phase_status(progress_path, task["phase_id"], "COMPLETE")

        return {
            "task_id": task_id,
            "status": "completed",
            "cluster": result.cluster_name,
            "files_written": files,
            "summary": result.summary,
        }

    except Exception as exc:
        fail_task(target_root, task_id, error=str(exc))
        return {"task_id": task_id, "status": "failed", "error": str(exc)}
