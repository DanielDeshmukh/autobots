"""Preflight checks for Autobots CLI commands."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class CheckStatus(Enum):
    """Status of a preflight check."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class PreflightCheck:
    """A single preflight check result."""
    name: str
    status: CheckStatus
    message: str
    details: str | None = None


@dataclass
class PreflightResult:
    """Result of running all preflight checks."""
    checks: list[PreflightCheck]
    target_root: Path | None = None

    @property
    def all_passed(self) -> bool:
        return all(c.status in (CheckStatus.PASS, CheckStatus.SKIP) for c in self.checks)

    @property
    def failed_checks(self) -> list[PreflightCheck]:
        return [c for c in self.checks if c.status == CheckStatus.FAIL]


def check_api_key_format(api_key: str | None) -> PreflightCheck:
    """Check if API key has valid format (nvapi- prefix for NVIDIA NIM)."""
    if not api_key:
        return PreflightCheck(
            name="API key",
            status=CheckStatus.FAIL,
            message="not set",
            details="Set NVIDIA_API_KEY environment variable or api_key in .autobots.toml",
        )

    if len(api_key) < 10:
        return PreflightCheck(
            name="API key",
            status=CheckStatus.FAIL,
            message="too short",
            details="API key should be at least 10 characters",
        )

    # NVIDIA NIM keys typically start with nvapi-
    if not api_key.startswith("nvapi-"):
        return PreflightCheck(
            name="API key",
            status=CheckStatus.WARN,
            message="unusual format",
            details="Expected nvapi- prefix for NVIDIA NIM API keys",
        )

    return PreflightCheck(
        name="API key",
        status=CheckStatus.PASS,
        message="valid format",
    )


def check_api_connectivity(api_key: str | None, base_url: str = "https://integrate.api.nvidia.com/v1") -> PreflightCheck:
    """Check API connectivity and measure latency."""
    if not api_key:
        return PreflightCheck(
            name="API connection",
            status=CheckStatus.SKIP,
            message="skipped (no API key)",
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)

        start_time = time.time()
        client.models.list()
        latency_ms = (time.time() - start_time) * 1000

        return PreflightCheck(
            name="API connection",
            status=CheckStatus.PASS,
            message=f"OK ({latency_ms:.0f}ms)",
        )
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return PreflightCheck(
                name="API connection",
                status=CheckStatus.FAIL,
                message="authentication failed",
                details="API key is invalid or expired",
            )
        if "403" in error_msg or "forbidden" in error_msg.lower():
            return PreflightCheck(
                name="API connection",
                status=CheckStatus.FAIL,
                message="access denied",
                details="API key does not have permission for this resource",
            )
        if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
            return PreflightCheck(
                name="API connection",
                status=CheckStatus.FAIL,
                message="connection failed",
                details=f"Cannot reach {base_url}",
            )
        return PreflightCheck(
            name="API connection",
            status=CheckStatus.FAIL,
            message="failed",
            details=error_msg[:200],
        )


def check_primary_model(model_id: str | None, api_key: str | None, base_url: str = "https://integrate.api.nvidia.com/v1") -> PreflightCheck:
    """Check if primary model is responsive."""
    if not api_key:
        return PreflightCheck(
            name="Primary model",
            status=CheckStatus.SKIP,
            message="skipped (no API key)",
        )

    if not model_id:
        return PreflightCheck(
            name="Primary model",
            status=CheckStatus.WARN,
            message="not configured",
            details="Using default model selection",
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Reply with only: OK"}],
            max_tokens=10,
            temperature=0.0,
        )

        if response.choices and response.choices[0].message.content:
            return PreflightCheck(
                name="Primary model",
                status=CheckStatus.PASS,
                message=f"{model_id} - responsive",
            )
        else:
            return PreflightCheck(
                name="Primary model",
                status=CheckStatus.WARN,
                message=f"{model_id} - empty response",
            )

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return PreflightCheck(
                name="Primary model",
                status=CheckStatus.FAIL,
                message=f"{model_id} - not found",
                details="Model ID may be incorrect or model not available",
            )
        return PreflightCheck(
            name="Primary model",
            status=CheckStatus.FAIL,
            message=f"{model_id} - error",
            details=error_msg[:200],
        )


def check_workspace_writable(workspace: Path | None) -> PreflightCheck:
    """Check if workspace directory is writable."""
    if not workspace:
        return PreflightCheck(
            name="Workspace",
            status=CheckStatus.WARN,
            message="not specified",
        )

    if not workspace.exists():
        return PreflightCheck(
            name="Workspace",
            status=CheckStatus.FAIL,
            message=f"{workspace} - not found",
            details="Target directory does not exist",
        )

    if not workspace.is_dir():
        return PreflightCheck(
            name="Workspace",
            status=CheckStatus.FAIL,
            message=f"{workspace} - not a directory",
        )

    # Check write permission
    test_file = workspace / ".autobots_write_test"
    try:
        test_file.write_text("test")
        test_file.unlink()
        return PreflightCheck(
            name="Workspace",
            status=CheckStatus.PASS,
            message=f"{workspace} - writable",
        )
    except PermissionError:
        return PreflightCheck(
            name="Workspace",
            status=CheckStatus.FAIL,
            message=f"{workspace} - not writable",
            details="Insufficient permissions to write to directory",
        )


