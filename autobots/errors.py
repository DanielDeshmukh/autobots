"""Structured error messages with recovery suggestions for Autobots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


@dataclass
class AutobotsError(Exception):
    """Base exception for all Autobots errors with structured guidance."""

    message: str
    reason: str
    suggestions: list[str] = field(default_factory=list)
    exit_code: int = 1

    def __str__(self) -> str:
        parts = [self.message]
        if self.reason:
            parts.append(f"\nWhy: {self.reason}")
        if self.suggestions:
            parts.append("\nTry:")
            for i, s in enumerate(self.suggestions, 1):
                parts.append(f"  {i}. {s}")
        return "\n".join(parts)


class ModelError(AutobotsError):
    """Errors related to model API calls and responses."""

    def __init__(
        self,
        message: str,
        reason: str = "",
        suggestions: list[str] | None = None,
        model_id: str | None = None,
        stage: str | None = None,
    ):
        super().__init__(message, reason, suggestions or [])
        self.model_id = model_id
        self.stage = stage


class ConfigError(AutobotsError):
    """Errors related to configuration loading or validation."""

    def __init__(
        self,
        message: str,
        reason: str = "",
        suggestions: list[str] | None = None,
        config_path: str | None = None,
    ):
        super().__init__(message, reason, suggestions or [])
        self.config_path = config_path


class WorkspaceError(AutobotsError):
    """Errors related to workspace filesystem operations."""

    def __init__(
        self,
        message: str,
        reason: str = "",
        suggestions: list[str] | None = None,
        path: str | None = None,
    ):
        super().__init__(message, reason, suggestions or [])
        self.path = path


class APIError(AutobotsError):
    """Errors related to API connectivity and authentication."""

    def __init__(
        self,
        message: str,
        reason: str = "",
        suggestions: list[str] | None = None,
        status_code: int | None = None,
        base_url: str | None = None,
    ):
        super().__init__(message, reason, suggestions or [])
        self.status_code = status_code
        self.base_url = base_url


class PreflightError(AutobotsError):
    """Errors from preflight check failures."""

    def __init__(
        self,
        message: str,
        reason: str = "",
        suggestions: list[str] | None = None,
        failed_checks: list[str] | None = None,
    ):
        super().__init__(message, reason, suggestions or [])
        self.failed_checks = failed_checks or []


def render_error(error: AutobotsError, console: Console | None = None) -> None:
    """Render a structured error to the console with Rich formatting."""
    if console is None:
        console = Console()

    content = Text()
    content.append(f"  {error.message}\n", style="red bold")

    if error.reason:
        content.append("\n  Why: ", style="dim bold")
        content.append(f"{error.reason}\n", style="white")

    if error.suggestions:
        content.append("\n  Try:\n", style="dim bold")
        for i, suggestion in enumerate(error.suggestions, 1):
            content.append(f"    {i}. {suggestion}\n", style="cyan")

    console.print(
        Panel(
            content,
            title="[red]Autobots Error[/red]",
            border_style="red",
            padding=(1, 2),
        )
    )


def render_warning(message: str, details: str = "", console: Console | None = None) -> None:
    """Render a warning message to the console."""
    if console is None:
        console = Console()

    content = Text()
    content.append(f"  {message}\n", style="yellow bold")

    if details:
        content.append(f"\n  {details}\n", style="dim")

    console.print(
        Panel(
            content,
            title="[yellow]Warning[/yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    )


# =============================================================================
# Factory Functions for Common Error Scenarios
# =============================================================================

def model_json_truncation(model_id: str = "unknown", max_tokens: int = 0) -> ModelError:
    """Create error for truncated JSON response from model."""
    expected_format = """Expected JSON format from specialist stage:

