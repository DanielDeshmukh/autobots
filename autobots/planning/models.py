"""Data models for planning operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryScan:
    """Result of scanning a repository."""

    build_files: tuple[str, ...]
    env_files: tuple[str, ...]
    docs: tuple[str, ...]
    source_roots: tuple[str, ...]
    test_roots: tuple[str, ...]
    frameworks: tuple[str, ...]


@dataclass(frozen=True)
class PhaseSpec:
    """Specification for a single phase."""

    phase_id: str
    title: str
    goal: str
    acceptance_checks: tuple[str, ...]
    depends_on: tuple[str, ...]
    relevant_paths: tuple[str, ...]
    validation_commands: tuple[str, ...]


@dataclass(frozen=True)
class PlanArtifacts:
    """Generated planning artifacts."""

    roadmap: str
    progress: str
    phases: tuple[PhaseSpec, ...]
