"""End-to-end tests for todo tracker and complete phase implementation."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from autobots.executor.todo_tracker import (
    TodoTracker,
    TaskState,
    render_phase_todo,
    append_milestone,
    update_phase_status,
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
  - Error handling added

### P3: Add tests
- Goal: Cover login with tests
- Depends on: P2
- Relevant paths: tests/
- Validation: python -m pytest -q
- Acceptance checks:
  - Unit tests pass
  - Integration tests pass
"""


class TodoTrackerBasicTests(unittest.TestCase):
    def test_creates_tracker_with_all_pending(self) -> None:
        tracker = TodoTracker("Phase 1", ["task A", "task B"])
        self.assertEqual(tracker.get_state("task A"), TaskState.PENDING)
        self.assertEqual(tracker.get_state("task B"), TaskState.PENDING)

    def test_mark_active_sets_state(self) -> None:
        tracker = TodoTracker("Phase 1", ["task A"])
        tracker.mark_active("task A")
        self.assertEqual(tracker.get_state("task A"), TaskState.ACTIVE)

    def test_mark_complete_sets_state(self) -> None:
        tracker = TodoTracker("Phase 1", ["task A"])
        tracker.mark_complete("task A")
        self.assertEqual(tracker.get_state("task A"), TaskState.COMPLETED)

    def test_mark_complete_overwrites_active(self) -> None:
        tracker = TodoTracker("Phase 1", ["task A"])
        tracker.mark_active("task A")
        tracker.mark_complete("task A")
        self.assertEqual(tracker.get_state("task A"), TaskState.COMPLETED)

    def test_unknown_task_returns_pending(self) -> None:
        tracker = TodoTracker("Phase 1", ["task A"])
        self.assertEqual(tracker.get_state("nonexistent"), TaskState.PENDING)

    def test_get_completed_count(self) -> None:
        tracker = TodoTracker("Phase 1", ["A", "B", "C"])
        tracker.mark_complete("A")
        tracker.mark_complete("B")
        self.assertEqual(tracker.get_completed_count(), 2)

    def test_get_total_count(self) -> None:
        tracker = TodoTracker("Phase 1", ["A", "B", "C"])
        self.assertEqual(tracker.get_total_count(), 3)

    def test_is_all_complete_false(self) -> None:
        tracker = TodoTracker("Phase 1", ["A", "B"])
        tracker.mark_complete("A")
        self.assertFalse(tracker.is_all_complete())

    def test_is_all_complete_true(self) -> None:
        tracker = TodoTracker("Phase 1", ["A", "B"])
        tracker.mark_complete("A")
        tracker.mark_complete("B")
        self.assertTrue(tracker.is_all_complete())


class TodoTrackerRenderTests(unittest.TestCase):
    def test_render_shows_all_pending(self) -> None:
        output = render_phase_todo("Phase 1", ["task A", "task B"])
        self.assertIn("# Todos", output)
        self.assertIn("[ ] task A", output)
        self.assertIn("[ ] task B", output)

    def test_render_shows_completed(self) -> None:
        states = {"task A": TaskState.COMPLETED}
        output = render_phase_todo("Phase 1", ["task A", "task B"], states)
        self.assertIn("[✓] task A", output)
        self.assertIn("[ ] task B", output)

    def test_render_shows_active(self) -> None:
        states = {"task A": TaskState.ACTIVE}
        output = render_phase_todo("Phase 1", ["task A", "task B"], states)
        self.assertIn("[•] task A", output)
        self.assertIn("[ ] task B", output)

    def test_render_mixed_states(self) -> None:
        states = {
            "task A": TaskState.COMPLETED,
            "task B": TaskState.ACTIVE,
            "task C": TaskState.PENDING,
        }
        output = render_phase_todo("Phase 1", ["task A", "task B", "task C"], states)
        self.assertIn("[✓] task A", output)
        self.assertIn("[•] task B", output)
        self.assertIn("[ ] task C", output)

    def test_render_order_matches_tasks(self) -> None:
        output = render_phase_todo("Phase 1", ["first", "second", "third"])
        lines = output.strip().split("\n")
        task_lines = [l for l in lines if l.startswith("[")]
        self.assertEqual(len(task_lines), 3)
        self.assertIn("first", task_lines[0])
        self.assertIn("second", task_lines[1])
        self.assertIn("third", task_lines[2])


