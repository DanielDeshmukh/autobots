"""Conversation transcript — renders messages, tool calls, and results."""

from __future__ import annotations

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

from .theme import Theme, load_theme
from .symbols import get_symbols, Symbols


def render_user_message(console: Console, text: str, theme: Theme | None = None) -> None:
    """Render a user message.
    
    Format:
    > Add refresh-token rotation and test the expiration behavior.
    """
    if theme is None:
        theme = load_theme()
    console.print(f"[bold theme.brand]>[/bold theme.brand]] {text}")


def render_assistant_message(console: Console, text: str, theme: Theme | None = None) -> None:
    """Render an assistant message (borderless)."""
    if theme is None:
        theme = load_theme()
    
    # Render as markdown for formatting
    md = Markdown(text)
    console.print(md)


def render_inspection(console: Console, items: list[dict], theme: Theme | None = None) -> None:
    """Render repository inspection activity.
    
    Format:
    ● Inspecting the authentication flow
      ├─ Read src/api/routes/auth.py
      ├─ Read src/services/tokens.py
      ├─ Search "refresh_token" in src                 12 matches
      └─ Read tests/test_auth.py                       lines 1-244
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    header = Text()
    header.append(f"{symbols.active} ", style=f"{theme.active}")
    header.append("Inspecting", style=f"bold {theme.primary}")
    console.print(header)
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = symbols.last if is_last else symbols.branch
        
        line = Text()
        line.append(f"  {connector} ", style=f"dim {theme.secondary}")
        
        action = item.get("action", "Read")
        path = item.get("path", "")
        detail = item.get("detail", "")
        
        line.append(f"{action} ", style=f"{theme.primary}")
        line.append(path, style=f"{theme.path}")
        
        if detail:
            # Right-align the detail
            padding = max(1, 50 - len(f"{action} {path}"))
            line.append(" " * padding, style=f"dim {theme.secondary}")
            line.append(detail, style=f"dim {theme.secondary}")
        
        console.print(line)


def render_plan(
    console: Console,
    *,
    title: str = "Implementation plan",
    steps: list[str] = None,
    expected_changes: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render an implementation plan.
    
    Format:
    ● Optimus prepared an implementation plan
    
      1. Add refresh-token identifiers and rotation metadata
      2. Revoke the previous token when a refresh succeeds
      ...
    
      Expected changes
      M  src/api/routes/auth.py
      A  src/services/token_store.py
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    header = Text()
    header.append(f"{symbols.active} ", style=f"{theme.active}")
    header.append(f"Optimus prepared ", style=f"{theme.primary}")
    header.append(title, style=f"bold {theme.primary}")
    console.print(header)
    console.print()
    
    if steps:
        for i, step in enumerate(steps, 1):
            console.print(f"  [dim {theme.secondary}]{i}.[/] {step}")
        console.print()
    
    if expected_changes:
        console.print(f"  [dim {theme.secondary}]Expected changes[/]")
        for change in expected_changes:
            status = change.get("status", "M")
            path = change.get("path", "")
            console.print(f"  [dim]{status}[/]  [{theme.path}]{path}[/]")
        console.print()


def render_completion_summary(
    console: Console,
    *,
    summary: str = "",
    changes: list[str] = None,
    validation: list[dict] = None,
    files_changed: int = 0,
    lines_added: int = 0,
    lines_removed: int = 0,
    snapshot: str = "",
    duration: str = "",
    cost: str = "",
    theme: Theme | None = None,
) -> None:
    """Render the completion response.
    
    Format:
    ● Implemented refresh-token rotation and replay protection.
    
      Changes
      - Added token identifiers and rotation metadata
      - Revoked previous refresh tokens after successful use
      ...
    
      Validation
      - 43 tests passed
      - Linting passed
      ...
    
      4 files changed · +237 -19
      Snapshot 01JAB92M · 4m 18s · estimated cost $0.18
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    # Header
    header = Text()
    header.append(f"{symbols.done} ", style=f"{theme.success}")
    header.append(summary, style=f"bold {theme.primary}")
    console.print(header)
    console.print()
    
    # Changes
    if changes:
        console.print(f"  [dim {theme.secondary}]Changes[/]")
        for change in changes:
            console.print(f"  [dim]-[/] {change}")
        console.print()
    
    # Validation
    if validation:
        console.print(f"  [dim {theme.secondary}]Validation[/]")
        for v in validation:
            status = v.get("status", "passed")
            label = v.get("label", "")
            detail = v.get("detail", "")
            style = f"{theme.success}" if status == "passed" else f"{theme.error}"
            console.print(f"  [{style}]{symbols.done}[/] {label}", end="")
            if detail:
                console.print(f" [dim]{detail}[/]", end="")
            console.print()
        console.print()
    
    # Stats
    stats = Text()
    if files_changed > 0:
        stats.append(f"  {files_changed} files changed", style=f"{theme.secondary}")
        if lines_added or lines_removed:
            stats.append(" · ", style=f"dim {theme.secondary}")
            if lines_added:
                stats.append(f"+{lines_added}", style=f"{theme.success}")
            if lines_removed:
                stats.append(f" -{lines_removed}", style=f"{theme.error}")
        console.print(stats)
    
    meta = Text()
    if snapshot:
        meta.append(f"  Snapshot {snapshot}", style=f"dim {theme.secondary}")
    if duration:
        meta.append(f" · {duration}", style=f"dim {theme.secondary}")
    if cost:
        meta.append(f" · estimated cost {cost}", style=f"dim {theme.secondary}")
    if meta.plain.strip():
        console.print(meta)
    
    console.print()
