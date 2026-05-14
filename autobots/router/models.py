"""Data models for routing operations."""

from __future__ import annotations

from dataclasses import dataclass
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
