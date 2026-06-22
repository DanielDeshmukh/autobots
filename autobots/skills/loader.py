"""
Loads context files from the target project's context/ directory
and bundles them into skill packs for each cluster.
Also loads NVIDIA-specific skills from autobots/skills/nvidia/.
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

# NVIDIA skills directory (bundled with autobots engine)
NVIDIA_SKILLS_DIR = Path(__file__).parent / "nvidia"

# Map: cluster_name → list of nvidia skill filenames to always inject
CLUSTER_NVIDIA_SKILLS: dict[str, list[str]] = {
    "Optimus": [
        "agent-skills.md",
        "autonomous-agent-research.md",
        "rag-blueprint.md",
        "session-memory.md",
    ],
    "UltraMagnus": [
        "rag-blueprint.md",
        "dynamo-router.md",
        "retrieval.md",
    ],
    "Jazz": [
        "rag-eval.md",
    ],
    "Ironhide": [
        "safety-policy.md",
    ],
    "Wheeljack": [
        "dynamo-deployment.md",
    ],
    "Perceptor": [
        "cuopt-optimization.md",
    ],
    "Bumblebee": [
        "retrieval.md",
    ],
}

# Universal suffix — appended to ALL clusters
UNIVERSAL_SUFFIX_SKILLS: list[str] = [
    "skill-evolution.md",
]

# Conditional skills: keyword → list of nvidia skill filenames
TASK_KEYWORD_TO_SKILL: dict[str, list[str]] = {
    "rag": ["rag-blueprint.md", "rag-eval.md"],
    "retrieval": ["retrieval.md", "rag-blueprint.md"],
    "fine-tun": ["nemotron-customize.md"],
    "train": ["neautomodel-recipe.md"],
    "routing": ["cuopt-routing.md"],
    "schedul": ["cuopt-optimization.md"],
    "optim": ["cuopt-optimization.md"],
    "dataframe": ["cudf.md"],
    "pandas": ["cudf.md"],
    "kubernetes": ["kubernetes-infra.md"],
    "k8s": ["kubernetes-infra.md"],
    "deploy": ["dynamo-deployment.md"],
    "video": ["holoscan.md"],
    "quantum": ["cudaq.md"],
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


def load_nvidia_skills(cluster_name: str) -> str:
    """
    Load NVIDIA skill markdown files for the given cluster.
    Returns a formatted string to inject into the system prompt.
    """
    if not NVIDIA_SKILLS_DIR.exists():
        return ""

    sections: list[str] = []
    filenames = CLUSTER_NVIDIA_SKILLS.get(cluster_name, []) + UNIVERSAL_SUFFIX_SKILLS

    for filename in filenames:
        path = NVIDIA_SKILLS_DIR / filename
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8-sig")
                if content.strip():
                    skill_name = filename.replace(".md", "").replace("-", " ").title()
                    sections.append(f"## NVIDIA Skill: {skill_name}\n\n{content}")
            except Exception:
                pass

    return "\n\n---\n\n".join(sections)


def detect_skills_from_roadmap(roadmap_text: str) -> list[str]:
    """
    Scan roadmap.md task descriptions for keywords.
    Return list of nvidia skill filenames to inject for this project.
    """
    roadmap_lower = roadmap_text.lower()
    skills_needed: set[str] = set()

    for keyword, skill_files in TASK_KEYWORD_TO_SKILL.items():
        if keyword in roadmap_lower:
            skills_needed.update(skill_files)

    return list(skills_needed)


def load_conditional_nvidia_skills(roadmap_text: str) -> str:
    """
    Load NVIDIA skills based on keywords detected in the roadmap.
    Returns a formatted string to inject into the system prompt.
    """
    if not NVIDIA_SKILLS_DIR.exists():
        return ""

    skill_files = detect_skills_from_roadmap(roadmap_text)
    if not skill_files:
        return ""

    sections: list[str] = []
    for filename in skill_files:
        path = NVIDIA_SKILLS_DIR / filename
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8-sig")
                if content.strip():
                    skill_name = filename.replace(".md", "").replace("-", " ").title()
                    sections.append(f"## NVIDIA Skill (Conditional): {skill_name}\n\n{content}")
            except Exception:
                pass

    return "\n\n---\n\n".join(sections)


def list_nvidia_skills() -> dict[str, list[str]]:
    """List all available NVIDIA skill files and their cluster assignments."""
    available: dict[str, list[str]] = {}
    if not NVIDIA_SKILLS_DIR.exists():
        return available

    for cluster, filenames in CLUSTER_NVIDIA_SKILLS.items():
        available[cluster] = []
        for f in filenames:
            if (NVIDIA_SKILLS_DIR / f).exists():
                available[cluster].append(f)

    # Add universal skills info
    available["universal"] = []
    for f in UNIVERSAL_SUFFIX_SKILLS:
        if (NVIDIA_SKILLS_DIR / f).exists():
            available["universal"].append(f)

    return available
