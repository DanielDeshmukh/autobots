"""Tests for autobots.errors module."""

import unittest
from io import StringIO

from rich.console import Console

from autobots.errors import (
    APIError,
    AutobotsError,
    ConfigError,
    ModelError,
    PreflightError,
    WorkspaceError,
    config_invalid,
    git_clean_tree_required,
    lock_acquisition_failed,
    model_auth_failure,
    model_invalid_response,
    model_json_truncation,
    model_not_found,
    model_timeout,
    no_pending_phases,
    phase_not_found,
    plan_not_found,
    preflight_failed,
    render_error,
    render_warning,
    rollback_failed,
    safety_branch_required,
    task_not_found,
    workspace_not_found,
    workspace_not_writable,
)


class TestAutobotsError(unittest.TestCase):
    """Tests for base AutobotsError class."""

    def test_basic_error(self):
        error = AutobotsError(message="Test error", reason="Test reason")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.reason, "Test reason")
        self.assertEqual(error.suggestions, [])
        self.assertEqual(error.exit_code, 1)

    def test_error_with_suggestions(self):
        suggestions = ["Suggestion 1", "Suggestion 2"]
        error = AutobotsError(
            message="Test error",
            reason="Test reason",
            suggestions=suggestions,
        )
        self.assertEqual(error.suggestions, suggestions)

    def test_error_str_representation(self):
        error = AutobotsError(
            message="Test error",
            reason="Test reason",
            suggestions=["Try this", "Try that"],
        )
        error_str = str(error)
        self.assertIn("Test error", error_str)
        self.assertIn("Why: Test reason", error_str)
        self.assertIn("1. Try this", error_str)
        self.assertIn("2. Try that", error_str)

    def test_error_inherits_exception(self):
        error = AutobotsError(message="Test", reason="Test")
        self.assertIsInstance(error, Exception)

    def test_error_can_be_raised_and_caught(self):
        with self.assertRaises(AutobotsError):
            raise AutobotsError(message="Test", reason="Test")


class TestSpecificErrorTypes(unittest.TestCase):
    """Tests for specific error type classes."""

    def test_model_error(self):
        error = ModelError(
            message="Model failed",
            reason="Timeout",
            model_id="test-model",
            stage="specialist",
        )
        self.assertIsInstance(error, AutobotsError)
        self.assertEqual(error.model_id, "test-model")
        self.assertEqual(error.stage, "specialist")

    def test_config_error(self):
        error = ConfigError(
            message="Config invalid",
            reason="Bad value",
            config_path="/path/to/config",
        )
        self.assertIsInstance(error, AutobotsError)
        self.assertEqual(error.config_path, "/path/to/config")

    def test_workspace_error(self):
        error = WorkspaceError(
            message="Workspace error",
            reason="Not found",
            path="/path/to/workspace",
        )
        self.assertIsInstance(error, AutobotsError)
        self.assertEqual(error.path, "/path/to/workspace")

    def test_api_error(self):
        error = APIError(
            message="API error",
            reason="Unauthorized",
            status_code=401,
            base_url="https://api.example.com",
        )
        self.assertIsInstance(error, AutobotsError)
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.base_url, "https://api.example.com")

    def test_preflight_error(self):
        error = PreflightError(
            message="Preflight failed",
            reason="Checks failed",
            failed_checks=["API key", "Git status"],
        )
        self.assertIsInstance(error, AutobotsError)
        self.assertEqual(error.failed_checks, ["API key", "Git status"])


