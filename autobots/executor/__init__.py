"""Phase execution and verification engine for real project work."""

from .models import EventHandler, ExecutionStep, ValidationResult, WorkPacket
from .commands import CommandExecutionError, CommandPolicyViolation, CommandValidator
from .validation import PhaseValidator
from .operations import FileOperations
from .core import PhaseExecutor
from .modes import ExecutionMode, ExecutionState, Blocker, BlockerType, ExecutionModeManager, parse_mode_from_string
from .autonomy import AutonomyEngine
from .state import AuditEntry, ChangeType, PhaseSnapshot, SessionMetadata, SessionState, StateManager, StaleLockRecovery

__all__ = [
    "EventHandler",
    "ExecutionStep",
    "ValidationResult",
    "WorkPacket",
    "CommandExecutionError",
    "CommandPolicyViolation",
    "CommandValidator",
    "PhaseValidator",
    "FileOperations",
    "PhaseExecutor",
    "ExecutionMode",
    "ExecutionState",
    "Blocker",
    "BlockerType",
    "ExecutionModeManager",
    "parse_mode_from_string",
    "AutonomyEngine",
    "AuditEntry",
    "ChangeType",
    "PhaseSnapshot",
    "SessionMetadata",
    "SessionState",
    "StateManager",
    "StaleLockRecovery",
]
