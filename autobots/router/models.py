"""Data models for routing operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..catalog import ModelSpec


EventHandler = Callable[[str], None]


@dataclass
class PhaseRecord:
    """A parsed phase from progress tracker."""

    line_index: int
    raw_line: str
    title: str
    status: str


@dataclass
class ClusterMessage:
    """A message from a cluster during execution."""

    speaker: str
    objective: str
    summary: str


@dataclass
class RoutingScore:
    """Scored routing evidence for a candidate cluster."""

    cluster_name: str
    score: int
    reasons: list[str] = field(default_factory=list)


@dataclass
class ClusterRoleAssignment:
    """Explicit role assignment for a cluster participant."""

    role_name: str
    cluster_name: str
    lead: ModelSpec
    reviewer: ModelSpec | None = None
    support: list[ModelSpec] = field(default_factory=list)
    objective: str = ""


@dataclass
class ParallelWorkstream:
    """Optional independent workstream planned for future parallel execution."""

    branch_id: str
    title: str
    focus_paths: list[str] = field(default_factory=list)
    assigned_cluster: str = "UltraMagnus"
    merge_strategy: str = "sequential_apply"


@dataclass
class ClusterPlan:
    """Execution plan assigning models to cluster roles."""

    primary_cluster: str
    primary_lead: ModelSpec
    primary_reviewer: ModelSpec
    primary_support: list[ModelSpec]
    command_lead: ModelSpec
    command_reviewer: ModelSpec
    secretary_lead: ModelSpec
    safety_lead: ModelSpec
    repair_lead: ModelSpec
    routing_scores: list[RoutingScore] = field(default_factory=list)
    routing_rationale: list[str] = field(default_factory=list)
    role_assignments: list[ClusterRoleAssignment] = field(default_factory=list)
    parallel_workstreams: list[ParallelWorkstream] = field(default_factory=list)
    merge_strategy: str = "sequential_apply"

    @property
    def merger(self) -> MergeStrategy:
        """Return the merge strategy handler for this plan."""
        return MergeStrategy(self.merge_strategy)

    def merge_results(self, results: list[dict]) -> list[dict]:
        """Merge results from parallel workstreams using the configured strategy."""
        return self.merger.merge_file_sets(results)


class MergeStrategy:
    """Defines how parallel workstream results are merged."""

    MERGE_MODES = {
        "sequential_apply": "Apply each branch result in order, later branches override earlier",
        "union_files": "Merge files from all branches, no conflicts",
        "best_effort": "Use first successful result, fall back to subsequent",
        "consensus": "Keep file only if all branches agree on content",
    }

    def __init__(self, mode: str = "sequential_apply"):
        self.mode = mode if mode in self.MERGE_MODES else "sequential_apply"

    def merge_file_sets(self, branches: list[dict]) -> list[dict]:
        """Merge file outputs from multiple workstream branches."""
        if not branches:
            return []

        if self.mode == "sequential_apply":
            return self._merge_sequential(branches)
        elif self.mode == "union_files":
            return self._merge_union(branches)
        elif self.mode == "best_effort":
            return self._merge_best_effort(branches)
        elif self.mode == "consensus":
            return self._merge_consensus(branches)
        return branches[-1] if branches else []

    def _merge_sequential(self, branches: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}
        for branch in branches:
            for file_entry in branch.get("files", []):
                key = f"{file_entry.get('root', 'src')}:{file_entry.get('path', '')}"
                merged[key] = file_entry
        return list(merged.values())

    def _merge_union(self, branches: list[dict]) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for branch in branches:
            for file_entry in branch.get("files", []):
                key = f"{file_entry.get('root', 'src')}:{file_entry.get('path', '')}"
                if key not in seen:
                    seen.add(key)
                    result.append(file_entry)
        return result

    def _merge_best_effort(self, branches: list[dict]) -> list[dict]:
        best: dict[str, dict] = {}
        best_success: dict[str, bool] = {}
        for branch in branches:
            success = branch.get("success", True)
            for file_entry in branch.get("files", []):
                key = f"{file_entry.get('root', 'src')}:{file_entry.get('path', '')}"
                if key not in best_success or (success and not best_success[key]):
                    best[key] = file_entry
                    best_success[key] = success
        return list(best.values())

    def _merge_consensus(self, branches: list[dict]) -> list[dict]:
        file_groups: dict[str, list[dict]] = {}
        for branch in branches:
            for file_entry in branch.get("files", []):
                key = f"{file_entry.get('root', 'src')}:{file_entry.get('path', '')}"
                file_groups.setdefault(key, []).append(file_entry)

        result: list[dict] = []
        for key, entries in file_groups.items():
            if len(entries) > 1:
                first_content = entries[0].get("content", "")
                if all(e.get("content", "") == first_content for e in entries):
                    result.append(entries[0])
            else:
                result.append(entries[0])
        return result


@dataclass
class ExecutionResult:
    """Result of executing a phase."""

    cluster_name: str
    summary: str
    raw_response: str
    files_written: list[str]
    journal: list[ClusterMessage]
    plan: ClusterPlan
    validation_passed: bool = True
    validation_report: str = ""
    verification_attempts: int = 0
