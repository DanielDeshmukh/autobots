"""Non-interactive output modes — plain, json, ascii."""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

from rich.console import Console

from ..theme import Theme, load_theme


# ─── Plain Output ────────────────────────────────────────────────────────────

class PlainRenderer:
    """Non-interactive plain text renderer.
    
    Format:
    [inspect] Reading repository
    [tool] Read src/services/tokens.py
    [tool] Search "refresh_token" in src: 12 matches
    [implement] Updated src/services/tokens.py: +47 -8
    [validate] Tests: 43 passed
    [complete] Refresh-token rotation implemented
    """
    
    def __init__(self, console: Console | None = None):
        self.console = console or Console(file=sys.stdout)
    
    def inspect(self, message: str) -> None:
        self.console.print(f"[inspect] {message}")
    
    def tool(self, message: str) -> None:
        self.console.print(f"[tool] {message}")
    
    def implement(self, message: str) -> None:
        self.console.print(f"[implement] {message}")
    
    def validate(self, message: str) -> None:
        self.console.print(f"[validate] {message}")
    
    def complete(self, message: str) -> None:
        self.console.print(f"[complete] {message}")
    
    def error(self, message: str) -> None:
        self.console.print(f"[error] {message}")
    
    def warning(self, message: str) -> None:
        self.console.print(f"[warning] {message}")
    
    def info(self, message: str) -> None:
        self.console.print(f"[info] {message}")


# ─── JSON Output ─────────────────────────────────────────────────────────────

class JsonRenderer:
    """JSON event output renderer.
    
    Format:
    {
        "event": "tool.completed",
        "tool": "Edit",
        "path": "src/services/tokens.py",
        "added": 47,
        "removed": 8,
        "duration_ms": 382
    }
    """
    
    def __init__(self, file=None):
        self.file = file or sys.stdout
    
    def emit(self, event: str, data: dict[str, Any] | None = None) -> None:
        """Emit a JSON event."""
        payload = {"event": event}
        if data:
            payload.update(data)
        
        line = json.dumps(payload, ensure_ascii=False)
        print(line, file=self.file)
    
    def tool_completed(
        self,
        tool: str,
        path: str = "",
        added: int = 0,
        removed: int = 0,
        duration_ms: int = 0,
    ) -> None:
        self.emit("tool.completed", {
            "tool": tool,
            "path": path,
            "added": added,
            "removed": removed,
            "duration_ms": duration_ms,
        })
    
    def phase_started(self, phase: str, task: str = "") -> None:
        self.emit("phase.started", {"phase": phase, "task": task})
    
    def phase_completed(self, phase: str, status: str = "passed") -> None:
        self.emit("phase.completed", {"phase": phase, "status": status})
    
    def agent_started(self, cluster: str, task: str = "") -> None:
        self.emit("agent.started", {"cluster": cluster, "task": task})
    
    def agent_completed(self, cluster: str, status: str = "done") -> None:
        self.emit("agent.completed", {"cluster": cluster, "status": status})
    
    def validation_started(self) -> None:
        self.emit("validation.started")
    
    def validation_completed(
        self,
        passed: int = 0,
        failed: int = 0,
    ) -> None:
        self.emit("validation.completed", {"passed": passed, "failed": failed})
    
    def run_completed(
        self,
        summary: str = "",
        files_changed: int = 0,
        duration_ms: int = 0,
    ) -> None:
        self.emit("run.completed", {
            "summary": summary,
            "files_changed": files_changed,
            "duration_ms": duration_ms,
        })
    
    def run_failed(self, error: str = "") -> None:
        self.emit("run.failed", {"error": error})


# ─── ASCII Mode ──────────────────────────────────────────────────────────────

def enable_ascii_mode() -> None:
    """Enable ASCII mode globally.
    
    Sets AUTOBOTS_ASCII=1 env var and configures symbols.
    """
    import os
    os.environ["AUTOBOTS_ASCII"] = "1"


def is_ascii_mode() -> bool:
    """Check if ASCII mode is enabled."""
    import os
    return os.getenv("AUTOBOTS_ASCII", "0") == "1"


def is_plain_mode() -> bool:
    """Check if plain output mode is active (stdout not a TTY)."""
    return not sys.stdout.isatty()


def is_json_mode() -> bool:
    """Check if JSON output mode is requested."""
    import os
    return os.getenv("AUTOBOTS_OUTPUT", "") == "json"
