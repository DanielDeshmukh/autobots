"""Phase specification building and plan synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import RepositoryScan, PhaseSpec, PlanArtifacts
from .scanner import RepositoryScanner
from .utils import (
    build_validation_commands,
    select_relevant_paths,
    select_validation_paths,
    select_doc_paths,
    normalize_phase_dependencies,
    render_phase_sections,
    build_progress_tracker,
)

if TYPE_CHECKING:
    from ..bootstrap import RepoProfile


class PlanSynthesizer:
    """Synthesizes planning artifacts."""

    @staticmethod
    def default_goal(profile: RepoProfile) -> str:
        """Generate a default goal based on repository profile."""
        primary_language = profile.languages[0] if profile.languages else "project"
        return f"Prepare the next implementation-ready plan for this {primary_language} repository."

    @staticmethod
    def build_phase_specs(
        profile: RepoProfile,
        scan: RepositoryScan,
        *,
        goal: str,
    ) -> tuple[PhaseSpec, ...]:
        """Build phase specifications."""
        validation_commands = build_validation_commands(profile, scan)
        relevant_paths = select_relevant_paths(scan, goal)
        docs_phase_needed = bool(scan.docs)
        paths_label = ", ".join(relevant_paths)
        validation_label = ", ".join(validation_commands) or "manual verification"
        phases: list[PhaseSpec] = [
            PhaseSpec(
                phase_id="P1",
                title=f"Set up project scaffolding for {goal}",
                goal=(
                    f"Create the foundational project structure needed for '{goal}'. "
                    f"Set up configuration files, dependencies, and the basic directory layout in {paths_label}."
                ),
                acceptance_checks=(
                    f"Project structure exists in {paths_label} with all required configuration files.",
                    "Dependencies are listed and the project can be initialized.",
                ),
                depends_on=(),
                relevant_paths=relevant_paths,
                validation_commands=(),
            ),
            PhaseSpec(
                phase_id="P2",
                title=f"Implement core functionality for {goal}",
                goal=(
                    f"Build the main application logic and components needed for '{goal}' in {paths_label}."
                ),
                acceptance_checks=(
                    "Core application logic is implemented and complete.",
                    "All required components and modules are created.",
                ),
                depends_on=("P1",),
                relevant_paths=relevant_paths,
                validation_commands=validation_commands,
            ),
            PhaseSpec(
                phase_id="P3",
                title=f"Polish and integrate {goal}",
                goal=(
                    f"Add styling, integration, and finishing touches so '{goal}' works end-to-end."
                ),
                acceptance_checks=(
                    "Application is fully styled and integrated.",
                    "All files work together as a complete runnable application.",
                ),
                depends_on=("P2",),
                relevant_paths=select_validation_paths(scan),
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
                    relevant_paths=select_doc_paths(scan),
                    validation_commands=(),
                )
            )
        return tuple(normalize_phase_dependencies(tuple(phases)))

    @staticmethod
    def synthesize_plan(
        profile: RepoProfile,
        scan: RepositoryScan,
        *,
        goal: str,
    ) -> PlanArtifacts:
        """Synthesize a complete plan."""
        source_roots = ", ".join(scan.source_roots)
        test_roots = ", ".join(scan.test_roots) or "None detected"
        build_files = ", ".join(scan.build_files) or "None detected"
        env_files = ", ".join(scan.env_files) or "None detected"
        docs = ", ".join(scan.docs) or "None detected"
        frameworks = ", ".join(scan.frameworks) or "None detected"
        languages = ", ".join(profile.languages)
        package_managers = ", ".join(profile.package_managers)
        test_tools = ", ".join(profile.test_tools)

        phases = PlanSynthesizer.build_phase_specs(profile, scan, goal=goal)
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
            f"{render_phase_sections(phases)}"
        )
        progress = build_progress_tracker(phases)
        return PlanArtifacts(roadmap=roadmap, progress=progress, phases=phases)
