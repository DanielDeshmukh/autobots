"""Responsive layout — adapts to terminal width."""

from __future__ import annotations

from rich.console import Console


class LayoutMode:
    """Terminal width breakpoints."""
    WIDE = 100       # 100+ columns: full two-column layout
    STANDARD = 70    # 70-99 columns: standard layout
    NARROW = 0       # Below 70: stacked/narrow layout


def get_layout_mode(console: Console) -> str:
    """Detect layout mode from terminal width."""
    width = console.width or 80
    if width >= LayoutMode.WIDE:
        return "wide"
    elif width >= LayoutMode.STANDARD:
        return "standard"
    else:
        return "narrow"


def truncate_path(path: str, max_width: int) -> str:
    """Truncate a path to fit within max_width.
    
    If too long, replace middle with ellipsis:
    src/api/routes/auth.py -> src/.../auth.py
    """
    if len(path) <= max_width:
        return path
    
    parts = path.split("/")
    if len(parts) <= 2:
        # Just trim from start
        return "..." + path[-(max_width - 3):]
    
    # Keep first and last, ellipsis middle
    first = parts[0]
    last = parts[-1]
    middle = "..."
    
    available = max_width - len(first) - len(last) - 2  # 2 for slashes
    if available < 3:
        return "..." + path[-(max_width - 3):]
    
    return f"{first}/{middle}/{last}"


def pad_or_truncate(text: str, width: int, align: str = "left") -> str:
    """Pad or truncate text to exact width."""
    if len(text) >= width:
        return text[:width - 1] + "…"
    
    if align == "right":
        return text.rjust(width)
    elif align == "center":
        return text.center(width)
    else:
        return text.ljust(width)


def right_align_metadata(parts: list[str], total_width: int) -> str:
    """Right-align metadata parts within total_width.
    
    Example:
    "UltraMagnus  Token architecture              done"
    """
    if not parts:
        return ""
    
    text = "  ".join(parts)
    if len(text) >= total_width:
        return text[:total_width - 1] + "…"
    
    padding = total_width - len(text)
    return text + " " * padding
