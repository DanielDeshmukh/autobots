from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from autobots.tools.base import Tool, ToolResult


class GrepTool(Tool):
    name = "grep"
    description = "Search file contents using regex. Returns matching file:line pairs."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include (e.g., '*.py', '*.{ts,tsx}')",
                },
            },
            "required": ["pattern"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern")
        search_path = kwargs.get("path", ".")
        include = kwargs.get("include")

        if not pattern:
            return ToolResult.failure("pattern is required")

        base = Path(search_path)
        if not base.exists():
            return ToolResult.failure(f"Path not found: {search_path}")

        if not base.is_dir():
            return ToolResult.failure(f"Not a directory: {search_path}")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult.failure(f"Invalid regex pattern: {e}")

        include_patterns = None
        if include:
            include_patterns = [
                p.strip() for p in include.replace("{", "").replace("}", "").split(",")
            ]

        matches = []
        files_searched = 0

        try:
            for path in base.rglob("*"):
                if not path.is_file():
                    continue

                if include_patterns and not any(
                    path.match(ip) for ip in include_patterns
                ):
                    continue

                files_searched += 1
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                for i, line in enumerate(content.splitlines(), start=1):
                    if regex.search(line):
                        truncated = line[:2000] + "..." if len(line) > 2000 else line
                        matches.append(f"{path}:{i}: {truncated}")
        except Exception as e:
            return ToolResult.failure(f"Error searching files: {e}")

        if not matches:
            return ToolResult.success(
                f"No matches found for '{pattern}' in {search_path}",
                matches=[],
                count=0,
                files_searched=files_searched,
            )

        output = "\n".join(matches)
        return ToolResult.success(
            output,
            matches=matches,
            count=len(matches),
            files_searched=files_searched,
        )
