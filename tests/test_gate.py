"""Tests for autobots.executor.gate module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from autobots.executor.gate import (
    GateResult,
    TestGate,
    TestResult,
    run_test_gate,
    run_test_suite,
)


class TestTestResult(unittest.TestCase):
    """Tests for TestResult dataclass."""

    def test_passed_result(self):
        result = TestResult(
            passed=True,
            total_tests=10,
            failures=0,
            errors=0,
            duration_seconds=1.5,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.total_tests, 10)
        self.assertEqual(result.failures, 0)

    def test_failed_result(self):
        result = TestResult(
            passed=False,
            total_tests=10,
            failures=2,
            errors=0,
            duration_seconds=1.5,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.failures, 2)


class TestGateResult(unittest.TestCase):
    """Tests for GateResult dataclass."""

    def test_passed_gate(self):
        result = GateResult(passed=True)
        self.assertTrue(result.passed)
        self.assertEqual(result.new_failures, 0)
        self.assertFalse(result.rolled_back)

    def test_failed_gate_with_rollback(self):
        result = GateResult(
            passed=False,
            new_failures=3,
            rolled_back=True,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.new_failures, 3)
        self.assertTrue(result.rolled_back)


class TestRunTestSuite(unittest.TestCase):
    """Tests for run_test_suite function."""

    def test_run_test_suite_returns_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_test_suite(
                workspace=Path(tmpdir),
                test_command="echo '1 passed'",
                timeout=10,
            )
            self.assertIsInstance(result, TestResult)
            self.assertTrue(result.passed)

    def test_run_test_suite_captures_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_test_suite(
                workspace=Path(tmpdir),
                test_command="echo 'test output'",
                timeout=10,
            )
            self.assertIn("test output", result.output)

    def test_run_test_suite_handles_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_test_suite(
                workspace=Path(tmpdir),
                test_command="echo '2 failed' && exit 1",
                timeout=10,
            )
            self.assertFalse(result.passed)


class TestTestGate(unittest.TestCase):
    """Tests for TestGate class."""

    def test_gate_initialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = TestGate(
                workspace=Path(tmpdir),
                test_command="echo 'passed'",
                test_timeout=30,
                enabled=True,
            )
            self.assertEqual(gate.workspace, Path(tmpdir))
            self.assertEqual(gate.test_command, "echo 'passed'")
            self.assertEqual(gate.test_timeout, 30)
            self.assertTrue(gate.enabled)

    def test_gate_disabled_skips_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = TestGate(
                workspace=Path(tmpdir),
                enabled=False,
            )

            result = gate.pre_execution()
            self.assertTrue(result.passed)
            self.assertEqual(result.output, "Test gate disabled")

            result = gate.post_execution()
            self.assertTrue(result.passed)

    def test_gate_pre_execution_stores_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = TestGate(
                workspace=Path(tmpdir),
                test_command="echo '1 passed'",
                enabled=True,
            )

            result = gate.pre_execution()
            self.assertTrue(result.passed)
            self.assertIsNotNone(gate._tests_before)

    def test_gate_execute_with_gate_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = TestGate(
                workspace=Path(tmpdir),
                test_command="echo '1 passed'",
                enabled=True,
            )

            def task_fn():
                pass

            result = gate.execute_with_gate(task_fn)
            self.assertTrue(result.passed)

    def test_gate_execute_with_gate_task_exception(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = TestGate(
                workspace=Path(tmpdir),
                test_command="echo '1 passed'",
                enabled=True,
            )

            def task_fn():
                raise ValueError("Task failed")

            result = gate.execute_with_gate(task_fn)
            self.assertFalse(result.passed)
            self.assertIn("Task failed", result.error)


class TestConvenienceFunction(unittest.TestCase):
    """Tests for run_test_gate convenience function."""

    def test_test_gate_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            def task_fn():
                pass

            result = run_test_gate(
                workspace=Path(tmpdir),
                task_fn=task_fn,
                test_command="echo '1 passed'",
            )
            self.assertTrue(result.passed)


class TestConfigOptions(unittest.TestCase):
    """Tests for test gate config options."""

    def test_config_has_test_gate_options(self):
        from autobots.config import AutobotsConfig
        config = AutobotsConfig()
        self.assertFalse(config.test_gate)
        self.assertEqual(config.test_command, "pytest tests/ -q")
        self.assertEqual(config.test_timeout, 120)

    def test_config_loads_test_gate_from_file(self):
        import os
        import tomllib
        from autobots.config import AutobotsConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = """
[autobots]
test_gate = true
test_command = "pytest tests/ -v"
test_timeout = 180
"""
            config_path = Path(tmpdir) / ".autobots.toml"
            config_path.write_text(config_content)

            config = AutobotsConfig.load(Path(tmpdir))
            self.assertTrue(config.test_gate)
            self.assertEqual(config.test_command, "pytest tests/ -v")
            self.assertEqual(config.test_timeout, 180)

    def test_config_loads_test_gate_from_env(self):
        import os
        from autobots.config import AutobotsConfig

        os.environ["AUTOBOTS_TEST_GATE"] = "true"
        os.environ["AUTOBOTS_TEST_COMMAND"] = "npm test"
        os.environ["AUTOBOTS_TEST_TIMEOUT"] = "60"

        try:
            config = AutobotsConfig()
            config._load_from_env(config)
            self.assertTrue(config.test_gate)
            self.assertEqual(config.test_command, "npm test")
            self.assertEqual(config.test_timeout, 60)
        finally:
            del os.environ["AUTOBOTS_TEST_GATE"]
            del os.environ["AUTOBOTS_TEST_COMMAND"]
            del os.environ["AUTOBOTS_TEST_TIMEOUT"]

    def test_config_apply_env_vars(self):
        import os
        from autobots.config import AutobotsConfig

        config = AutobotsConfig()
        config.test_gate = True
        config.test_command = "go test ./..."
        config.test_timeout = 90

        config.apply_env_vars()

        self.assertEqual(os.environ.get("AUTOBOTS_TEST_GATE"), "1")
        self.assertEqual(os.environ.get("AUTOBOTS_TEST_COMMAND"), "go test ./...")
        self.assertEqual(os.environ.get("AUTOBOTS_TEST_TIMEOUT"), "90")


if __name__ == "__main__":
    unittest.main()
