"""Welcome screen — shown when a session starts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from ..theme import Theme, load_theme
from ..symbols import get_symbols


# ─── ASCII Mark ──────────────────────────────────────────────────────────────

MARK_WIDE = r"""[bold {brand}]
       ╱╲       AUTOBOTS
    ╭─╯  ╰─╮    Coding swarm for your terminal
    │  ▪ ▪ │
    ╰╮ ██ ╭╯
     ╰────╯[/]"""

MARK_NARROW = r"[bold {brand}]AUTOBOTS[/] [dim]Coding swarm for your terminal[/]"


# ─── Welcome Screen ──────────────────────────────────────────────────────────

def render_welcome(
    console: Console,
    *,
    theme: Optional[Theme] = None,
    username: Optional[str] = None,
    project_name: Optional[str] = None,
    project_path: Optional[str] = None,
    branch: Optional[str] = None,
    git_clean: bool = True,
    recent_sessions: Optional[list[dict]] = None,
    context_files: int = 0,
    mode: str = "supervised",
    profile: str = "balanced",
    api_connected: bool = True,
    setup_error: Optional[str] = None,
    ascii_mode: bool = False,
) -> None:
    """Render the welcome screen.
    
    Args:
        console: Rich console to render to
        theme: Color theme (loads default if None)
        username: User's name for greeting
        project_name: Current project name
        project_path: Current project path
        branch: Current git branch
        git_clean: Whether working tree is clean
        recent_sessions: List of recent session dicts
        context_files: Number of context files loaded
        mode: Execution mode (plan/supervised/milestone/autonomous)
        profile: Model selection profile
        api_connected: Whether NVIDIA NIM is connected
        setup_error: Error message to display instead of welcome
        ascii_mode: Use ASCII symbols
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols(ascii_mode)
    
    width = console.width or 80
    use_wide = width >= 100
    
    if setup_error:
        _render_setup_error(console, theme, setup_error, width, use_wide)
        return
    
    # Build content
    content_parts = []
    
    # Greeting
    if username:
        content_parts.append(Text(f"\n  Welcome back, {username}", style=f"bold {theme.primary}"))
    else:
        content_parts.append(Text(""))
    
    # Project info
    if project_name:
        project_line = Text()
        project_line.append(f"\n  {project_name}", style=f"bold {theme.primary}")
        if project_path:
            project_line.append(f"\n  {project_path}", style=f"dim {theme.secondary}")
        content_parts.append(project_line)
        
        if branch:
            branch_line = Text()
            branch_line.append(f"  {branch}", style=f"{theme.active}")
            if git_clean:
                branch_line.append(" · clean", style=f"dim {theme.secondary}")
            else:
                branch_line.append(" · modified", style=f"dim {theme.warning}")
            content_parts.append(branch_line)
    
    # Recent sessions
    if recent_sessions:
        sessions_text = Text()
        sessions_text.append("\n  Recent sessions\n", style=f"dim {theme.secondary}")
        for session in recent_sessions[:2]:
            name = session.get("name", "Unnamed")
            ago = session.get("ago", "")
            sessions_text.append(f"  {name}", style=f"{theme.path}")
            if ago:
                sessions_text.append(f"  {ago}", style=f"dim {theme.secondary}")
            sessions_text.append("\n")
        content_parts.append(sessions_text)
    
    # Status line
    status = Text()
    status.append("\n  ")
    if api_connected:
        status.append("NVIDIA NIM connected", style=f"{theme.success}")
    else:
        status.append("NVIDIA NIM not connected", style=f"{theme.error}")
    
    if context_files > 0:
        status.append(f" · {context_files} context files", style=f"dim {theme.secondary}")
    
    status.append(f" · {mode}", style=f"dim {theme.secondary}")
    status.append(f" · {profile}", style=f"dim {theme.secondary}")
    content_parts.append(status)
    
    # Assemble panel
    content = Group(*content_parts)
    
    title = Text()
    title.append("  AUTOBOTS", style=f"bold {theme.brand}")
    if use_wide:
        title.append("    Coding swarm for your terminal", style=f"dim {theme.secondary}")
    
    console.print()
    console.print(
        Panel(
            content,
            title=title,
            border_style=theme.border,
            padding=(0, 1),
            width=min(width - 4, 90) if use_wide else None,
        )
    )
    console.print()


def _render_setup_error(
    console: Console,
    theme: Theme,
    error: str,
    width: int,
    use_wide: bool,
) -> None:
    """Render the setup-required welcome screen."""
    content = Text()
    content.append("\n  Setup required\n", style=f"bold {theme.warning}")
    content.append(f"\n  {error}\n", style=f"{theme.error}")
    content.append(f"\n  Run /login to configure a key or /doctor for diagnostics.\n", style=f"dim {theme.secondary}")
    
    title = Text()
    title.append("  AUTOBOTS", style=f"bold {theme.brand}")
    
    console.print()
    console.print(
        Panel(
            content,
            title=title,
            border_style=theme.warning,
            padding=(0, 1),
            width=min(width - 4, 90) if use_wide else None,
        )
    )
    console.print()


def render_prompt_hint(console: Console, theme: Optional[Theme] = None) -> None:
    """Render the initial prompt hint after welcome."""
    if theme is None:
        theme = load_theme()
    console.print(
        f'[dim {theme.secondary}]Try "build a calculator" or type / for commands[/]'
    )
    console.print()
