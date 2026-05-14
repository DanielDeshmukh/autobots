"""Utility functions for planning operations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .models import RepositoryScan, PhaseSpec
from .scanner import RepositoryScanner

if TYPE_CHECKING:
    from ..bootstrap import RepoProfile


def build_validation_commands(profile: RepoProfile, scan: RepositoryScan) -> tuple[str, ...]:
    """Build validation commands based on project profile."""
    commands: list[str] = []
    test_tools = set(profile.test_tools)
    if "pytest" in test_tools:
        commands.append("python -m pytest -q")
    if "npm test" in test_tools:
        commands.append("npm test")
    if "vitest" in test_tools:
        commands.append("npx vitest run")
    if "jest" in test_tools:
        commands.append("npx jest --runInBand")
    if not commands and scan.build_files:
        if "pyproject.toml" in scan.build_files:
            commands.append("python -m unittest discover -s tests -q")
        elif "package.json" in scan.build_files:
            commands.append("npm test")
    return tuple(dict.fromkeys(commands))


def select_relevant_paths(scan: RepositoryScan, goal: str) -> tuple[str, ...]:
    """Select relevant paths based on goal and scan."""
    normalized_goal = goal.lower()
    selected: list[str] = []
    goal_to_paths = {
        "cli": ("autobots/cli.py",),
        "plan": ("autobots/planning.py", "context/roadmap.md", "context/progress-tracker.md"),
        "planning": ("autobots/planning.py",),
        "router": ("autobots/router.py",),
        "catalog": ("autobots/catalog.py",),
        "bootstrap": ("autobots/bootstrap.py",),
        "publish": ("PUBLISHING.md", "pyproject.toml"),
        "package": ("pyproject.toml", "PUBLISHING.md"),
        "doc": ("README.md", "product-definition.md"),
        "readme": ("README.md",),
        "test": ("tests",),
    }
    for token, paths in goal_to_paths.items():
        if token in normalized_goal:
            selected.extend(paths)

    if not selected:
        for root in scan.source_roots:
            if root == ".":
                selected.append("project root")
            else:
                selected.append(root)
        if not selected and scan.docs:
            selected.extend(scan.docs[:2])

    return tuple(dict.fromkeys(selected[:5]))


def select_validation_paths(scan: RepositoryScan) -> tuple[str, ...]:
    """Select paths for validation testing."""
    selected: list[str] = []
    if scan.test_roots:
        selected.extend(scan.test_roots)
    elif "tests" in scan.source_roots:
        selected.append("tests")
    else:
        selected.append("project root")
    return tuple(dict.fromkeys(selected))


def select_doc_paths(scan: RepositoryScan) -> tuple[str, ...]:
    """Select documentation paths."""
    selected = list(scan.docs[:3]) or ["context/roadmap.md", "context/progress-tracker.md"]
    return tuple(dict.fromkeys(selected))


def normalize_phase_dependencies(phases: tuple[PhaseSpec, ...]) -> tuple[PhaseSpec, ...]:
    """Normalize phase dependencies to ensure proper sequencing."""
    if not phases:
        return phases
    normalized: list[PhaseSpec] = []
    for index, phase in enumerate(phases):
        if index == 0:
            normalized.append(phase)
            continue
        if phase.depends_on:
            normalized.append(phase)
            continue
        predecessor = normalized[index - 1].phase_id
        normalized.append(
            PhaseSpec(
                phase_id=phase.phase_id,
                title=phase.title,
                goal=phase.goal,
                acceptance_checks=phase.acceptance_checks,
                depends_on=(predecessor,),
                relevant_paths=phase.relevant_paths,
                validation_commands=phase.validation_commands,
            )
        )
    return tuple(normalized)


def render_phase_sections(phases: tuple[PhaseSpec, ...]) -> str:
    """Render phase sections for roadmap."""
    rendered: list[str] = []
    for phase in phases:
        rendered.append(f"### {phase.phase_id}: {phase.title}")
        rendered.append(f"- Goal: {phase.goal}")
        rendered.append(
            f"- Depends on: {', '.join(phase.depends_on) if phase.depends_on else 'None'}"
        )
        rendered.append(
            f"- Relevant paths: {', '.join(phase.relevant_paths) if phase.relevant_paths else 'None'}"
        )
        rendered.append(
            f"- Validation: {', '.join(phase.validation_commands) if phase.validation_commands else 'None'}"
        )
        rendered.append("- Acceptance checks:")
        for check in phase.acceptance_checks:
            rendered.append(f"  - {check}")
        rendered.append("")
    return "\n".join(rendered).strip() + "\n"


def build_progress_tracker(phases: tuple[PhaseSpec, ...]) -> str:
    """Build progress tracker content."""
    lines = ["# Progress Tracker", ""]
    for phase in phases:
        dependencies = ", ".join(phase.depends_on) if phase.depends_on else "none"
        acceptance = phase.acceptance_checks[0]
        validation = ", ".join(phase.validation_commands) if phase.validation_commands else "none"
        lines.append(
            f"- [ ] {phase.phase_id} | {phase.title} | depends on: {dependencies} | validation: {validation} | acceptance: {acceptance}"
        )
    return "\n".join(lines) + "\n"


def normalize_acceptance_check(line: str) -> str:
    """Normalize acceptance check text."""
    normalized = line.strip()
    normalized = normalized.removeprefix("- ").strip()
    return normalized


def extract_progress_phase_id(line: str) -> str:
    """Extract phase ID from progress line."""
    match = re.search(r"\]\s+(P\d+)\s+\|", line)
    return match.group(1).strip() if match else ""


def extract_progress_title(line: str) -> str:
    """Extract phase title from progress line."""
    match = re.search(r"\]\s+(?:P\d+\s+\|\s+)?(.+?)\s+\|\s+depends on:", line)
    return match.group(1).strip() if match else ""


def apply_status_to_line(line: str, status: str) -> str:
    """Apply status marker to progress line."""
    marker = {"PENDING": "[ ]", "IN_PROGRESS": "[~]", "COMPLETE": "[x]"}[status]
    return re.sub(r"\[[ x~]\]", marker, line, count=1)


def extract_progress_statuses(progress_text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Extract status information from progress tracker."""
    statuses_by_phase_id: dict[str, str] = {}
    statuses_by_title: dict[str, str] = {}
    for line in progress_text.splitlines():
        if "|" not in line:
            continue
        status = "PENDING"
        if "[x]" in line:
            status = "COMPLETE"
        elif "[~]" in line:
            status = "IN_PROGRESS"
        phase_id = extract_progress_phase_id(line)
        title = extract_progress_title(line)
        if phase_id:
            statuses_by_phase_id[phase_id] = status
        if title:
            statuses_by_title[title] = status
    return statuses_by_phase_id, statuses_by_title
