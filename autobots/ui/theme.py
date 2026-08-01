"""Autobots theme system — colors, symbols, and visual identity."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ThemeName(Enum):
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high-contrast"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class Theme:
    """Complete color palette for the UI."""
    # Brand
    brand: str = "#E25555"

    # Text
    primary: str = ""          # Terminal foreground (empty = default)
    secondary: str = "#8B929B"

    # State
    active: str = "#68AEE8"
    success: str = "#62C073"
    warning: str = "#D9A441"
    error: str = "#E05D65"

    # File paths
    path: str = "#8DA9E8"

    # Borders
    border: str = "#4A4F57"

    # Diff
    diff_add: str = "#62C073"
    diff_remove: str = "#E05D65"

    # Muted
    dim: str = "#6B7280"


# ─── Built-in Themes ─────────────────────────────────────────────────────────

THEMES: dict[ThemeName, Theme] = {
    ThemeName.DARK: Theme(),

    ThemeName.LIGHT: Theme(
        brand="#C0353B",
        primary="",
        secondary="#6B7280",
        active="#3B82F6",
        success="#16A34A",
        warning="#D97706",
        error="#DC2626",
        path="#4338CA",
        border="#D1D5DB",
        diff_add="#16A34A",
        diff_remove="#DC2626",
        dim="#9CA3AF",
    ),

    ThemeName.HIGH_CONTRAST: Theme(
        brand="#FF6B6B",
        primary="",
        secondary="#A0AEC0",
        active="#63B3ED",
        success="#68D391",
        warning="#F6E05E",
        error="#FC8181",
        path="#90CDF4",
        border="#718096",
        diff_add="#68D391",
        diff_remove="#FC8181",
        dim="#A0AEC0",
    ),

    ThemeName.TERMINAL: Theme(
        brand="",
        primary="",
        secondary="",
        active="",
        success="",
        warning="",
        error="",
        path="",
        border="",
        diff_add="",
        diff_remove="",
        dim="",
    ),
}


def load_theme(name: Optional[str] = None) -> Theme:
    """Load theme by name, or detect from config/env.
    
    Priority:
    1. Explicit name argument
    2. AUTOBOTS_THEME env var
    3. ~/.autobots/config.toml theme setting
    4. Default (dark)
    """
    if name:
        try:
            return THEMES[ThemeName(name)]
        except ValueError:
            return THEMES[ThemeName.DARK]

    # Check env
    env_theme = os.getenv("AUTOBOTS_THEME", "").strip().lower()
    if env_theme:
        try:
            return THEMES[ThemeName(env_theme)]
        except ValueError:
            pass

    # Check config
    try:
        import tomllib
        config_path = os.path.expanduser("~/.autobots/config.toml")
        if os.path.exists(config_path):
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            theme_name = data.get("autobots", {}).get("theme", "")
            if theme_name:
                return THEMES[ThemeName(theme_name)]
    except Exception:
        pass

    return THEMES[ThemeName.DARK]
