"""Tests for diff and logs commands."""

import json
import shutil
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from autobots.diff import (
    DiffResult,
    compute_diff,
    get_latest_snapshot,
    get_snapshot_dir,
    get_snapshot_metadata,
    list_snapshots,
)
from autobots.executor.state import (
    AuditEntry,
    ChangeType,
    RollbackManager,
    StateManager,
)


class TestDiffResult(unittest.TestCase):
    """Tests for DiffResult dataclass."""

    def test_has_changes_true_when_added(self):
        diff = DiffResult(
            snapshot_id="snap1",
            task_id="T1",
            created_at=1234567890,
            added=["new.py"]
        )
        self.assertTrue(diff.has_changes())

    def test_has_changes_true_when_removed(self):
        diff = DiffResult(
            snapshot_id="snap1",
            task_id="T1",
            created_at=1234567890,
            removed=["old.py"]
        )
        self.assertTrue(diff.has_changes())

    def test_has_changes_true_when_modified(self):
        diff = DiffResult(
            snapshot_id="snap1",
            task_id="T1",
            created_at=1234567890,
            modified=[{"path": "mod.py", "diff": "", "old_lines": 10, "new_lines": 12}]
        )
        self.assertTrue(diff.has_changes())

    def test_has_changes_false_when_empty(self):
        diff = DiffResult(
            snapshot_id="snap1",
            task_id="T1",
            created_at=1234567890
        )
        self.assertFalse(diff.has_changes())

    def test_summary_with_changes(self):
        diff = DiffResult(
            snapshot_id="snap1",
            task_id="T1",
            created_at=1234567890,
            added=["a.py"],
            removed=["b.py"],
            modified=[{"path": "c.py", "diff": "", "old_lines": 5, "new_lines": 7}]
        )
        summary = diff.summary()
        self.assertIn("1 added", summary)
        self.assertIn("1 removed", summary)
        self.assertIn("1 modified", summary)

    def test_summary_no_changes(self):
        diff = DiffResult(
            snapshot_id="snap1",
            task_id="T1",
            created_at=1234567890
        )
        self.assertEqual(diff.summary(), "No changes")


