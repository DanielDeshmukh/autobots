"""Validation and repair cycle views."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme
from ..symbols import get_symbols


def render_validation_start(
    console: Console,
    *,
    theme: Theme | None = None,
) -> None:
    """Render validation start header.
    
    Format:
    ● Validating changes
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    console.print(f"{symbols.active} [bold {theme.primary}]Validating changes[/]")
    console.print()


def render_validation_check(
    console: Console,
    *,
    name: str,
    status: str,
    detail: str = "",
    elapsed: str = "",
    theme: Theme | None = None,
) -> None:
    """Render a single validation check result.
    
    Format:
      Lint             passed                                      0.8s
      Tests            41 passed, 2 failed                         4.7s
      Security review  waiting
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    status_style = {
        "passed": f"{theme.success}",
        "failed": f"{theme.error}",
        "running": f"{theme.active}",
        "waiting": f"{theme.secondary}",
        "skipped": f"{theme.dim}",
    }.get(status, f"{theme.secondary}")
    
    status_icon = {
        "passed": symbols.done,
        "failed": symbols.failed,
        "running": symbols.active,
        "waiting": symbols.waiting,
        "skipped": "-",
    }.get(status, symbols.waiting)
    
    line = Text()
    line.append(f"  {name:<20}", style=f"{theme.primary}")
    line.append(f"{status_icon} {status}", style=status_style)
    
    if detail:
        line.append(f"  {detail}", style=f"dim {theme.secondary}")
    
    if elapsed:
        padding = max(1, 55 - len(name) - len(status) - len(detail))
        line.append(" " * padding, style=f"dim {theme.secondary}")
        line.append(elapsed, style=f"dim {theme.secondary}")
    
    console.print(line)


def render_validation_summary(
    console: Console,
    *,
    passed: int = 0,
    failed: int = 0,
    theme: Theme | None = None,
) -> None:
    """Render validation summary line."""
    if theme is None:
        theme = load_theme()
    
    console.print()
    summary = Text()
    summary.append("  ", style=f"dim {theme.secondary}")
    if passed:
        summary.append(f"{passed} passed", style=f"{theme.success}")
    if failed:
        if passed:
            summary.append(", ", style=f"dim {theme.secondary}")
        summary.append(f"{failed} failed", style=f"{theme.error}")
    console.print(summary)
    console.print()


def render_repair_start(
    console: Console,
    *,
    cluster: str = "Ratchet",
    issue_count: int = 0,
    attempt: int = 1,
    max_attempts: int = 3,
    theme: Theme | None = None,
) -> None:
    """Render repair cycle start.
    
    Format:
    ● Ratchet is repairing two failed tests              attempt 1/3
      ├─ Read tests/test_auth.py
      ├─ Found inconsistent expiration timezone handling
      └─ Updating token timestamp normalization
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    header = Text()
    header.append(f"{symbols.active} ", style=f"{theme.active}")
    header.append(f"{cluster}", style=f"bold {theme.primary}")
    header.append(f" is repairing ", style=f"{theme.primary}")
    header.append(f"{issue_count} issue{'s' if issue_count != 1 else ''}", style=f"bold {theme.primary}")
    
    if attempt > 0:
        header.append(f"  ", style=f"dim {theme.secondary}")
        header.append(f"attempt {attempt}/{max_attempts}", style=f"dim {theme.secondary}")
    
    console.print(header)
    console.print()


def render_repair_action(
    console: Console,
    *,
    action: str,
    detail: str = "",
    is_last: bool = False,
    theme: Theme | None = None,
) -> None:
    """Render a repair action line."""
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    connector = symbols.last if is_last else symbols.branch
    
    line = Text()
    line.append(f"  {connector} ", style=f"dim {theme.secondary}")
    line.append(action, style=f"{theme.primary}")
    if detail:
        line.append(f" {detail}", style=f"dim {theme.secondary}")
    
    console.print(line)


def render_revalidation(
    console: Console,
    *,
    theme: Theme | None = None,
) -> None:
    """Render revalidation header."""
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    console.print()
    console.print(f"{symbols.active} [bold {theme.primary}]Re-running failed checks[/]")
    console.print()


def render_validation_error(
    console: Console,
    *,
    error: str,
    suggestion: str = "",
    theme: Theme | None = None,
) -> None:
    """Render validation error with recovery guidance.
    
    Format:
    x Tests could not start
    
      pytest is not installed in the current Python environment.
    
      Suggested fix
      python -m pip install -e ".[dev]"
    
      Run /doctor to inspect the active environment.
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    console.print()
    console.print(f"{symbols.failed} [bold {theme.error}]Tests could not start[/]")
    console.print()
    console.print(f"  [dim {theme.secondary}]{error}[/]")
    
    if suggestion:
        console.print()
        console.print(f"  [dim {theme.secondary}]Suggested fix[/]")
        console.print(f"  [bold {theme.primary}]{suggestion}[/]")
    
    console.print()
    console.print(f"  [dim {theme.secondary}]Run /doctor to inspect the active environment.[/]")
    console.print()
