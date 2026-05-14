from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .bootstrap import RepoProfile, detect_repo_profile
from .workspace import TargetProjectWorkspace


BUILD_FILES = (
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
)
ENV_FILES = (".env", ".env.example", ".env.local", ".env.test")
DOC_FILES = ("README.md", "product-definition.md", "PUBLISHING.md")
TEST_DIR_NAMES = {"tests", "test"}
SOURCE_DIR_NAMES = {"src", "app", "lib", "autobots"}


@dataclass(frozen=True)
class RepositoryScan:
    build_files: tuple[str, ...]
    env_files: tuple[str, ...]
    docs: tuple[str, ...]
    source_roots: tuple[str, ...]
    test_roots: tuple[str, ...]
    frameworks: tuple[str, ...]


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    title: str
    goal: str
    acceptance_checks: tuple[str, ...]
    depends_on: tuple[str, ...]
    relevant_paths: tuple[str, ...]
    validation_commands: tuple[str, ...]


@dataclass(frozen=True)
class PlanArtifacts:
    roadmap: str
    progress: str
    phases: tuple[PhaseSpec, ...]


def scan_repository(target_root: str | Path) -> RepositoryScan:
    root = Path(target_root).expanduser().resolve()
    build_files = tuple(name for name in BUILD_FILES if (root / name).exists())
    env_files = tuple(name for name in ENV_FILES if (root / name).exists())
    docs = tuple(name for name in DOC_FILES if (root / name).exists())
    frameworks = _detect_frameworks(root)

    source_roots: list[str] = []
    test_roots: list[str] = []
    for child in root.iterdir():
        if child.name.startswith(".") or not child.exists():
            continue
        if child.is_dir():
            if child.name in TEST_DIR_NAMES:
                test_roots.append(child.name)
                continue
            if child.name in SOURCE_DIR_NAMES:
                source_roots.append(child.name)
            if child.name in {"context", "venv", "__pycache__", "dist"}:
                continue
            if (
                (child / "__init__.py").exists()
                or any(grandchild.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go"} for grandchild in child.iterdir())
            ):
                source_roots.append(child.name)
            continue

        if child.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go"}:
            source_roots.append(".")

    return RepositoryScan(
        build_files=build_files,
        env_files=env_files,
        docs=docs,
        source_roots=tuple(dict.fromkeys(source_roots or ["."])),
        test_roots=tuple(dict.fromkeys(test_roots)),
        frameworks=frameworks,
    )


def default_goal(profile: RepoProfile) -> str:
    primary_language = profile.languages[0] if profile.languages else "project"
    return f"Prepare the next implementation-ready plan for this {primary_language} repository."


def build_phase_specs(profile: RepoProfile, scan: RepositoryScan, *, goal: str) -> tuple[PhaseSpec, ...]:
    validation_commands = _build_validation_commands(profile, scan)
    relevant_paths = _select_relevant_paths(scan, goal)
    docs_phase_needed = bool(scan.docs)
    paths_label = ", ".join(relevant_paths)
    validation_label = ", ".join(validation_commands) or "manual verification"
    phases: list[PhaseSpec] = [
        PhaseSpec(
            phase_id="P1",
            title="Inspect impacted code and confirm implementation scope",
            goal=(
                f"Review the repository surfaces most relevant to '{goal}', especially {paths_label}, "
                "and identify constraints, entry points, dependencies, and missing context before editing begins."
            ),
            acceptance_checks=(
                f"Relevant implementation surfaces are narrowed to {paths_label}.",
                "Known blockers or unknowns are captured before implementation planning continues.",
            ),
            depends_on=(),
            relevant_paths=relevant_paths,
            validation_commands=(),
        ),
        PhaseSpec(
            phase_id="P2",
            title="Implement the core change in the primary code paths",
            goal=(
                f"Apply the main change needed for '{goal}' in {paths_label} and keep the work scoped to one coherent deliverable."
            ),
            acceptance_checks=(
                "The primary code paths needed for the goal are updated.",
                "The implementation stays aligned with the detected repository structure.",
            ),
            depends_on=("P1",),
            relevant_paths=relevant_paths,
            validation_commands=validation_commands,
        ),
        PhaseSpec(
            phase_id="P3",
            title="Add or update validation coverage for the change",
            goal=(
                f"Add or refresh automated checks so the change can be verified with {validation_label}."
            ),
            acceptance_checks=(
                "At least one validation path exists for the delivered change.",
                "Tests or validation coverage reflect the intended behavior.",
            ),
            depends_on=("P2",),
            relevant_paths=_select_validation_paths(scan),
            validation_commands=validation_commands,
        ),
    ]
    if docs_phase_needed:
        phases.append(
            PhaseSpec(
                phase_id="P4",
                title="Refresh supporting docs and execution context",
                goal=(
                    "Update operator-facing docs and context files so the new plan or behavior is discoverable to the next run."
                ),
                acceptance_checks=(
                    "Docs or context files mention the new behavior or workflow.",
                    "Follow-up operators can understand the change without diff-hunting through code.",
                ),
                depends_on=("P3",),
                relevant_paths=_select_doc_paths(scan),
                validation_commands=(),
            )
        )
    return tuple(_normalize_phase_dependencies(tuple(phases)))


def synthesize_plan(
    profile: RepoProfile,
    scan: RepositoryScan,
    *,
    goal: str,
) -> PlanArtifacts:
    source_roots = ", ".join(scan.source_roots)
    test_roots = ", ".join(scan.test_roots) or "None detected"
    build_files = ", ".join(scan.build_files) or "None detected"
    env_files = ", ".join(scan.env_files) or "None detected"
    docs = ", ".join(scan.docs) or "None detected"
    frameworks = ", ".join(scan.frameworks) or "None detected"
    languages = ", ".join(profile.languages)
    package_managers = ", ".join(profile.package_managers)
    test_tools = ", ".join(profile.test_tools)

    phases = build_phase_specs(profile, scan, goal=goal)
    roadmap = (
        "# Roadmap\n\n"
        "## Planning Objective\n"
        f"- {goal}\n\n"
        "## Repository Scan\n"
        f"- Languages: {languages}\n"
        f"- Package managers: {package_managers}\n"
        f"- Test tools: {test_tools}\n"
        f"- Source roots: {source_roots}\n"
        f"- Test roots: {test_roots}\n"
        f"- Build files: {build_files}\n"
        f"- Env files: {env_files}\n"
        f"- Frameworks: {frameworks}\n"
        f"- Docs: {docs}\n\n"
        "## Generated Phases\n\n"
        f"{_render_phase_sections(phases)}"
    )
    progress = _build_progress_tracker(phases)
    return PlanArtifacts(roadmap=roadmap, progress=progress, phases=phases)


def write_plan(
    workspace: TargetProjectWorkspace,
    *,
    goal: str | None = None,
    append: bool = False,
    insert_after: str | None = None,
    dry_run: bool = False,
) -> tuple[RepoProfile, RepositoryScan, PlanArtifacts]:
    profile = detect_repo_profile(workspace.target_root)
    scan = scan_repository(workspace.target_root)
    resolved_goal = (goal or "").strip() or default_goal(profile)
    generated = synthesize_plan(profile, scan, goal=resolved_goal)
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
        workspace.write_context_file("roadmap.md", artifacts.roadmap, lock_owner="Autobots/plan")
        workspace.write_context_file("progress-tracker.md", artifacts.progress, lock_owner="Autobots/plan")
    return profile, scan, artifacts


def _render_phase_sections(phases: tuple[PhaseSpec, ...]) -> str:
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


def _build_progress_tracker(phases: tuple[PhaseSpec, ...]) -> str:
    lines = ["# Progress Tracker", ""]
    for phase in phases:
        dependencies = ", ".join(phase.depends_on) if phase.depends_on else "none"
        acceptance = phase.acceptance_checks[0]
        validation = ", ".join(phase.validation_commands) if phase.validation_commands else "none"
        lines.append(
            f"- [ ] {phase.phase_id} | {phase.title} | depends on: {dependencies} | validation: {validation} | acceptance: {acceptance}"
        )
    return "\n".join(lines) + "\n"


def _read_optional_context_file(workspace: TargetProjectWorkspace, relative_path: str) -> str:
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
    statuses_by_phase_id, statuses_by_title = _extract_progress_statuses(existing_progress)
    merged_lines: list[str] = []
    for line in regenerated_progress.splitlines():
        phase_id = _extract_progress_phase_id(line)
        title = _extract_progress_title(line)
        status = None
        if phase_id:
            status = statuses_by_phase_id.get(phase_id)
        if status is None and title:
            status = statuses_by_title.get(title)
        if status is None:
            merged_lines.append(line)
            continue
        merged_lines.append(_apply_status_to_line(line, status))
    return "\n".join(merged_lines) + "\n"


def _parse_generated_phases(roadmap_text: str, progress_text: str) -> tuple[PhaseSpec, ...]:
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
            checks = tuple(_normalize_acceptance_check(line) for line in checks_block.splitlines() if line.strip())
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


def _extract_progress_statuses(progress_text: str) -> tuple[dict[str, str], dict[str, str]]:
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
        phase_id = _extract_progress_phase_id(line)
        title = _extract_progress_title(line)
        if phase_id:
            statuses_by_phase_id[phase_id] = status
        if title:
            statuses_by_title[title] = status
    return statuses_by_phase_id, statuses_by_title


def _extract_progress_phase_id(line: str) -> str:
    match = re.search(r"\]\s+(P\d+)\s+\|", line)
    return match.group(1).strip() if match else ""


def _next_phase_number(phases: tuple[PhaseSpec, ...]) -> int:
    phase_numbers = [
        int(match.group(1))
        for phase in phases
        if (match := re.match(r"P(\d+)$", phase.phase_id))
    ]
    return (max(phase_numbers) + 1) if phase_numbers else 1


def _renumber_phases(phases: tuple[PhaseSpec, ...], *, start_index: int) -> tuple[PhaseSpec, ...]:
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
        f"{_render_phase_sections(phases)}"
    )


