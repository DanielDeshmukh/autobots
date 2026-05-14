"""Tests for Phase 10 failure modes and edge cases."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from autobots.router.utils import PayloadValidator
from autobots.router.models import PhaseRecord
from autobots.workspace import TargetProjectWorkspace
from autobots.executor.state import StateManager


class FailureModeTests(unittest.TestCase):
    def test_payload_validator_rejects_invalid_json_shape(self) -> None:
        invalid_payload = {"not": "valid"}
        with self.assertRaises(ValueError):
            PayloadValidator.validate_command_payload(invalid_payload)

    def test_payload_validator_rejects_missing_required_fields(self) -> None:
        payload = {"summary": "test"}
        with self.assertRaises(ValueError):
            PayloadValidator.validate_command_payload(payload)

    def test_specialist_payload_rejects_invalid_file_root(self) -> None:
        payload = {
            "summary": "test",
            "files": [{"root": "invalid_root", "path": "test.py", "content": "print('test')"}],
        }
        with self.assertRaises(ValueError):
            PayloadValidator.validate_specialist_payload(payload)

    def test_review_payload_rejects_unknown_status(self) -> None:
        payload = {"status": "unknown_status", "summary": "test", "issues": []}
        with self.assertRaises(ValueError):
            PayloadValidator.validate_review_payload(payload)

    def test_state_manager_handles_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent = Path(tmpdir) / "nonexistent"
            manager = StateManager(non_existent)
            session = manager.get_session()
            self.assertIsNone(session)

    def test_workspace_handles_corrupted_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = TargetProjectWorkspace(Path(tmpdir))
            context_dir = workspace.context_root
            context_dir.mkdir(parents=True, exist_ok=True)
            (context_dir / "roadmap.md").write_text("not valid markdown content")
            (context_dir / "progress-tracker.md").write_text("- [ ] P1 | Test")

            from autobots.router import PhaseReader

            roadmap = (context_dir / "roadmap.md").read_text()
            progress = (context_dir / "progress-tracker.md").read_text()
            self.assertIsInstance(roadmap, str)
            self.assertIsInstance(progress, str)
            phase = PhaseReader.find_next_phase(progress)
            self.assertIsNotNone(phase)

    def test_workspace_handles_missing_phase_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = TargetProjectWorkspace(Path(tmpdir))
            context_dir = workspace.context_root
            context_dir.mkdir(parents=True, exist_ok=True)
            (context_dir / "roadmap.md").write_text("# Roadmap\n\n## P1 | Test\nGoal: Test")
            (context_dir / "progress-tracker.md").write_text("No phases here")

            from autobots.router import PhaseReader

            roadmap = (context_dir / "roadmap.md").read_text()
            progress = (context_dir / "progress-tracker.md").read_text()
            phase = PhaseReader.find_next_phase(progress)
            self.assertIsNone(phase)


class LockFailureTests(unittest.TestCase):
    def test_workspace_handles_lock_file_without_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = TargetProjectWorkspace(Path(tmpdir))
            workspace.context_root.mkdir(parents=True, exist_ok=True)
            workspace.lock_root.mkdir(parents=True, exist_ok=True)

            lock_file = workspace.lock_root / "test.lock.json"
            lock_file.write_text("{}")

            self.assertTrue(lock_file.exists())


class CommandPolicyTests(unittest.TestCase):
    def test_command_policy_rejects_dangerous_commands(self) -> None:
        from autobots.executor.commands import CommandValidator, CommandPolicyViolation

        dangerous = ["rm -rf /", "sudo rm", "dd if=/dev/zero"]
        for cmd in dangerous:
            with self.assertRaises(CommandPolicyViolation):
                CommandValidator.check_command_policy(cmd)

    def test_command_policy_allows_safe_commands(self) -> None:
        from autobots.executor.commands import CommandValidator

        safe = ["python -m pytest", "npm test", "npm run build"]
        for cmd in safe:
            CommandValidator.check_command_policy(cmd)


class EdgeCaseTests(unittest.TestCase):
    def test_phase_record_handles_empty_title(self) -> None:
        record = PhaseRecord(line_index=0, raw_line="- [ ] | Empty", title="", status="PENDING")
        self.assertEqual(record.status, "PENDING")

    def test_config_works_without_tomllib(self) -> None:
        from autobots.config import AutobotsConfig

        config = AutobotsConfig()
        self.assertEqual(config.model_selection_profile, "balanced")
        self.assertEqual(config.safety_branch, "autobots-safety")

    def test_cluster_catalog_fallback_on_empty_available_models(self) -> None:
        from autobots.catalog import ClusterCatalog

        catalog = ClusterCatalog(available_model_ids=[], refresh_live=False)
        self.assertIsNotNone(catalog.clusters)
        self.assertIn("Optimus", catalog.clusters)

    def test_autobot_router_graceful_no_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("autobots.router.core.ClusterCatalog") as mock_catalog:
                mock_instance = MagicMock()
                mock_instance.route_with_reasoning.return_value = MagicMock(
                    cluster_name="Optimus", score=1, reasons=(), scored_clusters=()
                )
                mock_instance.select_models.return_value = (
                    MagicMock(model_id="test-model"),
                    MagicMock(model_id="test-reviewer"),
                    [],
                )
                mock_catalog.return_value = mock_instance

                from autobots.router import AutobotRouter

                with self.assertRaises(RuntimeError):
                    router = AutobotRouter(api_key=None)
                    router._run_command_stage(
                        MagicMock(command_lead=MagicMock(model_id="test")),
                        PhaseRecord(line_index=0, raw_line="test", title="test", status="PENDING"),
                        "roadmap",
                        "progress",
                    )


if __name__ == "__main__":
    unittest.main()