class TestRenderError(unittest.TestCase):
    """Tests for render_error function."""

    def test_render_error_to_console(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        error = AutobotsError(
            message="Test error",
            reason="Test reason",
            suggestions=["Try this"],
        )
        render_error(error, console)
        output_text = output.getvalue()
        self.assertIn("Test error", output_text)
        self.assertIn("Test reason", output_text)
        self.assertIn("Try this", output_text)

    def test_render_error_creates_console_if_none(self):
        error = AutobotsError(message="Test", reason="Test")
        render_error(error)


class TestRenderWarning(unittest.TestCase):
    """Tests for render_warning function."""

    def test_render_warning_to_console(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        render_warning("Test warning", "Details here", console)
        output_text = output.getvalue()
        self.assertIn("Test warning", output_text)
        self.assertIn("Details here", output_text)

    def test_render_warning_creates_console_if_none(self):
        render_warning("Test warning")


class TestFactoryFunctions(unittest.TestCase):
    """Tests for error factory functions."""

    def test_model_json_truncation(self):
        error = model_json_truncation(model_id="test-model", max_tokens=1024)
        self.assertIsInstance(error, ModelError)
        self.assertEqual(error.model_id, "test-model")
        self.assertIn("invalid JSON", error.message)
        self.assertIn("max_tokens", error.reason)
        self.assertGreater(len(error.suggestions), 0)

    def test_model_json_truncation_without_max_tokens(self):
        error = model_json_truncation()
        self.assertIn("max_tokens", error.reason)

    def test_model_invalid_response(self):
        error = model_invalid_response(
            model_id="test-model",
            response_preview="invalid json...",
        )
        self.assertIsInstance(error, ModelError)
        self.assertIn("invalid response", error.message.lower())
        self.assertIn("invalid json...", error.reason)

    def test_model_timeout(self):
        error = model_timeout(model_id="test-model", timeout_seconds=60)
        self.assertIsInstance(error, ModelError)
        self.assertIn("60s", error.message)

    def test_model_auth_failure(self):
        error = model_auth_failure()
        self.assertIsInstance(error, APIError)
        self.assertEqual(error.status_code, 401)
        self.assertIn("authentication", error.message.lower())

    def test_model_not_found(self):
        error = model_not_found(model_id="missing-model")
        self.assertIsInstance(error, ModelError)
        self.assertIn("missing-model", error.message)

    def test_config_invalid(self):
        error = config_invalid(profile="invalid", mode="bad")
        self.assertIsInstance(error, ConfigError)
        self.assertIn("invalid", error.message.lower())

    def test_workspace_not_found(self):
        error = workspace_not_found(path="/missing/path")
        self.assertIsInstance(error, WorkspaceError)
        self.assertIn("/missing/path", error.message)

    def test_workspace_not_writable(self):
        error = workspace_not_writable(path="/readonly/path")
        self.assertIsInstance(error, WorkspaceError)
        self.assertIn("/readonly/path", error.message)

    def test_git_clean_tree_required(self):
        error = git_clean_tree_required()
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("uncommitted changes", error.message.lower())

    def test_safety_branch_required(self):
        error = safety_branch_required(branch="my-safety-branch")
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("my-safety-branch", error.message)

    def test_preflight_failed(self):
        error = preflight_failed(failed_checks=["API key", "Git"])
        self.assertIsInstance(error, PreflightError)
        self.assertEqual(error.failed_checks, ["API key", "Git"])

    def test_task_not_found(self):
        error = task_not_found(task_id="P1-T99")
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("P1-T99", error.message)

    def test_phase_not_found_with_id(self):
        error = phase_not_found(phase_id="P99")
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("P99", error.message)

    def test_phase_not_found_without_id(self):
        error = phase_not_found()
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("No phases found", error.message)

    def test_lock_acquisition_failed(self):
        error = lock_acquisition_failed(resource="architecture.md")
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("architecture.md", error.message)

    def test_rollback_failed(self):
        error = rollback_failed(snapshot_id="snap_123")
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("snap_123", error.message)

    def test_rollback_failed_with_reason(self):
        error = rollback_failed(snapshot_id="snap_123", reason="Corrupted")
        self.assertIn("Corrupted", error.reason)

    def test_no_pending_phases(self):
        error = no_pending_phases()
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("No pending phases", error.message)

    def test_plan_not_found(self):
        error = plan_not_found()
        self.assertIsInstance(error, AutobotsError)
        self.assertIn("No plan found", error.message)


class TestErrorSuggestions(unittest.TestCase):
    """Tests to verify all factory functions provide helpful suggestions."""

    def test_all_errors_have_suggestions(self):
        errors = [
            model_json_truncation(),
            model_invalid_response(),
            model_timeout(),
            model_auth_failure(),
            model_not_found(),
            config_invalid(),
            workspace_not_found("/test"),
            workspace_not_writable("/test"),
            git_clean_tree_required(),
            safety_branch_required(),
            preflight_failed(["test"]),
            task_not_found("P1-T1"),
            phase_not_found(),
            lock_acquisition_failed("test"),
            rollback_failed("test"),
            no_pending_phases(),
            plan_not_found(),
        ]
        for error in errors:
            self.assertGreater(
                len(error.suggestions),
                0,
                f"{type(error).__name__} should have suggestions",
            )


if __name__ == "__main__":
    unittest.main()
