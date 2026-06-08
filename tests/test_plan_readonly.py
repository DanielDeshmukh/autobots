"""Tests for read-only plan behaviour and parallel dispatch."""

import asyncio
import tempfile
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from autobots.planning.core import parse_roadmap, route_task, build_cluster_dispatch
from autobots.router.planning import dispatch_phase, route_to_cluster
from autobots.executor.queue_writer import append_result


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
  - Tests pass
"""


class ParseRoadmapTests(unittest.TestCase):
    def test_parse_roadmap_returns_list_of_phase_dicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "roadmap.md"
            path.write_text(SAMPLE_ROADMAP, encoding="utf-8")
            result = parse_roadmap(str(path))
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)
            self.assertIn("phase", result[0])
            self.assertIn("tasks", result[0])
            self.assertIn("complete", result[0])

    def test_parse_roadmap_extracts_phase_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "roadmap.md"
            path.write_text(SAMPLE_ROADMAP, encoding="utf-8")
            result = parse_roadmap(str(path))
            self.assertEqual(result[0]["phase"], "Inspect codebase")
            self.assertEqual(result[1]["phase"], "Implement login")
            self.assertEqual(result[2]["phase"], "Add tests")

    def test_parse_roadmap_extracts_acceptance_checks_as_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "roadmap.md"
            path.write_text(SAMPLE_ROADMAP, encoding="utf-8")
            result = parse_roadmap(str(path))
            self.assertEqual(result[0]["tasks"], ["Auth patterns documented", "Entry points identified"])
            self.assertEqual(result[1]["tasks"], ["Login endpoint works", "Sessions are managed"])
            self.assertEqual(result[2]["tasks"], ["Tests pass"])

    def test_parse_roadmap_marks_complete_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            roadmap_path = Path(tmpdir) / "roadmap.md"
            roadmap_path.write_text(SAMPLE_ROADMAP, encoding="utf-8")
            progress_path = Path(tmpdir) / "progress-tracker.md"
            progress_path.write_text(
                "- [x] P1 | Inspect codebase | depends on: none | validation: none | acceptance: done\n"
                "- [ ] P2 | Implement login | depends on: P1 | validation: none | acceptance: done\n",
                encoding="utf-8",
            )
            result = parse_roadmap(str(roadmap_path))
            self.assertTrue(result[0]["complete"])
            self.assertFalse(result[1]["complete"])

    def test_parse_roadmap_handles_bom_prefixed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "roadmap.md"
            path.write_text("\ufeff" + SAMPLE_ROADMAP, encoding="utf-8-sig")
            result = parse_roadmap(str(path))
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0]["phase"], "Inspect codebase")

    def test_parse_roadmap_returns_empty_for_missing_file(self) -> None:
        result = parse_roadmap("/nonexistent/roadmap.md")
        self.assertEqual(result, [])

    def test_parse_roadmap_returns_empty_for_empty_roadmap(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "roadmap.md"
            path.write_text("", encoding="utf-8")
            result = parse_roadmap(str(path))
            self.assertEqual(result, [])

    def test_parse_roadmap_falls_back_to_phase_title_when_no_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "roadmap.md"
            path.write_text(
                "# Roadmap\n\n### P1: Simple phase\n- Goal: do stuff\n",
                encoding="utf-8",
            )
            result = parse_roadmap(str(path))
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["tasks"], ["Simple phase"])


class RoadmapReadOnlyTests(unittest.TestCase):
    def test_roadmap_not_written_by_write_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            context = root / "context"
            context.mkdir()
            original = "# Roadmap\n\nold content\n"
            (context / "roadmap.md").write_text(original, encoding="utf-8")

            from autobots.workspace import TargetProjectWorkspace
            from autobots.planning import write_plan

            workspace = TargetProjectWorkspace(root)
            write_plan(workspace, goal="test goal")

            roadmap_after = (context / "roadmap.md").read_text(encoding="utf-8")
            self.assertEqual(roadmap_after, original)

    def test_progress_tracker_preserves_completion_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            context = root / "context"
            context.mkdir()
            existing = "# Progress Tracker\n\n- [x] P1 | Inspect impacted code and confirm implementation scope | depends on: none | validation: none | acceptance: done\n"
            (context / "progress-tracker.md").write_text(existing, encoding="utf-8")

            from autobots.workspace import TargetProjectWorkspace
            from autobots.planning import write_plan

            workspace = TargetProjectWorkspace(root)
            write_plan(workspace, goal="test goal")

            progress = (context / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("[x] P1", progress)
            self.assertIn("P2", progress)


class QueueWriterTests(unittest.TestCase):
    def test_append_result_writes_formatted_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("# Progress\n", encoding="utf-8")
            append_result(str(path), "Phase 1", "Task A", "result text")
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Phase 1", content)
            self.assertIn("Task A", content)
            self.assertIn("result text", content)
            self.assertIn("---", content)

    def test_append_result_preserves_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("existing content\n", encoding="utf-8")
            append_result(str(path), "P1", "task", "new")
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("existing content\n"))
            self.assertIn("new", content)

    def test_append_result_is_safe_under_concurrent_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "progress-tracker.md"
            path.write_text("", encoding="utf-8")
            errors: list[Exception] = []

            def writer(task_id: int) -> None:
                try:
                    append_result(str(path), "Phase", f"Task {task_id}", f"result {task_id}")
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            content = path.read_text(encoding="utf-8")
            for i in range(10):
                self.assertIn(f"Task {i}", content)
                self.assertIn(f"result {i}", content)


class DispatchPhaseTests(unittest.TestCase):
    def test_dispatch_phase_returns_results_in_order(self) -> None:
        cluster_map = {
            "task A": {"cluster": "Optimus", "score": 5, "reasons": ["keyword"]},
            "task B": {"cluster": "UltraMagnus", "score": 3, "reasons": ["backend"]},
        }
        results = asyncio.run(dispatch_phase(["task A", "task B"], cluster_map))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["task"], "task A")
        self.assertEqual(results[0]["cluster"], "Optimus")
        self.assertEqual(results[1]["task"], "task B")
        self.assertEqual(results[1]["cluster"], "UltraMagnus")

    def test_dispatch_phase_fires_concurrently(self) -> None:
        call_times: list[float] = []

        async def slow_route(task: str, cluster_map: dict) -> dict:
            call_times.append(time.monotonic())
            await asyncio.sleep(0.05)
            return {"task": task, "cluster": "Test", "score": 0, "reasons": []}

        with patch("autobots.router.planning.route_to_cluster", slow_route):
            results = asyncio.run(dispatch_phase(["a", "b", "c"], {}))

        self.assertEqual(len(results), 3)
        if len(call_times) >= 3:
            spread = max(call_times) - min(call_times)
            self.assertLess(spread, 0.05)

    def test_route_to_cluster_returns_cluster_info(self) -> None:
        cluster_map = {"my task": {"cluster": "Ratchet", "score": 7, "reasons": ["debug"]}}
        result = asyncio.run(route_to_cluster("my task", cluster_map))
        self.assertEqual(result["cluster"], "Ratchet")
        self.assertEqual(result["score"], 7)

    def test_route_to_cluster_defaults_to_ultramagnus(self) -> None:
        result = asyncio.run(route_to_cluster("unknown task", {}))
        self.assertEqual(result["cluster"], "UltraMagnus")


class BuildClusterDispatchTests(unittest.TestCase):
    def test_build_cluster_dispatch_returns_task_map(self) -> None:
        phases = [
            {"phase": "P1", "tasks": ["task A", "task B"], "complete": False},
        ]
        dispatch_map = build_cluster_dispatch(phases, api_key="test-key")
        self.assertIn("task A", dispatch_map)
        self.assertIn("task B", dispatch_map)
        self.assertIn("cluster", dispatch_map["task A"])

    def test_build_cluster_dispatch_deduplicates_tasks(self) -> None:
        phases = [
            {"phase": "P1", "tasks": ["shared task"], "complete": False},
            {"phase": "P2", "tasks": ["shared task"], "complete": False},
        ]
        dispatch_map = build_cluster_dispatch(phases, api_key="test-key")
        self.assertEqual(len(dispatch_map), 1)
        self.assertIn("shared task", dispatch_map)


class RouteTaskTests(unittest.TestCase):
    def test_route_task_returns_cluster_info(self) -> None:
        result = route_task("implement login endpoint", api_key="test-key")
        self.assertIn("cluster", result)
        self.assertIn("score", result)
        self.assertIn("reasons", result)
        self.assertIsInstance(result["reasons"], list)


class PlanRunnerTests(unittest.TestCase):
    def test_parse_roadmap_identifies_first_incomplete_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            roadmap_path = Path(tmpdir) / "roadmap.md"
            roadmap_path.write_text(SAMPLE_ROADMAP, encoding="utf-8")
            progress_path = Path(tmpdir) / "progress-tracker.md"
            progress_path.write_text(
                "- [x] P1 | Inspect codebase | depends on: none | validation: none | acceptance: done\n"
                "- [~] P2 | Implement login | depends on: P1 | validation: none | acceptance: done\n"
                "- [ ] P3 | Add tests | depends on: P2 | validation: none | acceptance: done\n",
                encoding="utf-8",
            )
            phases = parse_roadmap(str(roadmap_path))
            incomplete = [p for p in phases if not p["complete"]]
            self.assertEqual(len(incomplete), 2)
            self.assertEqual(incomplete[0]["phase"], "Implement login")

    def test_all_complete_returns_no_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            roadmap_path = Path(tmpdir) / "roadmap.md"
            roadmap_path.write_text(SAMPLE_ROADMAP, encoding="utf-8")
            progress_path = Path(tmpdir) / "progress-tracker.md"
            progress_path.write_text(
                "- [x] P1 | Inspect codebase | depends on: none | validation: none | acceptance: done\n"
                "- [x] P2 | Implement login | depends on: P1 | validation: none | acceptance: done\n"
                "- [x] P3 | Add tests | depends on: P2 | validation: none | acceptance: done\n",
                encoding="utf-8",
            )
            phases = parse_roadmap(str(roadmap_path))
            incomplete = [p for p in phases if not p["complete"]]
            self.assertEqual(len(incomplete), 0)


if __name__ == "__main__":
    unittest.main()