def _detect_frameworks(root: Path) -> tuple[str, ...]:
    detected: list[str] = []
    package_json = root / "package.json"
    pyproject = root / "pyproject.toml"
    if package_json.exists():
        payload = package_json.read_text(encoding="utf-8", errors="ignore").lower()
        if "\"react\"" in payload:
            detected.append("React")
        if "\"next\"" in payload:
            detected.append("Next.js")
        if "\"vue\"" in payload:
            detected.append("Vue")
    if pyproject.exists():
        payload = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
        if "django" in payload:
            detected.append("Django")
        if "fastapi" in payload:
            detected.append("FastAPI")
        if "flask" in payload:
            detected.append("Flask")
    return tuple(dict.fromkeys(detected))


def _normalize_acceptance_check(line: str) -> str:
    normalized = line.strip()
    normalized = normalized.removeprefix("- ").strip()
    return normalized


def _extract_progress_title(line: str) -> str:
    match = re.search(r"\]\s+(?:P\d+\s+\|\s+)?(.+?)\s+\|\s+depends on:", line)
    return match.group(1).strip() if match else ""


def _apply_status_to_line(line: str, status: str) -> str:
    marker = {"PENDING": "[ ]", "IN_PROGRESS": "[~]", "COMPLETE": "[x]"}[status]
    return re.sub(r"\[[ x~]\]", marker, line, count=1)


def _build_validation_commands(profile: RepoProfile, scan: RepositoryScan) -> tuple[str, ...]:
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


def _select_relevant_paths(scan: RepositoryScan, goal: str) -> tuple[str, ...]:
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


def _select_validation_paths(scan: RepositoryScan) -> tuple[str, ...]:
    selected: list[str] = []
    if scan.test_roots:
        selected.extend(scan.test_roots)
    elif "tests" in scan.source_roots:
        selected.append("tests")
    else:
        selected.append("project root")
    return tuple(dict.fromkeys(selected))


def _select_doc_paths(scan: RepositoryScan) -> tuple[str, ...]:
    selected = list(scan.docs[:3]) or ["context/roadmap.md", "context/progress-tracker.md"]
    return tuple(dict.fromkeys(selected))


def _normalize_phase_dependencies(phases: tuple[PhaseSpec, ...]) -> tuple[PhaseSpec, ...]:
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
