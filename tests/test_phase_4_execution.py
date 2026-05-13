"""Tests for Phase 4: Execution Engine For Real Project Work"""

import tempfile
import unittest
from pathlib import Path

from autobots.executor import PhaseExecutor, WorkPacket
from autobots.router import AutobotRouter
from autobots.workspace import TargetProjectWorkspace


class Phase4WorkspaceTests(unittest.TestCase):
    """Test Phase 4 workspace expansion to multiple project layout roots."""

    def test_write_file_to_app_root(self) -> None:
        """Test writing files to app/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "app").mkdir()
            workspace = TargetProjectWorkspace(root)

            workspace.write_file("app", "components/button.tsx", "export const Button = () => <button/>;")

            written = root / "app" / "components" / "button.tsx"
            self.assertTrue(written.exists())
            self.assertIn("Button", written.read_text())

    def test_write_file_to_lib_root(self) -> None:
        """Test writing files to lib/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "lib").mkdir()
            workspace = TargetProjectWorkspace(root)

            workspace.write_file("lib", "helpers.py", "def helper(): pass")

            written = root / "lib" / "helpers.py"
            self.assertTrue(written.exists())
            self.assertIn("helper", written.read_text())

    def test_write_file_to_tests_root(self) -> None:
        """Test writing files to tests/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tests").mkdir()
            workspace = TargetProjectWorkspace(root)

            workspace.write_file("tests", "test_feature.py", "def test_feature(): pass")

            written = root / "tests" / "test_feature.py"
            self.assertTrue(written.exists())
            self.assertIn("test_feature", written.read_text())

    def test_write_file_to_docs_root(self) -> None:
        """Test writing files to docs/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            workspace = TargetProjectWorkspace(root)

            workspace.write_file("docs", "README.md", "# Documentation")

            written = root / "docs" / "README.md"
            self.assertTrue(written.exists())
            self.assertIn("Documentation", written.read_text())

    def test_read_file_from_app_root(self) -> None:
        """Test reading files from app/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_dir = root / "app"
            app_dir.mkdir()
            (app_dir / "component.tsx").write_text("const Component = () => null;")
            workspace = TargetProjectWorkspace(root)

            content = workspace.read_file("app", "component.tsx")

            self.assertIn("Component", content)

    def test_apply_generated_files_multiple_roots(self) -> None:
        """Test apply_generated_files with multiple target roots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for dirname in ["src", "app", "lib", "tests", "docs"]:
                (root / dirname).mkdir()

            workspace = TargetProjectWorkspace(root)
            files = [
                {"root": "src", "path": "index.py", "content": "# src file"},
                {"root": "app", "path": "main.tsx", "content": "// app file"},
                {"root": "lib", "path": "util.py", "content": "# lib file"},
                {"root": "tests", "path": "test.py", "content": "# test file"},
                {"root": "docs", "path": "guide.md", "content": "# documentation"},
            ]

            written = workspace.apply_generated_files(files)

            self.assertEqual(len(written), 5)
            self.assertTrue((root / "src" / "index.py").exists())
            self.assertTrue((root / "app" / "main.tsx").exists())
            self.assertTrue((root / "lib" / "util.py").exists())
            self.assertTrue((root / "tests" / "test.py").exists())
            self.assertTrue((root / "docs" / "guide.md").exists())

    def test_list_files_from_root(self) -> None:
        """Test listing files in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("# main")
            (src_dir / "utils.py").write_text("# utils")
            (src_dir / "components").mkdir()
            (src_dir / "components" / "button.py").write_text("# button")

            workspace = TargetProjectWorkspace(root)
            files = workspace.list_files("src")

            file_paths = [f["path"] for f in files]
            self.assertIn("main.py", file_paths)
            self.assertIn("utils.py", file_paths)
            self.assertIn("components", file_paths)

    def test_get_file_summary(self) -> None:
        """Test generating file summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "app.py").write_text("def main():\n    print('Hello')\n    pass")

            workspace = TargetProjectWorkspace(root)
            summary = workspace.get_file_summary("src", ["app.py"])

            self.assertIn("app.py", summary)
            self.assertIn("main", summary)


