"""Autonomous execution engine with durable state and recovery hooks."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Callable

from .modes import ExecutionMode, ExecutionState, Blocker, parse_mode_from_string
from .state import ChangeType, PhaseSnapshot, SessionState, StateManager, StaleLockRecovery

if TYPE_CHECKING:
    from ..workspace import TargetProjectWorkspace
    from .modes import ExecutionCheckpoint


class AutonomyEngine:
    """Engine for autonomous execution with multiple modes."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SUPERVISED, api_key: str | None = None):
        self.mode = mode
        self.api_key = api_key
        self._router = None
        self._session_id: str | None = None
        self._mode_manager = None
        self._state_manager: StateManager | None = None

    @property
    def router(self):
        """Lazy load router to avoid circular import."""
        if self._router is None:
            from ..router import AutobotRouter

            self._router = AutobotRouter(api_key=self.api_key)
        return self._router

    def execute(
        self,
        workspace: "TargetProjectWorkspace",
        mode: ExecutionMode = ExecutionMode.SUPERVISED,
        milestone_threshold: int = 3,
        event_handler: Callable[[str], None] | None = None,
    ) -> "AutonomousResult":
        """Execute phases with the given autonomy mode."""
        return self._execute_loop(
            workspace,
            mode=mode,
            milestone_threshold=milestone_threshold,
            event_handler=event_handler,
            checkpoint=None,
        )

    def resume(self, workspace: "TargetProjectWorkspace", event_handler: Callable[[str], None] | None = None):
        """Resume from a checkpoint."""
        from .modes import ExecutionModeManager

        mode_manager = ExecutionModeManager()
        checkpoint = mode_manager.load_checkpoint(workspace.target_root)

        if not checkpoint:
            if event_handler:
                event_handler("No checkpoint found to resume")
            return AutonomousResult(
                status="no_checkpoint",
                phases_completed=[],
                session_id=None,
            )

        mode = parse_mode_from_string(checkpoint.mode)
        self.mode = mode
        self._session_id = checkpoint.session_id

        if event_handler:
            event_handler(f"Resuming session {checkpoint.session_id} in {mode.value} mode")
            event_handler(f"Last phase: {checkpoint.current_phase_title}")

        return self._execute_loop(
            workspace,
            mode=mode,
            milestone_threshold=ExecutionModeManager.DEFAULT_MILESTONE_THRESHOLD,
            event_handler=event_handler,
            checkpoint=checkpoint,
        )

    def _execute_loop(
        self,
        workspace: "TargetProjectWorkspace",
        *,
        mode: ExecutionMode,
        milestone_threshold: int,
        event_handler: Callable[[str], None] | None,
        checkpoint: "ExecutionCheckpoint | None",
    ) -> "AutonomousResult":
        from .modes import ExecutionModeManager

        self.mode = mode
        mode_manager = ExecutionModeManager(mode, milestone_threshold)
        self._mode_manager = mode_manager
        self._state_manager = StateManager(workspace.target_root)

        if self._session_id is None:
            self._session_id = str(uuid.uuid4())[:8]

        session = self._prepare_session(workspace, checkpoint)
        phases_completed = list(checkpoint.phases_completed) if checkpoint else list(session.phases_completed)
        current_index = len(phases_completed)

        self._recover_stale_locks(workspace, event_handler)

        if event_handler:
            event_handler(f"Starting autonomous execution in {mode.value} mode")

        while True:
            roadmap_text, progress_text = self.router.read_phase_documents(workspace)
            phase = self.router.find_next_phase(progress_text)

            if phase is None:
                self._finalize_session(workspace, phases_completed, event_handler)
                if event_handler:
                    event_handler("All phases complete")
                return AutonomousResult(
                    status="completed",
                    phases_completed=phases_completed,
                    session_id=self._session_id,
                )

            session.current_phase = phase.title
            session.phases_completed = list(phases_completed)
            session.state = SessionState.RUNNING.value
            self._state_manager.update_session(session)

            if event_handler:
                event_handler(f"Executing phase {phase.title}")

            if mode_manager.should_await_approval(current_index, len(phases_completed)):
                self._save_execution_checkpoint(
                    workspace=workspace,
                    mode=mode,
                    phase_index=current_index,
                    phase_title=phase.title,
                    phases_completed=phases_completed,
                    state=ExecutionState.PAUSED,
                    started_at=checkpoint.started_at if checkpoint else None,
                )
                session.state = SessionState.PAUSED.value
                self._state_manager.update_session(session)
                if event_handler:
                    event_handler("Approval required - switching to supervised mode for this phase")
                return AutonomousResult(
                    status="approval_required",
                    phases_completed=phases_completed,
                    current_phase=phase.title,
                    session_id=self._session_id,
                )

            phase_id = self.router._extract_phase_id(phase.title)
            snapshot = PhaseSnapshot(
                phase_id=phase_id,
                phase_title=phase.title,
                started_at=session.updated_at,
                status="running",
            )
            self._state_manager.save_phase_snapshot(snapshot)
            self._state_manager.log_audit(
                ChangeType.PHASE_STARTED,
                f"Started {phase.title}",
                phase_id=phase_id,
            )
            self._save_execution_checkpoint(
                workspace=workspace,
                mode=mode,
                phase_index=current_index,
                phase_title=phase.title,
                phases_completed=phases_completed,
                state=ExecutionState.RUNNING,
                started_at=checkpoint.started_at if checkpoint else None,
            )

            result = self.router.execute_phase(
                workspace,
                phase,
                roadmap_text,
                progress_text,
                event_handler=event_handler,
            )

            snapshot.files_written = list(result.files_written)
            snapshot.validation_attempts = result.verification_attempts
            snapshot.last_validation_output = result.validation_report
            snapshot.commands_executed = [
                {"command": command, "category": "validation"}
                for command in self.router.build_work_packet_from_phase(phase, roadmap_text).validation_commands
            ]
            snapshot.result_summary = result.summary

            self._record_phase_audit(phase_id, snapshot, result.validation_passed)
            self._state_manager.increment_command_count(len(snapshot.commands_executed))
            self._state_manager.increment_file_count(len(result.files_written))
            self._state_manager.save_recovery_point(
                self._session_id,
                phase_id,
                phase.title,
                result.files_written,
                snapshot.commands_executed,
            )

            blocker = mode_manager.check_blocker(result)
            if blocker:
                snapshot.status = "blocked"
                snapshot.error_log.append(blocker.message)
                self._state_manager.save_phase_snapshot(snapshot)
                self._save_execution_checkpoint(
                    workspace=workspace,
                    mode=mode,
                    phase_index=current_index,
                    phase_title=phase.title,
                    phases_completed=phases_completed,
                    state=ExecutionState.BLOCKED,
                    started_at=checkpoint.started_at if checkpoint else None,
                )
                session.state = SessionState.FAILED.value
                self._state_manager.increment_error_count()
                self._state_manager.update_session(session)
                self._state_manager.log_audit(
                    ChangeType.ERROR_ENCOUNTERED,
                    blocker.message,
                    phase_id=phase_id,
                    metadata={"blocker_type": blocker.blocker_type.value},
                )
                if event_handler:
                    event_handler(f"BLOCKER: {blocker.message}")
                return AutonomousResult(
                    status="blocked",
                    phases_completed=phases_completed,
                    blocker=blocker,
                    session_id=self._session_id,
                )

            self.router.complete_phase(
                workspace,
                phase,
                progress_text,
                result.plan,
                event_handler=event_handler,
            )
            phases_completed.append(phase.title)
            current_index += 1

            snapshot.status = "completed"
            snapshot.completed_at = session.updated_at
            self._state_manager.save_phase_snapshot(snapshot)
            self._state_manager.clear_recovery_point()
            self._state_manager.log_audit(
                ChangeType.PHASE_COMPLETED,
                f"Completed {phase.title}",
                phase_id=phase_id,
            )

            session.phases_completed = list(phases_completed)
            session.current_phase = None
            session.last_checkpoint_at = snapshot.completed_at
            self._state_manager.update_session(session)

            next_progress = workspace.read_context_file("progress-tracker.md")
            next_phase = self.router.find_next_phase(next_progress)
            next_title = next_phase.title if next_phase else phase.title
            next_state = ExecutionState.RUNNING if next_phase else ExecutionState.COMPLETED
            self._save_execution_checkpoint(
                workspace=workspace,
                mode=mode,
                phase_index=current_index,
                phase_title=next_title,
                phases_completed=phases_completed,
                state=next_state,
                started_at=checkpoint.started_at if checkpoint else None,
            )

        return AutonomousResult(
            status="unknown",
            phases_completed=phases_completed,
            session_id=self._session_id,
        )

    def _prepare_session(self, workspace: "TargetProjectWorkspace", checkpoint: "ExecutionCheckpoint | None"):
        session = self._state_manager.get_session()
        if session and session.session_id == self._session_id:
            session.mode = self.mode.value
            session.state = SessionState.RUNNING.value
            self._state_manager.update_session(session)
            self._state_manager.log_audit(
                ChangeType.CHECKPOINT_LOADED,
                f"Loaded session {session.session_id}",
                metadata={"checkpoint": checkpoint is not None},
            )
            return session

        session = self._state_manager.create_session(self._session_id, str(workspace.target_root), self.mode.value)
        session.state = SessionState.RUNNING.value
        if checkpoint:
            session.phases_completed = list(checkpoint.phases_completed)
            session.current_phase = checkpoint.current_phase_title
        self._state_manager.update_session(session)
        return session

    def _recover_stale_locks(
        self,
        workspace: "TargetProjectWorkspace",
        event_handler: Callable[[str], None] | None,
    ) -> None:
        recovered = StaleLockRecovery.auto_recover_stale_locks(workspace)
        if recovered["found"] == 0:
            return

        self._state_manager.log_audit(
            ChangeType.LOCK_RELEASED,
            "Recovered stale workspace locks before execution",
            metadata=recovered,
        )
        if event_handler:
            event_handler(
                f"Recovered {len(recovered['recovered'])}/{recovered['found']} stale context lock(s) before continuing."
            )

    def _record_phase_audit(self, phase_id: str, snapshot: PhaseSnapshot, validation_passed: bool) -> None:
        for file_path in snapshot.files_written:
            self._state_manager.log_audit(
                ChangeType.FILE_MODIFIED,
                f"Updated {file_path}",
                phase_id=phase_id,
                file_path=file_path,
            )

        for command_info in snapshot.commands_executed:
            command = command_info.get("command") or ""
            self._state_manager.log_audit(
                ChangeType.COMMAND_EXECUTED,
                f"Executed validation command: {command}",
                phase_id=phase_id,
                command=command,
                metadata=command_info,
            )

        audit_type = ChangeType.VALIDATION_PASSED if validation_passed else ChangeType.VALIDATION_FAILED
        self._state_manager.log_audit(
            audit_type,
            "Validation passed" if validation_passed else "Validation failed",
            phase_id=phase_id,
            metadata={"attempts": snapshot.validation_attempts},
        )

    def _save_execution_checkpoint(
        self,
        *,
        workspace: "TargetProjectWorkspace",
        mode: ExecutionMode,
        phase_index: int,
        phase_title: str,
        phases_completed: list[str],
        state: ExecutionState,
        started_at: float | None,
    ) -> None:
        self._mode_manager.save_checkpoint(
            target_root=workspace.target_root,
            session_id=self._session_id,
            mode=mode,
            phase_index=phase_index,
            phase_title=phase_title,
            phases_completed=phases_completed,
            state=state,
            started_at=started_at,
        )
        self._state_manager.log_audit(
            ChangeType.CHECKPOINT_SAVED,
            f"Checkpoint saved for {phase_title}",
            metadata={"state": state.value, "phases_completed": len(phases_completed)},
        )

    def _finalize_session(
        self,
        workspace: "TargetProjectWorkspace",
        phases_completed: list[str],
        event_handler: Callable[[str], None] | None,
    ) -> None:
        session = self._state_manager.get_session()
        if session:
            session.state = SessionState.COMPLETED.value
            session.phases_completed = list(phases_completed)
            session.current_phase = None
            session.last_checkpoint_at = session.updated_at
            self._state_manager.update_session(session)

        self._save_execution_checkpoint(
            workspace=workspace,
            mode=self.mode,
            phase_index=len(phases_completed),
            phase_title="All phases complete",
            phases_completed=phases_completed,
            state=ExecutionState.COMPLETED,
            started_at=None,
        )
        self._state_manager.clear_recovery_point()
        if event_handler:
            event_handler("Execution state marked complete and recovery point cleared")


class AutonomousResult:
    """Result of autonomous execution."""

    def __init__(
        self,
        status: str,
        phases_completed: list[str],
        session_id: str | None = None,
        current_phase: str | None = None,
        blocker: Blocker | None = None,
    ):
        self.status = status
        self.phases_completed = phases_completed
        self.session_id = session_id
        self.current_phase = current_phase
        self.blocker = blocker
