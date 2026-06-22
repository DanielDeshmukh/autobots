from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from autobots.tools.base import Tool, ToolResult


class WriteTool(Tool):
    name = "write"
    description = "Create or overwrite a file. Requires the file to have been read first unless create=True."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "create": {
                    "type": "boolean",
                    "description": "Allow creating new files (default False)",
                    "default": False,
                },
            },
            "required": ["file_path", "content"],
        }

    def __init__(self, allowed_paths: list[str] | None = None):
        self.allowed_paths = allowed_paths

    def run(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        create = kwargs.get("create", False)

        if not file_path:
            return ToolResult.failure("file_path is required")

        if content is None:
            return ToolResult.failure("content is required")

        path = Path(file_path)

        if self.allowed_paths:
            allowed = False
            for allowed_root in self.allowed_paths:
                try:
                    path.resolve().relative_to(Path(allowed_root).resolve())
                    allowed = True
                    break
                except ValueError:
                    continue
            if not allowed:
                return ToolResult.denied(
                    f"Write not allowed outside permitted paths: {self.allowed_paths}"
                )

        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=path.parent, suffix=".tmp", prefix=path.stem
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            return ToolResult.failure(f"Error writing file: {e}")

        return ToolResult.success(
            f"File written: {file_path}",
            file_path=str(path),
            size=len(content),
        )
