"""Tests for autobots.onboarding module."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from autobots.onboarding import (
    _get_or_prompt_api_key,
    _save_api_key_to_env,
    _scaffold_context_files,
    _write_config,
    check_and_prompt_api_key,
    run_onboarding_wizard,
)


class TestGetOrPromptApiKey(unittest.TestCase):
    """Tests for _get_or_prompt_api_key function."""

    def setUp(self):
        # Ensure clean state for each test
        os.environ.pop("NVIDIA_API_KEY", None)

    def test_returns_env_key_if_exists(self):
        os.environ["NVIDIA_API_KEY"] = "test-key-from-env"
        try:
            console = MagicMock()
            result = _get_or_prompt_api_key(console)
            self.assertEqual(result, "test-key-from-env")
        finally:
            del os.environ["NVIDIA_API_KEY"]

    def test_skips_prompt_when_env_key_exists(self):
        # Test that when env key exists, it returns without prompting
        os.environ["NVIDIA_API_KEY"] = "env-key"
        try:
            console = MagicMock()
            result = _get_or_prompt_api_key(console)
            self.assertEqual(result, "env-key")
            # Console should print the found message
            console.print.assert_called()
        finally:
            del os.environ["NVIDIA_API_KEY"]


class TestSaveApiKeyToEnv(unittest.TestCase):
    """Tests for _save_api_key_to_env function."""

    def test_saves_key_to_env_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            console = MagicMock()

            with patch("autobots.cli.ENGINE_ENV_PATH", env_path):
                _save_api_key_to_env("test-api-key", console)

            content = env_path.read_text()
            self.assertIn("NVIDIA_API_KEY=test-api-key", content)

    def test_updates_existing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("NVIDIA_API_KEY=old-key\nOTHER_VAR=value\n")
            console = MagicMock()

            with patch("autobots.cli.ENGINE_ENV_PATH", env_path):
                _save_api_key_to_env("new-api-key", console)

            content = env_path.read_text()
            self.assertIn("NVIDIA_API_KEY=new-api-key", content)
            self.assertNotIn("old-key", content)
            self.assertIn("OTHER_VAR=value", content)


class TestWriteConfig(unittest.TestCase):
    """Tests for _write_config function."""

    def test_creates_autobots_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            console = MagicMock()

            _write_config(
                target_root,
                "test-project",
                "Python,JavaScript",
                "pytest",
                "test-api-key",
                console,
            )

            config_path = target_root / ".autobots.toml"
            self.assertTrue(config_path.exists())

            content = config_path.read_text()
            self.assertIn("test-project", content)
            self.assertIn("pytest", content)
            # API key is stored in .env, not in TOML
            self.assertNotIn("test-api-key", content)
            self.assertIn("NVIDIA API key is stored in .env", content)

    def test_creates_config_without_api_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            console = MagicMock()

            _write_config(
                target_root,
                "test-project",
                "Python",
                "pytest",
                None,
                console,
            )

            config_path = target_root / ".autobots.toml"
            self.assertTrue(config_path.exists())

            content = config_path.read_text()
            self.assertIn("test-project", content)
            # API key note is always present (stored in .env)
            self.assertIn("NVIDIA API key is stored in .env", content)


class TestScaffoldContextFiles(unittest.TestCase):
    """Tests for _scaffold_context_files function."""

    def test_creates_context_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            console = MagicMock()

            _scaffold_context_files(
                target_root,
                "test-project",
                "Python",
                "pytest",
                console,
            )

            context_dir = target_root / "context"
            self.assertTrue(context_dir.exists())

            expected_files = [
                "architecture.md",
                "conventions.md",
                "testing-strategy.md",
                "security-auth.md",
                "roadmap.md",
            ]
            for filename in expected_files:
                file_path = context_dir / filename
                self.assertTrue(file_path.exists(), f"{filename} should exist")

    def test_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            context_dir = target_root / "context"
            context_dir.mkdir()
            existing_file = context_dir / "architecture.md"
            existing_file.write_text("Existing content")
            console = MagicMock()

            _scaffold_context_files(
                target_root,
                "test-project",
                "Python",
                "pytest",
                console,
            )

            # Should not overwrite
            content = existing_file.read_text()
            self.assertEqual(content, "Existing content")


class TestCheckAndPromptApiKey(unittest.TestCase):
    """Tests for check_and_prompt_api_key function."""

    def test_returns_env_key(self):
        os.environ["NVIDIA_API_KEY"] = "env-key"
        try:
            console = MagicMock()
            result = check_and_prompt_api_key(Path("."), console)
            self.assertEqual(result, "env-key")
        finally:
            del os.environ["NVIDIA_API_KEY"]

    @patch("autobots.onboarding.Prompt")
    def test_prompts_if_force_prompt(self, mock_prompt):
        mock_prompt.ask.return_value = "forced-key"
        os.environ["NVIDIA_API_KEY"] = "env-key"
        try:
            console = MagicMock()
            result = check_and_prompt_api_key(Path("."), console, force_prompt=True)
            self.assertEqual(result, "forced-key")
        finally:
            del os.environ["NVIDIA_API_KEY"]

    def test_checks_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            config_path = target_root / ".autobots.toml"
            config_path.write_text('[autobots]\napi_key = "config-key"\n')

            os.environ.pop("NVIDIA_API_KEY", None)
            console = MagicMock()

            # Mock the ENGINE_ENV_PATH to be nonexistent so it falls through to config
            with patch("autobots.onboarding.Path") as mock_path:
                mock_path.return_value = Path("/nonexistent")
                result = check_and_prompt_api_key(target_root, console)

            # The function should find the config key
            self.assertIsNotNone(result)


class TestRunOnboardingWizard(unittest.TestCase):
    """Tests for run_onboarding_wizard function."""

    @patch("autobots.onboarding.Confirm")
    @patch("autobots.onboarding.Prompt")
    def test_wizard_creates_config_and_files(self, mock_prompt, mock_confirm):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            console = MagicMock()

            # Mock prompts
            mock_prompt.ask.side_effect = [
                "test-project",  # project_name
                "Python",        # languages
                "pytest",        # test_framework
                "test-key",      # api_key
            ]
            mock_confirm.ask.return_value = True

            result = run_onboarding_wizard(target_root, console, skip_api_key=False)

            self.assertTrue(result)
            self.assertTrue((target_root / ".autobots.toml").exists())
            self.assertTrue((target_root / "context").exists())

    @patch("autobots.onboarding.Confirm")
    @patch("autobots.onboarding.Prompt")
    def test_wizard_cancels_if_not_confirmed(self, mock_prompt, mock_confirm):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_root = Path(tmpdir)
            console = MagicMock()

            # Mock prompts - need to provide all prompts before cancel
            mock_prompt.ask.side_effect = [
                "test-project",  # project_name
                "Python",        # languages
                "pytest",        # test_framework
            ]
            mock_confirm.ask.return_value = False

            result = run_onboarding_wizard(target_root, console, skip_api_key=True)

            self.assertFalse(result)
            self.assertFalse((target_root / ".autobots.toml").exists())


if __name__ == "__main__":
    unittest.main()
