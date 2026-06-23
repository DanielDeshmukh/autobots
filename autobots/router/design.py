"""Design principles — injects best-practice guidance instead of hardcoded themes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("autobots")


# ── Generic design principles (no hardcoded colors/themes) ──────────────

DESIGN_PRINCIPLES = """DESIGN RULES:
- Use CSS custom properties for colors
- Primary color matches project mood (blue=corporate, vibrant=startup, bold=creative)
- 8px spacing grid, border-radius: 4/8/12/16px
- Buttons: hover/active states, 150ms transitions
- Cards: subtle shadow, 1px border, rounded corners
- Mobile-first responsive (320px min)
- Dark mode: background #0a0a0a-#1a1a2e, surface slightly lighter
- Ensure WCAG AA contrast (4.5:1 text, 3:1 large text)
"""


@dataclass
class DesignGuidance:
    """Design guidance to inject into prompts."""
    principles: str
    source: str  # "default", "theme", "custom"

    def to_prompt_context(self) -> str:
        return self.principles


def get_design_guidance(
    project_description: str = "",
    theme_override: str | None = None,
    custom_design_md_path: str | None = None,
) -> DesignGuidance:
    """Get design guidance for a project.

    Priority:
    1. custom_design_md_path if provided
    2. theme_override if provided (future: load from themes/)
    3. Default principles (model decides colors)
    """
    # Custom DESIGN.md file takes priority
    if custom_design_md_path:
        from pathlib import Path
        path = Path(custom_design_md_path)
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                return DesignGuidance(principles=content, source="custom")
            except Exception as e:
                logger.warning("Failed to read custom design file: %s", e)

    # Theme override (future: could load from themes/ directory)
    if theme_override:
        logger.info("Theme override requested: %s (using default principles for now)", theme_override)

    # Default: let the model decide with good guidance
    return DesignGuidance(principles=DESIGN_PRINCIPLES, source="default")
