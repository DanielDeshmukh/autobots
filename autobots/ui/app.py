"""App controller — wires pipeline events to UI renderers."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text

from .events import EventBus, EventType, Event, get_event_bus
from .theme import Theme, load_theme
from .symbols import get_symbols, Symbols
from . import (
    render_welcome,
    render_prompt_hint,
    render_status_line,
    render_user_message,
    render_inspection,
    render_plan,
    render_swarm_compact,
    render_swarm_expanded,
    render_tool_compact,
    render_validation_start,
    render_validation_check,
    render_validation_summary,
    render_repair_start,
    render_repair_action,
    render_revalidation,
    render_completion,
    render_compaction_start,
    render_compaction_done,
)


class AppState:
    """Current application state."""
    
    def __init__(self):
        self.goal: str = ""
        self.output_dir: str = ""
        self.start_time: float = 0
        self.phase: str = "idle"
        self.clusters: dict[str, dict] = {}
        self.files_written: list[str] = []
        self.current_round: int = 0
        self.max_rounds: int = 3
        self.validation_passed: int = 0
        self.validation_failed: int = 0
        self.expanded_view: bool = False
        self.context_pct: float = 100.0


class App:
    """Main application controller.
    
    Wires pipeline events to UI renderers. The pipeline emits events
    through the EventBus, and App renders them to the console.
    
    Usage:
        app = App(console)
        app.start("Build a calculator", "/path/to/output")
        # ... pipeline runs, events are rendered ...
        app.finish()
    """
    
    def __init__(
        self,
        console: Console,
        theme: Theme | None = None,
        ascii_mode: bool = False,
    ):
        self.console = console
        self.theme = theme or load_theme()
        self.symbols = get_symbols(ascii_mode)
        self.state = AppState()
        self.bus = get_event_bus()
        self._live: Live | None = None
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Register event handlers."""
        self.bus.on(EventType.PLAN_STARTED, self._on_plan_started)
        self.bus.on(EventType.PLAN_COMPLETED, self._on_plan_completed)
        self.bus.on(EventType.AGENT_STARTED, self._on_agent_started)
        self.bus.on(EventType.AGENT_UPDATED, self._on_agent_updated)
        self.bus.on(EventType.AGENT_COMPLETED, self._on_agent_completed)
        self.bus.on(EventType.TOOL_COMPLETED, self._on_tool_completed)
        self.bus.on(EventType.FILE_WRITTEN, self._on_file_written)
        self.bus.on(EventType.VALIDATION_STARTED, self._on_validation_started)
        self.bus.on(EventType.VALIDATION_COMPLETED, self._on_validation_completed)
        self.bus.on(EventType.REPAIR_STARTED, self._on_repair_started)
        self.bus.on(EventType.BUILD_STARTED, self._on_build_started)
        self.bus.on(EventType.BUILD_COMPLETED, self._on_build_completed)
        self.bus.on(EventType.BUILD_FAILED, self._on_build_failed)
        self.bus.on(EventType.HEALING_STARTED, self._on_healing_started)
        self.bus.on(EventType.HEALING_COMPLETED, self._on_healing_completed)
        self.bus.on(EventType.RUN_COMPLETED, self._on_run_completed)
        self.bus.on(EventType.RUN_FAILED, self._on_run_failed)
        self.bus.on(EventType.LOG, self._on_log)
        self.bus.on(EventType.ERROR, self._on_error)
    
    def start(self, goal: str, output_dir: str) -> None:
        """Start a new build session."""
        self.state.goal = goal
        self.state.output_dir = output_dir
        self.state.start_time = time.time()
        self.state.phase = "starting"
        
        # Update terminal title
        self._set_title(f"Autobots -- {goal}")
        
        # Render header
        self.console.print()
        self.console.print(f"[bold {self.theme.brand}]{self.symbols.active}[/] [bold]{goal}[/]")
        self.console.print()
    
    def finish(self, success: bool = True) -> None:
        """Finish the build session."""
        elapsed = time.time() - self.state.start_time
        
        if success:
            file_count = len(self.state.files_written)
            render_completion(
                self.console,
                summary=f"Built {self.state.goal}",
                files_changed=file_count,
                duration=self._format_duration(elapsed),
                theme=self.theme,
            )
        else:
            self.console.print(
                f"[bold {self.theme.error}]{self.symbols.failed} Build failed[/]"
            )
        
        # Reset terminal title
        self._set_title("Autobots")
    
    # ─── Event Handlers ──────────────────────────────────────────────────
    
    def _on_plan_started(self, event: Event) -> None:
        self.state.phase = "planning"
        task_count = event.data.get("task_count", 0)
        self.console.print(
            f"{self.symbols.active} [bold]{self.theme.primary}][/] "
            f"[dim]Planning {task_count} tasks...[/]"
        )
    
    def _on_plan_completed(self, event: Event) -> None:
        steps = event.data.get("steps", [])
        changes = event.data.get("changes", [])
        if steps:
            render_plan(
                self.console,
                steps=steps,
                expected_changes=changes,
                theme=self.theme,
            )
    
    def _on_agent_started(self, event: Event) -> None:
        cluster = event.data.get("cluster", "")
        task = event.data.get("task", "")
        self.state.phase = "building"
        
        if cluster not in self.state.clusters:
            self.state.clusters[cluster] = {"task": task, "status": "active"}
        else:
            self.state.clusters[cluster]["status"] = "active"
            self.state.clusters[cluster]["task"] = task
        
        self._render_cluster_status()
    
    def _on_agent_updated(self, event: Event) -> None:
        cluster = event.data.get("cluster", "")
        status = event.data.get("status", "active")
        detail = event.data.get("detail", "")
        
        if cluster in self.state.clusters:
            self.state.clusters[cluster]["status"] = status
            if detail:
                self.state.clusters[cluster]["detail"] = detail
        
        self._render_cluster_status()
    
    def _on_agent_completed(self, event: Event) -> None:
        cluster = event.data.get("cluster", "")
        if cluster in self.state.clusters:
            self.state.clusters[cluster]["status"] = "done"
        
        self._render_cluster_status()
    
    def _on_tool_completed(self, event: Event) -> None:
        action = event.data.get("action", "")
        path = event.data.get("path", "")
        stat = event.data.get("stat", "")
        
        render_tool_compact(
            self.console,
            action=action,
            path=path,
            stat=stat,
            theme=self.theme,
        )
    
    def _on_file_written(self, event: Event) -> None:
        path = event.data.get("path", "")
        if path:
            self.state.files_written.append(path)
    
    def _on_validation_started(self, event: Event) -> None:
        self.state.phase = "reviewing"
        render_validation_start(self.console, theme=self.theme)
    
    def _on_validation_completed(self, event: Event) -> None:
        checks = event.data.get("checks", [])
        for check in checks:
            render_validation_check(
                self.console,
                name=check.get("name", ""),
                status=check.get("status", ""),
                detail=check.get("detail", ""),
                elapsed=check.get("elapsed", ""),
                theme=self.theme,
            )
        
        passed = event.data.get("passed", 0)
        failed = event.data.get("failed", 0)
        self.state.validation_passed += passed
        self.state.validation_failed += failed
        
        render_validation_summary(
            self.console,
            passed=passed,
            failed=failed,
            theme=self.theme,
        )
    
    def _on_repair_started(self, event: Event) -> None:
        cluster = event.data.get("cluster", "Ratchet")
        issue_count = event.data.get("issue_count", 0)
        attempt = event.data.get("attempt", 1)
        max_attempts = event.data.get("max_attempts", 3)
        
        render_repair_start(
            self.console,
            cluster=cluster,
            issue_count=issue_count,
            attempt=attempt,
            max_attempts=max_attempts,
            theme=self.theme,
        )
    
    def _on_build_started(self, event: Event) -> None:
        self.state.phase = "building"
        self.console.print(
            f"{self.symbols.active} [bold]Building project...[/]"
        )
    
    def _on_build_completed(self, event: Event) -> None:
        self.console.print(
            f"{self.symbols.done} [bold {self.theme.success}]Build passed[/]"
        )
    
    def _on_build_failed(self, event: Event) -> None:
        error = event.data.get("error", "")
        self.console.print(
            f"{self.symbols.failed} [bold {self.theme.error}]Build failed[/]"
        )
        if error:
            self.console.print(f"  [dim]{error[:200]}[/]")
    
    def _on_healing_started(self, event: Event) -> None:
        round_num = event.data.get("round", 1)
        self.state.current_round = round_num
        self.console.print()
        self.console.print(
            f"{self.symbols.followup} [bold {self.theme.warning}]"
            f"Healing round {round_num}[/]"
        )
    
    def _on_healing_completed(self, event: Event) -> None:
        success = event.data.get("success", False)
        if success:
            self.console.print(
                f"{self.symbols.done} [bold {self.theme.success}]Healing succeeded[/]"
            )
    
    def _on_run_completed(self, event: Event) -> None:
        self.state.phase = "done"
    
    def _on_run_failed(self, event: Event) -> None:
        self.state.phase = "error"
        error = event.data.get("error", "Unknown error")
        self.console.print(
            f"{self.symbols.failed} [bold {self.theme.error}]{error}[/]"
        )
    
    def _on_log(self, event: Event) -> None:
        message = event.data.get("message", "")
        level = event.data.get("level", "info")
        
        if level == "error":
            style = f"{self.theme.error}"
        elif level == "warning":
            style = f"{self.theme.warning}"
        else:
            style = f"dim {self.theme.secondary}"
        
        self.console.print(f"  [{style}]{message}[/]")
    
    def _on_error(self, event: Event) -> None:
        message = event.data.get("message", "Unknown error")
        self.console.print(
            f"{self.symbols.failed} [bold {self.theme.error}]{message}[/]"
        )
    
    # ─── Helpers ─────────────────────────────────────────────────────────
    
    def _render_cluster_status(self) -> None:
        """Render compact cluster status tree."""
        if not self.state.clusters:
            return
        
        # Only show active/done clusters, not idle
        active = {
            k: v for k, v in self.state.clusters.items()
            if v.get("status") != "idle"
        }
        
        if not active:
            return
        
        elapsed = time.time() - self.state.start_time
        
        render_swarm_compact(
            self.console,
            task_name=self.state.goal,
            elapsed=self._format_duration(elapsed),
            clusters=[
                {"name": k, "task": v.get("task", ""), "status": v.get("status", "waiting")}
                for k, v in active.items()
            ],
            active_count=sum(1 for v in active.values() if v.get("status") in ("active", "running")),
            completed_count=sum(1 for v in active.values() if v.get("status") == "done"),
            theme=self.theme,
        )
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration as '1m 42s' or '45s'."""
        if seconds >= 60:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        return f"{seconds:.0f}s"
    
    def _set_title(self, title: str) -> None:
        """Set terminal title via OSC escape sequence."""
        try:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
        except Exception:
            pass
