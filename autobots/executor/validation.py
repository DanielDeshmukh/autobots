"""Phase validation and feedback generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import ValidationResult
from .commands import CommandValidator

if TYPE_CHECKING:
    from .models import WorkPacket, EventHandler


class PhaseValidator:
    """Validates phases and generates validation reports."""

    @staticmethod
    def validate_phase(
        work_packet: WorkPacket,
        working_dir: str,
        allow_migrations: bool = False,
        event_handler: EventHandler | None = None,
    ) -> tuple[bool, list[ValidationResult]]:
        """Run validation commands for a work packet."""
        if not work_packet.validation_commands:
            PhaseValidator._emit(event_handler, "No validation commands specified.")
            return True, []

        results: list[ValidationResult] = []
        all_passed = True

        for command in work_packet.validation_commands:
            PhaseValidator._emit(event_handler, f"Running validation: {command}")
            try:
                result = CommandValidator.execute_command(
                    command,
                    working_dir,
                    allow_migrations=allow_migrations,
                )
                results.append(result)
                if result.passed:
                    PhaseValidator._emit(event_handler, f"  PASS ({result.category})")
                else:
                    PhaseValidator._emit(event_handler, f"  FAIL ({result.category})")
                    all_passed = False
            except Exception as exc:
                results.append(
                    ValidationResult(
                        command=command,
                        exit_code=-1,
                        stdout="",
                        stderr=str(exc),
                        passed=False,
                        category=CommandValidator.categorize_command(command),
                    )
                )
                PhaseValidator._emit(event_handler, f"  Error: {exc}")
                all_passed = False

        return all_passed, results

    @staticmethod
    def format_validation_results(results: list[ValidationResult]) -> str:
        """Format validation results into a report."""
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

    @staticmethod
    def summarize_validation_results(results: list[ValidationResult]) -> str:
        """Create a summary of validation results."""
        if not results:
            return "No validation commands were configured."

        failed = [result for result in results if not result.passed]
        if not failed:
            return f"Validation passed for {len(results)} command(s)."

        failed_labels = ", ".join(result.category for result in failed)
        return f"Validation failed for {len(failed)} of {len(results)} command(s): {failed_labels}."

    @staticmethod
    def build_validation_feedback(
        work_packet: WorkPacket,
        results: list[ValidationResult],
    ) -> dict:
        """Build feedback for a failed validation."""
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
            "validation_report": PhaseValidator.format_validation_results(results),
        }

    @staticmethod
    def _work_packet_allows_migrations(work_packet: WorkPacket) -> bool:
        """Check if work packet allows database migrations."""
        tokens = " ".join(work_packet.constraints).lower()
        return "allow migration" in tokens or "allow migrations" in tokens or "migrations allowed" in tokens

    @staticmethod
    def _emit(event_handler: EventHandler | None, message: str) -> None:
        if event_handler:
            event_handler(message)