class TodoTrackerWorkflowTests(unittest.TestCase):
    def test_full_lifecycle(self) -> None:
        tracker = TodoTracker("Phase 1", ["A", "B", "C"])

        tracker.mark_active("A")
        self.assertEqual(tracker.get_state("A"), TaskState.ACTIVE)
        self.assertEqual(tracker.get_completed_count(), 0)

        tracker.mark_complete("A")
        self.assertEqual(tracker.get_state("A"), TaskState.COMPLETED)
        self.assertEqual(tracker.get_completed_count(), 1)

        tracker.mark_active("B")
        self.assertEqual(tracker.get_state("B"), TaskState.ACTIVE)

        tracker.mark_complete("B")
        self.assertEqual(tracker.get_completed_count(), 2)
        self.assertFalse(tracker.is_all_complete())

        tracker.mark_complete("C")
        self.assertTrue(tracker.is_all_complete())
        self.assertEqual(tracker.get_completed_count(), 3)

    def test_render_during_lifecycle(self) -> None:
        tracker = TodoTracker("Phase 1", ["A", "B"])

        output1 = tracker.render()
        self.assertIn("[ ] A", output1)
        self.assertIn("[ ] B", output1)

        tracker.mark_active("A")
        output2 = tracker.render()
        self.assertIn("[•] A", output2)
        self.assertIn("[ ] B", output2)

        tracker.mark_complete("A")
        tracker.mark_active("B")
        output3 = tracker.render()
        self.assertIn("[✓] A", output3)
        self.assertIn("[•] B", output3)

        tracker.mark_complete("B")
        output4 = tracker.render()
        self.assertIn("[✓] A", output4)
        self.assertIn("[✓] B", output4)


class AppendMilestoneTests(unittest.TestCase):
    def test_append_milestone_writes_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("# Progress\n", encoding="utf-8")

            todo_snapshot = "# Todos\n\n[✓] task A\n[ ] task B\n"
            append_milestone(str(path), "Phase 1", "task A", "Optimus", todo_snapshot)

            content = path.read_text(encoding="utf-8")
            self.assertIn("## Phase 1", content)
            self.assertIn("task A", content)
            self.assertIn("Optimus", content)
            self.assertIn("[✓] task A", content)
            self.assertIn("[ ] task B", content)
            self.assertIn("### Progress", content)

    def test_append_milestone_preserves_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("existing content\n", encoding="utf-8")

            todo_snapshot = "# Todos\n\n[✓] done\n"
            append_milestone(str(path), "P1", "task", "result", todo_snapshot)

            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("existing content\n"))
            self.assertIn("task", content)

    def test_append_milestone_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("", encoding="utf-8")

            todo_snapshot = "# Todos\n\n[•] active\n[ ] pending\n"
            append_milestone(str(path), "Phase 1", "Task A", "Ratchet", todo_snapshot)

            content = path.read_text(encoding="utf-8")
            self.assertIn("---", content)
            self.assertIn("> Completed:", content)


class UpdatePhaseStatusTests(unittest.TestCase):
    def test_update_to_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("- [ ] P1 | Phase One | depends on: none\n", encoding="utf-8")

            update_phase_status(str(path), "P1", "COMPLETE")

            content = path.read_text(encoding="utf-8")
            self.assertIn("[x] P1", content)

    def test_update_to_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("- [ ] P1 | Phase One | depends on: none\n", encoding="utf-8")

            update_phase_status(str(path), "P1", "IN_PROGRESS")

            content = path.read_text(encoding="utf-8")
            self.assertIn("[~] P1", content)

    def test_update_preserves_other_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text(
                "- [ ] P1 | Phase One\n- [ ] P2 | Phase Two\n",
                encoding="utf-8",
            )

            update_phase_status(str(path), "P1", "COMPLETE")

            content = path.read_text(encoding="utf-8")
            self.assertIn("[x] P1", content)
            self.assertIn("[ ] P2", content)

    def test_update_missing_file_no_error(self) -> None:
        update_phase_status("/nonexistent/path.md", "P1", "COMPLETE")


