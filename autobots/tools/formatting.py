from __future__ import annotations

from typing import Any

from autobots.tools.base import ToolResult, ToolStatus


def format_tool_result(result: ToolResult, tool_name: str = "") -> str:
    prefix = f"[{tool_name}] " if tool_name else ""

    if result.status == ToolStatus.OK:
        return f"{prefix}{result.output}"

    if result.status == ToolStatus.DENIED:
        return f"{prefix}DENIED: {result.error}"

    return f"{prefix}ERROR: {result.error}"


def format_tool_call(tool_name: str, args: dict[str, Any]) -> str:
    parts = [tool_name]
    for key, value in args.items():
        if isinstance(value, str) and len(value) > 100:
            parts.append(f"{key}={value[:100]}...")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def format_permission_prompt(tool_name: str, args: dict[str, Any]) -> str:
    lines = [f"Allow {tool_name}?"]
    if args:
        for key, value in args.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            lines.append(f"  {key}: {val_str}")
    lines.append("  [y]es / [n]o / [a]lways / [Esc] cancel")
    return "\n".join(lines)
