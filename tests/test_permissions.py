"""Unit tests for autobots.permissions package."""
import json
import tempfile
import shutil
import unittest
from pathlib import Path

from autobots.tools.permissions import PermissionConfig, PermissionChecker, Permission, PermissionRule
from autobots.permissions.settings import PermissionSettings, load_settings
from autobots.permissions.logging import PermissionLogger


class TestPermissionSettings(unittest.TestCase):
    def test_merged_empty(self):
        s = PermissionSettings()
        config = s.merged()
        self.assertEqual(config.default, Permission.ASK)

    def test_merged_project_overrides_global(self):
        global_cfg = PermissionConfig(
            rules=[PermissionRule("Read", Permission.ALLOW)],
            default=Permission.ALLOW,
        )
        project_cfg = PermissionConfig(
            rules=[PermissionRule("Read", Permission.DENY)],
        )
        s = PermissionSettings(global_config=global_cfg, project_config=project_cfg)
        merged = s.merged()
        self.assertEqual(merged.check("Read"), Permission.DENY)

    def test_merged_env_allowed(self):
        s = PermissionSettings(env_allowed=["Read"])
        merged = s.merged()
        self.assertEqual(merged.check("Read"), Permission.ALLOW)

    def test_merged_env_denied(self):
        s = PermissionSettings(env_denied=["Write"])
        merged = s.merged()
        self.assertEqual(merged.check("Write"), Permission.DENY)


class TestLoadSettings(unittest.TestCase):
    def test_load_no_files(self):
        tmp = tempfile.mkdtemp()
        try:
            settings = load_settings(tmp)
            self.assertIsInstance(settings, PermissionSettings)
        finally:
            shutil.rmtree(tmp)

    def test_load_global_settings(self):
        tmp = tempfile.mkdtemp()
        try:
            global_dir = Path(tmp) / ".autobots"
            global_dir.mkdir()
            (global_dir / "settings.json").write_text(json.dumps({
                "permissions": {
                    "default": "allow",
                    "rules": [{"tool_pattern": "Read", "permission": "allow"}],
                }
            }))
            home_original = Path.home()
            import autobots.permissions.settings as mod
            original_fn = mod.Path.home
            mod.Path.home = lambda: Path(tmp)
            try:
                settings = load_settings()
                merged = settings.merged()
                self.assertEqual(merged.check("Read"), Permission.ALLOW)
            finally:
                mod.Path.home = original_fn
        finally:
            shutil.rmtree(tmp)

    def test_load_project_settings(self):
        tmp = tempfile.mkdtemp()
        try:
            proj_dir = Path(tmp) / "project"
            proj_dir.mkdir()
            settings_dir = proj_dir / ".autobots"
            settings_dir.mkdir()
            (settings_dir / "settings.json").write_text(json.dumps({
                "permissions": {
                    "rules": [{"tool_pattern": "Write", "permission": "deny"}],
                }
            }))
            settings = load_settings(proj_dir)
            merged = settings.merged()
            self.assertEqual(merged.check("Write"), Permission.DENY)
        finally:
            shutil.rmtree(tmp)


class TestPermissionLogger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_log_entry(self):
        logger = PermissionLogger()
        logger.log("Read", {"file_path": "/a"}, Permission.ALLOW, True)
        entries = logger.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].allowed)

    def test_log_denied(self):
        logger = PermissionLogger()
        logger.log("Bash", {"command": "rm -rf /"}, Permission.DENY, False)
        self.assertEqual(len(logger.get_denied()), 1)
        self.assertEqual(len(logger.get_allowed()), 0)

    def test_log_to_file(self):
        log_path = Path(self.tmp) / "audit.log"
        logger = PermissionLogger(log_path)
        logger.log("Read", {}, Permission.ALLOW, True)
        logger.log("Write", {}, Permission.DENY, False)

        content = log_path.read_text()
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_load_from_file(self):
        log_path = Path(self.tmp) / "audit.log"
        log_path.write_text(
            json.dumps({"timestamp": 1.0, "tool_name": "Read", "args": {}, "permission": "allow", "allowed": True}) + "\n"
            + json.dumps({"timestamp": 2.0, "tool_name": "Write", "args": {}, "permission": "deny", "allowed": False}) + "\n"
        )
        logger = PermissionLogger.load_from_file(log_path)
        self.assertEqual(len(logger.get_entries()), 2)
        self.assertEqual(len(logger.get_denied()), 1)

    def test_clear(self):
        logger = PermissionLogger()
        logger.log("Read", {}, Permission.ALLOW, True)
        logger.clear()
        self.assertEqual(len(logger.get_entries()), 0)


if __name__ == "__main__":
    unittest.main()
