"""Execution modes for autonomy levels."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ExecutionMode(Enum):
    """Autonomy level for phase execution."""

    SUPERVISED = "supervised"
    MILESTONE = "milestone"
    AUTONOMOUS = "autonomous"


class ExecutionState(Enum):
    """State of an execution session."""

    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class Milestone:
    """A milestone for approval-gated execution."""

    name: str
    phases_to_complete: int


class BlockerType(Enum):
    """Types of blockers that can halt execution."""

    SAFETY_BRANCH = "safety_branch"
    API_KEY = "api_key"
    VALIDATION_FAILURE = "validation_failure"
    LOCK_COLLISION = "lock_collision"
    PERMISSION_ERROR = "permission_error"
    DEPENDENCY_MISSING = "dependency_missing"


@dataclass
class Blocker:
    """Represents an execution blocker."""

    blocker_type: BlockerType
    message: str
    can_auto_resolve: bool = False
    resolution_hint: str | None = None


@dataclass
class ExecutionCheckpoint:
    """Checkpoint state for resumable execution."""

    session_id: str
    mode: str
    current_phase_index: int
    current_phase_title: str
    phases_completed: list[str]
    state: str
    started_at: float
    last_updated: float


class ExecutionModeManager:
    """Manages execution modes and checkpoints."""

    DEFAULT_MILESTONE_THRESHOLD = 3

    def __init__(self, mode: ExecutionMode = ExecutionMode.SUPERVISED, milestone_threshold: int = 3):
        self.mode = mode
        self.milestone_threshold = milestone_threshold
        self.phases_since_milestone = 0
        self._current_checkpoint: ExecutionState = ExecutionState.READY

    def should_await_approval(self, phase_index: int, phases_completed: int) -> bool:
        """Determine if execution should wait for user approval."""
        if self.mode == ExecutionMode.SUPERVISED:
            return True
        if self.mode == ExecutionMode.MILESTONE:
            if self.phases_since_milestone >= self.milestone_threshold:
                self.phases_since_milestone = 0
                return True
            self.phases_since_milestone += 1
            return False
        return False

    def check_blocker(self, result) -> Blocker | None:
        """Check for blockers after phase execution."""
        from .models import ValidationResult

        validation_passed = True
        if hasattr(result, "validation_passed"):
            validation_passed = result.validation_passed
        elif hasattr(result, "validation_report"):
            validation_passed = "FAIL" not in result.validation_report

        if not validation_passed and self.mode == ExecutionMode.AUTONOMOUS:
            if hasattr(result, "verification_attempts"):
                attempts = result.verification_attempts
                if attempts >= 3:
                    return Blocker(
                        blocker_type=BlockerType.VALIDATION_FAILURE,
                        message=f"Validation failed after {attempts} attempts for phase",
                        can_auto_resolve=False,
                        resolution_hint="Check validation commands or run in supervised mode",
                    )

        return None

    def get_checkpoint_file(self, target_root: Path) -> Path:
        """Get checkpoint file path for target project."""
        return target_root / ".autobots-checkpoint.json"

    def save_checkpoint(
        self,
        target_root: Path,
        session_id: str,
        mode: ExecutionMode,
        phase_index: int,
        phase_title: str,
        phases_completed: list[str],
        state: ExecutionState,
    ) -> None:
        """Save execution checkpoint for resumability."""
        checkpoint = ExecutionCheckpoint(
            session_id=session_id,
            mode=mode.value,
            current_phase_index=phase_index,
            current_phase_title=phase_title,
            phases_completed=phases_completed,
            state=state.value,
            started_at=time.time(),
            last_updated=time.time(),
        )
        checkpoint_path = self.get_checkpoint_file(target_root)
        checkpoint_path.write_text(json.dumps({
            "session_id": checkpoint.session_id,
            "mode": checkpoint.mode,
            "current_phase_index": checkpoint.current_phase_index,
            "current_phase_title": checkpoint.current_phase_title,
            "phases_completed": checkpoint.phases_completed,
            "state": checkpoint.state,
            "started_at": checkpoint.started_at,
            "last_updated": checkpoint.last_updated,
        }, indent=2), encoding="utf-8")

    def load_checkpoint(self, target_root: Path) -> ExecutionCheckpoint | None:
        """Load checkpoint if exists."""
        checkpoint_path = self.get_checkpoint_file(target_root)
        if not checkpoint_path.exists():
            return None

        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            return ExecutionCheckpoint(
                session_id=data["session_id"],
                mode=data["mode"],
                current_phase_index=data["current_phase_index"],
                current_phase_title=data["current_phase_title"],
                phases_completed=data["phases_completed"],
                state=data["state"],
                started_at=data["started_at"],
                last_updated=data["last_updated"],
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def clear_checkpoint(self, target_root: Path) -> None:
        """Clear checkpoint file."""
        checkpoint_path = self.get_checkpoint_file(target_root)
        if checkpoint_path.exists():
            checkpoint_path.unlink(missing_ok=True)


def parse_mode_from_string(mode_str: str) -> ExecutionMode:
    """Parse execution mode from string."""
    mode_lower = mode_str.lower().strip()
    for mode in ExecutionMode:
        if mode.value == mode_lower:
            return mode
    return ExecutionMode.SUPERVISED