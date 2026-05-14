"""File inspection and application operations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import EventHandler
from ..workspace import TargetProjectWorkspace, WorkspaceIOError

if TYPE_CHECKING:
    from .models import WorkPacket


class FileOperations:
    """Handles file inspection and application operations."""

    @staticmethod
    def inspect_phase_files(
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        event_handler: EventHandler | None = None,
    ) -> str:
        """Inspect and report on phase-relevant files."""
        FileOperations._emit(event_handler, f"Inspecting {len(work_packet.relevant_files)} files for {work_packet.phase_id}...")

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

    @staticmethod
    def apply_generated_changes(
        workspace: TargetProjectWorkspace,
        work_packet: WorkPacket,
        generated_files: list[dict],
        lock_owner: str,
        event_handler: EventHandler | None = None,
    ) -> list[str]:
        """Apply file changes from generated output."""
        FileOperations._emit(event_handler, f"Applying {len(generated_files)} file changes for {work_packet.phase_id}...")

        written_paths: list[str] = []
        for file_spec in generated_files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip()
            content = file_spec.get("content") or ""

            try:
                written = workspace.write_file(root_name, relative_path, content)
                written_paths.append(str(written))
                FileOperations._emit(event_handler, f"  Wrote {root_name}/{relative_path}")
            except WorkspaceIOError as exc:
                FileOperations._emit(event_handler, f"  Failed to write {root_name}/{relative_path}: {exc}")
                raise

        return written_paths

    @staticmethod
    def _emit(event_handler: EventHandler | None, message: str) -> None:
        if event_handler:
            event_handler(message)
