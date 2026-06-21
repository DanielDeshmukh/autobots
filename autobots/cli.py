from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .bootstrap import CORE_CONTEXT_FILES, detect_repo_profile
from .config import load_config
from .planning import write_plan, parse_roadmap
from .router import AutobotRouter, ExecutionResult, PhaseRecord
from .executor import plan_runner
from .executor.task_registry import get_all_tasks, get_phase_status, get_all_phases_status
from .workspace import TargetProjectWorkspace
from .executor import AutonomyEngine, ExecutionMode
from .executor.modes import ExecutionState
from .selectors import (
    resolve_target_project,
    resolve_target_project_from_args as _resolve_target_project_from_args,
    require_safety_branch,
    require_operational_context,
    missing_core_context_files,
    detect_git_branch,
)
from .logging import setup_logging
from .context_gen import check_six_file_architecture, format_missing_context_files
from .preflight import (
    run_preflight,
    render_preflight_result,
    auto_run_preflight,
)

# Global verbose flag — when True, router logs full prompts/responses
VERBOSE = False
from .errors import (
    AutobotsError,
    ModelError,
    ConfigError,
    WorkspaceError,
    APIError,
    render_error,
    render_warning,
    workspace_not_found,
    task_not_found,
    phase_not_found,
    preflight_failed,
)
from .onboarding import (
    run_onboarding_wizard,
    check_and_prompt_api_key,
)
from .ui import (
    _select,
    _text,
    _password,
    render_plan,
    render_registry_summary,
    render_stage_event,
    render_phase_panel,
    render_session_status,
    render_execution_result,
    render_model_validation_report,
    render_engage_screen,
    engage_prompt,
    ConsoleInstance,
)


ENGINE_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ENV_PATH = ENGINE_ROOT / ".env"
SAFETY_BRANCH = "autobots-safety"
ROLLOUT_MESSAGE = "Autobots, Roll out!"
init_path = ENGINE_ROOT / "autobots" / "__init__.py"
pyproject_path = ENGINE_ROOT / "pyproject.toml"
dist_dir = ENGINE_ROOT / "dist"


class InterruptHandler:
    """Handles Ctrl+C gracefully by releasing locks and saving checkpoints."""

    def __init__(self, console: Console):
        self.console = console
        self.interrupted = False
        self.workspace: TargetProjectWorkspace | None = None
        self.state_manager = None
        self.checkpoint_data: dict | None = None
        self._original_handler = None

    def setup(self, workspace: TargetProjectWorkspace | None = None) -> None:
        """Set up the interrupt handler with workspace context."""
        self.workspace = workspace
        if workspace:
            from .executor.state import StateManager
            self.state_manager = StateManager(workspace.target_root)

        def handler(sig, frame):
            self.interrupted = True
            self._cleanup_on_interrupt()

        self._original_handler = signal.signal(signal.SIGINT, handler)

    def _cleanup_on_interrupt(self) -> None:
        """Release locks and save checkpoint on interrupt."""
        self.console.print("\n")
        self.console.print(
            Panel.fit(
                "Interrupt received — cleaning up...",
                title="Shutdown",
                border_style="yellow",
            )
        )

        # Release any stale locks
        if self.workspace:
            try:
                from .executor.state import StaleLockRecovery
                result = StaleLockRecovery.auto_recover_stale_locks(self.workspace)
                if result["found"] > 0:
                    self.console.print(
                        f"[green]Released {len(result['recovered'])} lock(s)[/green]"
                    )
            except Exception:
                pass

        # Save checkpoint if we have checkpoint data
        if self.checkpoint_data:
            try:
                from .executor.modes import ExecutionModeManager
                mode_manager = ExecutionModeManager()
                mode_manager.save_checkpoint(
                    self.workspace.target_root if self.workspace else Path("."),
                    self.checkpoint_data.get("session_id", ""),
                    ExecutionMode(self.checkpoint_data.get("mode", "supervised")),
                    self.checkpoint_data.get("phase_index", 0),
                    self.checkpoint_data.get("phase_title", ""),
                    self.checkpoint_data.get("phases_completed", []),
                    ExecutionState.PAUSED,
                )
                self.console.print("[green]Checkpoint saved for resume[/green]")
            except Exception:
                pass

        self.console.print(
            Panel.fit(
                f"{ROLLOUT_MESSAGE}\n\nResume with: autobots resume",
                title="Shutdown Complete",
                border_style="green",
            )
        )

    def restore(self) -> None:
        """Restore original signal handler."""
        if self._original_handler:
            signal.signal(signal.SIGINT, self._original_handler)

    def set_checkpoint_data(self, **kwargs) -> None:
        """Store checkpoint data for potential save on interrupt."""
        self.checkpoint_data = kwargs


def _graceful_interrupt(console: Console) -> int:
    console.print(
        Panel.fit(
            ROLLOUT_MESSAGE,
            title="Shutdown",
            border_style="yellow",
        )
    )
    return 130


def _handle_error(console: Console, error: Exception, command: str) -> int:
    """Handle errors gracefully with helpful messages."""
    # Use structured error rendering for AutobotsError instances
    if isinstance(error, AutobotsError):
        render_error(error, console)
        return error.exit_code

    error_msg = str(error)
    error_type = type(error).__name__

    if isinstance(error, FileNotFoundError):
        console.print(
            Panel.fit(
                f"File or directory not found: {error_msg}",
                title=f"{command} Error",
                border_style="red",
            )
        )
        return 1

    if isinstance(error, PermissionError):
        console.print(
            Panel.fit(
                f"Permission denied: {error_msg}",
                title=f"{command} Error",
                border_style="red",
            )
        )
        return 1

    if isinstance(error, KeyboardInterrupt):
        return _graceful_interrupt(console)

    console.print(
        Panel.fit(
            f"An unexpected error occurred during {command}.\n\n"
            f"Error: {error_type}\n"
            f"Message: {error_msg}\n\n"
            f"Hint: Check that the target project is valid and all required dependencies are installed.",
            title=f"{command} Failed",
            border_style="red",
        )
    )
    return 1


def _ensure_api_key(console: Console, target_root: Path | None = None) -> None:
    """Ensure API key is available, checking multiple sources.

    Checks in order:
    1. NVIDIA_API_KEY environment variable
    2. .env file in engine root
    3. .autobots.toml in target project (if provided)
    4. Prompt user for input
    """
    # Check environment variable
    env_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if env_key:
        return

    # Check .env file
    env_values = dotenv_values(ENGINE_ENV_PATH)
    existing_key = (env_values.get("NVIDIA_API_KEY") or "").strip()
    if existing_key:
        return

    # Check target project config if provided
    if target_root:
        from .config import CONFIG_FILE_NAMES
        for config_name in CONFIG_FILE_NAMES:
            config_path = target_root / config_name
            if config_path.exists():
                try:
                    import tomllib
                    with open(config_path, "rb") as f:
                        data = tomllib.load(f)
                    config_key = data.get("autobots", {}).get("api_key", "")
                    if config_key:
                        # Set it in environment for this session
                        os.environ["NVIDIA_API_KEY"] = config_key
                        return
                except Exception:
                    pass

    # Prompt user
    console.print(
        "\n[yellow]NVIDIA API key is required for Autobots to function.[/yellow]\n"
        "[dim]Get your key at: https://build.nvidia.com/[/dim]\n"
    )

    api_key = _password("Enter your NVIDIA_API_KEY").strip()
    if not api_key:
        raise SystemExit("NVIDIA_API_KEY is required to engage the swarm.")

    lines: list[str] = []
    if ENGINE_ENV_PATH.exists():
        lines = ENGINE_ENV_PATH.read_text(encoding="utf-8").splitlines()

    updated = False
    for index, line in enumerate(lines):
        if line.startswith("NVIDIA_API_KEY="):
            lines[index] = f"NVIDIA_API_KEY={api_key}"
            updated = True
            break

    if not updated:
        lines.append(f"NVIDIA_API_KEY={api_key}")

    content = "\n".join(lines).strip() + "\n"
    ENGINE_ENV_PATH.write_text(content, encoding="utf-8")
    console.print(Panel.fit("Saved NVIDIA_API_KEY to .env", title="Credentials", border_style="green"))


