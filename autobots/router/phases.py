"""Phase reading and parsing utilities."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .models import PhaseRecord

if TYPE_CHECKING:
    from ..workspace import TargetProjectWorkspace


STATUS_PRIORITY = ("IN_PROGRESS", "PENDING")
STATUS_PATTERN = re.compile(r"\b(PENDING|IN_PROGRESS|COMPLETE)\b")
CHECKBOX_PATTERN = re.compile(r"\[( |x|~)\]")
PROGRESS_TRACKER_FILE = "progress-tracker.md"


class PhaseReader:
    """Reads and parses phase information."""

    @staticmethod
    def read_phase_documents(workspace: TargetProjectWorkspace) -> tuple[str, str]:
        """Read phase documents from workspace."""
        roadmap = workspace.read_context_file("roadmap.md")
        progress = workspace.read_context_file("progress-tracker.md")
        return roadmap, progress

    @staticmethod
    def find_next_phase(progress_text: str) -> PhaseRecord | None:
        """Find next phase to execute."""
        lines = progress_text.splitlines()
        parsed = [PhaseReader._parse_phase_line(index, line) for index, line in enumerate(lines)]
        parsed = [phase for phase in parsed if phase is not None]

        for status in STATUS_PRIORITY:
            for phase in parsed:
                if phase.status == status:
                    return phase
        return None

    @staticmethod
    def _parse_phase_line(index: int, line: str) -> PhaseRecord | None:
        """Parse a phase line from progress tracker."""
        status_match = STATUS_PATTERN.search(line)
        if status_match:
            status = status_match.group(1)
            title = STATUS_PATTERN.sub("", line, count=1)
            title = PhaseReader._clean_phase_title(title)
            return PhaseRecord(index, line, title or f"Phase {index + 1}", status)

        checkbox_match = CHECKBOX_PATTERN.search(line)
        if checkbox_match:
            marker = checkbox_match.group(0)
            status = {"[ ]": "PENDING", "[~]": "IN_PROGRESS", "[x]": "COMPLETE"}.get(marker)
            title = PhaseReader._clean_phase_title(CHECKBOX_PATTERN.sub("", line, count=1))
            return PhaseRecord(index, line, title or f"Phase {index + 1}", status)

        return None

    @staticmethod
    def _clean_phase_title(raw_title: str) -> str:
        """Clean phase title."""
        cleaned = raw_title.strip()
        cleaned = cleaned.strip("|")
        parts = [part.strip() for part in cleaned.split("|") if part.strip()]
        if parts:
            cleaned = " | ".join(parts)
        cleaned = re.sub(r"^[\-\*\d\.\)\s#:]+", "", cleaned)
        return cleaned.strip()

    @staticmethod
    def mark_phase_complete(progress_text: str, phase: PhaseRecord) -> str:
        """Mark a phase as complete."""
        return PhaseReader._update_phase_status(progress_text, phase, "COMPLETE")

    @staticmethod
    def _update_phase_status(progress_text: str, phase: PhaseRecord, status: str) -> str:
        """Update phase status."""
        lines = progress_text.splitlines()
        original = lines[phase.line_index]
        updated = STATUS_PATTERN.sub(status, original, count=1)

        if updated == original:
            checkbox = {"PENDING": "[ ]", "IN_PROGRESS": "[~]", "COMPLETE": "[x]"}[status]
            updated = CHECKBOX_PATTERN.sub(checkbox, original, count=1)
        if updated == original:
            updated = f"{original} {status}"

        lines[phase.line_index] = updated
        return "\n".join(lines) + ("\n" if progress_text.endswith("\n") else "")
