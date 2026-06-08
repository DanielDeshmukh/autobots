"""Command execution and validation policy."""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .models import ValidationResult

if TYPE_CHECKING:
    from .models import EventHandler


class CommandExecutionError(Exception):
    """Raised when command execution fails."""


class CommandPolicyViolation(Exception):
    """Raised when a command violates the safety policy."""


class CommandValidator:
    """Validates and executes commands with safety policies."""

    SAFE_COMMAND_PATTERNS = {
        "test": r"(^|\s)(pytest\b|python(?:\S+)?\s+-m\s+(?:pytest|unittest)\b|npm\s+test\b|npx\s+(?:vitest|jest)\b|cargo\s+test\b)",
        "lint": r"(^|\s)(pylint\b|flake8\b|eslint\b|clippy\b|ruff\s+check\b)",
        "format": r"(^|\s)(black\b|autopep8\b|prettier\b|ruff\s+format\b)",
        "type": r"(^|\s)(mypy\b|pyright\b|tsc\b)",
        "build": r"(^|\s)(python(?:\S+)?\s+-m\s+build\b|npm\s+run\s+build\b|cargo\s+build\b)",
        "utility": r"(^|\s)(echo\b|python(?:\S+)?\s+-c\b)",
    }
    MIGRATION_PATTERNS = (
        r"(^|\s)python(?:\S+)?\s+manage\.py\s+migrate\b",
        r"(^|\s)alembic\s+upgrade\b",
    )

    @classmethod
    def check_command_policy(cls, command: str, *, allow_migrations: bool = False) -> None:
        """Validate command against safety policies."""
        command_lower = command.lower()
        dangerous_patterns = [
            r"rm\s+-rf",
            r"sudo",
            r"shutdown",
            r"reboot",
            r"kill\s+-9",
            r"dd\s+if=",
            r"format\s+[a-z]:",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                raise CommandPolicyViolation(f"Dangerous command pattern detected: {command}")

        if cls._is_migration_command(command):
            if not allow_migrations:
                raise CommandPolicyViolation(
                    f"Migration commands require explicit allow-migrations approval: {command}"
                )
            return

        is_safe = any(
            re.search(pattern, command_lower, re.IGNORECASE)
            for pattern in cls.SAFE_COMMAND_PATTERNS.values()
        )
        if not is_safe:
            raise CommandPolicyViolation(f"Command not in safety whitelist: {command}")

    @classmethod
    def execute_command(
        cls,
        command: str,
        working_dir: str | Path,
        timeout_seconds: int = 30,
        allow_migrations: bool = False,
    ) -> ValidationResult:
        """Execute a command and return structured result."""
        cls.check_command_policy(command, allow_migrations=allow_migrations)
        category = cls.categorize_command(command)

        # On Unix, use shlex.split for safe argument parsing (no shell injection).
        # On Windows, fall back to shell=True because shlex uses POSIX rules.
        use_shell = sys.platform == "win32"
        cmd_args = command if use_shell else shlex.split(command)

        try:
            result = subprocess.run(
                cmd_args,
                cwd=str(working_dir),
                shell=use_shell,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return ValidationResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                passed=result.returncode == 0,
                category=category,
            )
        except subprocess.TimeoutExpired:
            raise CommandExecutionError(f"Command timed out after {timeout_seconds}s: {command}")
        except Exception as exc:
            raise CommandExecutionError(f"Command execution failed: {exc}")

    @classmethod
    def categorize_command(cls, command: str) -> str:
        """Categorize a command based on pattern matching."""
        command_lower = command.lower()
        if cls._is_migration_command(command):
            return "migration"
        for category, pattern in cls.SAFE_COMMAND_PATTERNS.items():
            if re.search(pattern, command_lower, re.IGNORECASE):
                return category
        return "validation"

    @classmethod
    def _is_migration_command(cls, command: str) -> bool:
        command_lower = command.lower()
        return any(re.search(pattern, command_lower, re.IGNORECASE) for pattern in cls.MIGRATION_PATTERNS)
