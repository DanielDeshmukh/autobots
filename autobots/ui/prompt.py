"""Prompt composer — the input area with status line."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme


def render_status_line(
    console: Console,
    *,
    mode: str = "supervised",
    profile: str = "balanced",
    context_pct: float = 100.0,
    branch: str = "",
    modified: bool = False,
    theme: Theme | None = None,
) -> None:
    """Render the persistent status line below the prompt.
    
    Format:
        supervised · balanced · 100% context left · autobots-safety
    
    Modified branch shows asterisk:
        supervised · balanced · 72% context left · autobots-safety*
    """
    if theme is None:
        theme = load_theme()
    
    line = Text()
    line.append(f"  {mode}", style=f"{theme.secondary}")
    line.append(" · ", style=f"dim {theme.secondary}")
    line.append(profile, style=f"{theme.secondary}")
    line.append(" · ", style=f"dim {theme.secondary}")
    
    # Context percentage with color
    if context_pct >= 80:
        ctx_style = f"{theme.success}"
    elif context_pct >= 50:
        ctx_style = f"{theme.warning}"
    else:
        ctx_style = f"{theme.error}"
    
    line.append(f"{context_pct:.0f}% context left", style=ctx_style)
    
    if branch:
        line.append(" · ", style=f"dim {theme.secondary}")
        line.append(branch, style=f"{theme.secondary}")
        if modified:
            line.append("*", style=f"{theme.warning}")
    
    console.print(line)


def render_prompt_symbol(
    console: Console,
    *,
    theme: Theme | None = None,
) -> None:
    """Render the prompt symbol (>).
    
    This is the main input indicator. The actual input is handled
    by prompt_toolkit in the final implementation.
    """
    if theme is None:
        theme = load_theme()
    
    console.print(f"[bold {theme.brand}]>{[/bold {theme.brand}] ", end="")


def render_multiline_hint(console: Console, theme: Theme | None = None) -> None:
    """Show multiline input hint."""
    if theme is None:
        theme = load_theme()
    console.print(f"[dim {theme.secondary}]  Shift+Enter for new line · Ctrl+J for new line[/]")
