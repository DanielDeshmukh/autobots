"""Autobots CLI UI - Unique terminal interface for the swarm orchestrator."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.columns import Columns
from rich.align import Align
from rich import box


# ─── Color Palette ───────────────────────────────────────────────────────────

class Colors:
    """Autobots brand colors."""
    BLUE = "#3B82F6"       # Primary (Optimus)
    AMBER = "#F59E0B"      # Accent (swarm glow)
    EMERALD = "#10B981"    # Success
    RED = "#EF4444"        # Error
    SLATE = "#0F172A"      # Surface
    WHITE = "#E2E8F0"      # Text
    GRAY = "#64748B"       # Muted
    PURPLE = "#A855F7"     # Specialist
    CYAN = "#06B6D4"       # Info


# ─── Swarm Monitor ───────────────────────────────────────────────────────────

class SwarmMonitor:
    """Real-time monitor for swarm pipeline progress.
    
    Usage:
        monitor = SwarmMonitor(console)
        monitor.start("Building calculator...")
        monitor.cluster_status("Jazz", "working")
        monitor.log("Jazz: Generating UI components")
        monitor.cluster_status("Jazz", "done")
        monitor.finish()
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.phase = "idle"
        self.cluster_states: dict[str, str] = {c: "idle" for c in CLUSTERS}
        self.logs: list[str] = []
        self.start_time: float = 0
        self._live: Optional[Live] = None
    
    def start(self, message: str = "Starting swarm...") -> None:
        """Start the monitoring dashboard."""
        self.start_time = time.time()
        self.phase = "starting"
        self.logs = [message]
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
        )
        self._live.start()
    
    def update_phase(self, phase: str) -> None:
        """Update the pipeline phase."""
        self.phase = phase
        self._refresh()
    
    def cluster_status(self, cluster: str, status: str) -> None:
        """Update a cluster's status."""
        if cluster in self.cluster_states:
            self.cluster_states[cluster] = status
            self._refresh()
    
    def log(self, message: str) -> None:
        """Add a log message."""
        self.logs.append(message)
        if len(self.logs) > 8:
            self.logs = self.logs[-8:]
        self._refresh()
    
    def finish(self, success: bool = True) -> None:
        """Finish monitoring and show final state."""
        if self._live:
            self.phase = "done" if success else "error"
            if not success:
                for c in self.cluster_states:
                    if self.cluster_states[c] == "working":
                        self.cluster_states[c] = "error"
            self._live.stop()
        self._live = None
    
    def _refresh(self) -> None:
        """Refresh the live display."""
        if self._live:
            self._live.update(self._render())
    
    def _render(self) -> Panel:
        """Render the current dashboard state."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        # Cluster table
        cluster_table = Table(
            box=box.SIMPLE,
            show_header=False,
            padding=(0, 1),
        )
        cluster_table.add_column("Cluster", style="bold")
        cluster_table.add_column("Status")
        cluster_table.add_column("Progress", min_width=20)
        
        for name, info in CLUSTERS.items():
            status = self.cluster_states.get(name, "idle")
            
            status_icon = {
                "idle":     "[dim]○[/]",
                "thinking": f"[{Colors.AMBER}]◎[/]",
                "working":  f"[{Colors.BLUE}]●[/]",
                "done":     f"[{Colors.EMERALD}]✓[/]",
                "error":    f"[{Colors.RED}]✗[/]",
            }.get(status, "[dim]○[/]")
            
            status_text = {
                "idle":     "[dim]Waiting[/]",
                "thinking": f"[bold {Colors.AMBER}]Thinking...[/]",
                "working":  f"[bold {Colors.BLUE}]Working...[/]",
                "done":     f"[bold {Colors.EMERALD}]Done[/]",
                "error":    f"[bold {Colors.RED}]Error[/]",
            }.get(status, "[dim]Waiting[/]")
            
            progress = _get_progress_bar(status)
            
            cluster_table.add_row(
                f"[{info['color']}]{info['icon']} {name}[/]",
                f"{status_icon} {status_text}",
                progress,
            )
        
        # Pipeline stages
        stage_map = {
            "idle": 0, "starting": 0, "planning": 0,
            "building": 1, "reviewing": 2, "done": 3, "error": 2,
        }
        current_stage = stage_map.get(self.phase, 0)
        
        stages_text = Text()
        for i, stage in enumerate(PIPELINE_STAGES):
            if i < current_stage:
                stages_text.append(" ■■■■■ ", style=Colors.EMERALD)
                stages_text.append(f"{stage} → ", style=f"bold {Colors.EMERALD}")
            elif i == current_stage:
                stages_text.append(" ■■■■■ ", style=Colors.AMBER)
                stages_text.append(f"{stage} → ", style=f"bold {Colors.AMBER}")
            else:
                stages_text.append(" □□□□□ ", style=Colors.GRAY)
                stages_text.append(f"{stage} → ", style=f"dim {Colors.GRAY}")
        
        if stages_text.plain.endswith(" → "):
            stages_text.plain = stages_text.plain[:-3]
        
        # Logs
        logs_text = Text()
        for log in self.logs[-5:]:
            logs_text.append(f"  › {log}\n", style=f"dim {Colors.GRAY}")
        
        # Combine
        content = Text()
        content.append_text(cluster_table)
        content.append("\n  ")
        content.append_text(stages_text)
        content.append("\n\n")
        content.append_text(logs_text)
        
        border_color = Colors.AMBER
        if self.phase == "done":
            border_color = Colors.EMERALD
        elif self.phase == "error":
            border_color = Colors.RED
        
        return Panel(
            content,
            title=f"[bold]Swarm Pipeline[/] [dim]{elapsed:.0f}s[/]",
            border_style=border_color,
            box=box.ROUNDED,
        )


# ─── ASCII Art ───────────────────────────────────────────────────────────────

LOGO = r"""[bold #3B82F6]
    ___    _      _    _____                   
   / _ \  / \    / \  |_   _|                  
  / /_)/ / _ \  / _ \   | |                    
 / ___/ / ___ \/ ___ \  | |                    
