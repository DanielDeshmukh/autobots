"""Compare current workspace state to snapshots."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DiffResult:
    """Result of comparing current state to a snapshot."""

    snapshot_id: str
    task_id: str
    created_at: float
    added: list[str] = None
    removed: list[str] = None
    modified: list[dict[str, Any]] = None

    def __post_init__(self):
        self.added = self.added or []
        self.removed = self.removed or []
        self.modified = self.modified or []

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.removed or self.modified)

    def summary(self) -> str:
        """Return a summary of the diff."""
        parts = []
        if self.added:
            parts.append(f"{len(self.added)} added")
        if self.removed:
            parts.append(f"{len(self.removed)} removed")
        if self.modified:
            parts.append(f"{len(self.modified)} modified")
        return ", ".join(parts) if parts else "No changes"


def get_snapshot_dir(snapshots_root: Path, snapshot_id: str) -> Path | None:
    """Get the directory for a snapshot."""
    snapshot_dir = snapshots_root / snapshot_id
    return snapshot_dir if snapshot_dir.exists() else None


def get_latest_snapshot(snapshots_root: Path) -> tuple[str, dict] | None:
    """Get the most recent snapshot."""
    if not snapshots_root.exists():
        return None

    snapshots = []
    for d in snapshots_root.iterdir():
        if d.is_dir():
            metadata_path = d / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    snapshots.append((d.name, metadata))
                except json.JSONDecodeError:
                    continue

    if not snapshots:
        return None

    snapshots.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
    return snapshots[0]


def get_snapshot_metadata(snapshots_root: Path, snapshot_id: str) -> dict | None:
    """Get metadata for a snapshot."""
    snapshot_dir = get_snapshot_dir(snapshots_root, snapshot_id)
    if not snapshot_dir:
        return None

    metadata_path = snapshot_dir / "metadata.json"
    if not metadata_path.exists():
        return None

    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def list_snapshots(snapshots_root: Path) -> list[dict]:
    """List all available snapshots."""
    if not snapshots_root.exists():
        return []

    snapshots = []
    for d in snapshots_root.iterdir():
        if d.is_dir():
            metadata_path = d / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    snapshots.append(metadata)
                except json.JSONDecodeError:
                    continue

    snapshots.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return snapshots


def _get_snapshot_files(snapshot_dir: Path) -> dict[str, str]:
    """Get all files in a snapshot as {relative_path: content}."""
    files = {}
    for f in snapshot_dir.rglob("*"):
        if f.is_file() and f.name != "metadata.json":
            rel = f.relative_to(snapshot_dir).as_posix()
            try:
                files[rel] = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                files[rel] = f"<binary file>"
    return files


def _get_current_files(workspace_root: Path, tracked_paths: list[str] | None = None) -> dict[str, str]:
    """Get current files from workspace as {relative_path: content}."""
    files = {}
    source_dirs = ["src", "app", "lib", "tests", "docs", "scripts"]

    for dir_name in source_dirs:
        dir_path = workspace_root / dir_name
        if not dir_path.exists():
            continue

        for ext in ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.json", "*.yaml", "*.yml", "*.md"]:
            for f in dir_path.rglob(ext):
                rel = f.relative_to(workspace_root).as_posix()
                if tracked_paths and rel not in tracked_paths:
                    continue
                try:
                    files[rel] = f.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    files[rel] = f"<binary file>"
    return files


def compute_diff(workspace_root: Path, snapshots_root: Path, snapshot_id: str | None = None) -> DiffResult | None:
    """Compute diff between current workspace and a snapshot.

    Args:
        workspace_root: Path to the project root
        snapshots_root: Path to the snapshots directory
        snapshot_id: Specific snapshot to compare, or None for latest

    Returns:
        DiffResult with changes, or None if snapshot not found
    """
    if snapshot_id:
        snapshot_info = get_snapshot_metadata(snapshots_root, snapshot_id)
        snapshot_dir = get_snapshot_dir(snapshots_root, snapshot_id)
    else:
        result = get_latest_snapshot(snapshots_root)
        if not result:
            return None
        snapshot_id, snapshot_info = result
        snapshot_dir = get_snapshot_dir(snapshots_root, snapshot_id)

    if not snapshot_info or not snapshot_dir:
        return None

    # Get files
    snapshot_files = _get_snapshot_files(snapshot_dir)
    current_files = _get_current_files(workspace_root)

    # Compute diff
    added = []
    removed = []
    modified = []

    # Files in current but not in snapshot = added
    for path in current_files:
        if path not in snapshot_files:
            added.append(path)

    # Files in snapshot but not in current = removed
    for path in snapshot_files:
        if path not in current_files:
            removed.append(path)

    # Files in both but different = modified
    for path in current_files:
        if path in snapshot_files:
            if current_files[path] != snapshot_files[path]:
                # Compute line-by-line diff
                old_lines = snapshot_files[path].splitlines(keepends=True)
                new_lines = current_files[path].splitlines(keepends=True)
                diff = list(difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"snapshot/{path}",
                    tofile=f"current/{path}",
                    lineterm=""
                ))
                modified.append({
                    "path": path,
                    "diff": "\n".join(diff),
                    "old_lines": len(old_lines),
                    "new_lines": len(new_lines)
                })

    return DiffResult(
        snapshot_id=snapshot_id,
        task_id=snapshot_info.get("task_id", "unknown"),
        created_at=snapshot_info.get("created_at", 0),
        added=added,
        removed=removed,
        modified=modified
    )
