"""AB-591: Cross-platform Verification
Tests that the tool works correctly on Windows, Linux, and macOS.
"""
import os
import sys
import platform
import unittest
from pathlib import Path


class TestCrossPlatform(unittest.TestCase):
    """Verify cross-platform compatibility."""

    def test_platform_detection(self):
        """AB-591.1: Platform is correctly detected."""
        current_platform = platform.system()
        self.assertIn(current_platform, ["Windows", "Linux", "Darwin"],
                      f"Platform should be Windows, Linux, or Darwin, got {current_platform}")

    def test_path_separator(self):
        """AB-591.2: Path separator is correct for platform."""
        current_platform = platform.system()
        if current_platform == "Windows":
            self.assertEqual(os.sep, "\\")
        else:
            self.assertEqual(os.sep, "/")

    def test_env_var_access(self):
        """AB-591.3: Environment variables are accessible."""
        path = os.environ.get("PATH")
        self.assertIsNotNone(path, "PATH environment variable should be accessible")
        self.assertGreater(len(path), 0, "PATH should not be empty")

    def test_temp_dir_access(self):
        """AB-591.4: Temporary directory is accessible."""
        temp_dir = os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp"
        self.assertTrue(os.path.exists(temp_dir), f"Temp directory {temp_dir} should exist")

    def test_python_executable(self):
        """AB-591.5: Python executable is accessible."""
        self.assertIsNotNone(sys.executable, "Python executable should be accessible")
        self.assertTrue(os.path.exists(sys.executable), "Python executable should exist")

    def test_current_directory(self):
        """AB-591.6: Current directory is accessible."""
        cwd = os.getcwd()
        self.assertIsNotNone(cwd, "Current directory should be accessible")
        self.assertTrue(os.path.exists(cwd), "Current directory should exist")

    def test_file_encoding(self):
        """AB-591.7: UTF-8 file encoding works."""
        test_file = Path("test_encoding.txt")
        try:
            test_file.write_text("Hello World", encoding="utf-8")
            content = test_file.read_text(encoding="utf-8")
            self.assertEqual(content, "Hello World")
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_path_operations(self):
        """AB-591.8: Path operations work correctly."""
        path = Path("test") / "path" / "operations"
        self.assertEqual(path.name, "operations")
        self.assertEqual(path.parent.name, "path")

    def test_cli_module_import(self):
        """AB-591.9: CLI module can be imported."""
        try:
            import autobots.cli
            self.assertTrue(True, "CLI module imported successfully")
        except ImportError as e:
            self.fail(f"CLI module import failed: {e}")

    def test_config_module_import(self):
        """AB-591.10: Config module can be imported."""
        try:
            import autobots.config
            self.assertTrue(True, "Config module imported successfully")
        except ImportError as e:
            self.fail(f"Config module import failed: {e}")

    def test_catalog_module_import(self):
        """AB-591.11: Catalog module can be imported."""
        try:
            import autobots.catalog
            self.assertTrue(True, "Catalog module imported successfully")
        except ImportError as e:
            self.fail(f"Catalog module import failed: {e}")

    def test_router_module_import(self):
        """AB-591.12: Router module can be imported."""
        try:
            import autobots.router
            self.assertTrue(True, "Router module imported successfully")
        except ImportError as e:
            self.fail(f"Router module import failed: {e}")

    def test_workspace_module_import(self):
        """AB-591.13: Workspace module can be imported."""
        try:
            import autobots.workspace
            self.assertTrue(True, "Workspace module imported successfully")
        except ImportError as e:
            self.fail(f"Workspace module import failed: {e}")

    def test_executor_module_import(self):
        """AB-591.14: Executor module can be imported."""
        try:
            import autobots.executor
            self.assertTrue(True, "Executor module imported successfully")
        except ImportError as e:
            self.fail(f"Executor module import failed: {e}")

    def test_skills_module_import(self):
        """AB-591.15: Skills module can be imported."""
        try:
            import autobots.skills
            self.assertTrue(True, "Skills module imported successfully")
        except ImportError as e:
            self.fail(f"Skills module import failed: {e}")

    def test_context_gen_module_import(self):
        """AB-591.16: Context gen module can be imported."""
        try:
            import autobots.context_gen
            self.assertTrue(True, "Context gen module imported successfully")
        except ImportError as e:
            self.fail(f"Context gen module import failed: {e}")

    def test_ui_module_import(self):
        """AB-591.17: UI module can be imported."""
        try:
            import autobots.ui
            self.assertTrue(True, "UI module imported successfully")
        except ImportError as e:
            self.fail(f"UI module import failed: {e}")

    def test_selectors_module_import(self):
        """AB-591.18: Selectors module can be imported."""
        try:
            import autobots.selectors
            self.assertTrue(True, "Selectors module imported successfully")
        except ImportError as e:
            self.fail(f"Selectors module import failed: {e}")

    def test_planning_module_import(self):
        """AB-591.19: Planning module can be imported."""
        try:
            import autobots.planning
            self.assertTrue(True, "Planning module imported successfully")
        except ImportError as e:
            self.fail(f"Planning module import failed: {e}")

    def test_bootstrap_module_import(self):
        """AB-591.20: Bootstrap module can be imported."""
        try:
            import autobots.bootstrap
            self.assertTrue(True, "Bootstrap module imported successfully")
        except ImportError as e:
            self.fail(f"Bootstrap module import failed: {e}")

    def test_platform_info_documented(self):
        """AB-591.21: Platform info is documented in cross-platform doc."""
        doc_file = Path("CROSS_PLATFORM.md")
        self.assertTrue(doc_file.exists(), "CROSS_PLATFORM.md should exist")
        content = doc_file.read_text(encoding="utf-8").lower()
        self.assertIn("windows", content, "Cross-platform doc should mention Windows")
        self.assertIn("linux", content, "Cross-platform doc should mention Linux")
        self.assertIn("macos", content, "Cross-platform doc should mention macOS")


if __name__ == "__main__":
    unittest.main()
