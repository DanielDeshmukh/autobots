"""Tests for Phase 4: Execution Engine For Real Project Work"""

import tempfile
import unittest
import json
from pathlib import Path

from autobots.executor import PhaseExecutor, WorkPacket
from autobots.catalog import ModelSpec
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

    def test_command_policy_requires_explicit_migration_opt_in(self) -> None:
        """Test that migration commands need explicit approval."""
        from autobots.executor import CommandPolicyViolation

        executor = PhaseExecutor()

        with self.assertRaises(CommandPolicyViolation):
            executor._check_command_policy("python manage.py migrate")

        executor._check_command_policy("python manage.py migrate", allow_migrations=True)

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

    class Phase5LoopRouter(AutobotRouter):
        def __init__(self) -> None:
            super().__init__(api_key="test-key")
            self.repair_calls = 0

        def build_cluster_plan(self, phase, roadmap_text):  # type: ignore[override]
            spec = ModelSpec(model_id="test/model", cluster="Optimus", tags=())
            from autobots.router import ClusterPlan

            return ClusterPlan(
                primary_cluster="UltraMagnus",
                primary_lead=spec,
                primary_reviewer=spec,
                primary_support=[],
                command_lead=spec,
                command_reviewer=spec,
                secretary_lead=spec,
                safety_lead=spec,
                repair_lead=spec,
            )

        def _run_command_stage(self, plan, phase, roadmap_text, progress_text):  # type: ignore[override]
            payload = {
                "summary": "Prepared the execution brief.",
                "implementation_goals": ["Create the implementation and validate it."],
                "risks": ["Validation may fail on the first attempt."],
                "acceptance_checks": ["Target repo tests pass."],
            }
            return payload, json.dumps(payload)

        def _run_specialist_stage(self, plan, workspace, phase, roadmap_text, progress_text, command_payload, event_handler=None):  # type: ignore[override]
            test_content = (
                "from pathlib import Path\n\n"
                "import unittest\n\n"
                "class GeneratedValidationTests(unittest.TestCase):\n"
                "    def test_generated_file_is_fixed(self):\n"
                "        value = Path('src/check.txt').read_text(encoding='utf-8').strip()\n"
                "        self.assertEqual(value, 'fixed')\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )
            payload = {
                "summary": "Created the initial implementation.",
                "implementation_notes": ["Wrote a draft file and its validation test."],
                "files": [
                    {"root": "src", "path": "check.txt", "content": "broken\n"},
                    {"root": "tests", "path": "test_generated.py", "content": test_content},
                ],
            }
            return payload, json.dumps(payload)

        def _run_safety_stage(self, plan, phase, specialist_payload, command_payload):  # type: ignore[override]
            payload = {"status": "pass", "summary": "Safety review passed.", "issues": []}
            return payload, json.dumps(payload)

        def _run_repair_stage(self, plan, workspace, phase, roadmap_text, progress_text, command_payload, specialist_payload, review_payload, event_handler=None):  # type: ignore[override]
            self.repair_calls += 1
            test_content = specialist_payload["files"][1]["content"]
            payload = {
                "summary": "Repaired the implementation after validation failure.",
                "files": [
                    {"root": "src", "path": "check.txt", "content": "fixed\n"},
                    {"root": "tests", "path": "test_generated.py", "content": test_content},
                ],
            }
            return payload, json.dumps(payload)

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

    def test_execute_phase_runs_automatic_verify_repair_loop(self) -> None:
        """Test that failed validation triggers an automatic repair cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            workspace = TargetProjectWorkspace(root)
            router = self.Phase5LoopRouter()

            from autobots.router import PhaseRecord

            phase = PhaseRecord(
                line_index=0,
                raw_line="- [ ] P1 | Demo phase",
                title="P1 | Demo phase",
                status="PENDING",
            )
            roadmap = (
                "# Roadmap\n\n"
                "## P1 | Demo phase\n"
                "Goal: Deliver a verified implementation\n"
                "Relevant paths: src/check.txt, tests/test_generated.py\n"
                "Validation: python -m unittest discover -s tests -q\n"
                "Acceptance: Target repo tests pass\n"
            )
            progress = "# Progress Tracker\n\n- [ ] P1 | Demo phase | depends on: none | validation: python -m unittest discover -s tests -q | acceptance: Target repo tests pass\n"

            result = router.execute_phase(workspace, phase, roadmap, progress)

            self.assertTrue(result.validation_passed)
            self.assertEqual(result.verification_attempts, 2)
            self.assertEqual(router.repair_calls, 1)
            self.assertIn("PASS", result.validation_report)
            self.assertEqual((root / "src" / "check.txt").read_text(encoding="utf-8").strip(), "fixed")


if __name__ == "__main__":
    unittest.main()
