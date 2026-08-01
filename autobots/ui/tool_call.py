"""Tool call rendering — compact and expanded views."""

from __future__ import annotations

from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text

from .theme import Theme, load_theme
from .symbols import get_symbols


# ─── Compact Tool Calls ──────────────────────────────────────────────────────

def render_tool_compact(
    console: Console,
    *,
    action: str,
    path: str = "",
    stat: str = "",
    theme: Theme | None = None,
) -> None:
    """Render a compact tool call line.
    
    Format:
      ├─ Read src/config.py
      ├─ Update src/services/tokens.py                 +47 -8
      ├─ Create src/services/token_store.py            +86
      └─ Bash python -m pytest tests/test_auth.py -q
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    line = Text()
    line.append(f"  {symbols.branch} ", style=f"dim {theme.secondary}")
    line.append(f"{action} ", style=f"{theme.primary}")
    if path:
        line.append(path, style=f"{theme.path}")
    if stat:
        line.append(f"  {stat}", style=f"dim {theme.secondary}")
    
    console.print(line)


# ─── Expanded Read ───────────────────────────────────────────────────────────

def render_tool_read_expanded(
    console: Console,
    *,
    path: str,
    lines: int = 0,
    line_range: str = "",
    theme: Theme | None = None,
) -> None:
    """Render expanded read tool output.
    
    Format:
    Read src/services/tokens.py
      Read 186 lines
    """
    if theme is None:
        theme = load_theme()
    
    console.print(f"[bold {theme.primary}]Read[/] [{theme.path}]{path}[/]")
    if lines:
        console.print(f"  [dim {theme.secondary}]Read {lines} lines[/]")
    if line_range:
        console.print(f"  [dim {theme.secondary}]{line_range}[/]")
    console.print()


# ─── Expanded Search ─────────────────────────────────────────────────────────

def render_tool_search_expanded(
    console: Console,
    *,
    query: str,
    path: str,
    match_count: int = 0,
    file_count: int = 0,
    matches: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render expanded search tool output.
    
    Format:
    Search "refresh_token" in src
      12 matches in 5 files
    
      src/api/routes/auth.py:84
      src/services/tokens.py:42
    """
    if theme is None:
        theme = load_theme()
    
    console.print(
        f'[bold {theme.primary}]Search[/] [dim]{query}[/] in [{theme.path}]{path}[/]'
    )
    console.print(
        f"  [dim {theme.secondary}]{match_count} matches in {file_count} files[/]"
    )
    
    if matches:
        console.print()
        for match in matches[:10]:
            file_path = match.get("file", "")
            line_num = match.get("line", "")
            console.print(f"  [{theme.path}]{file_path}:{line_num}[/]")
    
    console.print()


# ─── Expanded Edit ───────────────────────────────────────────────────────────

def render_tool_edit_expanded(
    console: Console,
    *,
    path: str,
    diff_lines: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render expanded edit tool output with syntax-highlighted diff.
    
    Format:
    Update src/services/tokens.py
    
      58   payload = build_payload(subject, expires_at)
      59 - return jwt.encode(payload, settings.jwt_secret)
      59 + return jwt.encode(
      60 +     payload,
      61 +     settings.jwt_secret,
      62 +     algorithm=settings.jwt_algorithm,
      63 + )
    """
    if theme is None:
        theme = load_theme()
    
    console.print(f"[bold {theme.primary}]Update[/] [{theme.path}]{path}[/]")
    console.print()
    
    if diff_lines:
        for dl in diff_lines:
            line_num = dl.get("num", "")
            old = dl.get("old", "")
            new = dl.get("new", "")
            is_context = dl.get("context", False)
            
            if is_context:
                console.print(f"  [dim]{line_num:>4}[/]  {old}")
            else:
                if old:
                    console.print(f"  [dim]{line_num:>4}[/] [dim {theme.error}]-[/] {old}")
                if new:
                    console.print(f"  [dim]{line_num:>4}[/] [dim {theme.success}]+[/] {new}")
    
    console.print()
