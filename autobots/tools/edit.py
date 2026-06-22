from __future__ import annotations

from pathlib import Path
from typing import Any

from autobots.tools.base import Tool, ToolResult


class EditTool(Tool):
    name = "edit"
    description = "Replace an exact string in a file with a new string. Supports replaceAll mode."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact string to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "String to replace with (must differ from old_string)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default False, replaces first only)",
                    "default": False,
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path")
        old_string = kwargs.get("old_string")
        new_string = kwargs.get("new_string")
        replace_all = kwargs.get("replace_all", False)

        if not file_path:
            return ToolResult.failure("file_path is required")

        if old_string is None:
            return ToolResult.failure("old_string is required")

        if new_string is None:
            return ToolResult.failure("new_string is required")

        if old_string == new_string:
            return ToolResult.failure("old_string and new_string must differ")

        path = Path(file_path)
        if not path.exists():
            return ToolResult.failure(f"File not found: {file_path}")

        if not path.is_file():
            return ToolResult.failure(f"Not a file: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult.failure(f"Error reading file: {e}")

        count = content.count(old_string)
        if count == 0:
            return ToolResult.failure(
                f"old_string not found in {file_path}. "
                "Provide the exact surrounding lines for a unique match."
            )

        if not replace_all and count > 1:
            return ToolResult.failure(
                f"old_string found {count} times in {file_path}. "
                "Provide more surrounding context for a unique match, "
                "or use replace_all=true."
            )

        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1

        try:
            path.write_text(new_content, encoding="utf-8")
        except Exception as e:
            return ToolResult.failure(f"Error writing file: {e}")

        return ToolResult.success(
            f"Replaced {replacements} occurrence(s) in {file_path}",
            replacements=replacements,
            file_path=str(path),
        )
