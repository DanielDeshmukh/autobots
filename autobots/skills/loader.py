"""
Loads context files from the target project's context/ directory
and bundles them into skill packs for each cluster.
"""
from __future__ import annotations

from pathlib import Path

from .cluster_prompts import CLUSTER_SYSTEM_PROMPTS


CONTEXT_FILES = {
    "architecture": "context/architecture.md",
    "conventions": "context/conventions.md",
    "testing": "context/testing-strategy.md",
    "security": "context/security-auth.md",
}


def load_skill_pack(project_root: str, cluster_name: str) -> str:
    """
    Returns a formatted skill pack string to inject into the system prompt.
    Only loads files that exist — silently skips missing ones.
    """
    root = Path(project_root)
    sections: list[str] = []

    for key, rel_path in CONTEXT_FILES.items():
        full_path = root / rel_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding="utf-8-sig")
                if content.strip():
                    sections.append(f"## Project {key.title()}\n\n{content}")
            except Exception:
                pass

    skill_pack = "\n\n---\n\n".join(sections)
    cluster_preamble = CLUSTER_SYSTEM_PROMPTS.get(cluster_name, "")

    if skill_pack:
        return f"{cluster_preamble}\n\n{skill_pack}"
    return cluster_preamble


def list_available_skills(project_root: str) -> dict[str, bool]:
    """List which context files are available in the project."""
    root = Path(project_root)
    available: dict[str, bool] = {}

    for key, rel_path in CONTEXT_FILES.items():
        full_path = root / rel_path
        available[key] = full_path.exists() and full_path.read_text(encoding="utf-8-sig").strip() != ""

    return available
