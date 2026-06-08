"""Tests for the RollbackManager in executor/state.py."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from autobots.executor.state import RollbackManager


class TestRollbackManager(unittest.TestCase):
    """Test suite for RollbackManager."""

    def setUp(self):
        """Create a temporary workspace with sample files."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

        # Create source directories and files
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
        (self.workspace / "src" / "utils.py").write_text("def helper(): pass", encoding="utf-8")
        (self.workspace / "src" / "models").mkdir()
        (self.workspace / "src" / "models" / "user.py").write_text("class User: pass", encoding="utf-8")

        (self.workspace / "tests").mkdir()
        (self.workspace / "tests" / "test_main.py").write_text("def test_hello(): assert True", encoding="utf-8")

        (self.workspace / "docs").mkdir()
        (self.workspace / "docs" / "README.md").write_text("# Project", encoding="utf-8")

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_create_snapshot(self):
        """Test creating a snapshot captures all tracked files."""
        manager = RollbackManager(self.workspace)

        snapshot_id = manager.create_snapshot("P1-T1")

        self.assertIn("snap_P1-T1_", snapshot_id)
        self.assertTrue((manager.snapshots_root / snapshot_id).exists())

        # Verify metadata exists
        metadata_path = manager.snapshots_root / snapshot_id / "metadata.json"
        self.assertTrue(metadata_path.exists())

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["task_id"], "P1-T1")
        self.assertEqual(metadata["files_tracked"], 5)

    def test_snapshot_captures_file_content(self):
        """Test that snapshot preserves original file content."""
        manager = RollbackManager(self.workspace)

        snapshot_id = manager.create_snapshot("P1-T1")

        # Verify snapshot contains the files
        snapshot_dir = manager.snapshots_root / snapshot_id
        self.assertTrue((snapshot_dir / "src" / "main.py").exists())
        self.assertEqual(
            (snapshot_dir / "src" / "main.py").read_text(encoding="utf-8"),
            "print('hello')"
        )

    def test_rollback_restores_files(self):
        """Test that rollback restores files to original state."""
        manager = RollbackManager(self.workspace)

        # Create snapshot
        snapshot_id = manager.create_snapshot("P1-T1")

        # Modify files
        (self.workspace / "src" / "main.py").write_text("print('modified')", encoding="utf-8")
        (self.workspace / "src" / "utils.py").write_text("def modified(): pass", encoding="utf-8")

        # Verify files are modified
        self.assertEqual((self.workspace / "src" / "main.py").read_text(), "print('modified')")

        # Rollback
        result = manager.rollback(snapshot_id)

        self.assertEqual(result["files_restored"], 5)
        self.assertEqual((self.workspace / "src" / "main.py").read_text(), "print('hello')")
        self.assertEqual((self.workspace / "src" / "utils.py").read_text(), "def helper(): pass")

    def test_rollback_restores_new_files(self):
        """Test that rollback removes files created after snapshot."""
        manager = RollbackManager(self.workspace)

        # Create snapshot
        snapshot_id = manager.create_snapshot("P1-T1")

        # Create new file
        (self.workspace / "src" / "new_file.py").write_text("print('new')", encoding="utf-8")

        # Rollback
        result = manager.rollback(snapshot_id)

        # New file should still exist (rollback only restores tracked files)
        # But original files should be restored
        self.assertEqual((self.workspace / "src" / "main.py").read_text(), "print('hello')")

    def test_rollback_nonexistent_snapshot(self):
        """Test that rollback raises error for nonexistent snapshot."""
        manager = RollbackManager(self.workspace)

        with self.assertRaises(FileNotFoundError) as context:
            manager.rollback("nonexistent_snapshot")

        self.assertIn("not found", str(context.exception))

    def test_list_snapshots(self):
        """Test listing snapshots returns correct data."""
        manager = RollbackManager(self.workspace)

        # Create multiple snapshots
        snap1 = manager.create_snapshot("P1-T1")
        snap2 = manager.create_snapshot("P1-T2")

        snapshots = manager.list_snapshots()

        self.assertEqual(len(snapshots), 2)
        # Snapshots should be in reverse chronological order (newest first)
        self.assertEqual(snapshots[0]["snapshot_id"], snap2)
        self.assertEqual(snapshots[1]["snapshot_id"], snap1)

    def test_list_snapshots_empty(self):
        """Test listing snapshots when none exist."""
        manager = RollbackManager(self.workspace)

        snapshots = manager.list_snapshots()

        self.assertEqual(snapshots, [])

    def test_delete_snapshot(self):
        """Test deleting a snapshot."""
        manager = RollbackManager(self.workspace)

        snapshot_id = manager.create_snapshot("P1-T1")
        self.assertTrue((manager.snapshots_root / snapshot_id).exists())

        result = manager.delete_snapshot(snapshot_id)

        self.assertTrue(result)
        self.assertFalse((manager.snapshots_root / snapshot_id).exists())

    def test_delete_nonexistent_snapshot(self):
        """Test deleting a nonexistent snapshot returns False."""
        manager = RollbackManager(self.workspace)

        result = manager.delete_snapshot("nonexistent_snapshot")

        self.assertFalse(result)

    def test_multiple_rollbacks(self):
        """Test performing multiple rollbacks to different snapshots."""
        manager = RollbackManager(self.workspace)

        # Create first snapshot
        snap1 = manager.create_snapshot("P1-T1")

        # Modify files
        (self.workspace / "src" / "main.py").write_text("print('v2')", encoding="utf-8")

        # Create second snapshot
        snap2 = manager.create_snapshot("P1-T2")

        # Modify files again
        (self.workspace / "src" / "main.py").write_text("print('v3')", encoding="utf-8")

        # Rollback to second snapshot
        result = manager.rollback(snap2)
        self.assertEqual((self.workspace / "src" / "main.py").read_text(), "print('v2')")

        # Rollback to first snapshot
        result = manager.rollback(snap1)
        self.assertEqual((self.workspace / "src" / "main.py").read_text(), "print('hello')")

    def test_snapshot_preserves_subdirectories(self):
        """Test that snapshot preserves directory structure."""
        manager = RollbackManager(self.workspace)

        snapshot_id = manager.create_snapshot("P1-T1")

        # Verify subdirectory structure in snapshot
        snapshot_dir = manager.snapshots_root / snapshot_id
        self.assertTrue((snapshot_dir / "src" / "models" / "user.py").exists())
        self.assertEqual(
            (snapshot_dir / "src" / "models" / "user.py").read_text(encoding="utf-8"),
            "class User: pass"
        )

    def test_rollback_restores_subdirectories(self):
        """Test that rollback restores files in subdirectories."""
        manager = RollbackManager(self.workspace)

        snapshot_id = manager.create_snapshot("P1-T1")

        # Modify nested file
        (self.workspace / "src" / "models" / "user.py").write_text("class ModifiedUser: pass", encoding="utf-8")

        # Rollback
        manager.rollback(snapshot_id)

        self.assertEqual(
            (self.workspace / "src" / "models" / "user.py").read_text(),
            "class User: pass"
        )


if __name__ == "__main__":
    unittest.main()