class Phase4ExecutorTests(unittest.TestCase):
    """Test Phase 4 execution engine."""

    def test_build_work_packet(self) -> None:
        """Test creating a work packet."""
        executor = PhaseExecutor()

        packet = executor.build_work_packet(
            phase_id="P1",
            title="Inspect repository",
            goal="Scan and understand the codebase",
            relevant_files=["src/main.py", "tests/test_main.py"],
            constraints=["No breaking changes", "Must maintain API"],
            validation_commands=["python -m pytest -q"],
            acceptance_checks=["All tests pass"],
        )

        self.assertEqual(packet.phase_id, "P1")
        self.assertEqual(packet.title, "Inspect repository")
        self.assertEqual(len(packet.validation_commands), 1)
        self.assertEqual(len(packet.acceptance_checks), 1)

    def test_inspect_phase_files(self) -> None:
        """Test file inspection for a phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main():\n    return 'Hello'\n")

            workspace = TargetProjectWorkspace(root)
            executor = PhaseExecutor()
            packet = executor.build_work_packet(
                phase_id="P1",
                title="Test phase",
                goal="Test inspection",
                relevant_files=["main.py"],
                constraints=[],
                validation_commands=[],
                acceptance_checks=[],
            )

            report = executor.inspect_phase_files(workspace, packet)

            self.assertIn("main.py", report)
            self.assertIn("main", report)

    def test_apply_generated_changes(self) -> None:
        """Test applying generated file changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir()

            workspace = TargetProjectWorkspace(root)
            executor = PhaseExecutor()
            packet = executor.build_work_packet(
                phase_id="P1",
                title="Test phase",
                goal="Test changes",
                relevant_files=[],
                constraints=[],
                validation_commands=[],
                acceptance_checks=[],
            )

            generated_files = [
                {"root": "src", "path": "new_file.py", "content": "def new_func():\n    pass\n"},
            ]

            written = executor.apply_generated_changes(workspace, packet, generated_files, "TestOwner")

            self.assertEqual(len(written), 1)
            self.assertTrue((root / "src" / "new_file.py").exists())

    def test_command_policy_rejects_dangerous_commands(self) -> None:
        """Test that command policy rejects dangerous commands."""
        from autobots.executor import CommandPolicyViolation
        executor = PhaseExecutor()

        with self.assertRaises(CommandPolicyViolation):
            executor._check_command_policy("rm -rf /")

        with self.assertRaises(CommandPolicyViolation):
            executor._check_command_policy("sudo apt-get install")

    def test_command_policy_allows_safe_commands(self) -> None:
        """Test that command policy allows safe test commands."""
        executor = PhaseExecutor()

        # These should not raise
        executor._check_command_policy("python -m pytest -q")
        executor._check_command_policy("pylint src/")
        executor._check_command_policy("mypy src/")

    def test_format_validation_results(self) -> None:
        """Test formatting validation results."""
        from autobots.executor import ValidationResult
        executor = PhaseExecutor()

        results = [
            ValidationResult(
                command="python -m pytest -q",
                exit_code=0,
                stdout="All tests passed",
                stderr="",
                passed=True,
            ),
            ValidationResult(
                command="pylint src/",
                exit_code=1,
                stdout="",
                stderr="Error: syntax issue",
                passed=False,
            ),
        ]

        report = executor.format_validation_results(results)

        self.assertIn("PASS", report)
        self.assertIn("FAIL", report)
        self.assertIn("pytest", report)
        self.assertIn("pylint", report)


class Phase4RouterTests(unittest.TestCase):
    """Test Phase 4 router extensions."""

    def test_build_work_packet_from_phase(self) -> None:
        """Test building a work packet from phase information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n")
            (root / "src").mkdir()

            router = AutobotRouter()
            from autobots.router import PhaseRecord

            phase = PhaseRecord(
                line_index=0,
                raw_line="- [ ] P1 | Inspect repository",
                title="P1 | Inspect repository",
                status="PENDING",
            )

            roadmap = """# Roadmap

## P1 | Inspect repository
Goal: Scan and understand the codebase
Validation: python -m pytest -q
Acceptance: All code is understood
"""

            packet = router.build_work_packet_from_phase(phase, roadmap)

            self.assertEqual(packet.phase_id, "P1")
            self.assertIn("pytest", packet.validation_commands[0] if packet.validation_commands else "")

    def test_extract_phase_id(self) -> None:
        """Test extracting phase ID from title."""
        router = AutobotRouter()

        phase_id = router._extract_phase_id("P1 | Inspect repository")
        self.assertEqual(phase_id, "P1")

        phase_id = router._extract_phase_id("Some title with P2 in it")
        self.assertEqual(phase_id, "P2")

    def test_run_validation_commands(self) -> None:
        """Test running validation commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "test.py").write_text("def test(): assert True\n")

            workspace = TargetProjectWorkspace(root)
            router = AutobotRouter()

            packet = router.executor.build_work_packet(
                phase_id="P1",
                title="Test phase",
                goal="Test validation",
                relevant_files=[],
                constraints=[],
                validation_commands=["python -c 'print(\"ok\")'"],
                acceptance_checks=[],
            )

            passed, report = router.run_validation_commands(workspace, packet)

            self.assertTrue(passed)
            self.assertIn("ok", report)


if __name__ == "__main__":
    unittest.main()
