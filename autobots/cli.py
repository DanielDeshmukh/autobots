from __future__ import annotations

import json
import sys
import tempfile
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
from .selectors import (
    resolve_target_project,
    resolve_target_project_from_args as _resolve_target_project_from_args,
    require_safety_branch,
    require_operational_context,
    missing_core_context_files,
    detect_git_branch,
)
from .context_gen import check_six_file_architecture, format_missing_context_files
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
    ConsoleInstance,
)


ENGINE_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ENV_PATH = ENGINE_ROOT / ".env"
SAFETY_BRANCH = "autobots-safety"
ROLLOUT_MESSAGE = "Autobots, Roll out!"


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


def _ensure_api_key(console: Console) -> None:
    env_values = dotenv_values(ENGINE_ENV_PATH)
    existing_key = (env_values.get("NVIDIA_API_KEY") or "").strip()
    if existing_key:
        return

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
    console = Console()
    console.print(
        Panel.fit(
            "Autobots Engage uses a package-based CLI, a scalable cluster registry, "
            "and hierarchical model handoffs for target-project coding.",
            title="Autobots Engage",
            border_style="blue",
        )
    )

    target_root = resolve_target_project(console)
    require_safety_branch(console, target_root)
    _ensure_api_key(console)
    router = AutobotRouter()
    render_registry_summary(console, router.catalog)
    if not check_six_file_architecture(console, target_root):
        raise SystemExit(1)

    workspace = TargetProjectWorkspace(target_root)
    while True:
        roadmap_text, progress_text = router.read_phase_documents(workspace)
        phase = router.find_next_phase(progress_text)

        if phase is None:
            console.print(
                Panel.fit(
                    "No IN_PROGRESS or PENDING phases remain. The target roadmap is fully processed.",
                    title="All Phases Complete",
                    border_style="green",
                )
            )
            return

        console.print(
            Panel.fit(
                f"Active phase: {phase.title}\nStatus: {phase.status}",
                title="Phase Dispatch",
                border_style="cyan",
            )
        )
        _approval_loop(console, router, workspace, phase, roadmap_text, progress_text)


def run_init(args: list[str]) -> None:
    """Check context files for a target project."""
    console = Console()

    # Auto-detect target: use provided path, or default to current directory
    if len(args) > 1 and not args[1].startswith("--"):
        target_root = Path(args[1]).expanduser().resolve()
        tokens = args[2:]
    else:
        target_root = Path.cwd().resolve()
        tokens = args[1:]

    if not target_root.exists() or not target_root.is_dir():
        console.print(
            Panel.fit(
                f"Target project not found: {target_root}",
                title="Init Error",
                border_style="red",
            )
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(
            f"Checking context in:\n{target_root}",
            title="Workspace",
            border_style="cyan",
        )
    )

    profile = detect_repo_profile(target_root)

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
            f"{format_missing_context_files(missing_files)}"
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
    router = AutobotRouter()
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

    console.print(
        Panel.fit(
            "Resuming from checkpoint",
            title="Autobots Resume",
            border_style="cyan",
        )
    )

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
    """Show current task and phase status from task-registry.json."""
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

    console.print(
        Panel.fit(f"Status for:\n{target_root}", title="Autobots Status", border_style="cyan")
    )

    phases_status = get_all_phases_status(str(target_root))

    if not phases_status:
        console.print(
            Panel.fit("No tasks planned. Run 'autobots plan' first.", title="Status", border_style="yellow")
        )
        return

    phases_table = Table(title="Phase Overview")
    phases_table.add_column("Phase", style="cyan")
    phases_table.add_column("Name")
    phases_table.add_column("Status")
    phases_table.add_column("Progress")

    for phase in phases_status:
        status_icon = {
            "complete": "[green][x][/green]",
            "in_progress": "[yellow][*][/yellow]",
            "failed": "[red][!][/red]",
            "pending": "[ ]",
        }.get(phase["status"], "[ ]")

        progress = f"{phase['completed']}/{phase['total']}"
        phases_table.add_row(
            phase["phase_id"],
            phase["phase_name"],
            status_icon,
            progress,
        )

    console.print(phases_table)

    for phase in phases_status:
        if phase["status"] in ("in_progress", "pending"):
            tasks = phase.get("tasks", [])
            if tasks:
                tasks_table = Table(title=f"Tasks: {phase['phase_id']} - {phase['phase_name']}")
                tasks_table.add_column("Task ID", style="cyan")
                tasks_table.add_column("Description")
                tasks_table.add_column("Status")
                tasks_table.add_column("Cluster")

                for task in tasks:
                    task_status_icon = {
                        "pending": "[ ]",
                        "active": "[*]",
                        "completed": "[x]",
                        "failed": "[!]",
                    }.get(task.get("status", "pending"), "[ ]")

                    tasks_table.add_row(
                        task.get("task_id", ""),
                        task.get("description", "")[:50],
                        task_status_icon,
                        task.get("cluster", "") or "-",
                    )

                console.print(tasks_table)


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
        ("validate-models", "Test live model contracts and validate API connectivity"),
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


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args:
        run_list()
        return 0

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
