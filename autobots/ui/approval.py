"""Permission prompts — file edit, shell command, dangerous command."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .theme import Theme, load_theme


def render_file_edit_prompt(
    console: Console,
    *,
    path: str,
    description: str = "",
    changes_added: int = 0,
    changes_removed: int = 0,
    theme: Theme | None = None,
) -> None:
    """Render file edit approval prompt.
    
    Format:
    ╭─ Edit file ───────────────────────────────────────────────────────────╮
    │                                                                        │
    │  src/services/tokens.py                                                │
    │                                                                        │
    │  Adds refresh-token identifiers, rotation, and replay detection.       │
    │  Changes: +47 -8                                                       │
    │                                                                        │
    ╰────────────────────────────────────────────────────────────────────────╯
    
    Do you want Autobots to make this edit?
    
    > 1. Yes
      2. Yes, allow file edits for this session
      3. No, and tell Autobots what to do differently
    """
    if theme is None:
        theme = load_theme()
    
    content = Text()
    content.append(f"\n  {path}\n", style=f"bold {theme.path}")
    
    if description:
        content.append(f"\n  {description}\n", style=f"{theme.primary}")
    
    changes = Text()
    if changes_added or changes_removed:
        changes.append("  Changes: ", style=f"dim {theme.secondary}")
        if changes_added:
            changes.append(f"+{changes_added}", style=f"{theme.success}")
        if changes_removed:
            changes.append(f" -{changes_removed}", style=f"{theme.error}")
        content.append_text(changes)
        content.append("\n")
    
    console.print(
        Panel(
            content,
            title="[bold]Edit file[/]",
            border_style=theme.border,
            padding=(0, 1),
        )
    )
    console.print()
    console.print("Do you want Autobots to make this edit?")
    console.print()
    console.print(f"[bold theme.brand]>[/bold theme.brand]] 1. Yes")
    console.print(f"  2. Yes, allow file edits for this session")
    console.print(f"  3. No, and tell Autobots what to do differently")
    console.print()


def render_shell_command_prompt(
    console: Console,
    *,
    command: str,
    working_dir: str = "",
    policy: str = "Allowed command · approval required",
    theme: Theme | None = None,
) -> None:
    """Render shell command approval prompt.
    
    Format:
    ╭─ Run command ──────────────────────────────────────────────────────────╮
    │                                                                        │
    │  python -m pytest tests/test_auth.py -q                                │
    │                                                                        │
    │  Working directory  ~/code/api                                          │
    │  Policy             Allowed command · approval required                 │
    │                                                                        │
    ╰────────────────────────────────────────────────────────────────────────╯
    
    > 1. Run this command
      2. Always allow this exact command during this session
      3. Deny and provide instructions
    """
    if theme is None:
        theme = load_theme()
    
    content = Text()
    content.append(f"\n  {command}\n", style=f"bold {theme.primary}")
    
    if working_dir:
        content.append(f"\n  Working directory  ", style=f"dim {theme.secondary}")
        content.append(working_dir, style=f"{theme.path}")
    
    if policy:
        content.append(f"\n  Policy             ", style=f"dim {theme.secondary}")
        content.append(policy, style=f"{theme.secondary}")
    
    content.append("\n")
    
    console.print(
        Panel(
            content,
            title="[bold]Run command[/]",
            border_style=theme.border,
            padding=(0, 1),
        )
    )
    console.print()
    console.print(f"[bold theme.brand]>[/bold theme.brand]] 1. Run this command")
    console.print(f"  2. Always allow this exact command during this session")
    console.print(f"  3. Deny and provide instructions")
    console.print()


def render_dangerous_command_prompt(
    console: Console,
    *,
    command: str,
    reason: str = "This command matches a denied command policy.",
    theme: Theme | None = None,
) -> None:
    """Render dangerous command blocked prompt.
    
    Format:
    ╭─ Command blocked ──────────────────────────────────────────────────────╮
    │                                                                        │
    │  rm -rf build/                                                         │
    │                                                                        │
    │  This command matches a denied command policy.                          │
    │  Autobots will not execute it.                                         │
    │                                                                        │
    ╰────────────────────────────────────────────────────────────────────────╯
    """
    if theme is None:
        theme = load_theme()
    
    content = Text()
    content.append(f"\n  {command}\n", style=f"bold {theme.error}")
    content.append(f"\n  {reason}\n", style=f"{theme.secondary}")
    content.append(f"  Autobots will not execute it.\n", style=f"{theme.error}")
    
    console.print(
        Panel(
            content,
            title="[bold]Command blocked[/]",
            border_style=theme.error,
            padding=(0, 1),
        )
    )
    console.print()


def render_feedback_prompt(console: Console, theme: Theme | None = None) -> None:
    """Render feedback input prompt after denying an action."""
    if theme is None:
        theme = load_theme()
    console.print(f"[dim {theme.secondary}]Tell Autobots what to do instead[/]")
    console.print(f"[bold theme.brand]>[/bold theme.brand]] ", end="")
