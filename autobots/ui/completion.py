"""Completion response — shows results after a successful build."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme
from ..symbols import get_symbols


def render_completion(
    console: Console,
    *,
    summary: str,
    changes: list[str] | None = None,
    validation: list[dict] | None = None,
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
    
      Validation
      ✓ 43 tests passed
      ✓ Linting passed
      ✓ Type checking passed
    
      4 files changed · +237 -19
      Snapshot 01JAB92M · 4m 18s · estimated cost $0.18
    
      Use /diff to review the changes or /undo to restore the snapshot.
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
    
    # Changes section
    if changes:
        console.print(f"  [dim {theme.secondary}]Changes[/]")
        for change in changes:
            console.print(f"  [dim {theme.secondary}]-[/] {change}")
        console.print()
    
    # Validation section
    if validation:
        console.print(f"  [dim {theme.secondary}]Validation[/]")
        for v in validation:
            status = v.get("status", "passed")
            label = v.get("label", "")
            style = f"{theme.success}" if status == "passed" else f"{theme.error}"
            icon = symbols.done if status == "passed" else symbols.failed
            console.print(f"  [{style}]{icon}[/] {label}")
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
    
    # Meta info
    meta_parts = []
    if snapshot:
        meta_parts.append(f"Snapshot {snapshot}")
    if duration:
        meta_parts.append(duration)
    if cost:
        meta_parts.append(f"estimated cost {cost}")
    
    if meta_parts:
        console.print(f"  [dim {theme.secondary}]{' · '.join(meta_parts)}[/]")
    
    console.print()
    
    # Hint
    console.print(
        f"  [dim {theme.secondary}]Use /diff to review the changes or /undo to restore the snapshot.[/]"
    )
    console.print()
