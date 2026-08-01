"""Rewind and undo system."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from .theme import Theme, load_theme
from .symbols import get_symbols


def render_rewind_picker(
    console: Console,
    *,
    snapshots: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render the rewind picker.
    
    Format:
    Rewind to a previous point
    
    > Before implementing token rotation              snapshot 01JAB91X
      After updating the token service                snapshot 01JAB92A
      Before the failed validation                    snapshot 01JAB92M
    
    Choose what to restore:
    
      1. Conversation only
      2. Files and conversation
      3. Files only
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Rewind to a previous point[/]")
    console.print()
    
    if snapshots:
        for i, snap in enumerate(snapshots):
            is_first = i == 0
            
            label = snap.get("label", "")
            snapshot_id = snap.get("id", "")
            
            line = Text()
            if is_first:
                line.append(f"> ", style=f"bold {theme.brand}")
            else:
                line.append(f"  ", style=f"dim {theme.secondary}")
            
            line.append(label, style=f"{theme.primary}")
            
            if snapshot_id:
                padding = max(1, 60 - len(label))
                line.append(" " * padding, style=f"dim {theme.secondary}")
                line.append(f"snapshot {snapshot_id}", style=f"dim {theme.secondary}")
            
            console.print(line)
    else:
        console.print(f"  [dim {theme.secondary}]No snapshots available[/]")
    
    console.print()
    console.print(f"  [dim {theme.secondary}]Choose what to restore:[/]")
    console.print()
    console.print(f"  [dim]1.[/] Conversation only")
    console.print(f"  [dim]2.[/] Files and conversation")
    console.print(f"  [dim]3.[/] Files only")
    console.print()


def render_undo_confirmation(
    console: Console,
    *,
    snapshot_id: str,
    files_restored: int = 0,
    conversation_restored: bool = False,
    theme: Theme | None = None,
) -> None:
    """Render undo confirmation.
    
    Format:
    ✓ Restored snapshot 01JAB92M
    
      6 files restored
      Conversation restored
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    console.print()
    console.print(
        f"{symbols.done} [bold {theme.success}]Restored snapshot {snapshot_id}[/]"
    )
    console.print()
    
    if files_restored:
        console.print(f"  [dim]{files_restored} files restored[/]")
    
    if conversation_restored:
        console.print(f"  [dim]Conversation restored[/]")
    
    console.print()
