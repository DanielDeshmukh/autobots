"""Skill injection system for Autobots clusters."""

from .loader import (
    load_skill_pack,
    load_nvidia_skills,
    load_conditional_nvidia_skills,
    detect_skills_from_roadmap,
    list_nvidia_skills,
    CONTEXT_FILES,
)
from .cluster_prompts import CLUSTER_SYSTEM_PROMPTS

__all__ = [
    "load_skill_pack",
    "load_nvidia_skills",
    "load_conditional_nvidia_skills",
    "detect_skills_from_roadmap",
    "list_nvidia_skills",
    "CONTEXT_FILES",
    "CLUSTER_SYSTEM_PROMPTS",
]
