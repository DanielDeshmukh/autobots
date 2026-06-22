from __future__ import annotations

from pathlib import Path
from typing import Any

from autobots.tools.base import Tool, ToolResult


class ReadTool(Tool):
    name = "read"
    description = "Read a file with optional offset and limit. Returns content with line numbers."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed, default 1)",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to return (default 2000)",
                    "default": 2000,
                },
            },
            "required": ["file_path"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path")
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit", 2000)

        if not file_path:
            return ToolResult.failure("file_path is required")

        path = Path(file_path)
        if not path.exists():
            return ToolResult.failure(f"File not found: {file_path}")

        if not path.is_file():
            return ToolResult.failure(f"Not a file: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return self._read_binary(path, offset, limit)
        except Exception as e:
            return ToolResult.failure(f"Error reading file: {e}")

        lines = content.splitlines()
        total = len(lines)
        start = max(0, offset - 1)
        end = min(total, start + limit)
        selected = lines[start:end]

        numbered = []
        for i, line in enumerate(selected, start=start + 1):
            truncated = line[:2000] + "..." if len(line) > 2000 else line
            numbered.append(f"{i}: {truncated}")

        output = "\n".join(numbered)
        if end < total:
            output += f"\n\n(End of file - total {total} lines)"

        return ToolResult.success(
            output,
            total_lines=total,
            start_line=start + 1,
            end_line=end,
        )

    def _read_binary(self, path: Path, offset: int, limit: int) -> ToolResult:
        try:
            content = path.read_bytes()
            ext = path.suffix.lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                import base64

                b64 = base64.b64encode(content).decode("ascii")
                return ToolResult.success(
                    f"[Image file: {path.name} ({len(content)} bytes)]",
                    image_base64=b64,
                    mime_type=f"image/{ext.lstrip('.')}",
                )
            if ext == ".pdf":
                return ToolResult.success(
                    f"[PDF file: {path.name} ({len(content)} bytes)]",
                    pdf_size=len(content),
                )
            return ToolResult.success(
                f"[Binary file: {path.name} ({len(content)} bytes)]",
                binary_size=len(content),
            )
        except Exception as e:
            return ToolResult.failure(f"Error reading binary file: {e}")
