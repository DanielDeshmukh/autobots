"""Test gate for validating changes before committing."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..errors import AutobotsError


@dataclass
class TestResult:
    """Result of running the test suite."""
    passed: bool
    total_tests: int
    failures: int
    errors: int
    duration_seconds: float
    output: str = ""


@dataclass
class GateResult:
    """Result of the test gate check."""
    passed: bool
    tests_before: TestResult | None = None
    tests_after: TestResult | None = None
    new_failures: int = 0
    rolled_back: bool = False
    error: str | None = None


def run_test_suite(
    workspace: Path,
    test_command: str = "pytest tests/ -q",
    timeout: int = 120,
) -> TestResult:
    """Run the test suite and return results.

    Args:
        workspace: Path to the target project
        test_command: Command to run tests
        timeout: Timeout in seconds

    Returns:
        TestResult with pass/fail status and counts
    """
    start_time = time.time()

    try:
        result = subprocess.run(
            test_command,
            cwd=workspace,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        duration = time.time() - start_time
        output = result.stdout + "\n" + result.stderr

        # Parse pytest output for counts
        failures = 0
        errors = 0
        total_tests = 0

        # Look for pytest summary line: "X passed, Y failed, Z errors"
        for line in output.splitlines():
            line = line.strip().lower()
            if "passed" in line or "failed" in line or "error" in line:
                # Try to extract numbers from pytest summary
                import re
                passed_match = re.search(r"(\d+)\s+passed", line)
                failed_match = re.search(r"(\d+)\s+failed", line)
                error_match = re.search(r"(\d+)\s+error", line)

                if passed_match:
                    total_tests += int(passed_match.group(1))
                if failed_match:
                    failures = int(failed_match.group(1))
                    total_tests += failures
                if error_match:
                    errors = int(error_match.group(1))
                    total_tests += errors

        passed = result.returncode == 0 and failures == 0 and errors == 0

        return TestResult(
            passed=passed,
            total_tests=total_tests,
            failures=failures,
            errors=errors,
            duration_seconds=duration,
            output=output,
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            passed=False,
            total_tests=0,
            failures=0,
            errors=1,
            duration_seconds=timeout,
            output=f"Test suite timed out after {timeout}s",
        )
    except Exception as e:
        return TestResult(
            passed=False,
            total_tests=0,
            failures=0,
            errors=1,
            duration_seconds=time.time() - start_time,
            output=f"Failed to run tests: {str(e)}",
        )


class TestGate:
    """Test gate that validates changes don't break existing tests.

    The gate runs tests before and after changes. If new failures are
    introduced, it triggers rollback and reports the issue.
    """

    def __init__(
        self,
        workspace: Path,
        test_command: str = "pytest tests/ -q",
        test_timeout: int = 120,
        enabled: bool = True,
    ):
        self.workspace = workspace
        self.test_command = test_command
        self.test_timeout = test_timeout
        self.enabled = enabled
        self._tests_before: TestResult | None = None

    def pre_execution(self) -> TestResult:
        """Run tests before executing changes."""
        if not self.enabled:
            return TestResult(
                passed=True,
                total_tests=0,
                failures=0,
                errors=0,
                duration_seconds=0,
                output="Test gate disabled",
            )

        self._tests_before = run_test_suite(
            self.workspace,
            self.test_command,
            self.test_timeout,
        )
        return self._tests_before

    def post_execution(self, snapshot_id: str | None = None) -> GateResult:
        """Run tests after executing changes and compare with pre-execution results.

        Args:
            snapshot_id: Optional snapshot ID to rollback to if tests fail

        Returns:
            GateResult with pass/fail status and rollback info
        """
        if not self.enabled:
            return GateResult(passed=True)

        tests_after = run_test_suite(
            self.workspace,
            self.test_command,
            self.test_timeout,
        )

        # Compare with pre-execution results
        new_failures = 0
        if self._tests_before:
            # Count new failures (failures that weren't there before)
            new_failures = max(0, tests_after.failures - self._tests_before.failures)
            new_failures += max(0, tests_after.errors - self._tests_before.errors)

        passed = tests_after.passed and new_failures == 0

        # Rollback if we have a snapshot and tests failed
        rolled_back = False
        if not passed and snapshot_id:
            try:
                from .state import RollbackManager
                manager = RollbackManager(self.workspace)
                manager.rollback(snapshot_id)
                rolled_back = True
            except Exception:
                pass

        return GateResult(
            passed=passed,
            tests_before=self._tests_before,
            tests_after=tests_after,
            new_failures=new_failures,
            rolled_back=rolled_back,
        )

    def execute_with_gate(
        self,
        task_fn: Callable[[], None],
        snapshot_id: str | None = None,
    ) -> GateResult:
        """Execute a task function with test gate validation.

        Args:
            task_fn: Function that makes changes to the workspace
            snapshot_id: Optional snapshot ID for rollback

        Returns:
            GateResult with pass/fail status
        """
        # Run tests before
        self.pre_execution()

        # Execute the task
        try:
            task_fn()
        except Exception as e:
            return GateResult(
                passed=False,
                tests_before=self._tests_before,
                error=str(e),
            )

        # Run tests after
        return self.post_execution(snapshot_id)


def run_test_gate(
    workspace: Path,
    task_fn: Callable[[], None],
    test_command: str = "pytest tests/ -q",
    test_timeout: int = 120,
    snapshot_id: str | None = None,
) -> GateResult:
    """Convenience function to run a task with test gate validation.

    Args:
        workspace: Path to the target project
        task_fn: Function that makes changes to the workspace
        test_command: Command to run tests
        test_timeout: Timeout in seconds
        snapshot_id: Optional snapshot ID for rollback

    Returns:
        GateResult with pass/fail status
    """
    gate = TestGate(
        workspace=workspace,
        test_command=test_command,
        test_timeout=test_timeout,
    )
    return gate.execute_with_gate(task_fn, snapshot_id)
