"""Phase 5: execution and verification engine for real project work."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .workspace import TargetProjectWorkspace, WorkspaceIOError


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


class CommandExecutionError(Exception):
    """Raised when command execution fails."""


class CommandPolicyViolation(Exception):
    """Raised when a command violates the safety policy."""


class PhaseExecutor:
    """Orchestrates the execution of a phase with structured work packets."""

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
        self._emit(event_handler, f"Inspecting {len(work_packet.relevant_files)} files for {work_packet.phase_id}...")

        inspection_report = [f"# File Inspection Report for {work_packet.phase_id}\n"]
        inspection_report.append(f"**Phase**: {work_packet.title}\n")
        inspection_report.append(f"**Goal**: {work_packet.goal}\n")
        inspection_report.append("## Inspected Files\n")

        for file_path in work_packet.relevant_files[:20]:
            try:
                content = None
                for root in ["src", "app", "lib", "tests", "docs", "scripts"]:
                    try:
                        content = workspace.read_file(root, file_path)
                        inspection_report.append(f"\n### {root}/{file_path}\n")
                        inspection_report.append("```\n")
                        inspection_report.append("\n".join(content.split("\n")[:30]))
                        inspection_report.append("\n```\n")
                        break
                    except WorkspaceIOError:
                        continue

                if content is None:
                    inspection_report.append(f"\n### {file_path}\n")
                    inspection_report.append("[File not found in any project root]\n")
            except Exception as exc:
                inspection_report.append(f"\n### {file_path}\n")
                inspection_report.append(f"[Error reading file: {exc}]\n")

        return "\n".join(inspection_report)

    def apply_generated_changes(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        generated_files: list[dict],
        lock_owner: str,
        event_handler: EventHandler | None = None,
    ) -> list[str]:
        self._emit(event_handler, f"Applying {len(generated_files)} file changes for {work_packet.phase_id}...")

        written_paths: list[str] = []
        for file_spec in generated_files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip()
            content = file_spec.get("content") or ""

            try:
                written = workspace.write_file(root_name, relative_path, content)
                written_paths.append(str(written))
                self._emit(event_handler, f"  Wrote {root_name}/{relative_path}")
            except WorkspaceIOError as exc:
                self._emit(event_handler, f"  Failed to write {root_name}/{relative_path}: {exc}")
                raise

        return written_paths

    def validate_phase(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        event_handler: EventHandler | None = None,
    ) -> tuple[bool, list[ValidationResult]]:
        if not work_packet.validation_commands:
            self._emit(event_handler, "No validation commands specified.")
            return True, []

        results: list[ValidationResult] = []
        all_passed = True
        allow_migrations = self._work_packet_allows_migrations(work_packet)

        for command in work_packet.validation_commands:
            self._emit(event_handler, f"Running validation: {command}")
            try:
                result = self.execute_command(
                    command,
                    workspace.target_root,
                    allow_migrations=allow_migrations,
                    event_handler=event_handler,
                )
                results.append(result)
                if result.passed:
                    self._emit(event_handler, f"  PASS ({result.category})")
                else:
                    self._emit(event_handler, f"  FAIL ({result.category})")
                    all_passed = False
            except CommandPolicyViolation as exc:
                results.append(
                    ValidationResult(
                        command=command,
                        exit_code=-1,
                        stdout="",
                        stderr=str(exc),
                        passed=False,
                        category=self._categorize_command(command),
                    )
                )
                self._emit(event_handler, f"  Policy violation: {exc}")
                all_passed = False
            except Exception as exc:
                results.append(
                    ValidationResult(
                        command=command,
                        exit_code=-1,
                        stdout="",
                        stderr=str(exc),
                        passed=False,
                        category=self._categorize_command(command),
                    )
                )
                self._emit(event_handler, f"  Error: {exc}")
                all_passed = False

        return all_passed, results

    def execute_command(
        self,
        command: str,
        working_dir: str | Path,
        timeout_seconds: int = 30,
        allow_migrations: bool = False,
        event_handler: EventHandler | None = None,
    ) -> ValidationResult:
        self._check_command_policy(command, allow_migrations=allow_migrations)
        category = self._categorize_command(command)

        try:
            result = subprocess.run(
                command,
                cwd=str(working_dir),
                shell=True,
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

    def _check_command_policy(self, command: str, *, allow_migrations: bool = False) -> None:
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

        if self._is_migration_command(command):
            if not allow_migrations:
                raise CommandPolicyViolation(
                    f"Migration commands require explicit allow-migrations approval: {command}"
                )
            return

        is_safe = any(
            re.search(pattern, command_lower, re.IGNORECASE)
            for pattern in self.SAFE_COMMAND_PATTERNS.values()
        )
        if not is_safe:
            raise CommandPolicyViolation(f"Command not in safety whitelist: {command}")

    def format_validation_results(self, results: list[ValidationResult]) -> str:
        report_lines = ["# Validation Report\n"]
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            report_lines.append(f"## {status}: {result.command}")
            report_lines.append(f"Category: {result.category}")
            report_lines.append(f"Exit Code: {result.exit_code}\n")

            if result.stdout:
                report_lines.append("### Output")
                report_lines.append("```")
                report_lines.append(result.stdout[:500])
                report_lines.append("```\n")

            if result.stderr:
                report_lines.append("### Errors")
                report_lines.append("```")
                report_lines.append(result.stderr[:500])
                report_lines.append("```\n")

        return "\n".join(report_lines)

    def build_validation_feedback(
        self,
        work_packet: WorkPacket,
        results: list[ValidationResult],
    ) -> dict:
        failed = [result for result in results if not result.passed]
        issues: list[str] = []
        for result in failed:
            excerpt = (result.stderr or result.stdout or "Validation failed.").strip().splitlines()
            detail = excerpt[0] if excerpt else "Validation failed."
            issues.append(f"{result.category} failed for `{result.command}`: {detail}")

        return {
            "status": "revise",
            "summary": (
                f"Validation failed for {len(failed)} command(s). "
                "Repair the implementation so the project passes the target toolchain checks."
            ),
            "issues": issues,
            "acceptance_checks": list(work_packet.acceptance_checks),
            "validation_report": self.format_validation_results(results),
        }

    def summarize_validation_results(self, results: list[ValidationResult]) -> str:
        if not results:
            return "No validation commands were configured."

        failed = [result for result in results if not result.passed]
        if not failed:
            return f"Validation passed for {len(results)} command(s)."

        failed_labels = ", ".join(result.category for result in failed)
        return f"Validation failed for {len(failed)} of {len(results)} command(s): {failed_labels}."

    def _categorize_command(self, command: str) -> str:
        command_lower = command.lower()
        if self._is_migration_command(command):
            return "migration"
        for category, pattern in self.SAFE_COMMAND_PATTERNS.items():
            if re.search(pattern, command_lower, re.IGNORECASE):
                return category
        return "validation"

    def _is_migration_command(self, command: str) -> bool:
        command_lower = command.lower()
        return any(re.search(pattern, command_lower, re.IGNORECASE) for pattern in self.MIGRATION_PATTERNS)

    def _work_packet_allows_migrations(self, work_packet: WorkPacket) -> bool:
        tokens = " ".join(work_packet.constraints).lower()
        return "allow migration" in tokens or "allow migrations" in tokens or "migrations allowed" in tokens

    def _emit(self, event_handler: EventHandler | None, message: str) -> None:
        if event_handler:
            event_handler(message)
