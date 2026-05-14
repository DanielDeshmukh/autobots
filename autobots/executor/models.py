"""Data models for phase execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


EventHandler = Callable[[str], None]


@dataclass(frozen=True)
class WorkPacket:
    """Structured work packet for phase execution."""

    phase_id: str
    title: str
    goal: str
    relevant_files: list[str]
    constraints: list[str]
    validation_commands: list[str]
    acceptance_checks: list[str]


@dataclass(frozen=True)
class ExecutionStep:
    """A single step in the execution loop."""

    step_type: str
    description: str
    status: str
    result: str
    output: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of running validation commands."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    category: str = "validation"
