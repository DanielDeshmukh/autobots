"""Skill injection system for Autobots clusters."""

from .loader import load_skill_pack, CONTEXT_FILES
from .cluster_prompts import CLUSTER_SYSTEM_PROMPTS

__all__ = ["load_skill_pack", "CONTEXT_FILES", "CLUSTER_SYSTEM_PROMPTS"]
