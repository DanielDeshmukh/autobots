"""Core planning operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from .models import RepositoryScan, PhaseSpec, PlanArtifacts
from .scanner import RepositoryScanner
from .synthesis import PlanSynthesizer
from .utils import (
    extract_progress_phase_id,
    extract_progress_title,
    apply_status_to_line,
    extract_progress_statuses,
    normalize_acceptance_check,
)

if TYPE_CHECKING:
    from ..bootstrap import RepoProfile
    from ..workspace import TargetProjectWorkspace


def parse_roadmap(path: str) -> list[dict]:
    """
    Reads roadmap.md (utf-8-sig to handle BOM on Windows) and returns
    a list of phase dicts: [{"phase": str, "tasks": [str], "complete": bool}]
    """
    roadmap_path = Path(path)
    if not roadmap_path.exists():
        return []

    roadmap_text = roadmap_path.read_text(encoding="utf-8-sig")
    progress_path = roadmap_path.parent / "progress-tracker.md"
    progress_text = progress_path.read_text(encoding="utf-8-sig") if progress_path.exists() else ""

    complete_ids = _extract_complete_phase_ids(progress_text)

    phases: list[dict] = []
    phase_blocks = re.split(r"(?=^### )", roadmap_text, flags=re.MULTILINE)
    for block in phase_blocks:
        block = block.strip()
        if not block.startswith("###"):
            continue

        header_match = re.match(r"### (P\d+):\s*(.+)", block)
        if not header_match:
            continue

        phase_id = header_match.group(1)
        phase_title = header_match.group(2).strip()

        tasks: list[str] = []
        checks_match = re.search(r"- Acceptance checks:\s*\n((?:\s+- .+\n?)+)", block)
        if checks_match:
            for line in checks_match.group(1).splitlines():
                cleaned = line.strip().lstrip("- ").strip()
                if cleaned:
                    tasks.append(cleaned)

        if not tasks:
            tasks = [phase_title]

        phases.append({
            "phase": phase_title,
            "phase_id": phase_id,
            "tasks": tasks,
            "complete": phase_id in complete_ids,
        })

    return phases


def _extract_complete_phase_ids(progress_text: str) -> set[str]:
    """Extract phase IDs marked as COMPLETE from progress tracker text."""
    complete_ids: set[str] = set()
    for line in progress_text.splitlines():
        if "[x]" not in line:
            continue
        match = re.search(r"\]\s+(P\d+)\s+\|", line)
        if match:
            complete_ids.add(match.group(1))
    return complete_ids


def route_task(task: str, api_key: str | None = None) -> dict:
    """Route a task to the best cluster and return routing info."""
    from ..catalog import ClusterCatalog

    catalog = ClusterCatalog(api_key=api_key)
    decision = catalog.route_with_reasoning(task)
    return {
        "cluster": decision.cluster_name,
        "score": decision.score,
        "reasons": list(decision.reasons),
    }


def build_cluster_dispatch(phases: list[dict], api_key: str | None = None) -> dict[str, dict]:
    """Build a dispatch map for all tasks across all phases."""
    from ..catalog import ClusterCatalog

    catalog = ClusterCatalog(api_key=api_key)
    dispatch_map: dict[str, dict] = {}
    for phase in phases:
        for task in phase["tasks"]:
            if task not in dispatch_map:
                decision = catalog.route_with_reasoning(task)
                dispatch_map[task] = {
                    "cluster": decision.cluster_name,
                    "score": decision.score,
                    "reasons": list(decision.reasons),
                }
    return dispatch_map


def write_plan(
    workspace: TargetProjectWorkspace,
    *,
    goal: str | None = None,
    append: bool = False,
    insert_after: str | None = None,
    dry_run: bool = False,
) -> tuple[RepoProfile, RepositoryScan, PlanArtifacts]:
    """Write a plan to the workspace. roadmap.md is read-only; progress-tracker.md is append-only."""
    from ..bootstrap import detect_repo_profile

    profile = detect_repo_profile(workspace.target_root)
    scan = RepositoryScanner.scan_repository(workspace.target_root)
    resolved_goal = (goal or "").strip() or PlanSynthesizer.default_goal(profile)
    generated = PlanSynthesizer.synthesize_plan(profile, scan, goal=resolved_goal)
    existing_progress = _read_optional_context_file(workspace, "progress-tracker.md")
    existing_roadmap = _read_optional_context_file(workspace, "roadmap.md")
    artifacts = generated
    if append:
        artifacts = _append_plan(
            existing_roadmap=existing_roadmap,
            existing_progress=existing_progress,
            generated=generated,
            goal=resolved_goal,
            insert_after=insert_after,
        )
    elif existing_progress:
        artifacts = PlanArtifacts(
            roadmap=generated.roadmap,
            progress=_merge_existing_progress(existing_progress, generated.progress),
            phases=generated.phases,
        )
    if not dry_run:
        workspace.write_context_file("progress-tracker.md", artifacts.progress, lock_owner="Autobots/plan")
    return profile, scan, artifacts


def _read_optional_context_file(workspace: TargetProjectWorkspace, relative_path: str) -> str:
    """Read an optional context file."""
    path = workspace.context_root / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _append_plan(
    *,
    existing_roadmap: str,
    existing_progress: str,
    generated: PlanArtifacts,
    goal: str,
    insert_after: str | None,
) -> PlanArtifacts:
    """Append a new plan to existing plans."""
    existing_phases = _parse_generated_phases(existing_roadmap, existing_progress)
    if not existing_phases:
        phases = _renumber_phases(generated.phases, start_index=1)
        progress = _merge_existing_progress(existing_progress, _build_progress_tracker(phases)) if existing_progress else _build_progress_tracker(phases)
        return PlanArtifacts(
            roadmap=_render_combined_roadmap(existing_roadmap, goal, phases),
            progress=progress,
            phases=phases,
        )

    insertion_index = len(existing_phases)
    if insert_after:
        for index, phase in enumerate(existing_phases):
            if phase.phase_id == insert_after:
                insertion_index = index + 1
                break

    start_index = _next_phase_number(existing_phases)
    new_phases = _renumber_phases(generated.phases, start_index=start_index)
    anchored_existing, anchored_new = _anchor_inserted_phases(existing_phases, new_phases, insertion_index)
    combined_phases = (
        anchored_existing[:insertion_index]
        + anchored_new
        + anchored_existing[insertion_index:]
    )
    progress = _build_progress_tracker(tuple(combined_phases))
    if existing_progress:
        progress = _merge_existing_progress(existing_progress, progress)
    roadmap = _render_combined_roadmap(existing_roadmap, goal, tuple(combined_phases))
    return PlanArtifacts(roadmap=roadmap, progress=progress, phases=tuple(combined_phases))


def _merge_existing_progress(existing_progress: str, regenerated_progress: str) -> str:
    """Merge existing progress with regenerated progress."""
    statuses_by_phase_id, statuses_by_title = extract_progress_statuses(existing_progress)
    merged_lines: list[str] = []
    for line in regenerated_progress.splitlines():
        phase_id = extract_progress_phase_id(line)
        title = extract_progress_title(line)
        status = None
        if phase_id:
            status = statuses_by_phase_id.get(phase_id)
        if status is None and title:
            status = statuses_by_title.get(title)
        if status is None:
            merged_lines.append(line)
            continue
        merged_lines.append(apply_status_to_line(line, status))
    return "\n".join(merged_lines) + "\n"


def _parse_generated_phases(roadmap_text: str, progress_text: str) -> tuple[PhaseSpec, ...]:
    """Parse generated phases from roadmap and progress."""
    matches = re.findall(
        r"### (P\d+): (.+?)\n- Goal: (.+?)\n- Depends on: (.+?)\n- Relevant paths: (.+?)\n- Validation: (.+?)\n- Acceptance checks:\n((?:  - .+\n)+)",
        roadmap_text,
        re.MULTILINE,
    )
    if matches:
        phases: list[PhaseSpec] = []
        for phase_id, title, goal, depends_on, relevant_paths, validation, checks_block in matches:
            dependencies = () if depends_on.strip() == "None" else tuple(
                item.strip() for item in depends_on.split(",") if item.strip()
            )
            parsed_paths = () if relevant_paths.strip() == "None" else tuple(
                item.strip() for item in relevant_paths.split(",") if item.strip()
            )
            parsed_validation = () if validation.strip() == "None" else tuple(
                item.strip() for item in validation.split(",") if item.strip()
            )
            checks = tuple(normalize_acceptance_check(line) for line in checks_block.splitlines() if line.strip())
            phases.append(
                PhaseSpec(
                    phase_id=phase_id.strip(),
                    title=title.strip(),
                    goal=goal.strip(),
                    acceptance_checks=checks,
                    depends_on=dependencies,
                    relevant_paths=parsed_paths,
                    validation_commands=parsed_validation,
                )
            )
        return tuple(phases)

    fallback: list[PhaseSpec] = []
    for line in progress_text.splitlines():
        match = re.match(
            r"- \[[ x~]\] (P\d+) \| (.+?) \| depends on: (.+?) \| validation: (.+?) \| acceptance: (.+)",
            line,
        )
        if not match:
            continue
        phase_id, title, depends_on, validation, acceptance = match.groups()
        dependencies = () if depends_on.strip() == "none" else tuple(
            item.strip() for item in depends_on.split(",") if item.strip()
        )
        parsed_validation = () if validation.strip() == "none" else tuple(
            item.strip() for item in validation.split(",") if item.strip()
        )
        fallback.append(
            PhaseSpec(
                phase_id=phase_id,
                title=title.strip(),
                goal=f"Continue work on {title.strip()}",
                acceptance_checks=(acceptance.strip(),),
                depends_on=dependencies,
                relevant_paths=(),
                validation_commands=parsed_validation,
            )
        )
    return tuple(fallback)


def _next_phase_number(phases: tuple[PhaseSpec, ...]) -> int:
    """Find the next phase number."""
    phase_numbers = [
        int(match.group(1))
        for phase in phases
        if (match := re.match(r"P(\d+)$", phase.phase_id))
    ]
    return (max(phase_numbers) + 1) if phase_numbers else 1


def _renumber_phases(phases: tuple[PhaseSpec, ...], *, start_index: int) -> tuple[PhaseSpec, ...]:
    """Renumber phases starting from a given index."""
    renumbered: list[PhaseSpec] = []
    old_to_new: dict[str, str] = {}
    for offset, phase in enumerate(phases):
        new_id = f"P{start_index + offset}"
        old_to_new[phase.phase_id] = new_id
        renumbered.append(
            PhaseSpec(
                phase_id=new_id,
                title=phase.title,
                goal=phase.goal,
                acceptance_checks=phase.acceptance_checks,
                depends_on=phase.depends_on,
                relevant_paths=phase.relevant_paths,
                validation_commands=phase.validation_commands,
            )
        )
    return tuple(
        PhaseSpec(
            phase_id=phase.phase_id,
            title=phase.title,
            goal=phase.goal,
            acceptance_checks=phase.acceptance_checks,
            depends_on=tuple(old_to_new.get(dep, dep) for dep in phase.depends_on),
            relevant_paths=phase.relevant_paths,
            validation_commands=phase.validation_commands,
        )
        for phase in renumbered
    )


def _anchor_inserted_phases(
    existing_phases: tuple[PhaseSpec, ...],
    new_phases: tuple[PhaseSpec, ...],
    insertion_index: int,
) -> tuple[tuple[PhaseSpec, ...], tuple[PhaseSpec, ...]]:
    """Anchor new phases to existing phases."""
    updated_existing = list(existing_phases)
    updated_new = list(new_phases)
    if new_phases and insertion_index > 0:
        anchor_id = existing_phases[insertion_index - 1].phase_id
        updated_first = updated_new[0]
        new_depends = tuple(dict.fromkeys((*updated_first.depends_on, anchor_id)))
        updated_new[0] = PhaseSpec(
            phase_id=updated_first.phase_id,
            title=updated_first.title,
            goal=updated_first.goal,
            acceptance_checks=updated_first.acceptance_checks,
            depends_on=new_depends,
            relevant_paths=updated_first.relevant_paths,
            validation_commands=updated_first.validation_commands,
        )
    if updated_new and insertion_index < len(existing_phases):
        next_phase = existing_phases[insertion_index]
        if updated_new[-1].phase_id not in next_phase.depends_on:
            updated_existing[insertion_index] = PhaseSpec(
                phase_id=next_phase.phase_id,
                title=next_phase.title,
                goal=next_phase.goal,
                acceptance_checks=next_phase.acceptance_checks,
                depends_on=tuple(dict.fromkeys((*next_phase.depends_on, updated_new[-1].phase_id))),
                relevant_paths=next_phase.relevant_paths,
                validation_commands=next_phase.validation_commands,
            )
    return tuple(updated_existing), tuple(updated_new)


def _render_combined_roadmap(existing_roadmap: str, goal: str, phases: tuple[PhaseSpec, ...]) -> str:
    """Render a combined roadmap."""
    from .utils import render_phase_sections

    goal_match = re.search(r"## Planning Objective\n- (.+)", existing_roadmap)
    prior_goal = goal_match.group(1).strip() if goal_match else ""
    planning_objective = goal if not prior_goal else f"{prior_goal}; re-plan goal: {goal}"
    scan_match = re.search(
        r"## Repository Scan\n(.+?)\n## Generated Phases",
        existing_roadmap,
        re.DOTALL,
    )
    repository_scan = scan_match.group(1).strip() if scan_match else "- Scan data unavailable"
    return (
        "# Roadmap\n\n"
        "## Planning Objective\n"
        f"- {planning_objective}\n\n"
        "## Repository Scan\n"
        f"{repository_scan}\n\n"
        "## Generated Phases\n\n"
        f"{render_phase_sections(phases)}"
    )


def _build_progress_tracker(phases: tuple[PhaseSpec, ...]) -> str:
    """Build progress tracker."""
    from .utils import build_progress_tracker
    return build_progress_tracker(phases)
