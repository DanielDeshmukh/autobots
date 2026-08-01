"""Terminal utilities — title, cursor, NO_COLOR, OSC links."""

from __future__ import annotations

import os
import sys
from typing import Optional


def set_title(title: str) -> None:
    """Set terminal title via OSC escape sequence.
    
    Works on most terminals (xterm, iTerm2, Windows Terminal, etc.).
    """
    try:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
    except Exception:
        pass


def reset_title() -> None:
    """Reset terminal title to default."""
    set_title("Terminal")


def hide_cursor() -> None:
    """Hide the terminal cursor."""
    try:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
    except Exception:
        pass


def show_cursor() -> None:
    """Show the terminal cursor."""
    try:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
    except Exception:
        pass


def osc_link(path: str, text: str) -> str:
    """Create an OSC 8 clickable link (if supported).
    
    Format: \033]8;;URL\033\\TEXT\033]8;;\033\\
    """
    return f"\033]8;;{path}\033\\{text}\033]8;;\033\\"


def supports_osc8() -> bool:
    """Check if terminal supports OSC 8 links."""
    term = os.getenv("TERM_PROGRAM", "")
    return term in ("iTerm.app", "WezTerm", "vscode", "Hyper")


def clear_screen() -> None:
    """Clear the terminal screen."""
    try:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    except Exception:
        pass


def clear_line() -> None:
    """Clear the current terminal line."""
    try:
        sys.stdout.write("\033[2K\r")
        sys.stdout.flush()
    except Exception:
        pass


def bell() -> None:
    """Send a terminal bell (for long task completion)."""
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


def is_no_color() -> bool:
    """Check if NO_COLOR environment variable is set."""
    return os.getenv("NO_COLOR") is not None


def is_dumb_terminal() -> bool:
    """Check if running on a dumb terminal."""
    return os.getenv("TERM", "") == "dumb"


def get_terminal_width() -> int:
    """Get terminal width, with fallback."""
    try:
        return os.get_terminal_size().columns
    except (ValueError, OSError):
        return 80


def get_terminal_height() -> int:
    """Get terminal height, with fallback."""
    try:
        return os.get_terminal_size().lines
    except (ValueError, OSError):
        return 24