\/    /_/   \_\/   \_\ |_|                    
[/]
[bold #F59E0B]  Multi-Model Swarm Orchestrator[/]
[dim #64748B]  9 specialized AI models. One sentence. Complete project.[/]"""


LOGO_COMPACT = r"[bold #3B82F6]Autobots[/] [dim #64748B]v2.1.0[/]"


# ─── Cluster Definitions ─────────────────────────────────────────────────────

CLUSTERS = {
    "Optimus":   {"role": "Planning",      "color": "#3B82F6", "icon": "◆"},
    "Jazz":      {"role": "UI/UX",         "color": "#A855F7", "icon": "◇"},
    "Ratchet":   {"role": "Logic",         "color": "#10B981", "icon": "⚙"},
    "RedAlert":  {"role": "Safety",        "color": "#EF4444", "icon": "▲"},
    "Perceptor": {"role": "Build",         "color": "#F59E0B", "icon": "◎"},
    "Bumblebee": {"role": "Testing",       "color": "#EAB308", "icon": "◉"},
    "Ironhide":  {"role": "Security",      "color": "#64748B", "icon": "■"},
    "Wheeljack": {"role": "Innovation",    "color": "#06B6D4", "icon": "✦"},
    "UltraMagnus": {"role": "Coordination","color": "#EC4899", "icon": "◈"},
}

PIPELINE_STAGES = ["Plan", "Build", "Review", "Done"]


# ─── Console Setup ───────────────────────────────────────────────────────────

def get_console(quiet: bool = False) -> Console:
    """Get a configured Rich console."""
    return Console(
        quiet=quiet,
        highlight=False,
        markup=True,
    )


# ─── Rendering Helpers ───────────────────────────────────────────────────────

def render_logo(console: Console) -> None:
    """Render the Autobots logo."""
    console.print()
    console.print(Align.center(LOGO))
    console.print()


def render_logo_compact(console: Console) -> None:
    """Render compact logo for inline use."""
    console.print(LOGO_COMPACT)


def render_version(console: Console) -> None:
    """Render version info."""
    from autobots import __version__
    console.print(f"[dim #64748B]autobots {__version__}[/]")


def render_cluster_status_table(clusters: dict[str, str]) -> Table:
    """Render a table showing cluster status.
    
    Args:
        clusters: Dict of cluster_name -> status (idle/thinking/working/done/error)
    """
    table = Table(
        box=box.ROUNDED,
        border_style=Colors.BLUE,
        title="[bold]Swarm Pipeline[/]",
        title_style=Colors.AMBER,
        show_header=True,
        header_style=f"bold {Colors.BLUE}",
        padding=(0, 1),
    )
    table.add_column("Cluster", style="bold")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Progress", min_width=20)

    for name, info in CLUSTERS.items():
        status = clusters.get(name, "idle")
        status_style = {
            "idle":     f"[dim]{name}[/]",
            "thinking": f"[bold {Colors.AMBER}]● Thinking...[/]",
            "working":  f"[bold {Colors.BLUE}]● Working...[/]",
            "done":     f"[bold {Colors.EMERALD}]✓ Done[/]",
            "error":    f"[bold {Colors.RED}]✗ Error[/]",
        }.get(status, f"[dim]{status}[/]")

        progress = _get_progress_bar(status)
        table.add_row(
            f"[{info['color']}]{info['icon']} {name}[/]",
            f"[dim]{info['role']}[/]",
            status_style,
            progress,
        )

    return table


def _get_progress_bar(status: str, width: int = 15) -> str:
    """Generate a progress bar based on status."""
    if status == "idle":
        filled = "░" * width
        return f"[dim]{filled}[/]"
    elif status == "thinking":
        filled = "█" * (width // 3)
        empty = "░" * (width - width // 3)
        return f"[{Colors.AMBER}]{filled}{empty}[/]"
    elif status == "working":
        filled = "█" * (width * 2 // 3)
        empty = "░" * (width - width * 2 // 3)
        return f"[{Colors.BLUE}]{filled}{empty}[/]"
    elif status == "done":
        filled = "█" * width
        return f"[{Colors.EMERALD}]{filled}[/]"
    elif status == "error":
        filled = "█" * (width // 2)
        return f"[{Colors.RED}]{filled}[/]"
    return "░" * width


def render_pipeline_stages(current: int, elapsed: float = 0) -> Panel:
    """Render pipeline stage indicator."""
    stages_text = Text()
    for i, stage in enumerate(PIPELINE_STAGES):
        if i < current:
            stages_text.append(f" [{Colors.EMERALD}]■■■■■[/] ", style=Colors.EMERALD)
            stages_text.append(f"{stage} → ", style=f"bold {Colors.EMERALD}")
        elif i == current:
            stages_text.append(f" [{Colors.AMBER}]■■■■■[/] ", style=Colors.AMBER)
            stages_text.append(f"{stage} → ", style=f"bold {Colors.AMBER}")
        else:
            stages_text.append(f" [dim]□□□□□[/] ", style=Colors.GRAY)
            stages_text.append(f"{stage} → ", style=f"dim {Colors.GRAY}")

    # Remove trailing arrow
    if stages_text.plain.endswith(" → "):
        stages_text.plain = stages_text.plain[:-3]

    title = f"[bold]Pipeline[/]"
    if elapsed > 0:
        title += f" [dim]{elapsed:.0f}s elapsed[/]"

    return Panel(
        stages_text,
        title=title,
        border_style=Colors.AMBER,
        box=box.ROUNDED,
    )


def render_log_line(message: str, level: str = "info") -> Text:
    """Render a formatted log line."""
    prefix_style = {
        "info":    f"[{Colors.CYAN}]›[/]",
        "success": f"[{Colors.EMERALD}]✓[/]",
        "warning": f"[{Colors.AMBER}]⚠[/]",
        "error":   f"[{Colors.RED}]✗[/]",
        "cluster": f"[{Colors.PURPLE}]●[/]",
    }.get(level, f"[{Colors.GRAY}]·[/]")

    text = Text()
    text.append(f" {prefix_style} ", style="default")
    text.append(message, style="default" if level == "info" else f"dim {Colors.GRAY}")
    return text


def render_completion_panel(
    project_name: str,
    project_path: Path,
    file_count: int,
    elapsed: float,
    errors: int = 0,
) -> Panel:
    """Render the build completion summary."""
    content = Text()
    content.append(f"\n  ✓ ", style=f"bold {Colors.EMERALD}")
    content.append(f"{project_name} ", style=f"bold {Colors.WHITE}")
    content.append(f"built in ", style=f"dim {Colors.GRAY}")
    content.append(f"{elapsed:.0f}s\n", style=f"bold {Colors.AMBER}")


def render_cluster_dashboard(phase: str = "idle") -> Panel:
    """Render the live cluster dashboard showing swarm status.
    
    Args:
        phase: Current pipeline phase (idle/planning/building/reviewing/done/error)
    """
    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Cluster", style="bold")
    table.add_column("Status")
    table.add_column("Progress", min_width=20)
    
    # Determine cluster statuses based on phase
    cluster_statuses = {
        "idle":     {c: "idle" for c in CLUSTERS},
        "starting": {"Optimus": "thinking", **{c: "idle" for c in CLUSTERS if c != "Optimus"}},
        "planning": {"Optimus": "working", **{c: "idle" for c in CLUSTERS if c != "Optimus"}},
        "building": {
            "Optimus": "done",
            "Jazz": "working",
            "Ratchet": "working",
            "UltraMagnus": "working",
            "Perceptor": "thinking",
            **{c: "idle" for c in CLUSTERS if c not in ["Optimus", "Jazz", "Ratchet", "UltraMagnus", "Perceptor"]},
        },
        "reviewing": {
            "Optimus": "done",
            "Jazz": "done",
            "Ratchet": "done",
            "UltraMagnus": "done",
            "RedAlert": "working",
            "Perceptor": "thinking",
            **{c: "idle" for c in CLUSTERS if c not in ["Optimus", "Jazz", "Ratchet", "UltraMagnus", "RedAlert", "Perceptor"]},
        },
        "done": {c: "done" for c in CLUSTERS},
        "error": {
            **{c: "done" for c in CLUSTERS if c not in ["RedAlert", "Ratchet"]},
            "RedAlert": "error",
            "Ratchet": "working",
        },
    }
    
    statuses = cluster_statuses.get(phase, cluster_statuses["idle"])
    
    for name, info in CLUSTERS.items():
        status = statuses.get(name, "idle")
        
        status_icon = {
            "idle":     "[dim]○[/]",
            "thinking": f"[{Colors.AMBER}]◎[/]",
            "working":  f"[{Colors.BLUE}]●[/]",
            "done":     f"[{Colors.EMERALD}]✓[/]",
            "error":    f"[{Colors.RED}]✗[/]",
        }.get(status, "[dim]○[/]")
        
        status_text = {
            "idle":     "[dim]Waiting[/]",
            "thinking": f"[bold {Colors.AMBER}]Thinking...[/]",
            "working":  f"[bold {Colors.BLUE}]Working...[/]",
            "done":     f"[bold {Colors.EMERALD}]Done[/]",
            "error":    f"[bold {Colors.RED}]Error[/]",
        }.get(status, "[dim]Waiting[/]")
        
        progress = _get_progress_bar(status)
        
        table.add_row(
            f"[{info['color']}]{info['icon']} {name}[/]",
            f"{status_icon} {status_text}",
            progress,
        )
    
    # Pipeline stages
    stage_map = {
        "idle": 0,
        "starting": 0,
        "planning": 0,
        "building": 1,
        "reviewing": 2,
        "done": 3,
        "error": 2,
    }
    current_stage = stage_map.get(phase, 0)
    
    stages_text = Text()
    for i, stage in enumerate(PIPELINE_STAGES):
        if i < current_stage:
            stages_text.append(" ■■■■■ ", style=Colors.EMERALD)
            stages_text.append(f"{stage} → ", style=f"bold {Colors.EMERALD}")
        elif i == current_stage:
            stages_text.append(" ■■■■■ ", style=Colors.AMBER)
            stages_text.append(f"{stage} → ", style=f"bold {Colors.AMBER}")
        else:
            stages_text.append(" □□□□□ ", style=Colors.GRAY)
            stages_text.append(f"{stage} → ", style=f"dim {Colors.GRAY}")
    
    if stages_text.plain.endswith(" → "):
        stages_text.plain = stages_text.plain[:-3]
    
    # Build the panel
    content = Text()
    content.append_text(table)
    content.append("\n")
    content.append_text(stages_text)
    
    return Panel(
        content,
        title="[bold]Swarm Pipeline[/]",
        border_style=Colors.AMBER if phase not in ("done", "error") else Colors.EMERALD if phase == "done" else Colors.RED,
        box=box.ROUNDED,
    )

    stats = Text()
    stats.append(f"    {file_count} files written", style=f"{Colors.EMERALD}")
    if errors > 0:
        stats.append(f", {errors} errors", style=f"{Colors.RED}")
    else:
        stats.append(f", 0 errors", style=f"{Colors.EMERALD}")

    content.append_text(stats)
    content.append(f"\n    Ready: ", style=f"dim {Colors.GRAY}")
    content.append(f"cd {project_path.name} && npm install", style=f"bold {Colors.CYAN}")
    content.append("\n")

    return Panel(
        content,
        border_style=Colors.EMERALD,
        box=box.ROUNDED,
    )


def render_wizard_step(step: int, total: int, title: str) -> Panel:
    """Render a wizard step header."""
    content = Text()
    content.append(f"  Step {step}/{total}: ", style=f"dim {Colors.GRAY}")
    content.append(title, style=f"bold {Colors.WHITE}")
    return Panel(
        content,
        border_style=Colors.BLUE,
        box=box.ROUNDED,
    )


# ─── First-Run Wizard ────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".autobots"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _load_preferences() -> dict:
    """Load saved preferences from config file."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    
    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)
    return data.get("autobots", {})


def _save_preferences(prefs: dict) -> None:
    """Save preferences to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    lines = ["[autobots]"]
    for key, value in prefs.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    
    CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_first_run() -> bool:
    """Check if this is the first time running autobots."""
    prefs = _load_preferences()
    return "projects_dir" not in prefs


def get_projects_dir() -> Path:
    """Get the configured projects directory."""
    prefs = _load_preferences()
    if "projects_dir" in prefs:
        return Path(prefs["projects_dir"]).expanduser().resolve()
    return Path.home() / "projects"


def run_first_run_wizard(console: Console) -> bool:
    """Run the interactive first-run setup wizard.
    
    Returns True if setup completed, False if cancelled.
    """
    console.print()
    console.print(Align.center(LOGO))
    console.print()
    
    console.print(
        Panel(
            "[bold]Welcome to Autobots![/]\n\n"
            "I'm a swarm of 9 specialized AI models that build complete\n"
            "projects from a single sentence. No code writing needed.\n\n"
            "[dim]Let's get you set up. This only takes a moment.[/]",
            border_style=Colors.BLUE,
            box=box.ROUNDED,
        )
    )
    console.print()
    
    # Step 1: Projects directory
    console.print(render_wizard_step(1, 2, "Projects Directory"))
    console.print()
    
    default_dir = str(Path.home() / "projects")
    console.print(
        f"  [dim]Where do you want projects built?[/]\n"
        f"  [dim]I'll create a subfolder for each project.[/]\n"
    )
    
    from rich.prompt import Prompt
    projects_input = Prompt.ask(
        "  [bold #3B82F6]>[/] Projects directory",
        default=default_dir,
        console=console,
    )
    projects_dir = Path(projects_input).expanduser().resolve()
    
    # Create if doesn't exist
    if not projects_dir.exists():
        projects_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"  [dim #64748B]Created {projects_dir}[/]")
    
    console.print(f"  [bold #10B981]✓[/] Projects will go to: [bold]{projects_dir}[/]")
    console.print()
    
    # Step 2: API key
    console.print(render_wizard_step(2, 2, "NVIDIA API Key"))
    console.print()
    
    console.print(
        f"  [dim]Autobots uses NVIDIA NIM models to generate code.[/]\n"
        f"  [dim]Get your free key at: [link]https://build.nvidia.com[/link][/]\n"
    )
    
    from rich.prompt import Password
    api_key = Password.ask(
        "  [bold #3B82F6]→[/] NVIDIA API Key",
        console=console,
    )
    
    if api_key and api_key.strip():
        _save_api_key(api_key.strip())
        console.print(f"  [bold #10B981]✓[/] API key saved")
    else:
        console.print(f"  [dim #64748B]Skipped. Set NVIDIA_API_KEY env var later.[/]")
    
    console.print()
    
    # Save preferences
    _save_preferences({
        "projects_dir": str(projects_dir),
        "setup_complete": True,
    })
    
    console.print(
        Panel(
            "[bold #10B981]Setup complete![/]\n\n"
            "Try: [bold #3B82F6]autobots build calculator[/]",
            border_style=Colors.EMERALD,
            box=box.ROUNDED,
        )
    )
    console.print()
    
    return True


def _save_api_key(api_key: str) -> None:
    """Save API key to .env file in engine root."""
    try:
        from .cli import ENGINE_ENV_PATH
        env_path = ENGINE_ENV_PATH
    except ImportError:
        env_path = Path(__file__).resolve().parent.parent / ".env"
    
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    
    # Update or add API key
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("NVIDIA_API_KEY="):
            lines[index] = f"NVIDIA_API_KEY={api_key}"
            updated = True
            break
    
    if not updated:
        lines.append(f"NVIDIA_API_KEY={api_key}")
    
    content = "\n".join(lines).strip() + "\n"
    env_path.write_text(content, encoding="utf-8")


# ─── Build Command ───────────────────────────────────────────────────────────

def run_build(args: list[str], console: Console) -> int:
    """Run the 'autobots build' command.
    
    Usage: autobots build <project-name> [--dir <output-dir>]
    """
    # Check first run
    if is_first_run():
        if not run_first_run_wizard(console):
            return 1
    
    # Parse arguments
    project_name = None
    output_dir = None
    
    i = 0
    while i < len(args):
        if args[i] == "--dir" and i + 1 < len(args):
            output_dir = Path(args[i + 1]).expanduser().resolve()
            i += 2
        elif not args[i].startswith("-"):
            project_name = args[i]
            i += 1
        else:
            console.print(f"[bold {Colors.RED}]Unknown flag: {args[i]}[/]")
            return 1
    
    if not project_name:
        console.print()
        console.print(
            Panel(
                "[bold]Usage:[/]\n\n"
                "  [bold #3B82F6]autobots build[/] [bold]<project-name>[/]\n\n"
                "[dim]Examples:[/]\n"
                "  autobots build calculator\n"
                "  autobots build todo-app\n"
                "  autobots build \"weather dashboard\"",
                title="Build Command",
                border_style=Colors.BLUE,
            )
        )
        return 1
    
    # Resolve output directory
    if not output_dir:
        projects_dir = get_projects_dir()
        output_dir = projects_dir / project_name
    
    # Check if directory exists
    if output_dir.exists() and any(output_dir.iterdir()):
        console.print(
            f"[bold {Colors.AMBER}]⚠ Directory already exists:[/] {output_dir}\n"
            f"[dim]Use a different name or remove the directory.[/]"
        )
        return 1
    
    # Check for NVIDIA API key
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        try:
            from dotenv import dotenv_values
            try:
                from .cli import ENGINE_ENV_PATH
                env_path = ENGINE_ENV_PATH
            except ImportError:
                env_path = Path(__file__).resolve().parent.parent / ".env"
            
            if env_path.exists():
                env_values = dotenv_values(env_path)
                api_key = (env_values.get("NVIDIA_API_KEY") or "").strip()
        except Exception:
            pass
    
    if not api_key:
        console.print(
            f"[bold {Colors.RED}]✗ No NVIDIA API key found.[/]\n\n"
            f"[dim]Set it with:[/]\n"
            f"  export NVIDIA_API_KEY=your-key-here\n\n"
            f"[dim]Or run 'autobots config' to set it.[/]"
        )
        return 1
    
    # Show build header
    console.print()
    console.print(Align.center(LOGO))
    console.print()
    
    console.print(
        Panel(
            f"[bold #3B82F6]Building:[/] [bold]{project_name}[/]\n"
            f"[dim #64748B]Output:[/] {output_dir}\n"
            f"[dim #64748B]Models:[/] 9 clusters, 100+ NIM models",
            border_style=Colors.AMBER,
            box=box.ROUNDED,
        )
    )
    console.print()
    
    # Run the swarm pipeline
    return _execute_swarm(project_name, output_dir, console)


def _execute_swarm(project_name: str, output_dir: Path, console: Console) -> int:
    """Execute the swarm pipeline with the new UI App controller."""
    from .swarm_pipeline import run_pipeline
    from .ui.app import App
    from .ui.theme import load_theme
    
    theme = load_theme()
    app = App(console, theme=theme)
    
    try:
        # Start the app
        app.start(project_name, str(output_dir))
        
        # Run pipeline (events are emitted automatically)
        result = run_pipeline(
            f"Build a {project_name} application",
            str(output_dir),
            max_healing_rounds=3,
        )
        
        # Show completion
        if result is not None:
            app.finish(success=True)
            return 0
        else:
            app.finish(success=False)
            return 1
            
    except KeyboardInterrupt:
        app.finish(success=False)
        console.print(f"\n[bold {theme.warning}]Build cancelled.[/]")
        return 1
    except Exception as e:
        app.finish(success=False)
        console.print(f"\n[bold {theme.error}]Error: {e}[/]")
        return 1
    except Exception as e:
        live.update(render_cluster_dashboard("error"))
        raise
