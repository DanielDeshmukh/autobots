"""Routing utilities and validation."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from ..workspace import TargetProjectWorkspace

if TYPE_CHECKING:
    pass


class ModelContractError(ValueError):
    """Raised when model output violates contract."""

    pass


class PayloadValidator:
    """Validates model payloads."""

    MIN_SUMMARY_LENGTH = 10
    MIN_LIST_ITEM_LENGTH = 5
    MIN_FILE_CONTENT_LENGTH = 10
    MAX_FILE_CONTENT_LENGTH = 500_000

    @staticmethod
    def parse_json(raw_content: str) -> dict:
        """Parse JSON from model response."""
        candidate = raw_content.strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if fenced_match:
            candidate = fenced_match.group(1)

        payload = json.loads(candidate)
        if not isinstance(payload, dict):
            raise ValueError("Model response must be a JSON object.")
        return payload

    @staticmethod
    def validate_command_payload(payload: dict) -> None:
        """Validate command stage payload."""
        summary = PayloadValidator._require_string(payload, "summary", "command payload")
        PayloadValidator._validate_summary_content(summary, "command payload")
        goals = PayloadValidator._require_string_list(payload, "implementation_goals", "command payload")
        PayloadValidator._validate_list_content(goals, "implementation_goals", "command payload")
        risks = PayloadValidator._require_string_list(payload, "risks", "command payload")
        PayloadValidator._validate_list_content(risks, "risks", "command payload")
        checks = PayloadValidator._require_string_list(payload, "acceptance_checks", "command payload")
        PayloadValidator._validate_list_content(checks, "acceptance_checks", "command payload")

    @staticmethod
    def validate_specialist_payload(payload: dict) -> None:
        """Validate specialist stage payload."""
        summary = PayloadValidator._require_string(payload, "summary", "specialist payload")
        PayloadValidator._validate_summary_content(summary, "specialist payload")
        notes = PayloadValidator._require_string_list(payload, "implementation_notes", "specialist payload")
        PayloadValidator._validate_list_content(notes, "implementation_notes", "specialist payload")
        PayloadValidator._require_file_list(payload, "specialist payload")

    @staticmethod
    def validate_review_payload(payload: dict) -> None:
        """Validate safety review payload."""
        status = PayloadValidator._require_string(payload, "status", "review payload").lower()
        if status not in {"pass", "revise"}:
            raise ModelContractError(
                f"review payload field 'status' must be 'pass' or 'revise', got '{payload.get('status')}'."
            )
        summary = PayloadValidator._require_string(payload, "summary", "review payload")
        PayloadValidator._validate_summary_content(summary, "review payload")
        issues = PayloadValidator._require_string_list(payload, "issues", "review payload")
        if status == "revise" and not issues:
            raise ModelContractError(
                "review payload with status 'revise' must include at least one issue."
            )
        PayloadValidator._validate_list_content(issues, "issues", "review payload")

    @staticmethod
    def validate_repair_payload(payload: dict) -> None:
        """Validate repair stage payload."""
        summary = PayloadValidator._require_string(payload, "summary", "repair payload")
        PayloadValidator._validate_summary_content(summary, "repair payload")
        PayloadValidator._require_file_list(payload, "repair payload")

    @staticmethod
    def _require_string(payload: dict, field: str, payload_name: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ModelContractError(
                f"{payload_name} field '{field}' must be a non-empty string."
            )
        return value

    @staticmethod
    def _require_string_list(payload: dict, field: str, payload_name: str) -> list[str]:
        value = payload.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ModelContractError(
                f"{payload_name} field '{field}' must be a list of strings."
            )
        return value

    @staticmethod
    def _require_file_list(payload: dict, payload_name: str) -> list[dict]:
        files = payload.get("files")
        if not isinstance(files, list):
            raise ModelContractError(f"{payload_name} field 'files' must be a list.")

        allowed_roots = TargetProjectWorkspace.ALLOWED_WRITE_ROOTS
        for index, file_spec in enumerate(files):
            if not isinstance(file_spec, dict):
                raise ModelContractError(
                    f"{payload_name} files[{index}] must be an object."
                )
            root_name = file_spec.get("root")
            relative_path = file_spec.get("path")
            content = file_spec.get("content")
            if root_name not in allowed_roots:
                raise ModelContractError(
                    f"{payload_name} files[{index}].root must be one of: {', '.join(sorted(allowed_roots))}."
                )
            if not isinstance(relative_path, str) or not relative_path.strip():
                raise ModelContractError(
                    f"{payload_name} files[{index}].path must be a non-empty string."
                )
            if not isinstance(content, str):
                raise ModelContractError(
                    f"{payload_name} files[{index}].content must be a string."
                )
            PayloadValidator._validate_file_content(content, relative_path, payload_name, index)
        return files

    @staticmethod
    def _validate_summary_content(summary: str, payload_name: str) -> None:
        """Validate that summary has meaningful content."""
        stripped = summary.strip()
        if len(stripped) < PayloadValidator.MIN_SUMMARY_LENGTH:
            raise ModelContractError(
                f"{payload_name} field 'summary' is too short ({len(stripped)} chars, minimum {PayloadValidator.MIN_SUMMARY_LENGTH})."
            )
        if len(set(stripped.lower().split())) < 3:
            raise ModelContractError(
                f"{payload_name} field 'summary' lacks sufficient unique words."
            )

    @staticmethod
    def _validate_list_content(items: list[str], field_name: str, payload_name: str) -> None:
        """Validate that list items have meaningful content."""
        if not items:
            return
        for index, item in enumerate(items):
            stripped = item.strip()
            if len(stripped) < PayloadValidator.MIN_LIST_ITEM_LENGTH:
                raise ModelContractError(
                    f"{payload_name} field '{field_name}'[{index}] is too short ({len(stripped)} chars)."
                )

    @staticmethod
    def _validate_file_content(content: str, file_path: str, payload_name: str, index: int) -> None:
        """Validate that file content is reasonable."""
        if not content.strip():
            raise ModelContractError(
                f"{payload_name} files[{index}] ('{file_path}') has empty content."
            )
        if len(content) > PayloadValidator.MAX_FILE_CONTENT_LENGTH:
            raise ModelContractError(
                f"{payload_name} files[{index}] ('{file_path}') exceeds maximum length ({len(content)} > {PayloadValidator.MAX_FILE_CONTENT_LENGTH})."
            )


class FileEntryHelper:
    """Helps with file entry operations."""

    @staticmethod
    def file_entries_from_paths(
        file_paths: list[str],
        workspace: TargetProjectWorkspace,
    ) -> list[dict]:
        """Convert file paths to file entries."""
        layout_roots = {
            "src": workspace.src_root,
            "app": workspace.target_root / "app",
            "lib": workspace.target_root / "lib",
            "tests": workspace.target_root / "tests",
            "docs": workspace.target_root / "docs",
            "scripts": workspace.target_root / "scripts",
            "context": workspace.context_root,
        }
        entries: list[dict] = []
        for file_path in file_paths:
            path = os.path.abspath(file_path)
            match = None
            for root_name, root_path in layout_roots.items():
                root_str = str(root_path)
                if path == root_str or path.startswith(root_str + os.sep):
                    match = (root_name, os.path.relpath(path, root_path))
                    break
            if match is None:
                continue
            root, relative = match
            entries.append(
                {
                    "root": root,
                    "path": relative.replace("\\", "/"),
                    "content": Path(path).read_text(encoding="utf-8"),
                }
            )
        return entries
