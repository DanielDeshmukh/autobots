"""Repository scanning, phase specification, and plan synthesis."""

from .models import RepositoryScan, PhaseSpec, PlanArtifacts
from .scanner import RepositoryScanner
from .synthesis import PlanSynthesizer
from .core import write_plan, parse_roadmap, route_task, build_cluster_dispatch


def scan_repository(target_root):
    """Convenience function for scanning a repository."""
    return RepositoryScanner.scan_repository(target_root)


__all__ = [
    "RepositoryScan",
    "PhaseSpec",
    "PlanArtifacts",
    "RepositoryScanner",
    "PlanSynthesizer",
    "write_plan",
    "scan_repository",
    "parse_roadmap",
    "route_task",
    "build_cluster_dispatch",
]
