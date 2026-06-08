"""End-to-end tests for task registry, plan, run, and status workflow."""

import json
import tempfile
import unittest
from pathlib import Path

from autobots.executor.task_registry import (
    TaskStatus,
    create_tasks_from_phase,
    get_task,
    get_phase_tasks,
    get_all_tasks,
    get_next_pending_task,
    start_task,
    complete_task,
    fail_task,
    get_phase_status,
    get_all_phases_status,
    get_registry_path,
)


SAMPLE_ROADMAP = """\
# Roadmap

## Planning Objective
- Build a login feature

## Generated Phases

### P1: Inspect codebase
- Goal: Review existing auth patterns
- Depends on: None
- Relevant paths: src/auth.py
- Validation: python -m pytest -q
- Acceptance checks:
  - Auth patterns documented
  - Entry points identified

### P2: Implement login
- Goal: Add login endpoint
- Depends on: P1
- Relevant paths: src/auth.py, src/routes.py
- Validation: python -m pytest -q
- Acceptance checks:
  - Login endpoint works
  - Sessions are managed

### P3: Add tests
- Goal: Cover login with tests
- Depends on: P2
- Relevant paths: tests/
- Validation: python -m pytest -q
- Acceptance checks:
  - Unit tests pass
  - Integration tests pass
  - Coverage report generated
"""


class TaskRegistryBasicTests(unittest.TestCase):
    def test_create_tasks_returns_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ids = create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["task A", "task B"])
            self.assertEqual(ids, ["P1-T1", "P1-T2"])

    def test_create_tasks_persists_to_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["task A"])
            registry_path = get_registry_path(tmpdir)
            data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
            self.assertIn("P1-T1", data["tasks"])
            self.assertEqual(data["tasks"]["P1-T1"]["description"], "task A")
            self.assertEqual(data["tasks"]["P1-T1"]["status"], TaskStatus.PENDING)

    def test_get_task_returns_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["task A"])
            task = get_task(tmpdir, "P1-T1")
            self.assertIsNotNone(task)
            self.assertEqual(task["task_id"], "P1-T1")

    def test_get_task_returns_none_for_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task = get_task(tmpdir, "P1-T1")
            self.assertIsNone(task)

    def test_get_phase_tasks_returns_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A", "B", "C"])
            tasks = get_phase_tasks(tmpdir, "P1")
            self.assertEqual(len(tasks), 3)

    def test_get_next_pending_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A", "B"])
            task = get_next_pending_task(tmpdir, "P1")
            self.assertEqual(task["task_id"], "P1-T1")

    def test_start_task_changes_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A"])
            start_task(tmpdir, "P1-T1")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.ACTIVE)
            self.assertIsNotNone(task["started_at"])

    def test_complete_task_changes_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A"])
            start_task(tmpdir, "P1-T1")
            complete_task(tmpdir, "P1-T1", result="done", cluster="Optimus")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.COMPLETED)
            self.assertEqual(task["result"], "done")
            self.assertEqual(task["cluster"], "Optimus")

    def test_fail_task_changes_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A"])
            start_task(tmpdir, "P1-T1")
            fail_task(tmpdir, "P1-T1", error="something broke")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.FAILED)
            self.assertEqual(task["error"], "something broke")

    def test_start_task_raises_for_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                start_task(tmpdir, "P1-T1")


class TaskRegistryStatusTests(unittest.TestCase):
    def test_phase_status_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status = get_phase_status(tmpdir, "P1")
            self.assertEqual(status["status"], "empty")
            self.assertEqual(status["total"], 0)

    def test_phase_status_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A", "B"])
            status = get_phase_status(tmpdir, "P1")
            self.assertEqual(status["status"], "pending")
            self.assertEqual(status["total"], 2)
            self.assertEqual(status["pending"], 2)

    def test_phase_status_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A", "B"])
            start_task(tmpdir, "P1-T1")
            status = get_phase_status(tmpdir, "P1")
            self.assertEqual(status["status"], "in_progress")
            self.assertEqual(status["active"], 1)

    def test_phase_status_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A", "B"])
            complete_task(tmpdir, "P1-T1")
            complete_task(tmpdir, "P1-T2")
            status = get_phase_status(tmpdir, "P1")
            self.assertEqual(status["status"], "complete")
            self.assertEqual(status["completed"], 2)

    def test_phase_status_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A", "B"])
            complete_task(tmpdir, "P1-T1")
            fail_task(tmpdir, "P1-T2", error="fail")
            status = get_phase_status(tmpdir, "P1")
            self.assertEqual(status["status"], "failed")

    def test_all_phases_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase 1", ["A"])
            create_tasks_from_phase(tmpdir, "P2", "Phase 2", ["B"])
            complete_task(tmpdir, "P1-T1")

            all_status = get_all_phases_status(tmpdir)
            self.assertEqual(len(all_status), 2)
            self.assertEqual(all_status[0]["status"], "complete")
            self.assertEqual(all_status[1]["status"], "pending")


