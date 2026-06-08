"""Cluster planning and model selection."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from ..catalog import ClusterCatalog, ModelSpec
from .models import ClusterPlan, ClusterRoleAssignment, ParallelWorkstream, PhaseRecord, RoutingScore
from ..executor import WorkPacket

if TYPE_CHECKING:
    pass


def route_to_cluster(task: str, cluster_map: dict) -> dict:
    """Route a single task to its cluster and return the routing result."""
    info = cluster_map.get(task, {"cluster": "UltraMagnus", "score": 0, "reasons": []})
    return {
        "task": task,
        "cluster": info["cluster"],
        "score": info["score"],
        "reasons": info["reasons"],
    }


def dispatch_phase(tasks: list[str], cluster_map: dict) -> list[dict]:
    """
    Routes all tasks to their clusters.
    Returns results in the same order as input tasks.
    """
    return [route_to_cluster(task, cluster_map) for task in tasks]


class ClusterPlanner:
    """Plans cluster assignments and model selection."""

    def __init__(self, catalog: ClusterCatalog | None = None, api_key: str | None = None):
        self.catalog = catalog or ClusterCatalog(api_key=api_key)
        self.parallel_planning_enabled = os.getenv("AUTOBOTS_ENABLE_PARALLEL_PLANNING", "0") == "1"

    def build_cluster_plan(self, phase: PhaseRecord, roadmap_text: str) -> ClusterPlan:
        """Build a cluster plan for a phase."""
        signal = f"{phase.title}\n{roadmap_text}"
        route_decision = self.catalog.route_with_reasoning(signal)
        primary_cluster = route_decision.cluster_name
        primary_lead, primary_reviewer, primary_support = self.catalog.select_models(primary_cluster, signal)
        command_lead, command_reviewer, _ = self.catalog.select_models("Optimus", signal)
        secretary_lead = self._select_secretary_model()
        safety_lead, _, _ = self.catalog.select_models("RedAlert", signal)
        repair_lead, _, _ = self.catalog.select_models("Ratchet", signal)
        role_assignments = [
            ClusterRoleAssignment(
                role_name="planner",
                cluster_name="Optimus",
                lead=command_lead,
                reviewer=command_reviewer,
                objective="Break the phase into an executable mission brief.",
            ),
            ClusterRoleAssignment(
                role_name="implementer",
                cluster_name=primary_cluster,
                lead=primary_lead,
                reviewer=primary_reviewer,
                support=primary_support,
                objective="Produce the main implementation artifacts for the phase.",
            ),
            ClusterRoleAssignment(
                role_name="reviewer",
                cluster_name="RedAlert",
                lead=safety_lead,
                objective="Review correctness, safety, and maintainability before completion.",
            ),
            ClusterRoleAssignment(
                role_name="repair",
                cluster_name="Ratchet",
                lead=repair_lead,
                objective="Repair validation or review failures without losing intent.",
            ),
        ]
        workstreams = self._plan_parallel_workstreams(phase, roadmap_text)
        return ClusterPlan(
            primary_cluster=primary_cluster,
            primary_lead=primary_lead,
            primary_reviewer=primary_reviewer,
            primary_support=primary_support,
            command_lead=command_lead,
            command_reviewer=command_reviewer,
            secretary_lead=secretary_lead,
            safety_lead=safety_lead,
            repair_lead=repair_lead,
            routing_scores=[
                RoutingScore(cluster_name=name, score=score)
                for name, score in route_decision.scored_clusters
            ],
            routing_rationale=list(route_decision.reasons),
            role_assignments=role_assignments,
            parallel_workstreams=workstreams,
            merge_strategy="sequential_apply" if workstreams else "single_branch",
        )

    def build_work_packet_from_phase(
        self,
        phase: PhaseRecord,
        roadmap_text: str,
    ) -> WorkPacket:
        """Extract phase information and build a work packet."""
        phase_id = self._extract_phase_id(phase.title)
        constraints = self._extract_constraints(roadmap_text, phase_id)
        validation_commands = self._extract_validation_commands(roadmap_text, phase_id)
        acceptance_checks = self._extract_acceptance_checks(roadmap_text, phase_id)
        relevant_paths = self._extract_relevant_paths(roadmap_text, phase_id)

        return WorkPacket(
            phase_id=phase_id,
            title=phase.title,
            goal=self._extract_phase_goal(roadmap_text, phase_id),
            relevant_files=relevant_paths,
            constraints=constraints,
            validation_commands=validation_commands,
            acceptance_checks=acceptance_checks,
        )

    def _extract_phase_id(self, title: str) -> str:
        """Extract phase ID from title."""
        match = re.search(r"\b(P\d+)\b", title)
        return match.group(1) if match else "P0"

    def _extract_phase_goal(self, roadmap_text: str, phase_id: str) -> str:
        """Extract phase goal from roadmap."""
        pattern = rf"## {phase_id}.*?\n\n.*?(?=##|\Z)"
        match = re.search(pattern, roadmap_text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(0)
            lines = text.split("\n")
            for line in lines:
                if "goal:" in line.lower():
                    return line.split(":", 1)[1].strip()
        return f"Execute {phase_id}"

    def _extract_relevant_paths(self, roadmap_text: str, phase_id: str) -> list[str]:
        """Extract relevant paths from roadmap."""
        pattern = rf"## {phase_id}.*?[Rr]elevant\s+(?:paths|files):\s*(.+?)(?:\n\n|\Z)"
        match = re.search(pattern, roadmap_text, re.DOTALL)
        if match:
            paths_text = match.group(1).strip()
            paths = [p.strip() for p in re.split(r"[,;]", paths_text) if p.strip()]
            return paths[:20]
        return []

    def _extract_validation_commands(self, roadmap_text: str, phase_id: str) -> list[str]:
        """Extract validation commands from roadmap."""
        pattern = rf"## {phase_id}.*?[Vv]alidation.*?:\s*(.+?)(?:\n\n|\Z)"
        match = re.search(pattern, roadmap_text, re.DOTALL)
        if match:
            commands_text = match.group(1).strip()
            commands = [c.strip() for c in re.split(r"[,;]", commands_text) if c.strip()]
            return commands[:5]
        return []

    def _extract_constraints(self, roadmap_text: str, phase_id: str) -> list[str]:
        """Extract constraints from roadmap."""
        pattern = rf"## {phase_id}.*?[Cc]onstraints?:\s*(.+?)(?:\n\n|\Z)"
        match = re.search(pattern, roadmap_text, re.DOTALL)
        if match:
            constraints_text = match.group(1).strip()
            constraints = [c.strip() for c in re.split(r"[,;]", constraints_text) if c.strip()]
            return constraints[:5]
        return []

    def _extract_acceptance_checks(self, roadmap_text: str, phase_id: str) -> list[str]:
        """Extract acceptance checks from roadmap."""
        pattern = rf"## {phase_id}.*?[Aa]ccept(?:ance)?.*?:\s*(.+?)(?:\n\n|\Z)"
        match = re.search(pattern, roadmap_text, re.DOTALL)
        if match:
            checks_text = match.group(1).strip()
            checks = [c.strip() for c in re.split(r"[,;]", checks_text) if c.strip()]
            return checks[:5]
        return []

    def _select_secretary_model(self) -> ModelSpec:
        """Select a secretary model."""
        optimus = self.catalog.get_cluster("Optimus")
        for model in optimus.models:
            if model.model_id.lower().endswith("step-3.5-flash"):
                return model
        return optimus.models[0]

    def _plan_parallel_workstreams(self, phase: PhaseRecord, roadmap_text: str) -> list[ParallelWorkstream]:
        """Identify independent path groups that could run in parallel in a future phase."""
        if not self.parallel_planning_enabled:
            return []

        phase_id = self._extract_phase_id(phase.title)
        relevant_paths = self._extract_relevant_paths(roadmap_text, phase_id)
        if len(relevant_paths) < 2:
            return []

        grouped: dict[str, list[str]] = {}
        for path in relevant_paths:
            normalized = path.strip().replace("\\", "/")
            root = normalized.split("/", 1)[0] if "/" in normalized else normalized
            grouped.setdefault(root, []).append(normalized)

        workstreams: list[ParallelWorkstream] = []
        for index, (root, paths) in enumerate(sorted(grouped.items()), start=1):
            if len(paths) == 0:
                continue
            assigned_cluster = self._cluster_for_path_root(root)
            workstreams.append(
                ParallelWorkstream(
                    branch_id=f"{phase_id}-B{index}",
                    title=f"{phase.title} [{root}]",
                    focus_paths=paths[:5],
                    assigned_cluster=assigned_cluster,
                    merge_strategy="sequential_apply",
                )
            )

        return workstreams[:3] if len(workstreams) > 1 else []

    def _cluster_for_path_root(self, root: str) -> str:
        normalized = root.lower()
        if normalized in {"app", "ui", "frontend", "styles"}:
            return "Jazz"
        if normalized in {"tests", "specs"}:
            return "Ratchet"
        if normalized in {"docs", "context"}:
            return "Optimus"
        return "UltraMagnus"