def _approval_loop(
    console: Console,
    router: AutobotRouter,
    workspace: TargetProjectWorkspace,
    phase: PhaseRecord,
    roadmap_text: str,
    progress_text: str,
    config=None,
) -> None:
    result = router.execute_phase(
        workspace,
        phase,
        roadmap_text,
        progress_text,
        event_handler=lambda message: render_stage_event(console, message),
    )
    render_plan(console, result)

    while True:
        render_phase_panel(console, result)
        decision = _select(
            console,
            "How would you like to handle this phase output?",
            choices=[
                "Approve and continue",
                "Request a revision",
                "Give revision feedback",
            ],
            default="Approve and continue",
        )

        if decision == "Approve and continue":
            updated_progress = router.complete_phase(
                workspace,
                phase,
                progress_text,
                result.plan,
                event_handler=lambda message: render_stage_event(console, message),
            )
            console.print(
                Panel.fit(
                    f"Marked '{phase.title}' as COMPLETE.",
                    title="Progress Tracker Updated",
                    border_style="green",
                )
            )

            # Auto-commit if enabled
            if config and config.auto_commit:
                from .git_utils import auto_commit_after_phase, is_git_repo
                if is_git_repo(workspace.root):
                    commit_result = auto_commit_after_phase(
                        workspace.root,
                        phase_id=phase.task_id or phase.title,
                        phase_title=phase.title,
                        enabled=True,
                    )
                    if commit_result and commit_result.success:
                        console.print(
                            Panel.fit(
                                f"Auto-committed {commit_result.files_committed} files\n"
                                f"Commit: {commit_result.commit_hash[:8] if commit_result.commit_hash else 'unknown'}",
                                title="Git Auto-Commit",
                                border_style="green",
                            )
                        )
                    elif commit_result and commit_result.error:
                        console.print(
                            Panel.fit(
                                f"Auto-commit skipped: {commit_result.error}",
                                title="Git Auto-Commit",
                                border_style="yellow",
                            )
                        )

            return

        feedback = ""
        if decision == "Give revision feedback":
            feedback = _text("Enter revision feedback").strip()
        result = router.refine_with_ratchet(
            workspace=workspace,
            phase=phase,
            roadmap_text=roadmap_text,
            progress_text=progress_text,
            previous_result=result,
            feedback=feedback,
            event_handler=lambda message: render_stage_event(console, message),
        )


def run_engage() -> None:
    config = load_config()
    render_engage_screen(config)

    target_root = resolve_target_project(ConsoleInstance)
    require_safety_branch(ConsoleInstance, target_root, config.safety_branch)
    _ensure_api_key(ConsoleInstance, target_root)
    from .costs import UsageTracker
    usage_tracker = UsageTracker(session_dir=target_root / ".autobots-state")
    router = AutobotRouter(usage_tracker=usage_tracker)
    render_registry_summary(ConsoleInstance, router.catalog)
    if not check_six_file_architecture(ConsoleInstance, target_root):
        raise SystemExit(1)

    # Auto-run preflight check
    import os
    from .config import CONFIG_FILE_NAMES
    api_key = os.getenv("NVIDIA_API_KEY") or config.api_key
    config_file = None
    for name in CONFIG_FILE_NAMES:
        path = target_root / name
        if path.exists():
            config_file = path
            break

    if not auto_run_preflight(
        api_key=api_key,
        workspace=target_root,
        config=config,
        config_file=config_file,
        console=ConsoleInstance,
    ):
        raise SystemExit(1)

    workspace = TargetProjectWorkspace(target_root)

    # Set up interrupt handler
    interrupt_handler = InterruptHandler(ConsoleInstance)
    interrupt_handler.setup(workspace)

    try:
        while True:
            roadmap_text, progress_text = router.read_phase_documents(workspace)
            phase = router.find_next_phase(progress_text)

            if phase is None:
                ConsoleInstance.print(
                    Panel.fit(
                        "No IN_PROGRESS or PENDING phases remain. The target roadmap is fully processed.",
                        title="All Phases Complete",
                        border_style="green",
                    )
                )
                return

            # Update checkpoint data for interrupt handler
            interrupt_handler.set_checkpoint_data(
                session_id=f"engage_{target_root.name}",
                mode="supervised",
                phase_index=0,
                phase_title=phase.title,
                phases_completed=[],
            )

            ConsoleInstance.print(
                Panel.fit(
                    f"Active phase: {phase.title}\nStatus: {phase.status}",
                    title="Phase Dispatch",
                    border_style="cyan",
                )
            )
            _approval_loop(ConsoleInstance, router, workspace, phase, roadmap_text, progress_text, config)

            # Check if interrupted during approval loop
            if interrupt_handler.interrupted:
                return
    finally:
        interrupt_handler.restore()
        # Display usage summary
        if usage_tracker and usage_tracker.usages:
            from .costs import format_cost, format_tokens
            summary = usage_tracker.summary()
            totals = summary["total_tokens"]
            ConsoleInstance.print(
                Panel.fit(
                    f"Token Usage:\n"
                    f"  Input: {format_tokens(totals['input'])}\n"
                    f"  Output: {format_tokens(totals['output'])}\n"
                    f"  Total: {format_tokens(totals['total'])}\n\n"
                    f"Estimated Cost: {format_cost(summary['total_cost_estimate'])}\n"
                    f"API Calls: {summary['call_count']}",
                    title="Session Summary",
                    border_style="cyan",
                )
            )
            usage_tracker.save()


def run_init(args: list[str]) -> None:
    """Check context files for a target project."""
    console = Console()

    # Parse arguments
    interactive = "--interactive" in args or "--wizard" in args
    skip_api_key = "--skip-api-key" in args

    # Auto-detect target: use provided path, or default to current directory
    target_root = None
    tokens = []
    for arg in args[1:]:
        if arg.startswith("--"):
            tokens.append(arg)
        elif target_root is None:
            target_root = Path(arg).expanduser().resolve()
        else:
            tokens.append(arg)

    if target_root is None:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        raise workspace_not_found(str(target_root))

    # Run interactive onboarding if requested
    if interactive:
        run_onboarding_wizard(target_root, console, skip_api_key)
        return

    console.print(
        Panel.fit(
            f"Checking context in:\n{target_root}",
            title="Workspace",
            border_style="cyan",
        )
    )

    profile = detect_repo_profile(target_root)

    # Ensure API key is available for future operations
    _ensure_api_key(console, target_root)

    selected_files = _parse_init_file_args(tokens)
    missing_files = missing_core_context_files(target_root)
    if selected_files is not None:
        missing_files = [filename for filename in selected_files if filename in missing_files]

    table = Table(title="Autobots Init Summary")
    table.add_column("Detected")
    table.add_column("Value")
    table.add_row("Project", profile.project_name)
    table.add_row("Languages", ", ".join(profile.languages))
    table.add_row("Package Managers", ", ".join(profile.package_managers))
    table.add_row("Test Tools", ", ".join(profile.test_tools))
    table.add_row("Source Roots", ", ".join(profile.source_roots))
    console.print(table)

    if missing_files:
        message = (
            "Autobots no longer creates target-project context files.\n\n"
            "Create these files in the target project's context folder:\n"
            f"{format_missing_context_files(missing_files)}\n\n"
            "Or run: autobots init --interactive for guided setup"
        )
        border_style = "yellow"
    else:
        message = "All requested context files are present."
        border_style = "green"

    console.print(
        Panel.fit(
            message,
            title="Context Check",
            border_style=border_style,
        )
    )

    # Show API key status
    import os
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if api_key:
        console.print("[green]OK[/green] NVIDIA API key: configured")
    else:
        console.print("[yellow]WARN[/yellow] NVIDIA API key: not set (required for swarm operations)")


def _parse_init_file_args(tokens: list[str]) -> tuple[str, ...] | None:
    selected_files: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--all":
            selected_files.extend(CORE_CONTEXT_FILES)
            index += 1
            continue
        if token == "--file":
            if index + 1 >= len(tokens):
                raise SystemExit("Missing value for --file")
            selected_files.append(tokens[index + 1].strip())
            index += 2
            continue
        raise SystemExit(f"Unknown init option: {token}")

    if not selected_files:
        return None

    selected = tuple(dict.fromkeys(selected_files))
    unknown_files = tuple(filename for filename in selected if filename not in CORE_CONTEXT_FILES)
    if unknown_files:
        allowed = ", ".join(CORE_CONTEXT_FILES)
        raise SystemExit(f"Unknown context file(s): {', '.join(unknown_files)}. Allowed: {allowed}")
    return selected


