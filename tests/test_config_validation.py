"""Tests for config validation."""

import shutil
import tempfile
import unittest
from pathlib import Path

from autobots.config import (
    AutobotsConfig,
    ConfigValidationError,
    ConfigValidationResult,
    VALID_EXECUTION_MODES,
    VALID_MODEL_PROFILES,
)


class TestConfigValidation(unittest.TestCase):
    """Tests for configuration validation."""

    def test_valid_config_passes(self):
        config = AutobotsConfig()
        result = config.validate()
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_invalid_model_selection_profile(self):
        config = AutobotsConfig(model_selection_profile="invalid")
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("model_selection_profile", result.errors[0]["field"])

    def test_invalid_default_mode(self):
        config = AutobotsConfig(default_mode="invalid")
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("default_mode", result.errors[0]["field"])

    def test_milestone_threshold_too_low(self):
        config = AutobotsConfig(milestone_threshold=0)
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertIn("milestone_threshold", result.errors[0]["field"])

    def test_max_verification_attempts_too_low(self):
        config = AutobotsConfig(max_verification_attempts=0)
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertIn("max_verification_attempts", result.errors[0]["field"])

    def test_test_timeout_too_low(self):
        config = AutobotsConfig(test_timeout=5)
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertIn("test_timeout", result.errors[0]["field"])

    def test_empty_safety_branch(self):
        config = AutobotsConfig(safety_branch="")
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertIn("safety_branch", result.errors[0]["field"])

    def test_whitespace_safety_branch(self):
        config = AutobotsConfig(safety_branch="   ")
        result = config.validate()
        self.assertFalse(result.valid)

    def test_missing_model_registry_warns(self):
        config = AutobotsConfig(model_registry_path="/nonexistent/path.json")
        result = config.validate()
        self.assertTrue(result.valid)  # Valid but with warnings
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("model_registry_path", result.warnings[0]["field"])

    def test_auto_commit_missing_placeholder_warns(self):
        config = AutobotsConfig(auto_commit_message_template="commit without placeholder")
        result = config.validate()
        self.assertTrue(result.valid)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("auto_commit_message_template", result.warnings[0]["field"])

    def test_multiple_errors(self):
        config = AutobotsConfig(
            model_selection_profile="bad",
            default_mode="bad",
            milestone_threshold=0,
        )
        result = config.validate()
        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.errors), 3)

    def test_result_to_dict(self):
        result = ConfigValidationResult(
            valid=True,
            warnings=[{"field": "test", "message": "warning"}],
        )
        d = result.to_dict()
        self.assertTrue(d["valid"])
        self.assertEqual(len(d["warnings"]), 1)


class TestValidValues(unittest.TestCase):
    """Tests for valid value sets."""

    def test_valid_model_profiles(self):
        self.assertIn("balanced", VALID_MODEL_PROFILES)
        self.assertIn("speed", VALID_MODEL_PROFILES)
        self.assertIn("quality", VALID_MODEL_PROFILES)

    def test_valid_execution_modes(self):
        self.assertIn("supervised", VALID_EXECUTION_MODES)
        self.assertIn("milestone", VALID_EXECUTION_MODES)
        self.assertIn("autonomous", VALID_EXECUTION_MODES)


class TestConfigError(unittest.TestCase):
    """Tests for ConfigValidationError."""

    def test_error_message(self):
        errors = [
            {"field": "test_field", "message": "bad value", "suggestion": "use good value"}
        ]
        exc = ConfigValidationError(errors)
        self.assertIn("test_field", str(exc))
        self.assertIn("bad value", str(exc))
        self.assertIn("use good value", str(exc))

    def test_error_without_suggestion(self):
        errors = [
            {"field": "field", "message": "error"}
        ]
        exc = ConfigValidationError(errors)
        self.assertIn("field", str(exc))


if __name__ == "__main__":
    unittest.main()
