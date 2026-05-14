"""Tests for Phase 9 configuration management."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autobots.config import AutobotsConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_config_loads_defaults(self) -> None:
        config = AutobotsConfig()
        self.assertEqual(config.model_selection_profile, "balanced")
        self.assertEqual(config.safety_branch, "autobots-safety")
        self.assertEqual(config.default_mode, "supervised")
        self.assertEqual(config.milestone_threshold, 3)

    def test_config_loads_from_env(self) -> None:
        env_vars = {
            "AUTOBOTS_MODEL_SELECTION_PROFILE": "speed",
            "AUTOBOTS_SAFETY_BRANCH": "custom-branch",
            "AUTOBOTS_DEFAULT_MODE": "autonomous",
            "AUTOBOTS_MILESTONE_THRESHOLD": "5",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = AutobotsConfig.load()
            self.assertEqual(config.model_selection_profile, "speed")
            self.assertEqual(config.safety_branch, "custom-branch")
            self.assertEqual(config.default_mode, "autonomous")
            self.assertEqual(config.milestone_threshold, 5)

    def test_config_loads_parallel_planning_from_env(self) -> None:
        with patch.dict(os.environ, {"AUTOBOTS_ENABLE_PARALLEL_PLANNING": "1"}):
            config = AutobotsConfig.load()
            self.assertTrue(config.parallel_planning)

    def test_config_loads_disable_live_catalog_from_env(self) -> None:
        with patch.dict(os.environ, {"AUTOBOTS_DISABLE_LIVE_CATALOG": "true"}):
            config = AutobotsConfig.load()
            self.assertTrue(config.disable_live_catalog)

    def test_config_applies_env_vars(self) -> None:
        config = AutobotsConfig()
        config.model_selection_profile = "quality"
        config.safety_branch = "test-branch"
        config.parallel_planning = True
        config.apply_env_vars()

        self.assertEqual(os.getenv("AUTOBOTS_MODEL_SELECTION_PROFILE"), "quality")
        self.assertEqual(os.getenv("AUTOBOTS_SAFETY_BRANCH"), "test-branch")
        self.assertEqual(os.getenv("AUTOBOTS_ENABLE_PARALLEL_PLANNING"), "1")

    def test_load_config_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".autobots.toml"
            config_path.write_text("""[autobots]
model_selection_profile = "speed"
safety_branch = "custom-branch"
milestone_threshold = 4
""")

            env_to_clear = [
                "AUTOBOTS_MODEL_SELECTION_PROFILE",
                "AUTOBOTS_SAFETY_BRANCH",
                "AUTOBOTS_MILESTONE_THRESHOLD",
            ]
            old_env = {k: os.environ.get(k) for k in env_to_clear}
            try:
                for k in env_to_clear:
                    os.environ.pop(k, None)
                config = load_config(Path(tmpdir))
                self.assertEqual(config.model_selection_profile, "speed")
                self.assertEqual(config.safety_branch, "custom-branch")
                self.assertEqual(config.milestone_threshold, 4)
            finally:
                for k, v in old_env.items():
                    if v is not None:
                        os.environ[k] = v

    def test_config_with_extra_clusters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".autobots.toml"
            config_path.write_text("""[autobots]
[autobots.extra_clusters]
CustomCluster = ["model1", "model2"]
""")

            env_to_clear = ["AUTOBOTS_MODEL_SELECTION_PROFILE"]
            old_env = {k: os.environ.get(k) for k in env_to_clear}
            try:
                for k in env_to_clear:
                    os.environ.pop(k, None)
                config = load_config(Path(tmpdir))
                self.assertEqual(config.extra_clusters.get("CustomCluster"), ["model1", "model2"])
            finally:
                for k, v in old_env.items():
                    if v is not None:
                        os.environ[k] = v

    def test_config_priority_env_over_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".autobots.toml"
            config_path.write_text("""[autobots]
model_selection_profile = "quality"
""")

            env_to_clear = ["AUTOBOTS_MODEL_SELECTION_PROFILE"]
            old_env = {k: os.environ.get(k) for k in env_to_clear}
            try:
                for k in env_to_clear:
                    os.environ.pop(k, None)
                with patch.dict(os.environ, {"AUTOBOTS_MODEL_SELECTION_PROFILE": "speed"}):
                    config = load_config(Path(tmpdir))
                    self.assertEqual(config.model_selection_profile, "speed")
            finally:
                for k, v in old_env.items():
                    if v is not None:
                        os.environ[k] = v


if __name__ == "__main__":
    unittest.main()