class TestDiffHelpers(unittest.TestCase):
    """Tests for diff helper functions."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir) / "workspace"
        self.snapshots = Path(self.tmpdir) / "snapshots"
        self.workspace.mkdir()
        self.snapshots.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_snapshot(self, snapshot_id: str, files: dict[str, str], task_id: str = "T1"):
        """Create a test snapshot."""
        snap_dir = self.snapshots / snapshot_id
        snap_dir.mkdir()
        for path, content in files.items():
            f = snap_dir / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
        metadata = {
            "snapshot_id": snapshot_id,
            "task_id": task_id,
            "created_at": time.time() - 100,
            "files_tracked": len(files),
        }
        (snap_dir / "metadata.json").write_text(json.dumps(metadata))

    def test_get_snapshot_dir_exists(self):
        self._create_snapshot("snap1", {"a.py": "content"})
        result = get_snapshot_dir(self.snapshots, "snap1")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "snap1")

    def test_get_snapshot_dir_not_exists(self):
        result = get_snapshot_dir(self.snapshots, "nonexistent")
        self.assertIsNone(result)

    def test_get_latest_snapshot(self):
        self._create_snapshot("snap1", {"a.py": "c1"}, task_id="T1")
        self._create_snapshot("snap2", {"a.py": "c2"}, task_id="T2")
        result = get_latest_snapshot(self.snapshots)
        self.assertIsNotNone(result)
        snap_id, metadata = result
        self.assertEqual(snap_id, "snap2")
        self.assertEqual(metadata["task_id"], "T2")

    def test_get_latest_snapshot_empty(self):
        result = get_latest_snapshot(self.snapshots)
        self.assertIsNone(result)

    def test_get_snapshot_metadata(self):
        self._create_snapshot("snap1", {"a.py": "content"})
        metadata = get_snapshot_metadata(self.snapshots, "snap1")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["snapshot_id"], "snap1")

    def test_get_snapshot_metadata_not_found(self):
        metadata = get_snapshot_metadata(self.snapshots, "nonexistent")
        self.assertIsNone(metadata)

    def test_list_snapshots(self):
        self._create_snapshot("snap1", {"a.py": "c1"})
        self._create_snapshot("snap2", {"a.py": "c2"})
        result = list_snapshots(self.snapshots)
        self.assertEqual(len(result), 2)

    def test_list_snapshots_empty(self):
        result = list_snapshots(self.snapshots)
        self.assertEqual(len(result), 0)


class TestComputeDiff(unittest.TestCase):
    """Tests for compute_diff function."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir) / "workspace"
        self.snapshots = Path(self.tmpdir) / "snapshots"
        self.workspace.mkdir()
        self.snapshots.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_snapshot(self, snapshot_id: str, files: dict[str, str]):
        snap_dir = self.snapshots / snapshot_id
        snap_dir.mkdir()
        for path, content in files.items():
            f = snap_dir / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
        metadata = {
            "snapshot_id": snapshot_id,
            "task_id": "T1",
            "created_at": time.time() - 100,
            "files_tracked": len(files),
        }
        (snap_dir / "metadata.json").write_text(json.dumps(metadata))

    def _create_workspace_file(self, path: str, content: str):
        f = self.workspace / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")

    def test_no_changes(self):
        self._create_snapshot("snap1", {"src/main.py": "print('hello')"})
        self._create_workspace_file("src/main.py", "print('hello')")

        diff = compute_diff(self.workspace, self.snapshots, "snap1")
        self.assertIsNotNone(diff)
        self.assertFalse(diff.has_changes())

    def test_added_file(self):
        self._create_snapshot("snap1", {"src/main.py": "print('hello')"})
        self._create_workspace_file("src/main.py", "print('hello')")
        self._create_workspace_file("src/utils.py", "def helper(): pass")

        diff = compute_diff(self.workspace, self.snapshots, "snap1")
        self.assertIn("src/utils.py", diff.added)

    def test_removed_file(self):
        self._create_snapshot("snap1", {
            "src/main.py": "print('hello')",
            "src/old.py": "old code"
        })
        self._create_workspace_file("src/main.py", "print('hello')")

        diff = compute_diff(self.workspace, self.snapshots, "snap1")
        self.assertIn("src/old.py", diff.removed)

    def test_modified_file(self):
        self._create_snapshot("snap1", {"src/main.py": "line1\nline2\n"})
        self._create_workspace_file("src/main.py", "line1\nline2\nline3\n")

        diff = compute_diff(self.workspace, self.snapshots, "snap1")
        self.assertEqual(len(diff.modified), 1)
        self.assertEqual(diff.modified[0]["path"], "src/main.py")

    def test_latest_snapshot(self):
        self._create_snapshot("snap1", {"src/main.py": "old"})
        self._create_workspace_file("src/main.py", "new")

        diff = compute_diff(self.workspace, self.snapshots, None)
        self.assertIsNotNone(diff)
        self.assertEqual(diff.snapshot_id, "snap1")

    def test_no_snapshot_found(self):
        diff = compute_diff(self.workspace, self.snapshots, "nonexistent")
        self.assertIsNone(diff)

    def test_no_snapshots_at_all(self):
        diff = compute_diff(self.workspace, self.snapshots, None)
        self.assertIsNone(diff)

    def test_complex_diff(self):
        """Test multiple changes at once."""
        self._create_snapshot("snap1", {
            "src/main.py": "old content",
            "src/delete_me.py": "to be deleted",
            "src/same.py": "unchanged"
        })
        self._create_workspace_file("src/main.py", "new content")
        self._create_workspace_file("src/same.py", "unchanged")
        self._create_workspace_file("src/new_file.py", "brand new")

        diff = compute_diff(self.workspace, self.snapshots, "snap1")
        self.assertIn("src/new_file.py", diff.added)
        self.assertIn("src/delete_me.py", diff.removed)
        self.assertEqual(len(diff.modified), 1)
        self.assertEqual(diff.modified[0]["path"], "src/main.py")


class TestLogsCommand(unittest.TestCase):
    """Tests for logs functionality."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir) / "workspace"
        self.workspace.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _add_audit_entry(self, change_type: str, description: str, phase_id: str = None, **kwargs):
        manager = StateManager(self.workspace)
        entry = AuditEntry(
            timestamp=time.time(),
            change_type=change_type,
            phase_id=phase_id,
            description=description,
            **kwargs
        )
        manager.ensure_state_dir()
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with manager.audit_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_audit_entries_exist(self):
        self._add_audit_entry("phase_started", "Phase P1 started", "P1")
        self._add_audit_entry("file_modified", "Modified main.py", "P1", file_path="src/main.py")
        self._add_audit_entry("phase_completed", "Phase P1 completed", "P1")

        manager = StateManager(self.workspace)
        entries = manager.get_audit_trail()
        self.assertEqual(len(entries), 3)

    def test_filter_by_phase(self):
        self._add_audit_entry("phase_started", "Phase P1 started", "P1")
        self._add_audit_entry("phase_started", "Phase P2 started", "P2")
        self._add_audit_entry("phase_completed", "Phase P1 completed", "P1")

        manager = StateManager(self.workspace)
        entries = manager.get_audit_trail(phase_id="P1")
        self.assertEqual(len(entries), 2)

    def test_filter_by_change_type(self):
        self._add_audit_entry("file_created", "Created a.py")
        self._add_audit_entry("file_modified", "Modified b.py")
        self._add_audit_entry("file_created", "Created c.py")

        manager = StateManager(self.workspace)
        entries = manager.get_audit_trail()
        file_created = [e for e in entries if e.change_type == "file_created"]
        self.assertEqual(len(file_created), 2)

    def test_limit_entries(self):
        for i in range(100):
            self._add_audit_entry("command_executed", f"Command {i}")

        manager = StateManager(self.workspace)
        entries = manager.get_audit_trail(limit=10)
        self.assertEqual(len(entries), 10)


if __name__ == "__main__":
    unittest.main()
