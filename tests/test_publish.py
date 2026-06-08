"""Tests for autobots publish command and version bumping."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from autobots.cli import _bump_version


class BumpVersionTests(unittest.TestCase):
    def test_bump_patch(self) -> None:
        self.assertEqual(_bump_version("0.1.4"), "0.1.5")

    def test_bump_patch_9(self) -> None:
        self.assertEqual(_bump_version("0.1.9"), "0.1.10")

    def test_bump_minor(self) -> None:
        self.assertEqual(_bump_version("0.9.9"), "0.9.10")

    def test_bump_major(self) -> None:
        self.assertEqual(_bump_version("9.9.9"), "9.9.10")

    def test_bump_zero(self) -> None:
        self.assertEqual(_bump_version("0.0.0"), "0.0.1")

    def test_invalid_version_raises(self) -> None:
        with self.assertRaises(SystemExit):
            _bump_version("1.2")

    def test_invalid_version_string_raises(self) -> None:
        with self.assertRaises(SystemExit):
            _bump_version("abc")


class PublishDryRunTests(unittest.TestCase):
    def test_dry_run_does_not_modify_files(self) -> None:
        tmpdir = Path(tempfile.mkdtemp())
        try:
            init_file = tmpdir / "__init__.py"
            pyproject_file = tmpdir / "pyproject.toml"

            init_file.write_text('__version__ = "0.1.4"\n', encoding="utf-8")
            pyproject_file.write_text('version = "0.1.4"\n', encoding="utf-8")

            with patch("autobots.cli.ENGINE_ROOT", tmpdir):
                with patch("autobots.cli.init_path", init_file):
                    with patch("autobots.cli.pyproject_path", pyproject_file):
                        from autobots.cli import run_publish
                        run_publish(["publish", "--dry-run"])

            self.assertEqual(init_file.read_text(encoding="utf-8"), '__version__ = "0.1.4"\n')
            self.assertEqual(pyproject_file.read_text(encoding="utf-8"), 'version = "0.1.4"\n')
        finally:
            shutil.rmtree(tmpdir)


class PublishIntegrationTests(unittest.TestCase):
    def test_publish_updates_version_files(self) -> None:
        tmpdir = Path(tempfile.mkdtemp())
        try:
            init_file = tmpdir / "autobots" / "__init__.py"
            pyproject_file = tmpdir / "pyproject.toml"
            dist_dir = tmpdir / "dist"
            init_file.parent.mkdir(parents=True, exist_ok=True)
            dist_dir.mkdir(parents=True, exist_ok=True)

            init_file.write_text('__version__ = "0.1.4"\n', encoding="utf-8")
            pyproject_file.write_text('version = "0.1.4"\n', encoding="utf-8")

            with patch("autobots.cli.ENGINE_ROOT", tmpdir):
                with patch("autobots.cli.init_path", init_file):
                    with patch("autobots.cli.pyproject_path", pyproject_file):
                        with patch("autobots.cli.dist_dir", dist_dir):
                            with patch("subprocess.run") as mock_run:
                                mock_run.return_value = subprocess.CompletedProcess(
                                    args=[], returncode=0, stdout="", stderr=""
                                )
                                from autobots.cli import run_publish
                                run_publish(["publish"])

            self.assertIn("0.1.5", init_file.read_text(encoding="utf-8"))
            self.assertIn("0.1.5", pyproject_file.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()
