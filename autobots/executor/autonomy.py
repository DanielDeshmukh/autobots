"""Autonomous execution engine with configurable modes."""

from __future__ import annotations

import uuid
from typing import Callable

from ..router import AutobotRouter
from ..workspace import TargetProjectWorkspace
from .modes import ExecutionMode, ExecutionState, Blocker, parse_mode_from_string


class AutonomyEngine:
    """Engine for autonomous execution with multiple modes."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SUPERVISED, api_key: str | None = None):
        self.mode = mode
        self.router = AutobotRouter(api_key=api_key)
        self._session_id: str | None = None
        self._mode_manager = None

    def execute(
        self,
        workspace: TargetProjectWorkspace,
        mode: ExecutionMode = ExecutionMode.SUPERVISED,
        milestone_threshold: int = 3,
        event_handler: Callable[[str], None] | None = None,
    ) -> AutonomousResult:
        """Execute phases with the given autonomy mode."""
        from .modes import ExecutionModeManager

        self.mode = mode
        mode_manager = ExecutionModeManager(mode, milestone_threshold)
        self._mode_manager = mode_manager

        self._session_id = str(uuid.uuid4())[:8]

        phases_completed: list[str] = []
        current_index = 0

        if event_handler:
            event_handler(f"Starting autonomous execution in {mode.value} mode")

        while True:
            roadmap_text, progress_text = self.router.read_phase_documents(workspace)
            phase = self.router.find_next_phase(progress_text)

            if phase is None:
                if event_handler:
                    event_handler("All phases complete")
                return AutonomousResult(
                    status="completed",
                    phases_completed=phases_completed,
                    session_id=self._session_id,
                )

            if event_handler:
                event_handler(f"Executing phase {phase.title}")

            if mode_manager.should_await_approval(current_index, len(phases_completed)):
                if event_handler:
                    event_handler("Approval required - switching to supervised mode for this phase")
                return AutonomousResult(
                    status="approval_required",
                    phases_completed=phases_completed,
                    current_phase=phase.title,
                    session_id=self._session_id,
                )

            result = self.router.execute_phase(
                workspace,
                phase,
                roadmap_text,
                progress_text,
                event_handler=event_handler,
            )

            blocker = mode_manager.check_blocker(result)
            if blocker:
                if event_handler:
                    event_handler(f"BLOCKER: {blocker.message}")
                return AutonomousResult(
                    status="blocked",
                    phases_completed=phases_completed,
                    blocker=blocker,
                    session_id=self._session_id,
                )

            mode_manager.save_checkpoint(
                target_root=workspace.target_root,
                session_id=self._session_id,
                mode=mode,
                phase_index=current_index,
                phase_title=phase.title,
                phases_completed=phases_completed,
                state=ExecutionState.RUNNING,
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

        return AutonomousResult(
            status="unknown",
            phases_completed=phases_completed,
            session_id=self._session_id,
        )

    def resume(self, workspace: TargetProjectWorkspace, event_handler: Callable[[str], None] | None = None):
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

        if event_handler:
            event_handler(f"Resuming session {checkpoint.session_id} in {mode.value} mode")
            event_handler(f"Last phase: {checkpoint.current_phase_title}")

        return self.execute(workspace, mode=mode, event_handler=event_handler)


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