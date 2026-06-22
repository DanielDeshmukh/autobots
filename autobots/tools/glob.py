from __future__ import annotations

from pathlib import Path
from typing import Any

from autobots.tools.base import Tool, ToolResult


class GlobTool(Tool):
    name = "glob"
    description = "Find files by glob pattern. Supports patterns like **/*.py, src/**/*.ts, etc."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
            },
            "required": ["pattern"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern")
        search_path = kwargs.get("path", ".")

        if not pattern:
            return ToolResult.failure("pattern is required")

        base = Path(search_path)
        if not base.exists():
            return ToolResult.failure(f"Path not found: {search_path}")

        if not base.is_dir():
            return ToolResult.failure(f"Not a directory: {search_path}")

        try:
            matches = sorted(str(p) for p in base.glob(pattern) if p.is_file())
        except Exception as e:
            return ToolResult.failure(f"Error matching pattern: {e}")

        if not matches:
            return ToolResult.success(
                f"No files found matching '{pattern}' in {search_path}",
                matches=[],
                count=0,
            )

        output = "\n".join(matches)
        return ToolResult.success(
            output,
            matches=matches,
            count=len(matches),
        )
