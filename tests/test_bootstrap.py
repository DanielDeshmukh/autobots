import tempfile
import unittest
from pathlib import Path

from autobots.bootstrap import CORE_CONTEXT_FILES, detect_repo_profile, initialize_context
from autobots.workspace import TargetProjectWorkspace


class BootstrapTests(unittest.TestCase):
    def test_detect_repo_profile_reads_basic_python_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "src").mkdir()

            profile = detect_repo_profile(root)

            self.assertIn("Python", profile.languages)
            self.assertIn("pip/pyproject", profile.package_managers)
            self.assertIn("pytest", profile.test_tools)
            self.assertIn("src", profile.source_roots)

    def test_initialize_context_writes_all_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text(
                '{"scripts":{"test":"vitest"},"devDependencies":{"vitest":"1.0.0"}}',
                encoding="utf-8",
            )
            workspace = TargetProjectWorkspace(root)
            profile = detect_repo_profile(root)

            written = initialize_context(workspace, profile)

            self.assertEqual(len(written), len(CORE_CONTEXT_FILES))
            for filename in CORE_CONTEXT_FILES:
                path = root / "context" / filename
                self.assertTrue(path.exists(), msg=f"missing {filename}")
            briefing = (root / "context" / "project-briefing.md").read_text(encoding="utf-8")
            self.assertIn("JavaScript/TypeScript", briefing)
            self.assertIn("vitest", briefing)

    def test_initialize_context_writes_selected_file_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = TargetProjectWorkspace(root)
            profile = detect_repo_profile(root)

            written = initialize_context(workspace, profile, selected_files=("roadmap.md",))

            self.assertEqual([path.name for path in written], ["roadmap.md"])
            self.assertTrue((root / "context" / "roadmap.md").exists())
            self.assertFalse((root / "context" / "architecture.md").exists())


if __name__ == "__main__":
    unittest.main()
