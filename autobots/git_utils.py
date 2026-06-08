"""Git auto-commit functionality for Autobots."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CommitResult:
    """Result of a git commit operation."""

    success: bool
    commit_hash: str | None = None
    message: str = ""
    files_committed: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "files_committed": self.files_committed,
            "error": self.error,
        }


def _run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Git command timed out"
    except FileNotFoundError:
        return 1, "", "Git not found"


def is_git_repo(path: Path) -> bool:
    """Check if a path is inside a git repository."""
    rc, _, _ = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    return rc == 0


def get_git_status(path: Path) -> dict[str, list[str]]:
    """Get the current git status."""
    rc, stdout, _ = _run_git(["status", "--porcelain"], cwd=path)
    if rc != 0:
        return {"modified": [], "added": [], "deleted": [], "untracked": []}

    status = {"modified": [], "added": [], "deleted": [], "untracked": []}
    for line in stdout.splitlines():
        if len(line) < 4:
            continue
        status_code = line[:2]
        filename = line[3:].strip()

        # Check first character for index status, second for worktree status
        index_status = status_code[0]
        worktree_status = status_code[1]

        if index_status == "M" or worktree_status == "M":
            status["modified"].append(filename)
        elif index_status == "A":
            status["added"].append(filename)
        elif index_status == "D" or worktree_status == "D":
            status["deleted"].append(filename)
        elif status_code == "??":
            status["untracked"].append(filename)

    return status


def get_changed_files(path: Path) -> list[str]:
    """Get list of changed files (staged and unstaged)."""
    rc, stdout, _ = _run_git(["diff", "--name-only"], cwd=path)
    if rc != 0:
        return []
    return [f for f in stdout.splitlines() if f]


def get_staged_files(path: Path) -> list[str]:
    """Get list of staged files."""
    rc, stdout, _ = _run_git(["diff", "--cached", "--name-only"], cwd=path)
    if rc != 0:
        return []
    return [f for f in stdout.splitlines() if f]


def has_changes(path: Path) -> bool:
    """Check if there are any uncommitted changes."""
    rc, stdout, _ = _run_git(["status", "--porcelain"], cwd=path)
    if rc != 0:
        return False
    return bool(stdout.strip())


def stage_all(path: Path) -> bool:
    """Stage all changes."""
    rc, _, _ = _run_git(["add", "-A"], cwd=path)
    return rc == 0


def commit(
    path: Path,
    message: str,
    stage_all: bool = True,
) -> CommitResult:
    """Create a git commit.

    Args:
        path: Path to git repository
        message: Commit message
        stage_all: If True, stage all changes before committing

    Returns:
        CommitResult with operation details
    """
    if not is_git_repo(path):
        return CommitResult(
            success=False,
            error="Not a git repository",
        )

    # Stage all changes if requested
    if stage_all:
        if not _run_git(["add", "-A"], cwd=path)[0] == 0:
            # Try individual add as fallback
            changed = get_changed_files(path)
            for f in changed:
                _run_git(["add", f], cwd=path)

    # Get count of staged files
    staged = get_staged_files(path)
    if not staged:
        return CommitResult(
            success=False,
            message=message,
            files_committed=0,
            error="No changes to commit",
        )

    # Create commit
    rc, stdout, stderr = _run_git(["commit", "-m", message], cwd=path)
    if rc != 0:
        return CommitResult(
            success=False,
            message=message,
            files_committed=0,
            error=stderr or "Commit failed",
        )

    # Get the commit hash
    rc, hash_stdout, _ = _run_git(["rev-parse", "HEAD"], cwd=path)
    commit_hash = hash_stdout if rc == 0 else None

    return CommitResult(
        success=True,
        commit_hash=commit_hash,
        message=message,
        files_committed=len(staged),
    )


def auto_commit_after_phase(
    path: Path,
    phase_id: str,
    phase_title: str,
    enabled: bool = True,
) -> CommitResult | None:
    """Automatically commit changes after a successful phase.

    Args:
        path: Path to git repository
        phase_id: Phase identifier (e.g., "P1")
        phase_title: Phase title for commit message
        enabled: Whether auto-commit is enabled

    Returns:
        CommitResult if committed, None if auto-commit disabled
    """
    if not enabled:
        return None

    if not has_changes(path):
        return None

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"autobots: complete phase {phase_id} - {phase_title}\n\nAutomatically committed by Autobots at {timestamp}"

    return commit(path, message, stage_all=True)


def get_recent_commits(path: Path, limit: int = 10) -> list[dict]:
    """Get recent commit history."""
    rc, stdout, _ = _run_git(
        ["log", f"--max-count={limit}", "--pretty=format:%H|%s|%ai"],
        cwd=path,
    )
    if rc != 0:
        return []

    commits = []
    for line in stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "date": parts[2],
            })
    return commits
