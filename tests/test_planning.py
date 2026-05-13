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

    def test_write_plan_refreshes_roadmap_and_progress_tracker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            workspace = TargetProjectWorkspace(root)

            write_plan(workspace, goal="Add a planning workflow")

            roadmap = (root / "context" / "roadmap.md").read_text(encoding="utf-8")
            progress = (root / "context" / "progress-tracker.md").read_text(encoding="utf-8")
            self.assertIn("Add a planning workflow", roadmap)
            self.assertIn("Queue the first implementation-ready phase", progress)


if __name__ == "__main__":
    unittest.main()
