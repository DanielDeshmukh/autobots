"""Slash command palette — categorized, searchable command menu."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from .theme import Theme, load_theme


# ─── Command Definitions ─────────────────────────────────────────────────────

COMMANDS: dict[str, list[tuple[str, str]]] = {
    "Workflow": [
        ("plan", "Create or revise an implementation plan"),
        ("run", "Execute the current plan"),
        ("steer", "Add instructions to the active run"),
        ("agents", "Show swarm and cluster activity"),
        ("tasks", "Show active and background tasks"),
    ],
    "Session": [
        ("clear", "Clear the current conversation"),
        ("compact", "Compact conversation context"),
        ("resume", "Open a previous session"),
        ("rename", "Rename the current session"),
        ("export", "Export the transcript"),
        ("cost", "Show tokens and estimated cost"),
    ],
    "Project": [
        ("status", "Show workspace and execution status"),
        ("diff", "Review workspace changes"),
        ("review", "Run a code review"),
        ("undo", "Restore a previous snapshot"),
        ("memory", "View loaded instructions"),
        ("context", "Inspect context usage"),
    ],
    "Configuration": [
        ("model", "Select model profile or models"),
        ("permissions", "Review permission rules"),
        ("config", "Open project configuration"),
        ("mcp", "Manage MCP servers"),
        ("hooks", "Review hooks"),
        ("doctor", "Run health checks"),
    ],
    "General": [
        ("home", "Show the welcome screen"),
        ("help", "Show commands and keyboard shortcuts"),
        ("exit", "Exit Autobots"),
    ],
}


def render_command_palette(
    console: Console,
    *,
    filter_text: str = "",
    theme: Theme | None = None,
) -> None:
    """Render the slash command palette.
    
    Format:
    > /
    
      Workflow
    > /plan          Create or revise an implementation plan
      /run           Execute the current plan
      ...
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"[bold theme.brand]>[/bold theme.brand]] /[filter_text]")
    console.print()
    
    for category, commands in COMMANDS.items():
        console.print(f"  [dim {theme.secondary}]{category}[/]")
        
        for cmd, desc in commands:
            if filter_text and filter_text not in cmd:
                continue
            
            # Highlight matching prefix
            if filter_text and cmd.startswith(filter_text):
                line = Text()
                line.append(f"  ", style=f"dim {theme.secondary}")
                line.append(f"/{cmd}", style=f"bold {theme.brand}")
                line.append(f"  {desc}", style=f"{theme.secondary}")
                console.print(line)
            else:
                console.print(f"  [dim {theme.secondary}]/{cmd}[/]  {desc}")
        
        console.print()


def render_command_help(
    console: Console,
    *,
    theme: Theme | None = None,
) -> None:
    """Render command help."""
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [dim {theme.secondary}]Type / followed by a command name[/]")
    console.print(f"  [dim {theme.secondary}]Use arrow keys to navigate, Enter to select[/]")
    console.print()