{
  "summary": "Brief description of what was implemented",
  "implementation_notes": "Detailed explanation of the changes",
  "files": [
    {
      "root": "src",
      "path": "module/file.py",
      "content": "full file content here..."
    }
  ]
}"""

    suggestions = [
        "Run the task again - this is often transient",
        f"Increase max_tokens in .autobots.toml (current: {max_tokens})" if max_tokens else "Increase max_tokens in .autobots.toml",
        'Try a different model: model_selection_profile = "quality"',
        "Check the audit log: .autobots/audit.jsonl",
    ]
    return ModelError(
        message="Model returned invalid JSON",
        reason="The model response was truncated because max_tokens was reached before the JSON closed.",
        suggestions=suggestions + [f"Ensure response matches this format:\n\n{expected_format}"],
        model_id=model_id,
        stage="specialist",
    )


def model_invalid_response(model_id: str = "unknown", response_preview: str = "") -> ModelError:
    """Create error for invalid model response format."""
    reason = "The model did not return a valid JSON response."
    if response_preview:
        reason += f" Got: {response_preview[:100]}..."

    expected_format = """Expected JSON format:

{
  "summary": "Brief description of changes",
  "implementation_notes": "Detailed explanation",
  "files": [
    {
      "root": "src|app|lib|tests|docs|scripts",
      "path": "relative/path/to/file.py",
      "content": "full file content"
    }
  ]
}"""

    return ModelError(
        message="Model returned invalid response format",
        reason=reason,
        suggestions=[
            "Run the task again - model responses can vary",
            'Try a different model: model_selection_profile = "quality"',
            "Check if the task description is clear enough",
            f"Verify model {model_id} is available",
            f"Ensure response matches this format:\n\n{expected_format}",
        ],
        model_id=model_id,
    )


def model_timeout(model_id: str = "unknown", timeout_seconds: int = 120) -> ModelError:
    """Create error for model call timeout."""
    return ModelError(
        message=f"Model call timed out after {timeout_seconds}s",
        reason="The model took too long to respond. This can happen with complex tasks or high load.",
        suggestions=[
            "Try again - timeouts can be transient",
            "Break the task into smaller pieces",
            'Try a faster model: model_selection_profile = "speed"',
            "Increase timeout if consistently needed",
        ],
        model_id=model_id,
    )


def model_auth_failure(base_url: str = "https://integrate.api.nvidia.com/v1") -> APIError:
    """Create error for API authentication failure."""
    return APIError(
        message="API authentication failed",
        reason="The NVIDIA API key is invalid or expired.",
        suggestions=[
            "Verify your API key: echo $NVIDIA_API_KEY",
            "Get a new key from https://build.nvidia.com/",
            "Check .env file in the engine repo root",
            "Run: autobots doctor to verify configuration",
        ],
        status_code=401,
        base_url=base_url,
    )


def model_not_found(model_id: str = "unknown") -> ModelError:
    """Create error for model not found."""
    expected_format = """Model IDs follow the format: provider/model-name

Examples from NVIDIA NIM:
  nvidia/llama-3.1-nemotron-70b-instruct
  nvidia/llama-3.1-8b-instruct
  qwen/qwen3-coder-480b-a35b-instruct
  meta/llama-3.1-70b-instruct

View available models:
  autobots catalog list              # List all bundled models
  autobots catalog list --cluster X  # List models for a cluster
  autobots validate-models           # Test model availability"""

    return ModelError(
        message=f"Model not found: {model_id}",
        reason="The specified model ID does not exist or is not available.",
        suggestions=[
            f"Check the model ID format: {model_id} -> expected provider/model-name",
            "Run: autobots catalog list to see available models",
            "Try a different model with model_selection_profile",
            f"Model ID reference:\n\n{expected_format}",
        ],
        model_id=model_id,
    )


