from __future__ import annotations

from typing import Any

from autobots.tools.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> Tool | None:
        return self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def to_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    def run(self, tool_name: str, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult.failure(f"Unknown tool: {tool_name}")
        return tool.run(**kwargs)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        names = ", ".join(self._tools.keys())
        return f"ToolRegistry({names})"
