"""Tests for Phase 7: durable state, checkpointing, and recovery."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from autobots.executor import (
    AutonomyEngine,
    ExecutionMode,
    ExecutionModeManager,
    ExecutionState,
    PhaseSnapshot,
    StateManager,
    StaleLockRecovery,
)
from autobots.router.models import ExecutionResult, PhaseRecord
from autobots.router.phases import PhaseReader
from autobots.workspace import TargetProjectWorkspace


class Phase7StateManagerTests(unittest.TestCase):
    def test_state_manager_persists_session_snapshot_and_recovery_point(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manager = StateManager(root)

            session = manager.create_session("sess-1", str(root), "autonomous")
            session.current_phase = "P1 | Demo"
            session.phases_completed = ["P0 | Setup"]
            manager.update_session(session)

            manager.save_phase_snapshot(
                PhaseSnapshot(
                    phase_id="P1",
                    phase_title="P1 | Demo",
                    started_at=1.0,
                    status="running",
                    files_written=["src/demo.py"],
                    validation_attempts=1,
                    last_validation_output="PASS",
                    commands_executed=[{"command": "python -m pytest -q"}],
                    result_summary="Started demo",
                )
            )
            manager.save_recovery_point(
                "sess-1",
                "P1",
                "P1 | Demo",
                ["src/demo.py"],
                [{"command": "python -m pytest -q"}],
            )

            loaded_session = manager.get_session()
            snapshot = manager.get_phase_snapshot("P1")
            recovery = manager.get_recovery_point()

            self.assertIsNotNone(loaded_session)
            self.assertEqual(loaded_session.current_phase, "P1 | Demo")
            self.assertEqual(loaded_session.phases_completed, ["P0 | Setup"])
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.files_written, ["src/demo.py"])
            self.assertEqual(recovery["phase_id"], "P1")

    def test_stale_lock_recovery_detects_and_recovers_expired_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "context").mkdir()
            workspace = TargetProjectWorkspace(root)
            workspace.lock_root.mkdir(parents=True, exist_ok=True)

            lock_path = workspace.lock_root / "architecture.md.lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "path": "architecture.md",
                        "owner": "Autobots/test",
                        "acquired_at": 1.0,
                        "expires_at": 1.0,
                    }
                ),
                encoding="utf-8",
            )

            stale = StaleLockRecovery.find_stale_locks(workspace)
            summary = StaleLockRecovery.auto_recover_stale_locks(workspace)

            self.assertEqual(len(stale), 1)
            self.assertEqual(summary["found"], 1)
            self.assertEqual(summary["recovered"], [lock_path.name])
            self.assertFalse(lock_path.exists())


class Phase7AutonomyTests(unittest.TestCase):
    class DummyRouter:
        def read_phase_documents(self, workspace: TargetProjectWorkspace) -> tuple[str, str]:
            return (
                workspace.read_context_file("roadmap.md"),
                workspace.read_context_file("progress-tracker.md"),
            )

        def find_next_phase(self, progress_text: str) -> PhaseRecord | None:
            return PhaseReader.find_next_phase(progress_text)

        def _extract_phase_id(self, title: str) -> str:
            return title.split("|", 1)[0].strip()

        def build_work_packet_from_phase(self, phase: PhaseRecord, roadmap_text: str):
            return SimpleNamespace(validation_commands=["python -m pytest -q"])

        def execute_phase(self, workspace, phase, roadmap_text, progress_text, event_handler=None):
            workspace.write_file("src", f"{self._extract_phase_id(phase.title).lower()}.txt", "done\n")
            return ExecutionResult(
                cluster_name="UltraMagnus",
                summary=f"Finished {phase.title}",
                raw_response="ok",
                files_written=[str(workspace.target_root / "src" / f"{self._extract_phase_id(phase.title).lower()}.txt")],
                journal=[],
                plan=SimpleNamespace(),
                validation_passed=True,
                validation_report="PASS",
                verification_attempts=1,
            )

        def complete_phase(self, workspace, phase, progress_text, plan, event_handler=None):
            updated = PhaseReader.mark_phase_complete(progress_text, phase)
            workspace.write_context_file("progress-tracker.md", updated, lock_owner="Autobots/test")
            return updated

    def test_execute_persists_durable_state_and_audit_trail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "context").mkdir()
            (root / "context" / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "context" / "progress-tracker.md").write_text(
                "- [ ] P1 | Demo phase\n- [ ] P2 | Follow-up phase\n",
                encoding="utf-8",
            )

            engine = AutonomyEngine(mode=ExecutionMode.AUTONOMOUS)
            engine._router = self.DummyRouter()

            result = engine.execute(TargetProjectWorkspace(root), mode=ExecutionMode.AUTONOMOUS)
            manager = StateManager(root)
            checkpoint = ExecutionModeManager().load_checkpoint(root)
            audit = manager.get_audit_trail()
            session = manager.get_session()

            self.assertEqual(result.status, "completed")
            self.assertEqual(len(result.phases_completed), 2)
            self.assertIsNotNone(session)
            self.assertEqual(session.state, "completed")
            self.assertEqual(len(session.phases_completed), 2)
            self.assertIsNotNone(checkpoint)
            self.assertEqual(checkpoint.state, "completed")
            self.assertTrue(any(entry.change_type == "phase_started" for entry in audit))
            self.assertTrue(any(entry.change_type == "phase_completed" for entry in audit))
            self.assertTrue(any(entry.change_type == "file_modified" for entry in audit))

    def test_supervised_mode_saves_paused_checkpoint_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "context").mkdir()
            (root / "context" / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "context" / "progress-tracker.md").write_text("- [ ] P1 | Demo phase\n", encoding="utf-8")

            engine = AutonomyEngine(mode=ExecutionMode.SUPERVISED)
            engine._router = self.DummyRouter()

            result = engine.execute(TargetProjectWorkspace(root), mode=ExecutionMode.SUPERVISED)
            checkpoint = ExecutionModeManager().load_checkpoint(root)
            session = StateManager(root).get_session()

            self.assertEqual(result.status, "approval_required")
            self.assertIsNotNone(checkpoint)
            self.assertEqual(checkpoint.state, "paused")
            self.assertEqual(checkpoint.current_phase_title, "P1 | Demo phase")
            self.assertIsNotNone(session)
            self.assertEqual(session.state, "paused")

    def test_resume_reuses_last_checkpoint_and_completes_remaining_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "context").mkdir()
            (root / "context" / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "context" / "progress-tracker.md").write_text("- [x] P1 | Finished\n- [ ] P2 | Remaining\n", encoding="utf-8")

            manager = ExecutionModeManager()
            manager.save_checkpoint(
                target_root=root,
                session_id="sess-2",
                mode=ExecutionMode.AUTONOMOUS,
                phase_index=1,
                phase_title="P2 | Remaining",
                phases_completed=["P1 | Finished"],
                state=ExecutionState.RUNNING,
            )

            state_manager = StateManager(root)
            session = state_manager.create_session("sess-2", str(root), "autonomous")
            session.phases_completed = ["P1 | Finished"]
            session.current_phase = "P2 | Remaining"
            state_manager.update_session(session)

            engine = AutonomyEngine()
            engine._router = self.DummyRouter()

            result = engine.resume(TargetProjectWorkspace(root))
            resumed_session = state_manager.get_session()

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.session_id, "sess-2")
            self.assertEqual(result.phases_completed, ["P1 | Finished", "P2 | Remaining"])
            self.assertIsNotNone(resumed_session)
            self.assertEqual(resumed_session.state, "completed")

    @patch("autobots.cli.Console")
    def test_status_can_surface_prior_run_session_details(self, console_cls) -> None:
        from autobots.cli import run_status

        console = console_cls.return_value
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "context").mkdir()
            (root / "context" / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "context" / "progress-tracker.md").write_text("- [x] P1 | Finished\n", encoding="utf-8")

            state_manager = StateManager(root)
            session = state_manager.create_session("sess-3", str(root), "autonomous")
            session.state = "completed"
            session.phases_completed = ["P1 | Finished"]
            session.total_files_changed = 2
            state_manager.update_session(session)

            with patch("autobots.cli._resolve_target_project_from_args", return_value=root):
                run_status(["status", str(root)])

            self.assertTrue(console.print.called)


if __name__ == "__main__":
    unittest.main()