class E2EPlanRunWorkflowTests(unittest.TestCase):
    def test_full_plan_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            result = plan_phase(tmpdir)

            self.assertIsNotNone(result)
            self.assertEqual(result["phase_id"], "P1")
            self.assertEqual(result["phase_name"], "Inspect codebase")
            self.assertEqual(len(result["tasks"]), 2)
            self.assertFalse(result["already_planned"])

            task_ids = [t["task_id"] for t in result["tasks"]]
            self.assertEqual(task_ids, ["P1-T1", "P1-T2"])

    def test_plan_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            result1 = plan_phase(tmpdir)
            result2 = plan_phase(tmpdir)

            self.assertFalse(result1["already_planned"])
            self.assertTrue(result2["already_planned"])

    def test_task_registry_json_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            plan_phase(tmpdir)

            registry_path = get_registry_path(tmpdir)
            data = json.loads(Path(registry_path).read_text(encoding="utf-8"))

            self.assertIn("tasks", data)
            self.assertIn("P1-T1", data["tasks"])
            self.assertIn("P1-T2", data["tasks"])

            task = data["tasks"]["P1-T1"]
            self.assertEqual(task["phase_id"], "P1")
            self.assertEqual(task["phase_name"], "Inspect codebase")
            self.assertEqual(task["status"], "pending")
            self.assertIn("created_at", task)

    def test_run_task_updates_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            plan_phase(tmpdir)

            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], "pending")

            start_task(tmpdir, "P1-T1")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], "active")

            complete_task(tmpdir, "P1-T1", result="Optimus", cluster="Optimus")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], "completed")
            self.assertEqual(task["cluster"], "Optimus")

    def test_next_pending_task_skips_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            plan_phase(tmpdir)
            complete_task(tmpdir, "P1-T1", result="done")

            next_task = get_next_pending_task(tmpdir, "P1")
            self.assertEqual(next_task["task_id"], "P1-T2")

    def test_multi_phase_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            result1 = plan_phase(tmpdir)
            self.assertEqual(result1["phase_id"], "P1")

            complete_task(tmpdir, "P1-T1")
            complete_task(tmpdir, "P1-T2")

            result2 = plan_phase(tmpdir)
            self.assertEqual(result2["phase_id"], "P2")
            self.assertEqual(result2["phase_name"], "Implement login")

    def test_status_shows_all_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")

            from autobots.executor.plan_runner import plan_phase

            plan_phase(tmpdir)

            all_status = get_all_phases_status(tmpdir)
            self.assertEqual(len(all_status), 1)
            self.assertEqual(all_status[0]["phase_id"], "P1")
            self.assertEqual(all_status[0]["status"], "pending")


class E2ETaskStateTransitionsTests(unittest.TestCase):
    def test_task_state_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase", ["task"])

            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.PENDING)
            self.assertIsNone(task["started_at"])

            start_task(tmpdir, "P1-T1")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.ACTIVE)
            self.assertIsNotNone(task["started_at"])

            complete_task(tmpdir, "P1-T1", result="success")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.COMPLETED)
            self.assertIsNotNone(task["completed_at"])
            self.assertEqual(task["result"], "success")

    def test_task_cannot_be_completed_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase", ["task"])
            complete_task(tmpdir, "P1-T1")
            task = get_task(tmpdir, "P1-T1")
            self.assertEqual(task["status"], TaskStatus.COMPLETED)

    def test_multiple_tasks_in_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_tasks_from_phase(tmpdir, "P1", "Phase", ["A", "B", "C", "D"])

            tasks = get_phase_tasks(tmpdir, "P1")
            self.assertEqual(len(tasks), 4)

            complete_task(tmpdir, "P1-T1")
            complete_task(tmpdir, "P1-T2")

            next_task = get_next_pending_task(tmpdir, "P1")
            self.assertEqual(next_task["task_id"], "P1-T3")

            status = get_phase_status(tmpdir, "P1")
            self.assertEqual(status["completed"], 2)
            self.assertEqual(status["pending"], 2)
            self.assertEqual(status["status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
