"""Phase 4: Execution Engine For Real Project Work

Provides structured work packets and iterative execution loops for autonomous
phase execution. Supports file inspection, generation, application, and
validation within safety constraints.
"""

from __future__ import annotations

import json
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
    step_type: str  # "inspect", "generate", "apply", "validate", "evaluate"
    description: str
    status: str  # "pending", "in-progress", "complete", "failed"
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


class CommandExecutionError(Exception):
    """Raised when command execution fails."""
    pass


class CommandPolicyViolation(Exception):
    """Raised when a command violates the safety policy."""
    pass


class PhaseExecutor:
    """Orchestrates the execution of a phase with structured work packets."""

    # Safe command patterns for validation
    SAFE_COMMAND_PATTERNS = {
        "pytest": r"pytest",
        "test": r"python.*-m\s+pytest|npm\s+test|cargo\s+test",
        "lint": r"pylint|flake8|eslint|clippy",
        "format": r"black|autopep8|prettier",
        "type": r"mypy|pyright|tsc",
        "build": r"python.*-m\s+build|npm\s+run\s+build|cargo\s+build",
    }

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
        """Create a structured work packet for phase execution."""
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
        """Inspect relevant files for the work packet."""
        self._emit(event_handler, f"Inspecting {len(work_packet.relevant_files)} files for {work_packet.phase_id}...")

        inspection_report = [f"# File Inspection Report for {work_packet.phase_id}\n"]
        inspection_report.append(f"**Phase**: {work_packet.title}\n")
        inspection_report.append(f"**Goal**: {work_packet.goal}\n")
        inspection_report.append("## Inspected Files\n")

        for file_path in work_packet.relevant_files[:20]:  # Limit to first 20
            try:
                # Try to read from different potential roots
                content = None
                for root in ["src", "app", "lib", "tests", "docs", "scripts"]:
                    try:
                        content = workspace.read_file(root, file_path)
                        inspection_report.append(f"\n### {root}/{file_path}\n")
                        inspection_report.append("```\n")
                        lines = content.split("\n")[:30]  # First 30 lines
                        inspection_report.append("\n".join(lines))
                        inspection_report.append("\n```\n")
                        break
                    except WorkspaceIOError:
                        continue

                if content is None:
                    inspection_report.append(f"\n### {file_path}\n")
                    inspection_report.append("[File not found in any project root]\n")
            except Exception as e:
                inspection_report.append(f"\n### {file_path}\n")
                inspection_report.append(f"[Error reading file: {str(e)}]\n")

        return "\n".join(inspection_report)

    def apply_generated_changes(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        generated_files: list[dict],
        lock_owner: str,
        event_handler: EventHandler | None = None,
    ) -> list[str]:
        """Apply generated file changes to the workspace."""
        self._emit(event_handler, f"Applying {len(generated_files)} file changes for {work_packet.phase_id}...")

        written_paths = []
        for file_spec in generated_files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip()
            content = file_spec.get("content") or ""

            try:
                written = workspace.write_file(root_name, relative_path, content)
                written_paths.append(str(written))
                self._emit(event_handler, f"  ✓ Wrote {root_name}/{relative_path}")
            except WorkspaceIOError as e:
                self._emit(event_handler, f"  ✗ Failed to write {root_name}/{relative_path}: {e}")
                raise

        return written_paths

    def validate_phase(
        self,
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        event_handler: EventHandler | None = None,
    ) -> tuple[bool, list[ValidationResult]]:
        """Run validation commands for the phase."""
        if not work_packet.validation_commands:
            self._emit(event_handler, "No validation commands specified.")
            return True, []

        results: list[ValidationResult] = []
        all_passed = True

        for command in work_packet.validation_commands:
            self._emit(event_handler, f"Running validation: {command}")
            try:
                result = self.execute_command(command, workspace.target_root, event_handler=event_handler)
                results.append(result)
                if result.passed:
                    self._emit(event_handler, f"  ✓ Passed")
                else:
                    self._emit(event_handler, f"  ✗ Failed")
                    all_passed = False
            except CommandPolicyViolation as e:
                self._emit(event_handler, f"  ⚠ Policy violation: {e}")
                all_passed = False
            except Exception as e:
                self._emit(event_handler, f"  ✗ Error: {e}")
                all_passed = False

        return all_passed, results

    def execute_command(
        self,
        command: str,
        working_dir: str | Path,
        timeout_seconds: int = 30,
        event_handler: EventHandler | None = None,
    ) -> ValidationResult:
        """Execute a shell command with safety policy enforcement."""
        self._check_command_policy(command)

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
            )
        except subprocess.TimeoutExpired:
            raise CommandExecutionError(f"Command timed out after {timeout_seconds}s: {command}")
        except Exception as e:
            raise CommandExecutionError(f"Command execution failed: {e}")

    def _check_command_policy(self, command: str) -> None:
        """Enforce safety policy for command execution."""
        command_lower = command.lower()

        # Block dangerous commands
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
            import re
            if re.search(pattern, command_lower):
                raise CommandPolicyViolation(f"Dangerous command pattern detected: {command}")

        # Validate against whitelist patterns
        is_safe = any(
            __import__("re").search(pattern, command_lower, __import__("re").IGNORECASE)
            for pattern in self.SAFE_COMMAND_PATTERNS.values()
        )

        if not is_safe and not any(cmd in command_lower for cmd in ["echo", "python", "npm", "cargo"]):
            raise CommandPolicyViolation(f"Command not in safety whitelist: {command}")

    def format_validation_results(self, results: list[ValidationResult]) -> str:
        """Format validation results into a readable report."""
        report_lines = ["# Validation Report\n"]

        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            report_lines.append(f"## {status}: {result.command}")
            report_lines.append(f"Exit Code: {result.exit_code}\n")

            if result.stdout:
                report_lines.append("### Output")
                report_lines.append("```")
                report_lines.append(result.stdout[:500])  # First 500 chars
                report_lines.append("```\n")

            if result.stderr:
                report_lines.append("### Errors")
                report_lines.append("```")
                report_lines.append(result.stderr[:500])  # First 500 chars
                report_lines.append("```\n")

        return "\n".join(report_lines)

    def _emit(self, event_handler: EventHandler | None, message: str) -> None:
        if event_handler:
            event_handler(message)
