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
