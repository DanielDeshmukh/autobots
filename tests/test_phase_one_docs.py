"""Tests for Phase 1 documentation (now in README.md)."""

import unittest
from pathlib import Path


class PhaseOneDocsTests(unittest.TestCase):
    def test_readme_documents_target_command_surface(self) -> None:
        """Verify README.md contains all CLI commands."""
        content = Path("README.md").read_text(encoding="utf-8")
        for command in ("autobots init", "autobots plan", "autobots run", "autobots resume", "autobots status", "autobots engage"):
            self.assertIn(command, content)

    def test_readme_has_model_registry(self) -> None:
        """Verify README.md contains model registry."""
        content = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("Optimus", content)
        self.assertIn("UltraMagnus", content)
        self.assertIn("RedAlert", content)
        self.assertIn("NVIDIA_API_KEY", content)

    def test_readme_has_configuration_section(self) -> None:
        """Verify README.md has configuration documentation."""
        content = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("Configuration", content)
        self.assertIn(".autobots.toml", content)


if __name__ == "__main__":
    unittest.main()