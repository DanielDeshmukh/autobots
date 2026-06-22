from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffHunk:
    file: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)


@dataclass
class DiffSummary:
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    hunks: list[DiffHunk] = field(default_factory=list)
    raw_diff: str = ""


def _run_git(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_diff(target: str = "HEAD", cwd: str | None = None) -> DiffSummary:
    code, stdout, _ = _run_git(["diff", target], cwd=cwd)
    if code != 0:
        return DiffSummary()

    return _parse_diff(stdout)


def get_staged_diff(cwd: str | None = None) -> DiffSummary:
    code, stdout, _ = _run_git(["diff", "--cached"], cwd=cwd)
    if code != 0:
        return DiffSummary()
    return _parse_diff(stdout)


def get_pr_diff(pr_number: int, cwd: str | None = None) -> DiffSummary:
    code, stdout, _ = _run_git(
        ["diff", f"origin/main...HEAD"], cwd=cwd
    )
    if code != 0:
        return DiffSummary()
    return _parse_diff(stdout)


def _parse_diff(raw: str) -> DiffSummary:
    summary = DiffSummary(raw_diff=raw)
    current_hunk: DiffHunk | None = None

    for line in raw.splitlines():
        if line.startswith("diff --git"):
            summary.files_changed += 1
        elif line.startswith("+") and not line.startswith("+++"):
            summary.insertions += 1
        elif line.startswith("-") and not line.startswith("---"):
            summary.deletions += 1
        elif line.startswith("@@"):
            if current_hunk:
                summary.hunks.append(current_hunk)
            parts = line.split()
            if len(parts) >= 2:
                old_range = parts[1].strip("+-").split(",")
                new_range = parts[2].strip("+-").split(",") if len(parts) > 2 else ["0", "0"]
                current_hunk = DiffHunk(
                    file="",
                    old_start=int(old_range[0]) if old_range[0] else 0,
                    old_count=int(old_range[1]) if len(old_range) > 1 else 1,
                    new_start=int(new_range[0]) if new_range[0] else 0,
                    new_count=int(new_range[1]) if len(new_range) > 1 else 1,
                )
            if current_hunk:
                current_hunk.lines.append(line)
        elif current_hunk:
            current_hunk.lines.append(line)

    if current_hunk:
        summary.hunks.append(current_hunk)

    return summary


def review_diff(diff: DiffSummary | None = None, cwd: str | None = None) -> str:
    if diff is None:
        diff = get_diff(cwd=cwd)

    if diff.files_changed == 0:
        return "No changes to review."

    lines = [
        f"Reviewing {diff.files_changed} file(s): +{diff.insertions} -{diff.deletions}",
        "",
    ]

    issues = []

    if diff.insertions > 500:
        issues.append("Large change: >500 lines inserted. Consider breaking into smaller PRs.")

    if diff.files_changed > 20:
        issues.append(f"Many files changed ({diff.files_changed}). Consider splitting.")

    if not issues:
        lines.append("No issues found.")
    else:
        for issue in issues:
            lines.append(f"- {issue}")

    return "\n".join(lines)


def review_pr(pr_number: int, cwd: str | None = None) -> str:
    diff = get_pr_diff(pr_number, cwd=cwd)
    return review_diff(diff, cwd=cwd)