def config_invalid(profile: str = "", mode: str = "", issues: list[str] | None = None) -> ConfigError:
    """Create error for invalid configuration."""
    reason_parts = []
    if profile:
        reason_parts.append(f"model_selection_profile={profile}")
    if mode:
        reason_parts.append(f"default_mode={mode}")

    expected_format = """Expected .autobots.toml format:

[autobots]
# Model selection: balanced | speed | quality
model_selection_profile = "balanced"

# Execution mode: supervised | milestone | autonomous
default_mode = "supervised"

# Milestone threshold (phases between approvals)
milestone_threshold = 3

# Max verification attempts per phase
max_verification_attempts = 3

# Safety branch name (disable with "none")
safety_branch = "autobots-safety"

# Parallel planning (experimental)
parallel_planning = false

# Disable live catalog discovery
disable_live_catalog = false

# Custom model registry path
# model_registry_path = "path/to/registry.json"

# Extra clusters (optional)
# [autobots.extra_clusters]
# DataEngineer = ["nvidia/llama-3.1-nemotron-70b-instruct"]"""

    suggestions = [
        f"Ensure .autobots.toml follows this format:\n\n{expected_format}",
        "Valid profiles: balanced, speed, quality",
        "Valid modes: supervised, milestone, autonomous",
        "Run: autobots doctor to validate configuration",
    ]

    if issues:
        suggestions = [f"Fix: {issue}" for issue in issues] + suggestions

    return ConfigError(
        message="Invalid configuration",
        reason=f"Configuration values are invalid: {', '.join(reason_parts)}" if reason_parts else "One or more configuration values are invalid",
        suggestions=suggestions,
    )


def workspace_not_found(path: str) -> WorkspaceError:
    """Create error for missing workspace directory."""
    return WorkspaceError(
        message=f"Target project not found: {path}",
        reason="The specified directory does not exist.",
        suggestions=[
            "Check the path for typos",
            "Navigate to the target project directory",
            "Use: autobots run <path> for a specific project",
            "Verify the directory exists: ls -la",
        ],
        path=path,
    )


def workspace_not_writable(path: str) -> WorkspaceError:
    """Create error for unwritable workspace."""
    return WorkspaceError(
        message=f"Cannot write to workspace: {path}",
        reason="Insufficient permissions or directory is read-only.",
        suggestions=[
            "Check file permissions: ls -la",
            "Run with appropriate permissions",
            "Choose a different workspace directory",
            "Check if the directory is mounted read-only",
        ],
        path=path,
    )


def git_clean_tree_required() -> AutobotsError:
    """Create error when git working tree is not clean."""
    return AutobotsError(
        message="Git working tree has uncommitted changes",
        reason="Autobots requires a clean working tree to safely modify files.",
        suggestions=[
            "Commit changes: git add . && git commit -m 'WIP'",
            "Stash changes: git stash push -m 'autobots safety'",
            "Discard changes: git checkout -- . (caution: loses work)",
            "Use a separate branch: git checkout -b autobots-work",
        ],
    )


def safety_branch_required(branch: str = "autobots-safety") -> AutobotsError:
    """Create error when not on required safety branch."""
    return AutobotsError(
        message=f"Not on required safety branch: {branch}",
        reason="Autobots requires being on a safety branch to prevent accidental changes to main.",
        suggestions=[
            f"Switch to the safety branch: git checkout {branch}",
            f"Create the branch: git checkout -b {branch}",
            "Or disable safety: AUTOBOTS_SAFETY_BRANCH=none",
            "Check current branch: git branch --show-current",
        ],
    )


def preflight_failed(failed_checks: list[str]) -> PreflightError:
    """Create error for preflight check failures."""
    return PreflightError(
        message=f"Preflight checks failed: {len(failed_checks)} check(s) failed",
        reason="One or more preflight checks failed. Fix the issues before continuing.",
        suggestions=[
            "Run: autobots doctor to see all check results",
            "Fix the issues listed above",
            "Check API key: echo $NVIDIA_API_KEY",
            "Verify workspace is writable",
        ],
        failed_checks=failed_checks,
    )


def task_not_found(task_id: str) -> AutobotsError:
    """Create error for missing task."""
    expected_format = """Task IDs follow the format: P{phase}-T{task}

Examples:
  P1-T1    Phase 1, Task 1
  P2-T3    Phase 2, Task 3
  P10-T1   Phase 10, Task 1

View available tasks:
  autobots status          # Shows all phases and tasks
  autobots run             # Runs next pending task automatically"""

    return AutobotsError(
        message=f"Task not found: {task_id}",
        reason="The specified task ID does not exist in the task registry.",
        suggestions=[
            f"Check the task ID format: {task_id} -> expected P{{phase}}-T{{task}} (e.g., P1-T1)",
            "Run: autobots status to see all available tasks",
            "Run: autobots plan to create tasks",
            f"Task ID reference:\n\n{expected_format}",
        ],
    )


