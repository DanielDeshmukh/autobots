"""Cluster planning and model selection."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..catalog import ClusterCatalog, ModelSpec
from .models import ClusterPlan, PhaseRecord
from ..executor import WorkPacket

if TYPE_CHECKING:
    pass


class ClusterPlanner:
    """Plans cluster assignments and model selection."""

    def __init__(self, catalog: ClusterCatalog | None = None, api_key: str | None = None):
        self.catalog = catalog or ClusterCatalog(api_key=api_key)

    def build_cluster_plan(self, phase: PhaseRecord, roadmap_text: str) -> ClusterPlan:
        """Build a cluster plan for a phase."""
        signal = f"{phase.title}\n{roadmap_text}"
        primary_cluster = self.catalog.route(signal)
        primary_lead, primary_reviewer, primary_support = self.catalog.select_models(primary_cluster, signal)
        command_lead, command_reviewer, _ = self.catalog.select_models("Optimus", signal)
        secretary_lead = self._select_secretary_model()
        safety_lead, _, _ = self.catalog.select_models("RedAlert", signal)
        repair_lead, _, _ = self.catalog.select_models("Ratchet", signal)
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
