"""Main phase executor orchestrating all execution operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import ExecutionStep, EventHandler, WorkPacket
from .validation import PhaseValidator
from .operations import FileOperations
from .commands import CommandValidator, CommandPolicyViolation

if TYPE_CHECKING:
    from ..workspace import TargetProjectWorkspace


class PhaseExecutor:
    """Orchestrates the execution of a phase with structured work packets."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._execution_history: list[ExecutionStep] = []

    def build_work_packet(
        self,
        phase_id: str,
        title: str,
        goal: str,
        relevant_files: list[str],
        constraints: list[str],
        validation_commands: list[str],
        acceptance_checks: list[str],
    ) -> WorkPacket:
        """Build a structured work packet."""
        return WorkPacket(
            phase_id=phase_id,
            title=title,
            goal=goal,
            relevant_files=relevant_files,
            constraints=constraints,
            validation_commands=validation_commands,
            acceptance_checks=acceptance_checks,
        )

    def inspect_phase_files(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        event_handler: EventHandler | None = None,
    ) -> str:
        """Inspect phase files and generate report."""
        return FileOperations.inspect_phase_files(workspace, work_packet, event_handler)

    def apply_generated_changes(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        generated_files: list[dict],
        lock_owner: str,
        event_handler: EventHandler | None = None,
    ) -> list[str]:
        """Apply generated file changes."""
        return FileOperations.apply_generated_changes(workspace, work_packet, generated_files, lock_owner, event_handler)

    def validate_phase(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        event_handler: EventHandler | None = None,
    ) -> tuple[bool, list]:
        """Validate phase execution."""
        allow_migrations = PhaseValidator._work_packet_allows_migrations(work_packet)
        return PhaseValidator.validate_phase(work_packet, str(workspace.target_root), allow_migrations, event_handler)

    def execute_command(
        self,
        command: str,
        working_dir: str,
        timeout_seconds: int = 30,
        allow_migrations: bool = False,
        event_handler: EventHandler | None = None,
    ):
        """Execute a single command."""
        try:
            return CommandValidator.execute_command(command, working_dir, timeout_seconds, allow_migrations)
        except CommandPolicyViolation as exc:
            self._emit(event_handler, f"Policy violation: {exc}")
            raise

    def format_validation_results(self, results):
        """Format validation results."""
        return PhaseValidator.format_validation_results(results)

    def summarize_validation_results(self, results):
        """Summarize validation results."""
        return PhaseValidator.summarize_validation_results(results)

    def build_validation_feedback(self, work_packet: WorkPacket, results):
        """Build validation feedback."""
        return PhaseValidator.build_validation_feedback(work_packet, results)

    def _check_command_policy(self, command: str, *, allow_migrations: bool = False) -> None:
        """Backward compatibility wrapper for command policy checking."""
        return CommandValidator.check_command_policy(command, allow_migrations=allow_migrations)

    def _emit(self, event_handler: EventHandler | None, message: str) -> None:
        if event_handler:
            event_handler(message)