def phase_not_found(phase_id: str = "") -> AutobotsError:
    """Create error for missing phase."""
    if phase_id:
        message = f"Phase not found: {phase_id}"
    else:
        message = "No phases found"

    expected_format = """Your roadmap.md must use this structure:

# Roadmap

## Project Phases

### Phase 1: [Phase Name]

**Goal**: [What you want to achieve]
**Duration**: [Estimated timeline]

- [ ] [Milestone 1]
- [ ] [Milestone 2]
- [ ] [Milestone 3]

**Completion**: [Date or status]

### Phase 2: [Phase Name]
...

## Timeline

| Phase | Start | End    | Status        |
| ----- | ----- | ------ | ------------- |
| P1    | Jan   | Feb    | Not Started   |
| P2    | Feb   | Mar    | Not Started   |

## Blockers

- [Any blockers preventing progress]

## Next Steps

- [Immediate action items to unblock work]"""

    return AutobotsError(
        message=message,
        reason="The roadmap does not contain any phases or the specified phase was not found.",
        suggestions=[
            "Run: autobots plan to create a roadmap",
            f"Check context/roadmap.md exists and uses this format:\n\n{expected_format}",
            "Each phase must start with: ### Phase N: [Name]",
            "Each milestone must be a checkbox: - [ ] or - [x] for complete",
        ],
    )


def lock_acquisition_failed(resource: str) -> AutobotsError:
    """Create error when file lock cannot be acquired."""
    return AutobotsError(
        message=f"Cannot acquire lock on: {resource}",
        reason="Another Autobots process may be running or a stale lock exists.",
        suggestions=[
            "Wait for the other process to finish",
            "Run: autobots undo to release stale locks",
            "Delete the lock file manually if no other process is running",
            "Check .autobots-locks/ directory",
        ],
    )


def rollback_failed(snapshot_id: str, reason: str = "") -> AutobotsError:
    """Create error when rollback fails."""
    return AutobotsError(
        message=f"Rollback failed for snapshot: {snapshot_id}",
        reason=reason or "The snapshot may be corrupted or missing.",
        suggestions=[
            "Run: autobots snapshots to list available snapshots",
            "Verify the snapshot ID is correct",
            "Check .autobots/snapshots/ directory exists",
            "Try creating a new snapshot before rollback",
        ],
    )


def plan_not_found() -> AutobotsError:
    """Create error when no plan exists."""
    expected_format = """Your roadmap.md must use this structure:

# Roadmap

## Project Phases

### Phase 1: [Phase Name]

**Goal**: [What you want to achieve]
**Duration**: [Estimated timeline]

- [ ] [Milestone 1]
- [ ] [Milestone 2]
- [ ] [Milestone 3]

**Completion**: [Date or status]

### Phase 2: [Phase Name]
...

## Timeline

| Phase | Start | End    | Status        |
| ----- | ----- | ------ | ------------- |
| P1    | Jan   | Feb    | Not Started   |
| P2    | Feb   | Mar    | Not Started   |

## Blockers

- [Any blockers preventing progress]

## Next Steps

- [Immediate action items to unblock work]"""

    return AutobotsError(
        message="No plan found",
        reason="The target project has not been planned yet.",
        suggestions=[
            "Run: autobots plan to create a plan",
            f"Create context/roadmap.md with this format:\n\n{expected_format}",
            "Each phase must start with: ### Phase N: [Name]",
            "Each milestone must be a checkbox: - [ ] or - [x] for complete",
        ],
    )


def no_pending_phases() -> AutobotsError:
    """Create error when no pending phases remain."""
    return AutobotsError(
        message="No pending phases to execute",
        reason="All phases in the roadmap have been completed.",
        suggestions=[
            "Run: autobots status to see completion status",
            "Check context/roadmap.md for remaining work",
            "Add new phases if more work is needed",
        ],
    )
