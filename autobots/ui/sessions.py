"""Session resume and picker."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme
from ..symbols import get_symbols


def render_session_picker(
    console: Console,
    *,
    sessions: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render the session resume picker.
    
    Format:
    Resume a session
    
    > Fix timer and card sizing
      memory-card-flip · autobots-safety · 14 minutes ago
    
      Add component tests
      memory-card-flip · autobots-safety · yesterday
    
      Implement JWT authentication
      api-service · feature/auth · 3 days ago
    
    Enter to resume · p to preview · d to delete · Esc to close
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Resume a session[/]")
    console.print()
    
    if sessions:
        for i, session in enumerate(sessions):
            is_first = i == 0
            
            name = session.get("name", "Unnamed")
            project = session.get("project", "")
            branch = session.get("branch", "")
            ago = session.get("ago", "")
            
            line = Text()
            if is_first:
                line.append(f"> ", style=f"bold {theme.brand}")
            else:
                line.append(f"  ", style=f"dim {theme.secondary}")
            
            line.append(name, style=f"bold {theme.path}")
            console.print(line)
            
            detail = Text()
            detail.append(f"  ", style=f"dim {theme.secondary}")
            if project:
                detail.append(project, style=f"{theme.secondary}")
            if branch:
                if project:
                    detail.append(f" · ", style=f"dim {theme.secondary}")
                detail.append(branch, style=f"{theme.secondary}")
            if ago:
                if project or branch:
                    detail.append(f" · ", style=f"dim {theme.secondary}")
                detail.append(ago, style=f"dim {theme.secondary}")
            console.print(detail)
            console.print()
    else:
        console.print(f"  [dim {theme.secondary}]No recent sessions found[/]")
        console.print()
    
    console.print(
        f"  [dim {theme.secondary}]Enter to resume · p to preview · d to delete · Esc to close[/]"
    )
    console.print()


def render_session_preview(
    console: Console,
    *,
    name: str,
    project: str = "",
    branch: str = "",
    last_active: str = "",
    message_count: int = 0,
    files_changed: int = 0,
    snapshot: str = "",
    status: str = "",
    theme: Theme | None = None,
) -> None:
    """Render session preview details.
    
    Format:
    Fix timer and card sizing
    
      Project       ~/code/memory-card-flip
      Branch        autobots-safety
      Last active   14 minutes ago
      Messages      18
      Files changed 6
      Snapshot      01JAB92M
      Status        completed
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]{name}[/]")
    console.print()
    
    fields = [
        ("Project", project),
        ("Branch", branch),
        ("Last active", last_active),
        ("Messages", str(message_count) if message_count else ""),
        ("Files changed", str(files_changed) if files_changed else ""),
        ("Snapshot", snapshot),
        ("Status", status),
    ]
    
    for label, value in fields:
        if value:
            console.print(f"  [dim {theme.secondary}]{label:<15}[/] {value}")
    
    console.print()
