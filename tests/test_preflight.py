"""Tests for autobots.preflight module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from autobots.preflight import (
    CheckStatus,
    PreflightCheck,
    PreflightResult,
    check_api_key_format,
    check_api_connectivity,
    check_config_valid,
    check_git_status,
    check_primary_model,
    check_workspace_writable,
    run_preflight,
)


class TestCheckApiKeyFormat(unittest.TestCase):
    """Tests for check_api_key_format function."""

    def test_empty_key_fails(self):
        result = check_api_key_format(None)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertEqual(result.name, "API key")
        self.assertIn("not set", result.message)

    def test_empty_string_fails(self):
        result = check_api_key_format("")
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("not set", result.message)

    def test_too_short_fails(self):
        result = check_api_key_format("short")
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("too short", result.message)

    def test_valid_nvapi_key_passes(self):
        # Uses clearly fake key format - never use real API keys in tests
        fake_key = "nvapi-0000000000000000"
        result = check_api_key_format(fake_key)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertIn("valid format", result.message)

    def test_unusual_format_warns(self):
        result = check_api_key_format("sk-something123456789")
        self.assertEqual(result.status, CheckStatus.WARN)
        self.assertIn("unusual format", result.message)

    def test_long_non_nvapi_key_warns(self):
        result = check_api_key_format("my-custom-api-key-1234567890")
        self.assertEqual(result.status, CheckStatus.WARN)
        self.assertIn("unusual format", result.message)


class TestCheckApiConnectivity(unittest.TestCase):
    """Tests for check_api_connectivity function."""

    def test_no_api_key_skips(self):
        result = check_api_connectivity(None)
        self.assertEqual(result.status, CheckStatus.SKIP)
        self.assertIn("skipped", result.message)

    @patch("openai.OpenAI")
    def test_successful_connection(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.return_value = MagicMock()

        result = check_api_connectivity("nvapi-test123456789")
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertIn("OK", result.message)
        self.assertIn("ms", result.message)

    @patch("openai.OpenAI")
    def test_401_error_fails(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.side_effect = Exception("401 Unauthorized")

        result = check_api_connectivity("nvapi-badkey")
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("authentication failed", result.message)

    @patch("openai.OpenAI")
    def test_connection_error_fails(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Connection timeout")

        result = check_api_connectivity("nvapi-test123456789")
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("connection failed", result.message)


class TestCheckPrimaryModel(unittest.TestCase):
    """Tests for check_primary_model function."""

    def test_no_api_key_skips(self):
        result = check_primary_model("model-id", None)
        self.assertEqual(result.status, CheckStatus.SKIP)

    def test_no_model_id_warns(self):
        result = check_primary_model(None, "nvapi-test123456789")
        self.assertEqual(result.status, CheckStatus.WARN)
        self.assertIn("not configured", result.message)

    @patch("openai.OpenAI")
    def test_responsive_model_passes(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OK"
        mock_client.chat.completions.create.return_value = mock_response

        result = check_primary_model("qwen3-coder-480b", "nvapi-test123456789")
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertIn("responsive", result.message)

    @patch("openai.OpenAI")
    def test_404_model_not_found(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("404 Model not found")

        result = check_primary_model("nonexistent-model", "nvapi-test123456789")
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("not found", result.message)


class TestCheckWorkspaceWritable(unittest.TestCase):
    """Tests for check_workspace_writable function."""

    def test_no_workspace_warns(self):
        result = check_workspace_writable(None)
        self.assertEqual(result.status, CheckStatus.WARN)
        self.assertIn("not specified", result.message)

    def test_nonexistent_workspace_fails(self):
        result = check_workspace_writable(Path("/nonexistent/path"))
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("not found", result.message)

    def test_file_not_directory_fails(self):
        with tempfile.NamedTemporaryFile() as tmp:
            result = check_workspace_writable(Path(tmp.name))
            self.assertEqual(result.status, CheckStatus.FAIL)
            self.assertIn("not a directory", result.message)

    def test_writable_directory_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_workspace_writable(Path(tmpdir))
            self.assertEqual(result.status, CheckStatus.PASS)
            self.assertIn("writable", result.message)


class TestCheckConfigValid(unittest.TestCase):
    """Tests for check_config_valid function."""

    def test_valid_config_passes(self):
        config = MagicMock()
        config.model_selection_profile = "balanced"
        config.default_mode = "supervised"
        config.milestone_threshold = 3
        config.max_verification_attempts = 3

        result = check_config_valid(config)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertIn("valid", result.message)

    def test_invalid_profile_fails(self):
        config = MagicMock()
        config.model_selection_profile = "invalid_profile"
        config.default_mode = "supervised"
        config.milestone_threshold = 3
        config.max_verification_attempts = 3

        result = check_config_valid(config)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("model_selection_profile", result.details)

    def test_invalid_mode_fails(self):
        config = MagicMock()
        config.model_selection_profile = "balanced"
        config.default_mode = "invalid_mode"
        config.milestone_threshold = 3
        config.max_verification_attempts = 3

        result = check_config_valid(config)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("default_mode", result.details)

    def test_invalid_threshold_fails(self):
        config = MagicMock()
        config.model_selection_profile = "balanced"
        config.default_mode = "supervised"
        config.milestone_threshold = 0
        config.max_verification_attempts = 3

        result = check_config_valid(config)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("milestone_threshold", result.details)

    def test_config_file_name_shown(self):
        config = MagicMock()
        config.model_selection_profile = "balanced"
        config.default_mode = "supervised"
        config.milestone_threshold = 3
        config.max_verification_attempts = 3

        config_file = Path("custom.toml")
        result = check_config_valid(config, config_file)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertIn("custom.toml", result.message)


class TestCheckGitStatus(unittest.TestCase):
    """Tests for check_git_status function."""

    def test_no_workspace_skips(self):
        result = check_git_status(None)
        self.assertEqual(result.status, CheckStatus.SKIP)

    def test_non_git_repo_skips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_git_status(Path(tmpdir))
            self.assertEqual(result.status, CheckStatus.SKIP)
            self.assertIn("not a git repo", result.message)

    @patch("autobots.preflight.subprocess")
    def test_clean_git_tree_passes(self, mock_subprocess):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_subprocess.run.return_value = mock_result

            result = check_git_status(Path(tmpdir))
            self.assertEqual(result.status, CheckStatus.PASS)
            self.assertIn("clean", result.message)

    @patch("autobots.preflight.subprocess")
    def test_uncommitted_changes_warns(self, mock_subprocess):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = " M src/main.py\n?? new_file.txt"
            mock_subprocess.run.return_value = mock_result

            result = check_git_status(Path(tmpdir))
            self.assertEqual(result.status, CheckStatus.WARN)
            self.assertIn("uncommitted", result.message)
            self.assertIn("2", result.message)


class TestPreflightResult(unittest.TestCase):
    """Tests for PreflightResult class."""

    def test_all_passed_true_when_all_pass(self):
        checks = [
            PreflightCheck(name="A", status=CheckStatus.PASS, message="ok"),
            PreflightCheck(name="B", status=CheckStatus.SKIP, message="skipped"),
        ]
        result = PreflightResult(checks=checks)
        self.assertTrue(result.all_passed)

    def test_all_passed_false_when_any_fail(self):
        checks = [
            PreflightCheck(name="A", status=CheckStatus.PASS, message="ok"),
            PreflightCheck(name="B", status=CheckStatus.FAIL, message="failed"),
        ]
        result = PreflightResult(checks=checks)
        self.assertFalse(result.all_passed)

    def test_failed_checks_returns_failures(self):
        checks = [
            PreflightCheck(name="A", status=CheckStatus.PASS, message="ok"),
            PreflightCheck(name="B", status=CheckStatus.FAIL, message="failed"),
            PreflightCheck(name="C", status=CheckStatus.WARN, message="warned"),
            PreflightCheck(name="D", status=CheckStatus.FAIL, message="failed again"),
        ]
        result = PreflightResult(checks=checks)
        self.assertEqual(len(result.failed_checks), 2)
        self.assertEqual(result.failed_checks[0].name, "B")
        self.assertEqual(result.failed_checks[1].name, "D")


class TestRunPreflight(unittest.TestCase):
    """Tests for run_preflight function."""

    def test_run_preflight_returns_result(self):
        result = run_preflight(
            api_key=None,
            workspace=None,
            config=MagicMock(
                model_selection_profile="balanced",
                default_mode="supervised",
                milestone_threshold=3,
                max_verification_attempts=3,
            ),
            skip_model_check=True,
        )
        self.assertIsInstance(result, PreflightResult)
        self.assertGreater(len(result.checks), 0)

    def test_run_preflight_includes_all_checks(self):
        result = run_preflight(
            api_key=None,
            workspace=None,
            config=MagicMock(
                model_selection_profile="balanced",
                default_mode="supervised",
                milestone_threshold=3,
                max_verification_attempts=3,
            ),
            skip_model_check=False,
        )
        check_names = [c.name for c in result.checks]
        self.assertIn("API key", check_names)
        self.assertIn("API connection", check_names)
        self.assertIn("Primary model", check_names)
        self.assertIn("Workspace", check_names)
        self.assertIn("Config", check_names)
        self.assertIn("Git", check_names)


if __name__ == "__main__":
    unittest.main()