def check_config_valid(config: Any, config_file: Path | None = None) -> PreflightCheck:
    """Check if configuration is valid."""
    issues = []

    # Validate model_selection_profile
    valid_profiles = ("balanced", "speed", "quality")
    if config.model_selection_profile not in valid_profiles:
        issues.append(f"Invalid model_selection_profile: {config.model_selection_profile} (use: {', '.join(valid_profiles)})")

    # Validate default_mode
    valid_modes = ("supervised", "milestone", "autonomous")
    if config.default_mode not in valid_modes:
        issues.append(f"Invalid default_mode: {config.default_mode} (use: {', '.join(valid_modes)})")

    # Validate milestone_threshold
    if config.milestone_threshold < 1 or config.milestone_threshold > 100:
        issues.append(f"Invalid milestone_threshold: {config.milestone_threshold} (must be 1-100)")

    # Validate max_verification_attempts
    if config.max_verification_attempts < 1 or config.max_verification_attempts > 10:
        issues.append(f"Invalid max_verification_attempts: {config.max_verification_attempts} (must be 1-10)")

    if issues:
        return PreflightCheck(
            name="Config",
            status=CheckStatus.FAIL,
            message="invalid",
            details="\n".join(issues),
        )

    config_name = config_file.name if config_file else ".autobots.toml"
    return PreflightCheck(
        name="Config",
        status=CheckStatus.PASS,
        message=f"{config_name} - valid",
    )


def check_git_status(workspace: Path | None) -> PreflightCheck:
    """Check git working tree status."""
    if not workspace:
        return PreflightCheck(
            name="Git",
            status=CheckStatus.SKIP,
            message="skipped (no workspace)",
        )

    if not (workspace / ".git").exists():
        return PreflightCheck(
            name="Git",
            status=CheckStatus.SKIP,
            message="not a git repo",
        )

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return PreflightCheck(
                name="Git",
                status=CheckStatus.WARN,
                message="git error",
                details=result.stderr[:200],
            )

        changes = result.stdout.strip()
        if not changes:
            return PreflightCheck(
                name="Git",
                status=CheckStatus.PASS,
                message="clean working tree",
            )
        else:
            change_count = len(changes.splitlines())
            return PreflightCheck(
                name="Git",
                status=CheckStatus.WARN,
                message=f"{change_count} uncommitted change(s)",
                details="Consider committing or stashing changes before running Autobots",
            )

    except subprocess.TimeoutExpired:
        return PreflightCheck(
            name="Git",
            status=CheckStatus.WARN,
            message="git timed out",
        )
    except FileNotFoundError:
        return PreflightCheck(
            name="Git",
            status=CheckStatus.SKIP,
            message="git not installed",
        )


def run_preflight(
    api_key: str | None = None,
    base_url: str = "https://integrate.api.nvidia.com/v1",
    model_id: str | None = None,
    workspace: Path | None = None,
    config: Any = None,
    config_file: Path | None = None,
    skip_model_check: bool = False,
) -> PreflightResult:
    """Run all preflight checks and return results."""
    checks = [
        check_api_key_format(api_key),
        check_api_connectivity(api_key, base_url),
    ]

    if not skip_model_check:
        checks.append(check_primary_model(model_id, api_key, base_url))

    checks.extend([
        check_workspace_writable(workspace),
        check_config_valid(config, config_file),
        check_git_status(workspace),
    ])

    return PreflightResult(checks=checks, target_root=workspace)


def render_preflight_result(result: PreflightResult, console: Console | None = None, verbose: bool = True) -> None:
    """Render preflight result to console."""
    if console is None:
        console = Console()

    status_icons = {
        CheckStatus.PASS: "[green]OK[/green]",
        CheckStatus.FAIL: "[red]FAIL[/red]",
        CheckStatus.WARN: "[yellow]WARN[/yellow]",
        CheckStatus.SKIP: "[dim]SKIP[/dim]",
    }

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Status", width=6)
    table.add_column("Check", style="cyan")
    table.add_column("Result")

    for check in result.checks:
        icon = status_icons[check.status]
        message = check.message
        if check.details and verbose:
            message += f"\n  [dim]{check.details}[/dim]"
        table.add_row(icon, check.name, message)

    console.print(Panel(
        table,
        title="Autobots Preflight Check",
        border_style="green" if result.all_passed else "red",
    ))

    if result.all_passed:
        console.print("[green]All checks passed. Ready to swarm.[/green]")
    else:
        console.print(f"[red]{len(result.failed_checks)} check(s) failed. Fix issues above before continuing.[/red]")


def auto_run_preflight(
    api_key: str | None = None,
    base_url: str = "https://integrate.api.nvidia.com/v1",
    model_id: str | None = None,
    workspace: Path | None = None,
    config: Any = None,
    config_file: Path | None = None,
    console: Console | None = None,
    force_verbose: bool = False,
) -> bool:
    """Auto-run preflight for run/engage commands. Returns True if checks pass.

    If all checks pass, returns True silently.
    If checks fail, prints the result and returns False.
    """
    if console is None:
        console = Console()

    result = run_preflight(
        api_key=api_key,
        base_url=base_url,
        model_id=model_id,
        workspace=workspace,
        config=config,
        config_file=config_file,
    )

    if result.all_passed and not force_verbose:
        return True

    render_preflight_result(result, console, verbose=True)
    return result.all_passed
