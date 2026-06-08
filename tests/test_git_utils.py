"""Tests for git utilities module."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from autobots.git_utils import (
    CommitResult,
    auto_commit_after_phase,
    commit,
    get_changed_files,
    get_recent_commits,
    get_staged_files,
    get_git_status,
    has_changes,
    is_git_repo,
)


class TestGitUtils(unittest.TestCase):
    """Tests for git utility functions."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.git_repo = Path(self.tmpdir) / "test-repo"
        self.git_repo.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.git_repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=self.git_repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.git_repo,
            capture_output=True,
        )

    def tearDown(self):
        import time
        time.sleep(0.1)  # Brief pause to release file handles
        try:
            # On Windows, git objects may be locked briefly
            for retry in range(3):
                try:
                    shutil.rmtree(self.tmpdir)
                    break
                except PermissionError:
                    time.sleep(0.2)
        except Exception:
            pass  # Ignore cleanup errors on Windows

    def test_is_git_repo_true(self):
        self.assertTrue(is_git_repo(self.git_repo))

    def test_is_git_repo_false(self):
        non_repo = Path(self.tmpdir) / "not-a-repo"
        non_repo.mkdir()
        self.assertFalse(is_git_repo(non_repo))

    def test_has_changes_empty_repo(self):
        self.assertFalse(has_changes(self.git_repo))

    def test_has_changes_with_file(self):
        (self.git_repo / "test.txt").write_text("hello")
        self.assertTrue(has_changes(self.git_repo))

    def test_get_git_status_empty(self):
        status = get_git_status(self.git_repo)
        self.assertEqual(status["modified"], [])

    def test_get_git_status_with_file(self):
        (self.git_repo / "test.txt").write_text("hello")
        status = get_git_status(self.git_repo)
        # Check that there's at least one untracked file
        # (the exact filename parsing depends on git version)
        self.assertTrue(len(status["untracked"]) > 0 or len(status["modified"]) > 0)

    def test_get_changed_files_empty(self):
        files = get_changed_files(self.git_repo)
        self.assertEqual(files, [])

    def test_commit_success(self):
        (self.git_repo / "test.txt").write_text("hello")
        result = commit(self.git_repo, "Initial commit")
        self.assertTrue(result.success)
        self.assertEqual(result.files_committed, 1)
        self.assertIsNotNone(result.commit_hash)

    def test_commit_no_changes(self):
        result = commit(self.git_repo, "Empty commit")
        self.assertFalse(result.success)
        self.assertIn("No changes", result.error)

    def test_commit_not_git_repo(self):
        non_repo = Path(self.tmpdir) / "not-a-repo"
        non_repo.mkdir()
        result = commit(non_repo, "Test")
        self.assertFalse(result.success)
        self.assertIn("Not a git repository", result.error)

    def test_auto_commit_after_phase(self):
        (self.git_repo / "src").mkdir()
        (self.git_repo / "src" / "main.py").write_text("print('hello')")
        result = auto_commit_after_phase(
            self.git_repo,
            phase_id="P1",
            phase_title="Setup project",
        )
        self.assertTrue(result.success)
        self.assertIn("P1", result.message)

    def test_auto_commit_disabled(self):
        (self.git_repo / "test.txt").write_text("hello")
        result = auto_commit_after_phase(
            self.git_repo,
            phase_id="P1",
            phase_title="Test",
            enabled=False,
        )
        self.assertIsNone(result)

    def test_auto_commit_no_changes(self):
        result = auto_commit_after_phase(
            self.git_repo,
            phase_id="P1",
            phase_title="Test",
        )
        self.assertIsNone(result)

    def test_get_recent_commits(self):
        (self.git_repo / "test.txt").write_text("hello")
        commit(self.git_repo, "First commit")
        commits = get_recent_commits(self.git_repo, limit=5)
        self.assertGreater(len(commits), 0)
        self.assertIn("First commit", commits[0]["message"])

    def test_commit_result_to_dict(self):
        result = CommitResult(
            success=True,
            commit_hash="abc123",
            message="Test commit",
            files_committed=3,
        )
        d = result.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["commit_hash"], "abc123")
        self.assertEqual(d["files_committed"], 3)


class TestCommitResult(unittest.TestCase):
    """Tests for CommitResult dataclass."""

    def test_success_result(self):
        result = CommitResult(
            success=True,
            commit_hash="abc123def",
            message="Test",
            files_committed=5,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.files_committed, 5)
        self.assertIsNone(result.error)

    def test_failure_result(self):
        result = CommitResult(
            success=False,
            error="Not a git repo",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Not a git repo")


if __name__ == "__main__":
    unittest.main()
