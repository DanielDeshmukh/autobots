import tempfile
import unittest
from pathlib import Path

from autobots.planning import scan_repository, write_plan
from autobots.workspace import TargetProjectWorkspace


class PlanningTests(unittest.TestCase):
    def test_scan_repository_collects_phase_three_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / ".env").write_text("KEY=value\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "tests").mkdir()

            scan = scan_repository(root)

            self.assertIn("pyproject.toml", scan.build_files)
            self.assertIn(".env", scan.env_files)
            self.assertIn("README.md", scan.docs)
            self.assertIn("src", scan.source_roots)
            self.assertIn("tests", scan.test_roots)
            self.assertEqual(scan.frameworks, ())

    def test_write_plan_refreshes_roadmap_and_progress_tracker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            workspace = TargetProjectWorkspace(root)

            _, _, artifacts = write_plan(workspace, goal="Add a planning workflow")

            roadmap = (root / "context" / "roadmap.md").read_text(encoding="utf-8")
            progress = (root / "context" / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("Add a planning workflow", roadmap)
            self.assertIn("P2 | Implement the core change in the primary code paths", progress)
            self.assertIn("validation: python -m unittest discover -s tests -q", progress)
            self.assertIn("Depends on: P1", roadmap)
            self.assertIn("Relevant paths: autobots/planning.py", roadmap)
            self.assertEqual(len(artifacts.phases), 3)

    def test_write_plan_preserves_matching_completed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            context_root = root / "context"
            context_root.mkdir()
            (context_root / "progress-tracker.md").write_text(
                "# Progress Tracker\n\n"
                "- [x] P1 | Inspect repository structure and confirm the planning objective | depends on: none | validation: none | acceptance: repo scan exists\n",
                encoding="utf-8",
            )
            workspace = TargetProjectWorkspace(root)

            write_plan(workspace, goal="Add a planning workflow")

            progress = (context_root / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("- [x] P1 | Inspect impacted code and confirm implementation scope", progress)

    def test_write_plan_append_mode_inserts_new_phases_after_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            workspace = TargetProjectWorkspace(root)

            write_plan(workspace, goal="Initial planning")
            _, _, artifacts = write_plan(
                workspace,
                goal="Add release readiness follow-up",
                append=True,
                insert_after="P1",
            )

            progress = (root / "context" / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("P4 | Inspect impacted code and confirm implementation scope", progress)
            self.assertIn("P4 | Inspect impacted code and confirm implementation scope | depends on: P1", progress)
            self.assertIn("P2 | Implement the core change in the primary code paths | depends on: P1, P6", progress)
            self.assertEqual(len(artifacts.phases), 6)

    def test_write_plan_dry_run_does_not_write_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            workspace = TargetProjectWorkspace(root)

            _, _, artifacts = write_plan(workspace, goal="Preview planning only", dry_run=True)

            self.assertFalse((root / "context" / "roadmap.md").exists())
            self.assertIn("Preview planning only", artifacts.roadmap)

    def test_goal_specific_paths_shape_generated_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "tests").mkdir()
            workspace = TargetProjectWorkspace(root)

            _, _, artifacts = write_plan(workspace, goal="Update CLI planning workflow", dry_run=True)

            implementation_phase = artifacts.phases[1]
            self.assertIn("autobots/cli.py", implementation_phase.relevant_paths)
            self.assertIn("autobots/planning.py", implementation_phase.relevant_paths)
            self.assertIn("python -m pytest -q", implementation_phase.validation_commands)


if __name__ == "__main__":
    unittest.main()