def run_plan(args: list[str]) -> None:
    """Read roadmap.md, select next phase, create task IDs in task-registry.json."""
    console = Console()
    target_root = _parse_plan_target(args)

    _ensure_api_key(console)

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Plan Error", border_style="red")
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(f"Planning in:\n{target_root}", title="Workspace", border_style="cyan")
    )

    result = plan_runner.plan_phase(str(target_root))

    if result is None:
        console.print(
            Panel.fit("No phases found in roadmap.md or all phases complete.", title="Plan", border_style="yellow")
        )
        return

    phase_id = result["phase_id"]
    phase_name = result["phase_name"]
    tasks = result["tasks"]
    already_planned = result.get("already_planned", False)

    table = Table(title=f"Phase {phase_id}: {phase_name}")
    table.add_column("Task ID", style="cyan")
    table.add_column("Description")
    table.add_column("Status")

    for task in tasks:
        tid = task.get("task_id", "")
        desc = task.get("description", "")
        status = task.get("status", "pending")
        status_icon = {"pending": "[ ]", "active": "[*]", "completed": "[x]", "failed": "[!]"}.get(status, "[ ]")
        table.add_row(tid, desc, status_icon)

    console.print(table)

    if already_planned:
        console.print(
            Panel.fit(
                f"Phase {phase_id} already has task IDs.\nRun 'autobots run <taskId>' to execute tasks.",
                title="Already Planned",
                border_style="yellow",
            )
        )
    else:
        first_task_id = tasks[0].get("task_id", "") if tasks else ""
        console.print(
            Panel.fit(
                f"Created {len(tasks)} task(s) for phase {phase_id}.\n\n"
                f"Next: autobots run {first_task_id} --supervised",
                title="Plan Complete",
                border_style="green",
            )
        )


def _create_model_validation_workspace() -> TargetProjectWorkspace:
    temp_root = Path(tempfile.mkdtemp(prefix="autobots-model-validation-"))
    context_root = temp_root / "context"
    src_root = temp_root / "src"
    context_root.mkdir(parents=True, exist_ok=True)
    src_root.mkdir(parents=True, exist_ok=True)
    (context_root / "roadmap.md").write_text(
        "# Validation Roadmap\n\n- Create a tiny implementation artifact.\n",
        encoding="utf-8",
    )
    (context_root / "progress-tracker.md").write_text(
        "- [ ] Build a validation artifact\n",
        encoding="utf-8",
    )
    return TargetProjectWorkspace(temp_root)


def run_validate_models() -> None:
    console = Console()
    _ensure_api_key(console)
    from .costs import UsageTracker
    usage_tracker = UsageTracker()
    router = AutobotRouter(usage_tracker=usage_tracker)
    render_registry_summary(console, router.catalog)
    workspace = _create_model_validation_workspace()
    roadmap_text, progress_text = router.read_phase_documents(workspace)
    phase = router.find_next_phase(progress_text)
    if phase is None:
        raise RuntimeError("Validation workspace did not produce a runnable phase.")

    plan = router.build_cluster_plan(phase, roadmap_text)
    console.print(
        Panel.fit(
            f"Testing model contracts for phase: {phase.title}",
            title="Model Validation",
            border_style="blue",
        )
    )
    report_path = ENGINE_ROOT / "model-validation-report.json"

    try:
        command_payload, command_raw = router._run_command_stage(plan, phase, roadmap_text, progress_text)
        specialist_payload, specialist_raw = router._run_specialist_stage(
            plan,
            workspace,
            phase,
            roadmap_text,
            progress_text,
            command_payload,
        )
        review_payload, review_raw = router._run_safety_stage(
            plan,
            phase,
            specialist_payload,
            command_payload,
        )

        rows = [
            ("Command", plan.command_lead.model_id, command_payload),
            ("Specialist", plan.primary_lead.model_id, specialist_payload),
            ("Review", plan.safety_lead.model_id, review_payload),
        ]

        if (review_payload.get("status") or "").lower() == "revise":
            repair_payload, repair_raw = router._run_repair_stage(
                plan,
                workspace,
                phase,
                roadmap_text,
                progress_text,
                command_payload,
                specialist_payload,
                review_payload,
            )
            rows.append(("Repair", plan.repair_lead.model_id, repair_payload))
        else:
            repair_raw = ""

        table = Table(title="Model Contract Validation")
        table.add_column("Stage")
        table.add_column("Model")
        table.add_column("Validated Fields")
        for stage_name, model_id, payload in rows:
            table.add_row(stage_name, model_id, ", ".join(sorted(payload.keys())))
        console.print(table)

        transcript = {
            "status": "success",
            "plan": {
                "command_lead": plan.command_lead.model_id,
                "primary_cluster": plan.primary_cluster,
                "primary_lead": plan.primary_lead.model_id,
                "safety_lead": plan.safety_lead.model_id,
                "repair_lead": plan.repair_lead.model_id,
            },
            "responses": {
                "command": {"raw": command_raw, "payload": command_payload},
                "specialist": {"raw": specialist_raw, "payload": specialist_payload},
                "review": {"raw": review_raw, "payload": review_payload},
            },
        }
        if repair_raw:
            transcript["responses"]["repair"] = {"raw": repair_raw, "payload": repair_payload}

        report_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
        console.print(
            Panel.fit(
                f"Validated live model responses successfully.\nSaved report to:\n{report_path}",
                title="Validation Complete",
                border_style="green",
            )
        )
    except Exception as exc:
        failure_report = {
            "status": "failed",
            "plan": {
                "command_lead": plan.command_lead.model_id,
                "primary_cluster": plan.primary_cluster,
                "primary_lead": plan.primary_lead.model_id,
                "safety_lead": plan.safety_lead.model_id,
                "repair_lead": plan.repair_lead.model_id,
            },
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        report_path.write_text(json.dumps(failure_report, indent=2), encoding="utf-8")
        console.print(
            Panel.fit(
                f"Live model validation failed at runtime.\n"
                f"Likely cause: invalid or unavailable model IDs for the configured endpoint.\n"
                f"Saved failure report to:\n{report_path}",
                title="Validation Failed",
                border_style="red",
            )
        )
        raise SystemExit(1) from exc


def _parse_plan_args(args: list[str]) -> tuple[str | None, str, bool, str | None, bool]:
    target_path: str | None = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    tokens = args[2:] if target_path is not None else args[1:]
    goal_parts: list[str] = []
    append = False
    insert_after: str | None = None
    dry_run = False

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--append":
            append = True
            index += 1
            continue
        if token == "--dry-run":
            dry_run = True
            index += 1
            continue
        if token == "--insert-after":
            if index + 1 >= len(tokens):
                raise SystemExit("Missing value for --insert-after")
            insert_after = tokens[index + 1].strip()
            append = True
            index += 2
            continue
        if token == "--goal":
            if index + 1 >= len(tokens):
                raise SystemExit("Missing value for --goal")
            goal_parts.append(tokens[index + 1].strip())
            index += 2
            continue
        goal_parts.append(token)
        index += 1

    return target_path, " ".join(part for part in goal_parts if part).strip(), append, insert_after, dry_run


def _parse_plan_target(args: list[str]) -> Path:
    """Parse the target path from plan command arguments."""
    target_path = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    if target_path:
        return Path(target_path).expanduser().resolve()
    return Path.cwd().resolve()


def _parse_run_args(args: list[str]) -> tuple[str | None, str | None, str]:
    """Parse run command arguments: autobots run [target] [taskId] [--supervised|--autonomous|--milestone]"""
    target_path: str | None = None
    task_id: str | None = None
    mode = "supervised"

    tokens = args[1:]
    for token in tokens:
        if token == "--autonomous":
            mode = "autonomous"
        elif token == "--milestone":
            mode = "milestone"
        elif token == "--supervised":
            mode = "supervised"
        elif token.startswith("P") and "-T" in token:
            task_id = token
        elif not token.startswith("--"):
            if target_path is None:
                target_path = token

    return target_path, task_id, mode


def run_run(args: list[str]) -> None:
    """Run a specific task by ID with the specified mode."""
    console = Console()
    target_path, task_id, mode = _parse_run_args(args)

    if target_path:
        target_root = Path(target_path).expanduser().resolve()
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Run Error", border_style="red")
        )
        raise SystemExit(1)

    _ensure_api_key(console)

    # Auto-run preflight check
    config = load_config(target_root)
    import os
    from .config import CONFIG_FILE_NAMES
    api_key = os.getenv("NVIDIA_API_KEY") or config.api_key
    config_file = None
    for name in CONFIG_FILE_NAMES:
        path = target_root / name
        if path.exists():
            config_file = path
            break

    if not auto_run_preflight(
        api_key=api_key,
        workspace=target_root,
        config=config,
        config_file=config_file,
        console=console,
    ):
        raise SystemExit(1)

    if task_id:
        console.print(
            Panel.fit(
                f"Running task {task_id} in {mode} mode\nTarget: {target_root}",
                title="Autobots Run",
                border_style="cyan",
            )
        )

        result = plan_runner.run_task(str(target_root), task_id, mode=mode)

        if "error" in result:
            console.print(
                Panel.fit(f"Error: {result['error']}", title="Task Failed", border_style="red")
            )
            raise SystemExit(1)

        table = Table(title="Task Execution Summary")
        table.add_column("Property")
        table.add_column("Value")
        table.add_row("Task ID", result.get("task_id", ""))
        table.add_row("Status", result.get("status", ""))
        table.add_row("Cluster", result.get("cluster", ""))
        console.print(table)
    else:
        from .executor.task_registry import get_next_pending_task, get_phase_status
        from .planning.core import parse_roadmap

        roadmap_path = str(target_root / "context" / "roadmap.md")
        phases = parse_roadmap(roadmap_path)

        if not phases:
            console.print(
                Panel.fit("No phases found. Run 'autobots plan' first.", title="Run Error", border_style="red")
            )
            raise SystemExit(1)

        for phase in phases:
            if phase["complete"]:
                continue
            phase_id = phase.get("phase_id", "")
            next_task = get_next_pending_task(str(target_root), phase_id)
            if next_task:
                console.print(
                    Panel.fit(
                        f"Running next pending task: {next_task['task_id']}\n"
                        f"Phase: {phase_id} - {phase['phase']}\n"
                        f"Mode: {mode}",
                        title="Autobots Run",
                        border_style="cyan",
                    )
                )
                result = plan_runner.run_task(str(target_root), next_task["task_id"], mode=mode)
                if "error" in result:
                    console.print(
                        Panel.fit(f"Error: {result['error']}", title="Task Failed", border_style="red")
                    )
                    raise SystemExit(1)

                table = Table(title="Task Execution Summary")
                table.add_column("Property")
                table.add_column("Value")
                table.add_row("Task ID", result.get("task_id", ""))
                table.add_row("Status", result.get("status", ""))
                table.add_row("Cluster", result.get("cluster", ""))
                console.print(table)
                return

        console.print(
            Panel.fit("No pending tasks found. Run 'autobots plan' first.", title="Run", border_style="yellow")
        )