class E2ETodoTrackerIntegrationTests(unittest.TestCase):
    def test_complete_phase_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")
            (context / "progress-tracker.md").write_text(
                "- [ ] P1 | Inspect codebase | depends on: none | validation: none | acceptance: done\n"
                "- [ ] P2 | Implement login | depends on: P1 | validation: none | acceptance: done\n"
                "- [ ] P3 | Add tests | depends on: P2 | validation: none | acceptance: done\n",
                encoding="utf-8",
            )

            from autobots.planning.core import parse_roadmap
            from autobots.executor.todo_tracker import TodoTracker, append_milestone, update_phase_status

            phases = parse_roadmap(str(context / "roadmap.md"))
            self.assertEqual(len(phases), 3)
            self.assertFalse(phases[0]["complete"])

            phase = phases[0]
            tracker = TodoTracker(phase["phase"], phase["tasks"])

            progress_path = str(context / "progress-tracker.md")
            update_phase_status(progress_path, "P1", "IN_PROGRESS")

            for task in phase["tasks"]:
                tracker.mark_active(task)
                todo_snapshot = tracker.render()
                append_milestone(progress_path, phase["phase"], task, "Optimus", todo_snapshot)
                tracker.mark_complete(task)

            update_phase_status(progress_path, "P1", "COMPLETE")

            content = (context / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("[x] P1", content)
            self.assertIn("Inspect codebase", content)
            self.assertIn("### Progress", content)
            self.assertIn("[✓]", content)

    def test_multi_phase_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = root / "context"
            context.mkdir()
            (context / "roadmap.md").write_text(SAMPLE_ROADMAP, encoding="utf-8")
            (context / "progress-tracker.md").write_text(
                "- [ ] P1 | Inspect codebase | depends on: none\n"
                "- [ ] P2 | Implement login | depends on: P1\n"
                "- [ ] P3 | Add tests | depends on: P2\n",
                encoding="utf-8",
            )

            from autobots.planning.core import parse_roadmap
            from autobots.executor.todo_tracker import TodoTracker, append_milestone, update_phase_status

            phases = parse_roadmap(str(context / "roadmap.md"))
            progress_path = str(context / "progress-tracker.md")

            for phase in phases:
                if phase["complete"]:
                    continue

                phase_id = phase.get("phase_id", "")
                tracker = TodoTracker(phase["phase"], phase["tasks"])

                if phase_id:
                    update_phase_status(progress_path, phase_id, "IN_PROGRESS")

                for task in phase["tasks"]:
                    tracker.mark_active(task)
                    todo_snapshot = tracker.render()
                    append_milestone(progress_path, phase["phase"], task, "cluster", todo_snapshot)
                    tracker.mark_complete(task)

                if phase_id:
                    update_phase_status(progress_path, phase_id, "COMPLETE")

            content = (context / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("[x] P1", content)
            self.assertIn("[x] P2", content)
            self.assertIn("[x] P3", content)
            self.assertIn("[✓] Auth patterns documented", content)
            self.assertIn("[✓] Login endpoint works", content)
            self.assertIn("[✓] Unit tests pass", content)

    def test_todo_render_matches_expected_format(self) -> None:
        tracker = TodoTracker("Implement login", [
            "Login endpoint works",
            "Sessions are managed",
            "Error handling added",
        ])

        tracker.mark_complete("Login endpoint works")
        tracker.mark_active("Sessions are managed")

        output = tracker.render()

        expected_lines = [
            "# Todos",
            "",
            "[✓] Login endpoint works",
            "[•] Sessions are managed",
            "[ ] Error handling added",
        ]
        expected = "\n".join(expected_lines)

        self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()
