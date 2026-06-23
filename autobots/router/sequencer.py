"""Task sequencer — determines parallel vs sequential execution order."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .decomposer import Subtask

logger = logging.getLogger("autobots")


@dataclass
class ExecutionGroup:
    """A group of subtasks that can run in parallel."""
    subtasks: list[Subtask]
    group_index: int = 0

    @property
    def clusters(self) -> list[str]:
        return [s.cluster for s in self.subtasks]

    @property
    def descriptions(self) -> list[str]:
        return [s.task for s in self.subtasks]


@dataclass
class ExecutionPlan:
    """Sequential list of parallel execution groups."""
    groups: list[ExecutionGroup]
    total_subtasks: int = 0

    @property
    def parallel_groups(self) -> int:
        return sum(1 for g in self.groups if len(g.subtasks) > 1)

    @property
    def sequential_steps(self) -> int:
        return len(self.groups)

    def summary(self) -> str:
        lines = [f"Execution plan: {self.total_subtasks} subtasks in {self.sequential_steps} steps"]
        for i, group in enumerate(self.groups):
            if len(group.subtasks) == 1:
                s = group.subtasks[0]
                lines.append(f"  Step {i+1}: [{s.cluster}] {s.task}")
            else:
                lines.append(f"  Step {i+1} (parallel):")
                for s in group.subtasks:
                    lines.append(f"    - [{s.cluster}] {s.task}")
        return "\n".join(lines)


class TaskSequencer:
    """Determines execution order from decomposed subtasks."""

    def sequence(self, subtasks: list[Subtask]) -> ExecutionPlan:
        """Build execution plan from subtasks with dependencies."""
        if not subtasks:
            return ExecutionPlan(groups=[], total_subtasks=0)

        # Build dependency graph
        dep_map = {s.index: s.depends_on for s in subtasks}
        task_map = {s.index: s for s in subtasks}

        # Topological sort with parallel grouping
        completed = set()
        remaining = set(dep_map.keys())
        groups = []
        group_index = 0

        while remaining:
            # Find tasks whose dependencies are all completed
            ready = [
                idx for idx in remaining
                if all(d in completed for d in dep_map[idx])
            ]

            if not ready:
                # Circular dependency — break it by taking first remaining
                logger.warning("Circular dependency detected, breaking at %s", remaining)
                ready = [min(remaining)]

            # Create parallel group
            group = ExecutionGroup(
                subtasks=[task_map[idx] for idx in sorted(ready)],
                group_index=group_index,
            )
            groups.append(group)

            # Mark as completed
            completed.update(ready)
            remaining -= set(ready)
            group_index += 1

        return ExecutionPlan(
            groups=groups,
            total_subtasks=len(subtasks),
        )

    def sequence_simple(self, subtasks: list[Subtask]) -> ExecutionPlan:
        """Simple sequential execution — no parallelism."""
        return ExecutionPlan(
            groups=[ExecutionGroup(subtasks=[s], group_index=i) for i, s in enumerate(subtasks)],
            total_subtasks=len(subtasks),
        )
