"""Legacy UI compatibility — exports old-style functions for existing code."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt


# Global console instance (old-style)
ConsoleInstance = Console()


def _read_menu_key() -> str:
    """Read a keypress for menu navigation."""
    try:
        import msvcrt
    except ImportError:
        try:
            import termios
            import tty

            fd = sys.stdin.fileno()
            original = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                first = sys.stdin.read(1)
                if first == "\x1b":
                    second = sys.stdin.read(1)
                    third = sys.stdin.read(1)
                    if second == "[" and third == "A":
                        return "up"
                    if second == "[" and third == "B":
                        return "down"
                if first in {"\r", "\n"}:
                    return "enter"
                if first == "\x03":
                    raise KeyboardInterrupt
                return ""
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, original)
        except Exception:
            return ""
    
    first = msvcrt.getwch()
    if first in {"\x00", "\xe0"}:
        second = msvcrt.getwch()
        if second == "H":
            return "up"
        if second == "P":
            return "down"
        return ""
    if first in {"\r", "\n"}:
        return "enter"
    if first == "\x03":
        raise KeyboardInterrupt
    return ""


def _select(
    options: list[str],
    prompt: str = "Select",
    console: Console | None = None,
) -> str | None:
    """Interactive menu selection (legacy)."""
    if console is None:
        console = ConsoleInstance
    
    console.print(f"\n[bold]{prompt}[/bold]")
    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option}")
    
    while True:
        key = _read_menu_key()
        if key == "enter":
            return None
        if key == "up":
            return "up"
        if key == "down":
            return "down"
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(options):
                return options[idx]


def _text(
    prompt: str = "Input",
    default: str = "",
    console: Console | None = None,
) -> str:
    """Text input prompt (legacy)."""
    if console is None:
        console = ConsoleInstance
    
    try:
        return Prompt.ask(prompt, default=default, console=console)
    except (KeyboardInterrupt, EOFError):
        return default


def _password(
    prompt: str = "Password",
    console: Console | None = None,
) -> str:
    """Password input prompt (legacy)."""
    if console is None:
        console = ConsoleInstance
    
    from rich.prompt import Password
    try:
        return Password.ask(prompt, console=console)
    except (KeyboardInterrupt, EOFError):
        return ""


def render_plan(*args, **kwargs):
    """Stub for render_plan (now in transcript.py)."""
    pass


def render_registry_summary(*args, **kwargs):
    """Stub for render_registry_summary."""
    pass


def render_stage_event(*args, **kwargs):
    """Stub for render_stage_event."""
    pass


def render_phase_panel(*args, **kwargs):
    """Stub for render_phase_panel."""
    pass


def render_session_status(*args, **kwargs):
    """Stub for render_session_status."""
    pass


def render_execution_result(*args, **kwargs):
    """Stub for render_execution_result."""
    pass


def render_model_validation_report(*args, **kwargs):
    """Stub for render_model_validation_report."""
    pass


def render_engage_screen(*args, **kwargs):
    """Stub for render_engage_screen."""
    pass


def engage_prompt(*args, **kwargs):
    """Stub for engage_prompt."""
    pass