def run_resume(args: list[str]) -> None:
    """Resume from a checkpoint."""
    console = Console()

    # Auto-detect target: use provided path, or default to current directory
    target_path = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    if target_path:
        target_root = _resolve_target_project_from_args(console, ["status", target_path])
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Resume Error", border_style="red")
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(f"Resuming from checkpoint\nTarget: {target_root}", title="Autobots Resume", border_style="cyan")
    )

    require_operational_context(console, target_root, "resume")

    workspace = TargetProjectWorkspace(target_root)
    engine = AutonomyEngine()

    def event_handler(message: str):
        console.print(f"[bold cyan]Swarm[/bold cyan] {message}")

    result = engine.resume(workspace, event_handler=event_handler)

    table = Table(title="Resume Summary")
    table.add_column("Status")
    table.add_column("Phases Completed")
    table.add_row(result.status, str(len(result.phases_completed)))
    console.print(table)

    if result.status == "no_checkpoint":
        console.print(Panel.fit("No checkpoint found. Use 'autobots run' to start fresh.", title="No Checkpoint", border_style="yellow"))
    if result.blocker:
        console.print(
            Panel.fit(
                f"Type: {result.blocker.blocker_type.value}\n"
                f"Message: {result.blocker.message}\n"
                f"Hint: {result.blocker.resolution_hint or 'None'}",
                title="Execution Blocked",
                border_style="red",
            )
        )


