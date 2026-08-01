"""Autobots CLI UI - Unique terminal interface for the swarm orchestrator."""

from __future__ import annotations

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
        "  [bold #3B82F6]→[/] Projects directory",
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
