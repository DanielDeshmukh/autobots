"""Keyboard shortcuts and help screen."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme


# ─── Keyboard Shortcuts ──────────────────────────────────────────────────────

SHORTCUTS = [
    ("Enter", "Send message"),
    ("Shift+Enter", "Insert a new line"),
    ("Ctrl+J", "Insert a new line"),
    ("Esc", "Interrupt active generation"),
    ("Esc Esc", "Open rewind menu"),
    ("Ctrl+O", "Expand or collapse tool output"),
    ("Ctrl+R", "Search prompt history"),
    ("Ctrl+G", "Open the prompt in the configured editor"),
    ("Ctrl+L", "Clear the visible terminal"),
    ("Shift+Tab", "Cycle execution modes"),
    ("Ctrl+C", "Clear input or interrupt"),
    ("Ctrl+D", "Exit when the prompt is empty"),
]

INPUT_SHORTCUTS = [
    ("/", "Commands"),
    ("@", "Files and folders"),
    ("!", "Shell command"),
    ("#", "Save an instruction"),
]


def render_help(
    console: Console,
    *,
    theme: Theme | None = None,
) -> None:
    """Render the help screen with keyboard shortcuts.
    
    Format:
    Keyboard shortcuts
    
      Enter           Send message
      Shift+Enter     Insert a new line
      ...
    
    Input shortcuts
    
      /               Commands
      @               Files and folders
      !               Shell command
      #               Save an instruction
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Keyboard shortcuts[/]")
    console.print()
    
    for key, desc in SHORTCUTS:
        console.print(f"  [bold {theme.secondary}]{key:<16}[/] {desc}")
    
    console.print()
    console.print(f"  [bold {theme.primary}]Input shortcuts[/]")
    console.print()
    
    for key, desc in INPUT_SHORTCUTS:
        console.print(f"  [bold {theme.brand}]{key:<16}[/] {desc}")
    
    console.print()


def render_mode_switch(
    console: Console,
    *,
    current_mode: str,
    theme: Theme | None = None,
) -> None:
    """Render mode switch confirmation.
    
    Format:
    Switch to autonomous mode?
    
    Autobots will continue through phase gates without confirmation.
    Tool permissions, denied commands, workspace boundaries, and safety policies remain active.
    
    > 1. Switch for this session
      2. Cancel
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Switch to {current_mode} mode?[/]")
    console.print()
    console.print(f"  [dim {theme.secondary}]Autobots will continue through phase gates without confirmation.[/]")
    console.print(f"  [dim {theme.secondary}]Tool permissions, denied commands, workspace boundaries, and safety policies remain active.[/]")
    console.print()
    console.print(f"[bold {theme.brand}]>{[/bold {theme.brand}] 1. Switch for this session")
    console.print(f"  2. Cancel")
    console.print()
