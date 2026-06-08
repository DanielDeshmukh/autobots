import tempfile
import unittest
from pathlib import Path

from autobots.bootstrap import CORE_CONTEXT_FILES, detect_repo_profile


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

    def test_core_context_files_lists_required_filenames_only(self) -> None:
        self.assertEqual(
            CORE_CONTEXT_FILES,
            (
                "architecture.md",
                "roadmap.md",
                "ui-components.md",
                "progress-tracker.md",
                "project-briefing.md",
                "security-auth.md",
            ),
        )


if __name__ == "__main__":
    unittest.main()