def run_status(args: list[str]) -> None:
    """Show current task and phase status with rich output."""
    console = Console()

    target_path = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    if target_path:
        target_root = Path(target_path).expanduser().resolve()
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Status Error", border_style="red")
        )
        raise SystemExit(1)

    # Get project info
    from .selectors import detect_git_branch
    branch = detect_git_branch(target_root) or "unknown"

    console.print(
        Panel.fit(
            f"Project: [bold]{target_root.name}[/bold]  -  Branch: [cyan]{branch}[/cyan]",
            title="Autobots Status",
            border_style="cyan",
        )
    )

    phases_status = get_all_phases_status(str(target_root))

    if not phases_status:
        console.print(
            Panel.fit("No tasks planned. Run 'autobots plan' first.", title="Status", border_style="yellow")
        )
        return

    # Calculate totals
    total_tasks = 0
    completed_tasks = 0
    running_tasks = 0
    failed_tasks = 0

    for phase in phases_status:
        total_tasks += phase.get("total", 0)
        completed_tasks += phase.get("completed", 0)
        if phase["status"] == "in_progress":
            running_tasks += 1
        elif phase["status"] == "failed":
            failed_tasks += 1

    # Progress bar
    progress_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    progress_bar = "█" * int(progress_pct // 5) + "░" * (20 - int(progress_pct // 5))

    console.print(f"\n  Overall: {progress_bar}  {progress_pct:.0f}%  ({completed_tasks}/{total_tasks} tasks)\n")

    # Phase details
    for phase in phases_status:
        phase_total = phase.get("total", 0)
        phase_completed = phase.get("completed", 0)
        phase_pct = (phase_completed / phase_total * 100) if phase_total > 0 else 0
        phase_bar = "█" * int(phase_pct // 5) + "░" * (20 - int(phase_pct // 5))

        status_style = {
            "complete": "[green][done][/green]",
            "in_progress": "[yellow][running][/yellow]",
            "failed": "[red][failed][/red]",
            "pending": "[dim][pending][/dim]",
        }.get(phase["status"], "[dim][pending][/dim]")

        console.print(f"  Phase {phase['phase_id']}: {phase['phase_name']:<30} {phase_bar}  {phase_pct:>5.0f}%  {status_style}")

        # Show tasks for in-progress or pending phases
        if phase["status"] in ("in_progress", "pending"):
            tasks = phase.get("tasks", [])
            for task in tasks:
                task_icon = {
                    "pending": "[dim][~][/dim]",
                    "active": "[yellow][>>][/yellow]",
                    "completed": "[green][OK][/green]",
                    "failed": "[red][!!][/red]",
                }.get(task.get("status", "pending"), "[dim][~][/dim]")

                task_desc = task.get("description", "")[:40]
                task_id = task.get("task_id", "")
                console.print(f"    ├─ {task_id}  {task_desc:<40} {task_icon}")

    console.print()
    console.print(f"  Total tasks: {total_tasks}  -  Done: {completed_tasks}  -  Running: {running_tasks}  -  Failed: {failed_tasks}")

    # Estimate remaining time from audit trail
    from .executor.state import StateManager
    manager = StateManager(target_root)
    entries = manager.get_audit_trail(limit=100)

    if entries:
        durations = []
        for entry in entries:
            if entry.command and "duration_ms" in entry.metadata:
                durations.append(entry.metadata["duration_ms"])

        if durations:
            avg_duration_ms = sum(durations) / len(durations)
            remaining_tasks = total_tasks - completed_tasks
            est_remaining_ms = avg_duration_ms * remaining_tasks
            est_minutes = est_remaining_ms / 60000

            if est_minutes < 1:
                console.print(f"  Estimated remaining: ~{est_remaining_ms/1000:.0f}s")
            else:
                console.print(f"  Estimated remaining: ~{est_minutes:.1f} min")

    console.print()


def run_list() -> None:
    """List all available autobots commands."""
    console = Console()

    commands = [
        ("init", "Check required context files for a target project"),
        ("plan", "Read roadmap.md, select next phase, create task IDs in task-registry.json"),
        ("run", "Run task by ID: autobots run <taskId> [--supervised|--autonomous|--milestone]"),
        ("resume", "Resume execution from the last checkpoint"),
        ("status", "Show all phase and task statuses from task-registry.json"),
        ("engage", "Interactive swarm execution with operator approval at each phase"),
        ("doctor", "Run preflight checks to verify API, config, and workspace"),
        ("config", "Validate or show current configuration"),
        ("completions", "Generate shell completion scripts"),
        ("marketplace", "Search, install, and publish skill packs"),
        ("dashboard", "Start web dashboard for monitoring"),
        ("diff", "Compare current workspace state to a snapshot"),
        ("logs", "View audit trail logs with filtering"),
        ("validate-models", "Test live model contracts and validate API connectivity"),
        ("publish", "Auto-increment version, build, and publish to PyPI"),
        ("undo", "Undo the last task or a specific task's changes"),
        ("snapshots", "List available file snapshots for rollback"),
        ("catalog", "Manage model catalog: refresh, list"),
        ("list", "Show this help information"),
    ]

    table = Table(title="Autobots Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)
    console.print()
    console.print("[dim]Run 'autobots <command> --help' for detailed usage.[/dim]")


def run_doctor(args: list[str]) -> None:
    """Run preflight checks for Autobots."""
    console = Console()

    # Parse arguments
    target_path = None
    skip_model = False
    verbose = True

    for arg in args[1:]:
        if arg == "--skip-model":
            skip_model = True
        elif arg == "--quiet":
            verbose = False
        elif not arg.startswith("--"):
            target_path = arg

    # Determine workspace
    if target_path:
        workspace = Path(target_path).expanduser().resolve()
    else:
        workspace = Path.cwd().resolve()

    if not workspace.exists() or not workspace.is_dir():
        raise workspace_not_found(str(workspace))

    # Load config
    config = load_config(workspace)

    # Get API key from env or config
    import os
    api_key = os.getenv("NVIDIA_API_KEY") or config.api_key

    # Get config file path
    from .config import CONFIG_FILE_NAMES
    config_file = None
    for name in CONFIG_FILE_NAMES:
        path = workspace / name
        if path.exists():
            config_file = path
            break

    # Run preflight checks
    result = run_preflight(
        api_key=api_key,
        model_id=None,  # Will use default model selection
        workspace=workspace,
        config=config,
        config_file=config_file,
        skip_model_check=skip_model,
    )

    # Render result
    render_preflight_result(result, console, verbose=verbose)

    if not result.all_passed:
        raise SystemExit(1)


def run_undo(args: list[str]) -> None:
    """Undo the last task or a specific task's changes."""
    console = Console()

    target_path = None
    snapshot_id = None
    for arg in args[1:]:
        if arg.startswith("P") and "-T" in arg:
            snapshot_id = arg
        elif not arg.startswith("--"):
            target_path = arg

    if target_path:
        target_root = Path(target_path).expanduser().resolve()
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Undo Error", border_style="red")
        )
        raise SystemExit(1)

    from .executor.state import RollbackManager

    manager = RollbackManager(target_root)

    if not snapshot_id:
        snapshots = manager.list_snapshots()
        if not snapshots:
            console.print(Panel.fit("No snapshots found. Nothing to undo.", title="Undo", border_style="yellow"))
            return
        snapshot_id = snapshots[0]["snapshot_id"]

    try:
        result = manager.rollback(snapshot_id)
        console.print(
            Panel.fit(
                f"Restored {result['files_restored']} files from snapshot {snapshot_id}",
                title="Undo Complete",
                border_style="green",
            )
        )
    except FileNotFoundError as e:
        console.print(Panel.fit(str(e), title="Undo Error", border_style="red"))
        raise SystemExit(1)


def run_snapshots(args: list[str]) -> None:
    """List available snapshots."""
    console = Console()

    target_path = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    if target_path:
        target_root = Path(target_path).expanduser().resolve()
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Snapshots Error", border_style="red")
        )
        raise SystemExit(1)

    from .executor.state import RollbackManager

    manager = RollbackManager(target_root)
    snapshots = manager.list_snapshots()

    if not snapshots:
        console.print(Panel.fit("No snapshots found.", title="Snapshots", border_style="yellow"))
        return

    table = Table(title="Available Snapshots")
    table.add_column("Snapshot ID", style="cyan")
    table.add_column("Task ID")
    table.add_column("Created At")
    table.add_column("Files Tracked")

    for snap in snapshots:
        created = datetime.fromtimestamp(snap["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(snap["snapshot_id"], snap["task_id"], created, str(snap["files_tracked"]))

        console.print(table)


def run_diff(args: list[str]) -> None:
    """Compare current workspace to a snapshot."""
    console = Console()

    target_path = None
    snapshot_id = None

    for arg in args[1:]:
        if arg == "--help" or arg == "-h":
            console.print(
                Panel.fit(
                    "Usage: autobots diff [target] [snapshot_id]\n\n"
                    "Compare current workspace state to a snapshot.\n"
                    "If no snapshot_id is specified, compares to the latest snapshot.\n\n"
                    "Examples:\n"
                    "  autobots diff                    # Compare to latest snapshot\n"
                    "  autobots diff ./my-project        # Compare specific project\n"
                    "  autobots diff . snap_abc123       # Compare to specific snapshot",
                    title="Diff Command",
                    border_style="cyan",
                )
            )
            return
        elif not arg.startswith("--"):
            if snapshot_id:
                target_path = arg
            else:
                snapshot_id = arg

    if target_path:
        target_root = Path(target_path).expanduser().resolve()
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        raise workspace_not_found(str(target_root))

    from .executor.state import RollbackManager
    from .diff import compute_diff

    manager = RollbackManager(target_root)
    diff = compute_diff(target_root, manager.snapshots_root, snapshot_id)

    if diff is None:
        console.print(Panel.fit("No snapshots found.", title="Diff", border_style="yellow"))
        return

    if not diff.has_changes():
        console.print(Panel.fit("No changes since snapshot.", title="Diff", border_style="green"))
        return

    # Render diff
    console.print(f"\n[bold]Comparing to snapshot:[/bold] {diff.snapshot_id}")
    console.print(f"[dim]Task: {diff.task_id} | Created: {datetime.fromtimestamp(diff.created_at).strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    if diff.added:
        console.print(f"[green]Added ({len(diff.added)} files):[/green]")
        for path in sorted(diff.added):
            console.print(f"  + {path}")
        console.print()

    if diff.removed:
        console.print(f"[red]Removed ({len(diff.removed)} files):[/red]")
        for path in sorted(diff.removed):
            console.print(f"  - {path}")
        console.print()

    if diff.modified:
        console.print(f"[yellow]Modified ({len(diff.modified)} files):[/yellow]")
        for mod in sorted(diff.modified, key=lambda x: x["path"]):
            console.print(f"  ~ {mod['path']} ({mod['old_lines']} → {mod['new_lines']} lines)")
        console.print()

    console.print(f"[dim]{diff.summary()}[/dim]")


def run_logs(args: list[str]) -> None:
    """View audit trail logs."""
    console = Console()

    target_path = None
    phase_filter = None
    change_type = None
    limit = 50
    show_details = False

    for arg in args[1:]:
        if arg == "--help" or arg == "-h":
            console.print(
                Panel.fit(
                    "Usage: autobots logs [target] [options]\n\n"
                    "View audit trail logs with optional filtering.\n\n"
                    "Options:\n"
                    "  --phase <phaseId>     Filter by phase ID\n"
                    "  --type <changeType>   Filter by change type\n"
                    "  --limit <n>           Number of entries (default: 50)\n"
                    "  --details             Show detailed information\n\n"
                    "Change Types:\n"
                    "  file_created, file_modified, file_deleted\n"
                    "  phase_started, phase_completed\n"
                    "  validation_passed, validation_failed\n"
                    "  command_executed, error_encountered\n\n"
                    "Examples:\n"
                    "  autobots logs                    # Show recent 50 entries\n"
                    "  autobots logs --phase P1         # Filter by phase\n"
                    "  autobots logs --type file_modified --limit 20\n"
                    "  autobots logs --details          # Show full details",
                    title="Logs Command",
                    border_style="cyan",
                )
            )
            return
        elif arg == "--details":
            show_details = True
        elif arg == "--phase" and len(args) > args.index(arg) + 1:
            phase_filter = args[args.index(arg) + 1]
        elif arg == "--type" and len(args) > args.index(arg) + 1:
            change_type = args[args.index(arg) + 1]
        elif arg == "--limit" and len(args) > args.index(arg) + 1:
            try:
                limit = int(args[args.index(arg) + 1])
            except ValueError:
                pass
        elif not arg.startswith("--"):
            target_path = arg

    if target_path:
        target_root = Path(target_path).expanduser().resolve()
    else:
        target_root = Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        raise workspace_not_found(str(target_root))

    from .executor.state import StateManager, ChangeType as CT

    manager = StateManager(target_root)
    entries = manager.get_audit_trail(limit=1000)  # Get all, then filter

    # Apply filters
    if phase_filter:
        entries = [e for e in entries if e.phase_id == phase_filter]
    if change_type:
        entries = [e for e in entries if e.change_type == change_type]

    entries = entries[-limit:]

    if not entries:
        console.print(Panel.fit("No audit trail entries found.", title="Logs", border_style="yellow"))
        return

    # Group by phase
    phases: dict[str, list] = {}
    for entry in entries:
        phase = entry.phase_id or "global"
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(entry)

    # Render
    for phase, phase_entries in phases.items():
        if phase != "global":
            console.print(f"\n[bold cyan]Phase: {phase}[/bold cyan]")

        for entry in phase_entries:
            ts = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
            ct = entry.change_type.replace("_", " ").title()

            # Color based on change type
            if "failed" in entry.change_type or "error" in entry.change_type:
                style = "red"
            elif "passed" in entry.change_type or "completed" in entry.change_type:
                style = "green"
            elif "created" in entry.change_type:
                style = "cyan"
            elif "modified" in entry.change_type:
                style = "yellow"
            else:
                style = "white"

            console.print(f"  [{style}]{ts}[/] [{style}]{ct}[/] {entry.description}")

            if show_details:
                if entry.file_path:
                    console.print(f"    [dim]File: {entry.file_path}[/dim]")
                if entry.command:
                    console.print(f"    [dim]Command: {entry.command}[/dim]")
                if entry.metadata:
                    console.print(f"    [dim]Metadata: {json.dumps(entry.metadata, indent=2)}[/dim]")

    console.print(f"\n[dim]{len(entries)} entries shown (filtered from audit trail)[/dim]")


def run_explain(args: list[str]) -> None:
    """Explain what the swarm did for a given phase/task."""
    console = Console()

    target_path = None
    task_id = None

    for arg in args[1:]:
        if arg == "--help" or arg == "-h":
            console.print(
                Panel.fit(
                    "Usage: autobots explain [target] <phaseId|taskId>\n\n"
                    "Explain what the swarm did for a given phase or task.\n"
                    "Pulls information from the audit trail, phase summary,\n"
                    "cluster used, model calls, review results, and duration.\n\n"
                    "Examples:\n"
                    "  autobots explain P1              # Explain phase P1\n"
                    "  autobots explain P2-T3           # Explain specific task\n"
                    "  autobots explain ./my-project P2 # Explain in target project",
                    title="Explain Command",
                    border_style="cyan",
                )
            )
            return
        elif not arg.startswith("--") and task_id is None:
            if "." in arg or arg.startswith("P"):
                task_id = arg
            else:
                target_path = arg

    target_root = Path(target_path).expanduser().resolve() if target_path else Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Explain Error", border_style="red")
        )
        raise SystemExit(1)

    if not task_id:
        console.print(
            Panel.fit("Please specify a phase or task ID.\nUsage: autobots explain P2-T3", title="Explain", border_style="yellow")
        )
        return

    console.print(
        Panel.fit(f"Explaining: [bold]{task_id}[/bold]\nProject: {target_root}", title="Autobots Explain", border_style="cyan")
    )

    # Get audit trail
    from .executor.state import StateManager
    manager = StateManager(target_root)
    entries = manager.get_audit_trail(limit=200)

    # Filter relevant entries
    relevant = [e for e in entries if task_id in e.description]

    if not relevant:
        console.print(f"\n[dim]No audit trail entries found for {task_id}[/dim]\n")
        return

    console.print(f"\n[bold]Audit Trail for {task_id}:[/bold]")

    for entry in relevant:
        ts = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
        ct = entry.change_type

        if "completed" in ct or "passed" in ct:
            style = "green"
        elif "failed" in ct:
            style = "red"
        elif "created" in ct:
            style = "cyan"
        elif "modified" in ct:
            style = "yellow"
        else:
            style = "white"

        console.print(f"  [{style}]{ts}[/] [{style}]{ct}[/] {entry.description}")

        if entry.file_path:
            console.print(f"    [dim]File: {entry.file_path}[/dim]")
        if entry.command:
            console.print(f"    [dim]Command: {entry.command}[/dim]")

    # Phase summary
    summary_path = target_root / ".autobots-state" / f"{task_id}.json"
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                phase_data = json.load(f)
            console.print(f"\n[bold]Phase Details:[/bold]")
            if "cluster" in phase_data:
                console.print(f"  Cluster: {phase_data['cluster']}")
            if "model" in phase_data:
                console.print(f"  Model: {phase_data['model']}")
            if "duration_ms" in phase_data:
                dur = phase_data["duration_ms"]
                console.print(f"  Duration: {dur/1000:.1f}s")
            if "status" in phase_data:
                console.print(f"  Status: {phase_data['status']}")
        except Exception:
            pass

    console.print()


def run_stats(args: list[str]) -> None:
    """Show usage statistics and summary."""
    console = Console()

    target_path = None
    show_all = False

    for arg in args[1:]:
        if arg == "--help" or arg == "-h":
            console.print(
                Panel.fit(
                    "Usage: autobots stats [target] [--all]\n\n"
                    "Show usage statistics: tasks completed, tokens used,\n"
                    "costs, average duration, success rate, and more.\n\n"
                    "Options:\n"
                    "  --all     Show all-time stats, not just current session\n\n"
                    "Examples:\n"
                    "  autobots stats                    # Current session\n"
                    "  autobots stats ./my-project       # Specific project\n"
                    "  autobots stats --all              # All-time stats",
                    title="Stats Command",
                    border_style="cyan",
                )
            )
            return
        elif arg == "--all":
            show_all = True
        elif not arg.startswith("--"):
            target_path = arg

    target_root = Path(target_path).expanduser().resolve() if target_path else Path.cwd().resolve()

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(f"Target project not found: {target_root}", title="Stats Error", border_style="red")
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(f"Project: [bold]{target_root.name}[/bold]", title="Autobots Stats", border_style="cyan")
    )

    # Get audit trail
    from .executor.state import StateManager
    manager = StateManager(target_root)
    entries = manager.get_audit_trail(limit=500 if show_all else 100)

    if not entries:
        console.print("\n[dim]No audit trail entries found. Run a task first.[/dim]\n")
        return

    # Calculate stats
    total_tasks = 0
    completed_tasks = 0
    failed_tasks = 0
    file_creates = 0
    file_modifies = 0
    durations = []
    clusters = {}

    for entry in entries:
        if "phase_completed" in entry.change_type or "validation_passed" in entry.change_type:
            completed_tasks += 1
        elif "phase_failed" in entry.change_type or "validation_failed" in entry.change_type:
            failed_tasks += 1

        if "file_created" in entry.change_type:
            file_creates += 1
        elif "file_modified" in entry.change_type:
            file_modifies += 1

        if "duration_ms" in entry.metadata:
            durations.append(entry.metadata["duration_ms"])

        # Extract cluster from description
        for cluster in ["Optimus", "UltraMagnus", "RedAlert", "Jazz", "Ratchet", "Perceptor", "Bumblebee", "Ironhide", "Wheeljack"]:
            if cluster in entry.description:
                clusters[cluster] = clusters.get(cluster, 0) + 1

    total_tasks = completed_tasks + failed_tasks
    success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Display stats
    console.print(f"\n[bold]Task Summary:[/bold]")
    console.print(f"  Total tasks: {total_tasks}")
    console.print(f"  Completed: [green]{completed_tasks}[/green]")
    console.print(f"  Failed: [red]{failed_tasks}[/red]")
    console.print(f"  Success rate: {success_rate:.1f}%")
    console.print(f"\n[bold]File Changes:[/bold]")
    console.print(f"  Files created: {file_creates}")
    console.print(f"  Files modified: {file_modifies}")

    if durations:
        avg_duration = sum(durations) / len(durations)
        total_duration = sum(durations)
        console.print(f"\n[bold]Timing:[/bold]")
        console.print(f"  Average task duration: {avg_duration/1000:.1f}s")
        console.print(f"  Total time: {total_duration/60000:.1f} min")

    if clusters:
        console.print(f"\n[bold]Clusters Used:[/bold]")
        sorted_clusters = sorted(clusters.items(), key=lambda x: x[1], reverse=True)
        for cluster, count in sorted_clusters[:5]:
            console.print(f"  {cluster}: {count}")

    # Cost info from costs.py
    try:
        from .costs import UsageTracker
        tracker = UsageTracker(target_root)
        summary = tracker.summary()
        if summary.total_cost > 0:
            console.print(f"\n[bold]Costs:[/bold]")
            console.print(f"  Total cost: ${summary.total_cost:.4f}")
            console.print(f"  Input tokens: {summary.total_input_tokens:,}")
            console.print(f"  Output tokens: {summary.total_output_tokens:,}")
            console.print(f"  Estimated remaining: ${summary.estimated_remaining:.4f}")
    except Exception:
        pass

    console.print()


def run_config(args: list[str]) -> None:
    """Handle config subcommands: validate, show."""
    console = Console()

    if len(args) < 2:
        console.print(
            Panel.fit(
                "Usage: autobots config <validate|show>\n\n"
                "  validate  Validate configuration and show errors\n"
                "  show      Display current configuration",
                title="Config Commands",
                border_style="cyan",
            )
        )
        return

    subcommand = args[1]

    if subcommand == "validate":
        config = load_config()
        result = config.validate()

        if result.valid:
            console.print(
                Panel.fit(
                    "Configuration is valid!",
                    title="Config Validation",
                    border_style="green",
                )
            )
        else:
            error_lines = ["[red]Configuration errors:[/red]\n"]
            for error in result.errors:
                field = error.get("field", "unknown")
                message = error.get("message", "")
                suggestion = error.get("suggestion", "")
                error_lines.append(f"  [red]-[/red] {field}: {message}")
                if suggestion:
                    error_lines.append(f"    [dim]→ {suggestion}[/dim]")
            console.print(Panel.fit("\n".join(error_lines), title="Config Validation", border_style="red"))

        if result.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warn in result.warnings:
                field = warn.get("field", "unknown")
                message = warn.get("message", "")
                suggestion = warn.get("suggestion", "")
                console.print(f"  [yellow]-[/yellow] {field}: {message}")
                if suggestion:
                    console.print(f"    [dim]→ {suggestion}[/dim]")

        if not result.valid:
            raise SystemExit(1)

    elif subcommand == "show":
        config = load_config()
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("model_selection_profile", config.model_selection_profile)
        table.add_row("default_mode", config.default_mode)
        table.add_row("safety_branch", config.safety_branch)
        table.add_row("milestone_threshold", str(config.milestone_threshold))
        table.add_row("max_verification_attempts", str(config.max_verification_attempts))
        table.add_row("test_gate", str(config.test_gate))
        table.add_row("test_command", config.test_command)
        table.add_row("test_timeout", str(config.test_timeout))
        table.add_row("auto_commit", str(config.auto_commit))
        table.add_row("parallel_planning", str(config.parallel_planning))
        table.add_row("disable_live_catalog", str(config.disable_live_catalog))
        table.add_row("model_registry_path", config.model_registry_path or "None")
        table.add_row("api_key", "***" if config.api_key else "Not set")

        console.print(table)

    else:
        console.print(
            Panel.fit(
                f"Unknown subcommand: {subcommand}\n\n"
                "Available subcommands: validate, show",
                title="Config Error",
                border_style="red",
            )
        )
        raise SystemExit(1)


def run_completions(args: list[str]) -> None:
    """Generate shell completion scripts."""
    console = Console()

    if len(args) < 2 or args[1] == "--help" or args[1] == "-h":
        console.print(
            Panel.fit(
                "Usage: autobots completions <shell>\n\n"
                "Generate shell completion scripts for bash, zsh, or fish.\n\n"
                "Supported shells:\n"
                "  bash  - Bash shell\n"
                "  zsh   - Z shell\n"
                "  fish  - Fish shell\n\n"
                "Installation:\n"
                "  bash: source <(autobots completions bash)\n"
                "  zsh:  autobots completions zsh > ~/.zfunc/_autobots\n"
                "  fish: autobots completions fish > ~/.config/fish/completions/autobots.fish",
                title="Shell Completions",
                border_style="cyan",
            )
        )
        return

    shell = args[1].lower()
    from .completions import get_completion_script, get_available_shells

    script = get_completion_script(shell)
    if script is None:
        console.print(
            Panel.fit(
                f"Unsupported shell: {shell}\n\n"
                f"Supported shells: {', '.join(get_available_shells())}",
                title="Completions Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    # Output the script directly for piping
    print(script)


def run_marketplace(args: list[str]) -> None:
    """Handle marketplace subcommands: search, install, publish, list."""
    console = Console()

    if len(args) < 2:
        console.print(
            Panel.fit(
                "Usage: autobots marketplace <search|install|publish|list|info>\n\n"
                "  search   Search for skill packs\n"
                "  install  Install a skill pack\n"
                "  publish  Publish a skill pack\n"
                "  list     List available skill packs\n"
                "  info     Show info about a skill pack",
                title="Marketplace Commands",
                border_style="cyan",
            )
        )
        return

    subcommand = args[1]

    from .marketplace import Marketplace, get_builtin_skill_packs, SkillPack

    marketplace = Marketplace()

    if subcommand == "search":
        query = args[2] if len(args) > 2 else None
        results = marketplace.search(query=query)

        # Include built-in packs in search
        builtin = get_builtin_skill_packs()
        if query:
            query_lower = query.lower()
            builtin = [
                p for p in builtin
                if query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or query_lower in " ".join(p.tags).lower()
            ]

        if not results and not builtin:
            console.print(Panel.fit("No skill packs found.", title="Marketplace Search", border_style="yellow"))
            return

        table = Table(title="Search Results")
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Author")
        table.add_column("Description")
        table.add_column("Downloads")

        for entry in results:
            table.add_row(entry.name, entry.version, entry.author, entry.description[:50], str(entry.downloads))

        for pack in builtin:
            if not marketplace.get(pack.name):  # Don't duplicate
                table.add_row(pack.name, pack.version, pack.author, pack.description[:50], "built-in")

        console.print(table)

    elif subcommand == "list":
        # Show built-in packs
        builtin = get_builtin_skill_packs()

        table = Table(title="Available Skill Packs")
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Author")
        table.add_column("Description")
        table.add_column("Tags")

        for pack in builtin:
            table.add_row(
                pack.name,
                pack.version,
                pack.author,
                pack.description[:50],
                ", ".join(pack.tags[:3]),
            )

        console.print(table)

    elif subcommand == "install":
        if len(args) < 3:
            console.print("[red]Usage: autobots marketplace install <name>[/red]")
            raise SystemExit(1)

        name = args[2]

        # Check built-in packs
        builtin = get_builtin_skill_packs()
        builtin_pack = next((p for p in builtin if p.name == name), None)

        if builtin_pack:
            # Get target directory
            target_dir = Path.cwd()
            for arg in args[3:]:
                if not arg.startswith("--"):
                    target_dir = Path(arg)
                    break

            # Install built-in pack
            context_dir = target_dir / "context"
            context_dir.mkdir(parents=True, exist_ok=True)

            installed = []
            for filename, content in builtin_pack.context_files.items():
                target_file = context_dir / filename
                if not target_file.exists():
                    target_file.write_text(content, encoding="utf-8")
                    installed.append(filename)

            if installed:
                console.print(
                    Panel.fit(
                        f"Installed {len(installed)} files:\n" + "\n".join(f"  - {f}" for f in installed),
                        title=f"Installed {name}",
                        border_style="green",
                    )
                )
            else:
                console.print(f"[yellow]All files already exist for {name}[/yellow]")
        else:
            # Check marketplace registry
            entry = marketplace.get(name)
            if entry:
                target_dir = Path.cwd()
                if marketplace.install(name, target_dir):
                    console.print(f"[green]Installed {name}[/green]")
                else:
                    console.print(f"[red]Failed to install {name}[/red]")
            else:
                console.print(f"[red]Skill pack not found: {name}[/red]")

    elif subcommand == "publish":
        # Create a skill pack from current project
        if len(args) < 3:
            console.print("[red]Usage: autobots marketplace publish <name>[/red]")
            raise SystemExit(1)

        name = args[2]
        project_dir = Path.cwd()
        context_dir = project_dir / "context"

        if not context_dir.exists():
            console.print("[red]No context/ directory found. Run 'autobots init' first.[/red]")
            raise SystemExit(1)

        # Read context files
        context_files = {}
        for f in context_dir.glob("*.md"):
            if f.name.startswith("."):
                continue
            context_files[f.name] = f.read_text(encoding="utf-8")

        if not context_files:
            console.print("[red]No context files found in context/[/red]")
            raise SystemExit(1)

        # Get metadata
        author = "Local User"
        description = f"Skill pack: {name}"
        tags = ["custom"]

        skill_pack = SkillPack(
            name=name,
            version="1.0.0",
            author=author,
            description=description,
            tags=tags,
            context_files=context_files,
        )

        if marketplace.publish(skill_pack):
            console.print(
                Panel.fit(
                    f"Published {name} v{skill_pack.version}\n"
                    f"Files: {', '.join(context_files.keys())}",
                    title="Published",
                    border_style="green",
                )
            )
        else:
            console.print("[red]Failed to publish skill pack[/red]")

    elif subcommand == "info":
        if len(args) < 3:
            console.print("[red]Usage: autobots marketplace info <name>[/red]")
            raise SystemExit(1)

        name = args[2]

        # Check built-in packs
        builtin = get_builtin_skill_packs()
        builtin_pack = next((p for p in builtin if p.name == name), None)

        if builtin_pack:
            console.print(f"[bold cyan]{builtin_pack.name}[/bold cyan] v{builtin_pack.version}")
            console.print(f"Author: {builtin_pack.author}")
            console.print(f"Description: {builtin_pack.description}")
            console.print(f"Tags: {', '.join(builtin_pack.tags)}")
            console.print(f"Files: {', '.join(builtin_pack.context_files.keys())}")
        else:
            entry = marketplace.get(name)
            if entry:
                console.print(f"[bold cyan]{entry.name}[/bold cyan] v{entry.version}")
                console.print(f"Author: {entry.author}")
                console.print(f"Description: {entry.description}")
                console.print(f"Tags: {', '.join(entry.tags)}")
                console.print(f"Downloads: {entry.downloads}")
            else:
                console.print(f"[red]Skill pack not found: {name}[/red]")

    else:
        console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
        raise SystemExit(1)


def run_dashboard(args: list[str]) -> None:
    """Start the web dashboard for monitoring."""
    console = Console()

    if "--help" in args or "-h" in args:
        console.print(
            Panel.fit(
                "Usage: autobots dashboard [options]\n\n"
                "Start a web dashboard for real-time monitoring.\n\n"
                "Options:\n"
                "  --port <port>     Port number (default: 8080)\n"
                "  --host <host>     Host to bind (default: 127.0.0.1)\n"
                "  --no-open         Don't auto-open browser",
                title="Dashboard Command",
                border_style="cyan",
            )
        )
        return

    # Parse arguments
    port = 8080
    host = "127.0.0.1"
    auto_open = True

    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                pass
        elif arg == "--host" and i + 1 < len(args):
            host = args[i + 1]
        elif arg == "--no-open":
            auto_open = False

    from .dashboard import DashboardConfig, get_dashboard

    config = DashboardConfig(host=host, port=port, auto_open=auto_open)
    dashboard = get_dashboard(config)

    console.print(
        Panel.fit(
            f"Starting dashboard at http://{host}:{port}\n\n"
            "The dashboard will auto-refresh every 5 seconds.\n"
            "Press Ctrl+C to stop.",
            title="Autobots Dashboard",
            border_style="cyan",
        )
    )

    dashboard.start()

    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dashboard.stop()
        console.print("\n[yellow]Dashboard stopped.[/yellow]")


def run_catalog(args: list[str]) -> None:
    """Handle catalog subcommands: refresh, list."""
    console = Console()

    if len(args) < 2:
        console.print(
            Panel.fit(
                "Usage: autobots catalog <refresh|list>\n\n"
                "  refresh  Fetch live model list from NVIDIA NIM\n"
                "  list     Show available models from cache",
                title="Catalog Commands",
                border_style="cyan",
            )
        )
        return

    subcommand = args[1]

    if subcommand == "refresh":
        _ensure_api_key(console)
        from .catalog import ClusterCatalog

        catalog = ClusterCatalog()
        console.print(Panel.fit("Fetching live model catalog...", title="Catalog Refresh", border_style="cyan"))

        result = catalog.refresh_catalog(force="--force" in args)

        if "error" in result:
            console.print(Panel.fit(result["error"], title="Refresh Failed", border_style="red"))
        else:
            model_count = len(result)
            console.print(
                Panel.fit(
                    f"Successfully cached {model_count} models\n"
                    f"Cache location: ~/.autobots/catalog_cache.json\n"
                    f"Cache expires: 24 hours",
                    title="Refresh Complete",
                    border_style="green",
                )
            )

    elif subcommand == "list":
        from .catalog import ClusterCatalog

        catalog = ClusterCatalog()
        cached = catalog.get_cached_catalog()

        if not cached:
            console.print(
                Panel.fit(
                    "No cached catalog found.\nRun 'autobots catalog refresh' to fetch models.",
                    title="Catalog",
                    border_style="yellow",
                )
            )
            return

        # Parse --cluster filter
        cluster_filter = None
        for i, arg in enumerate(args):
            if arg == "--cluster" and i + 1 < len(args):
                cluster_filter = args[i + 1]

        table = Table(title="Available Models")
        table.add_column("Model ID", style="cyan")

        models = list(cached.keys())
        if cluster_filter:
            # Filter by cluster match tokens
            from .catalog import CLUSTER_MATCH_TOKENS

            tokens = CLUSTER_MATCH_TOKENS.get(cluster_filter, ())
            models = [m for m in models if any(t in m.lower() for t in tokens)]

        for model_id in sorted(models)[:50]:  # Limit to 50 for readability
            table.add_row(model_id)

        if len(models) > 50:
            table.add_row(f"... and {len(models) - 50} more")

        console.print(table)
        console.print(f"\n[dim]Total: {len(models)} models[/dim]")

    else:
        console.print(
            Panel.fit(
                f"Unknown catalog subcommand: {subcommand}\nUse 'refresh' or 'list'.",
                title="Catalog Error",
                border_style="red",
            )
        )


def _bump_version(version: str) -> str:
    """Bump patch version: 0.1.4 -> 0.1.5."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise SystemExit(f"Invalid version format: {version}. Expected X.Y.Z")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return f"{major}.{minor}.{patch + 1}"


def _update_version_in_file(file_path: Path, old_version: str, new_version: str) -> None:
    """Replace version string in a file."""
    content = file_path.read_text(encoding="utf-8")
    updated = content.replace(old_version, new_version)
    file_path.write_text(updated, encoding="utf-8")


def run_publish(args: list[str]) -> None:
    """Auto-increment version, build, and publish to PyPI."""
    console = Console()

    dry_run = "--dry-run" in args
    token = None
    for i, arg in enumerate(args):
        if arg == "--token" and i + 1 < len(args):
            token = args[i + 1]

    if not init_path.exists() or not pyproject_path.exists():
        console.print(
            Panel.fit(
                "Could not find __init__.py or pyproject.toml",
                title="Publish Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    init_content = init_path.read_text(encoding="utf-8")
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_content)
    if not version_match:
        console.print(
            Panel.fit(
                "Could not extract version from __init__.py",
                title="Publish Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    current_version = version_match.group(1)
    new_version = _bump_version(current_version)

    console.print(
        Panel.fit(
            f"Current version: {current_version}\nNew version: {new_version}",
            title="Version Bump",
            border_style="cyan",
        )
    )

    if dry_run:
        console.print(
            Panel.fit(
                "Dry run - skipping version update, build, and publish",
                title="Dry Run",
                style="yellow",
            )
        )
        return

    _update_version_in_file(init_path, current_version, new_version)
    _update_version_in_file(pyproject_path, current_version, new_version)

    console.print(
        Panel.fit(
            f"Updated __init__.py and pyproject.toml to {new_version}",
            title="Version Updated",
            border_style="green",
        )
    )

    console.print(
        Panel.fit(
            "Building package...",
            title="Build",
            border_style="cyan",
        )
    )

    build_result = subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=str(ENGINE_ROOT),
        capture_output=True,
        text=True,
    )

    if build_result.returncode != 0:
        console.print(
            Panel.fit(
                f"Build failed:\n{build_result.stderr}",
                title="Build Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(
            "Build successful",
            title="Build",
            border_style="green",
        )
    )

    if not dist_dir.exists():
        console.print(
            Panel.fit(
                "dist/ directory not found after build",
                title="Publish Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(
            f"Publishing to PyPI...\nVersion: {new_version}",
            title="Publish",
            border_style="cyan",
        )
    )

    env = {"PYPI_API_TOKEN": token} if token else {}
    publish_result = subprocess.run(
        [sys.executable, "-m", "twine", "upload", "--non-interactive", "--disable-progress-bar", "dist/*"],
        cwd=str(ENGINE_ROOT),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), **env},
    )

    if publish_result.returncode != 0:
        console.print(
            Panel.fit(
                f"Publish failed:\n{publish_result.stderr}",
                title="Publish Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(
            f"Successfully published autobot-swarm {new_version} to PyPI!\n\n"
            f"Install with: pip install autobot-swarm=={new_version}",
            title="Published",
            border_style="green",
        )
    )


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = argv or sys.argv[1:]
    if not args:
        run_list()
        return 0

    global VERBOSE
    VERBOSE = "--verbose" in args
    args = [a for a in args if a != "--verbose"]

    console = Console()

    try:
        config = load_config()
        config.apply_env_vars()
    except Exception:
        pass

    command = args[0]
    try:
        if command == "init":
            run_init(args)
        elif command == "plan":
            run_plan(args)
        elif command == "run":
            run_run(args)
        elif command == "resume":
            run_resume(args)
        elif command == "status":
            run_status(args)
        elif command == "engage":
            run_engage()
        elif command == "validate-models":
            run_validate_models()
        elif command == "publish":
            run_publish(args)
        elif command == "undo":
            run_undo(args)
        elif command == "snapshots":
            run_snapshots(args)
        elif command == "catalog":
            run_catalog(args)
        elif command == "doctor":
            run_doctor(args)
        elif command == "diff":
            run_diff(args)
        elif command == "logs":
            run_logs(args)
        elif command == "explain":
            run_explain(args)
        elif command == "stats":
            run_stats(args)
        elif command == "config":
            run_config(args)
        elif command == "completions":
            run_completions(args)
        elif command == "marketplace":
            run_marketplace(args)
        elif command == "dashboard":
            run_dashboard(args)
        elif command == "list":
            run_list()
        else:
            run_list()
            return 1
    except KeyboardInterrupt:
        return _graceful_interrupt(console)
    except EOFError:
        return _graceful_interrupt(console)
    except Exception as exc:
        return _handle_error(console, exc, command)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
