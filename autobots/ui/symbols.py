"""Status symbols and visual glyphs for the Autobots UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Symbols:
    """Unicode symbols for UI states."""
    # Status
    active: str = "\u25cf"      # ●
    waiting: str = "\u25cb"     # ○
    done: str = "\u2713"        # ✓
    failed: str = "\u00d7"      # ×
    warning: str = "!"          # !
    followup: str = "\u21b3"    # ↳

    # Tree connectors
    branch: str = "\u251c\u2500"  # ├─
    last: str = "\u2514\u2500"    # └─
    pipe: str = "\u2502"          # │

    # Prompt
    prompt: str = ">"            # >

    # Input prefixes
    cmd_prefix: str = "/"        # /
    file_prefix: str = "@"       # @
    shell_prefix: str = "!"      # !
    instruction_prefix: str = "#" # #


@dataclass(frozen=True)
class AsciiSymbols:
    """ASCII replacements for --ascii mode."""
    active: str = "*"
    waiting: str = "o"
    done: str = "x"
    failed: str = "X"
    warning: str = "!"
    followup: str = "->"

    branch: str = "|-"
    last: str = "`-"
    pipe: str = "|"

    prompt: str = ">"

    cmd_prefix: str = "/"
    file_prefix: str = "@"
    shell_prefix: str = "!"
    instruction_prefix: str = "#"


def get_symbols(ascii_mode: bool = False) -> Symbols | AsciiSymbols:
    """Get symbols based on mode."""
    if ascii_mode:
        return AsciiSymbols()
    return Symbols()
