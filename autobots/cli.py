from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from traceback import format_exc

from dotenv import dotenv_values
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .bootstrap import CORE_CONTEXT_FILES, detect_repo_profile, initialize_context
from .catalog import ClusterCatalog
from .config import AutobotsConfig, load_config
from .planning import PlanArtifacts, write_plan
from .router import AutobotRouter, ExecutionResult, PhaseRecord
from .workspace import TargetProjectWorkspace
from .executor import AutonomyEngine, ExecutionMode, parse_mode_from_string


ENGINE_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ENV_PATH = ENGINE_ROOT / ".env"
SAFETY_BRANCH = "autobots-safety"
ROLLOUT_MESSAGE = "Autobots, Roll out!"


def _detect_git_branch(target_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=target_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    branch = result.stdout.strip()
    return branch or None


def _find_sibling_projects() -> list[Path]:
    return sorted(
        [
            path
            for path in ENGINE_ROOT.parent.iterdir()
            if path.is_dir() and path.name != ENGINE_ROOT.name
        ],
        key=lambda item: item.name.lower(),
    )


def _read_menu_key() -> str:
    try:
        import msvcrt
    except ImportError:
        import termios
        import tty

        fd = sys.stdin.fileno()
        original = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            first = sys.stdin.read(1)
            if first == "\x1b":
                second = sys.stdin.read(1)
                third = sys.stdin.read(1)
                if second == "[" and third == "A":
                    return "up"
                if second == "[" and third == "B":
                    return "down"
            if first in {"\r", "\n"}:
                return "enter"
            if first == "\x03":
                raise KeyboardInterrupt
            return ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, original)

    first = msvcrt.getwch()
    if first in {"\x00", "\xe0"}:
        second = msvcrt.getwch()
        if second == "H":
            return "up"
        if second == "P":
            return "down"
        return ""
    if first == "\r":
        return "enter"
    if first == "\x03":
        raise KeyboardInterrupt
    return ""


def _render_menu(message: str, choices: list[str], selected_index: int) -> Group:
    items: list[Text] = [Text(message, style="bold blue"), Text("")]
    for index, choice in enumerate(choices):
        prefix = "› " if index == selected_index else "  "
        style = "bold red" if index == selected_index else ""
        items.append(Text(f"{prefix}{choice}", style=style))
    items.append(Text(""))
    items.append(Text("Use ↑/↓ to choose and Enter to confirm.", style="dim"))
    return Group(*items)


def _select(
    console: Console,
    message: str,
    choices: list[str],
    default: str | None = None,
) -> str:
    if not choices:
        raise ValueError("Selection choices cannot be empty.")

    selected_index = choices.index(default) if default in choices else 0
    with Live(
        _render_menu(message, choices, selected_index),
        console=console,
        refresh_per_second=20,
        transient=True,
    ) as live:
        while True:
            key = _read_menu_key()
            if key == "up":
                selected_index = (selected_index - 1) % len(choices)
                live.update(_render_menu(message, choices, selected_index))
            elif key == "down":
                selected_index = (selected_index + 1) % len(choices)
                live.update(_render_menu(message, choices, selected_index))
            elif key == "enter":
                choice = choices[selected_index]
                console.print(f"{message}\n[cyan]{choice}[/cyan]")
                return choice


def _text(message: str, default: str | None = None) -> str:
    if default is None:
        return Prompt.ask(message).strip()
    return Prompt.ask(message, default=default).strip()


def _password(message: str) -> str:
    return Prompt.ask(message, password=True).strip()


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


def _resolve_target_project(console: Console) -> Path:
    sibling_projects = _find_sibling_projects()
    sibling_hint = ", ".join(project.name for project in sibling_projects) or "none detected"

    location_mode = _select(
        console,
        f"Where is the target project located? Detected siblings: {sibling_hint}",
        choices=[
            "Sibling directory of autobots",
            "Parent folder of autobots",
            "Custom absolute path",
        ],
        default="Sibling directory of autobots" if sibling_projects else "Parent folder of autobots",
    )

    if location_mode == "Sibling directory of autobots":
        if sibling_projects:
            project_name = _select(
                console,
                "Choose the sibling target project",
                choices=[project.name for project in sibling_projects],
                default=sibling_projects[0].name,
            )
        else:
            project_name = _text("Enter the sibling directory name")
        target_root = (ENGINE_ROOT.parent / project_name).expanduser().resolve()
    elif location_mode == "Parent folder of autobots":
        target_root = ENGINE_ROOT.parent.resolve()
    else:
        target_root = Path(
            _text("Enter the absolute path to the target project")
        ).expanduser().resolve()

    if not target_root.exists() or not target_root.is_dir():
        raise FileNotFoundError(f"Target project not found: {target_root}")

    console.print(
        Panel.fit(
            f"Target workspace mapped to:\n{target_root}",
            title="Workspace",
            border_style="cyan",
        )
    )
    return target_root


def _resolve_target_project_from_args(console: Console, args: list[str]) -> Path:
    if len(args) > 1:
        target_root = Path(args[1]).expanduser().resolve()
        if not target_root.exists() or not target_root.is_dir():
            raise FileNotFoundError(f"Target project not found: {target_root}")
        console.print(
            Panel.fit(
                f"Target workspace mapped to:\n{target_root}",
                title="Workspace",
                border_style="cyan",
            )
        )
        return target_root
    return _resolve_target_project(console)


def _require_safety_branch(console: Console, target_root: Path) -> None:
    current_branch = _detect_git_branch(target_root)
    detected = current_branch or "unknown"

    branch_choice = _select(
        console,
        f"Safety branch check for '{SAFETY_BRANCH}'. Detected current branch: {detected}",
        choices=[
            "Yes, continue",
            "No, stop here",
        ],
        default="Yes, continue" if current_branch == SAFETY_BRANCH else "No, stop here",
    )
    confirmed = branch_choice == "Yes, continue"

    if not confirmed or current_branch != SAFETY_BRANCH:
        console.print(
            Panel.fit(
                "Execution blocked.\n"
                f"Switch the target project to `{SAFETY_BRANCH}` with:\n"
                f"`git checkout -b {SAFETY_BRANCH}`",
                title="Safety Branch Required",
                border_style="red",
            )
        )
        raise SystemExit(1)


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


def _check_six_file_architecture(console: Console, target_root: Path) -> None:
    context_dir = target_root / "context"
    context_files = [path for path in context_dir.iterdir()] if context_dir.exists() else []
    file_count = len([path for path in context_files if path.is_file()])

    architecture_choice = _select(
        console,
        f"6-File Architecture check in {context_dir}. Detected {file_count} files",
        choices=[
            "Yes, continue",
            "No, continue anyway",
        ],
        default="Yes, continue" if file_count >= 6 else "No, continue anyway",
    )
    confirmed = architecture_choice == "Yes, continue"
    if not confirmed:
        console.print(
            Panel.fit(
                "Continuing without the full 6-File Architecture. "
                "Make sure roadmap.md and progress-tracker.md exist in the target context folder.",
                title="Architecture Check",
                border_style="yellow",
            )
        )


def _missing_core_context_files(target_root: Path) -> list[str]:
    context_dir = target_root / "context"
    return [filename for filename in CORE_CONTEXT_FILES if not (context_dir / filename).exists()]


def _require_operational_context(console: Console, target_root: Path, command_name: str) -> None:
    """Require the initialized six-file context architecture for operational commands."""
    missing_files = _missing_core_context_files(target_root)
    if not missing_files:
        return

    console.print(
        Panel.fit(
            "The target project is missing required Autobots context files.\n"
            f"Command: {command_name}\n"
            f"Missing: {', '.join(missing_files)}\n\n"
            f"Run `autobots init {target_root}` first, then regenerate planning with `autobots plan {target_root}`.",
            title="Incomplete Context Setup",
            border_style="red",
        )
    )
    raise SystemExit(1)


def _render_plan(console: Console, result: ExecutionResult) -> None:
    table = Table(title="Hierarchical Cluster Plan")
    table.add_column("Stage")
    table.add_column("Cluster")
    table.add_column("Lead Model")

    table.add_row("Command", "Optimus", result.plan.command_lead.model_id)
    table.add_row("Secretary", "Optimus", result.plan.secretary_lead.model_id)
    table.add_row("Primary", result.plan.primary_cluster, result.plan.primary_lead.model_id)
    table.add_row("Review", "RedAlert", result.plan.safety_lead.model_id)
    table.add_row("Repair", "Ratchet", result.plan.repair_lead.model_id)
    console.print(table)


def _render_registry_summary(console: Console, catalog: ClusterCatalog) -> None:
    source_label = "Live NVIDIA registry" if catalog.using_live_catalog else "Bundled fallback registry"
    summary_lines = [f"{source_label}: {catalog.available_model_count or catalog.model_count} models"]
    if catalog.discovery_error:
        summary_lines.append(f"Discovery fallback: {catalog.discovery_error}")

    console.print(
        Panel.fit(
            "\n".join(summary_lines),
            title="Swarm Registry",
            border_style="cyan",
        )
    )

    table = Table(title="Functional Category Inventory")
    table.add_column("Cluster")
    table.add_column("Role")
    table.add_column("Models")
    for cluster_name, role, count in catalog.cluster_model_counts():
        table.add_row(cluster_name, role, str(count))
    console.print(table)


def _render_stage_event(console: Console, message: str) -> None:
    console.print(f"[bold cyan]Swarm[/bold cyan] {message}")


def _render_phase_panel(console: Console, result: ExecutionResult) -> None:
    if result.files_written:
        changes = "\n".join(f"- {path}" for path in result.files_written)
    else:
        changes = "- No files were written"

    transcript = "\n".join(
        f"[{entry.speaker}] {entry.summary}" for entry in result.journal
    )
    validation_block = ""
    if result.validation_report:
        verdict = "PASS" if result.validation_passed else "FAIL"
        validation_block = (
            f"\n\n[bold]Validation[/bold]\n"
            f"Verdict: {verdict}\n"
            f"Attempts: {result.verification_attempts}\n"
            f"{result.validation_report}"
        )
    console.print(
        Panel(
            f"{result.summary}\n\n[bold]Cluster journal[/bold]\n{transcript}\n\n[bold]Files changed[/bold]\n{changes}{validation_block}",
            title=f"Phase Output - {result.cluster_name}",
            border_style="magenta",
        )
    )


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
        event_handler=lambda message: _render_stage_event(console, message),
    )
    _render_plan(console, result)

    while True:
        _render_phase_panel(console, result)
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
                event_handler=lambda message: _render_stage_event(console, message),
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
            event_handler=lambda message: _render_stage_event(console, message),
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

    target_root = _resolve_target_project(console)
    _require_safety_branch(console, target_root)
    _ensure_api_key(console)
    router = AutobotRouter()
    _render_registry_summary(console, router.catalog)
    _check_six_file_architecture(console, target_root)

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
    console = Console()
    target_root = _resolve_target_project_from_args(console, args)
    workspace = TargetProjectWorkspace(target_root)
    profile = detect_repo_profile(target_root)
    written_paths = initialize_context(workspace, profile)

    table = Table(title="Autobots Init Summary")
    table.add_column("Detected")
    table.add_column("Value")
    table.add_row("Project", profile.project_name)
    table.add_row("Languages", ", ".join(profile.languages))
    table.add_row("Package Managers", ", ".join(profile.package_managers))
    table.add_row("Test Tools", ", ".join(profile.test_tools))
    table.add_row("Source Roots", ", ".join(profile.source_roots))
    console.print(table)

    file_list = "\n".join(f"- {path.name}" for path in written_paths)
    console.print(
        Panel.fit(
            f"Created or refreshed {len(CORE_CONTEXT_FILES)} context files.\n\n{file_list}",
            title="Context Initialized",
            border_style="green",
        )
    )


def run_plan(args: list[str]) -> None:
    console = Console()
    target_root, goal, append, insert_after, dry_run = _parse_plan_args(args)
    target_root = _resolve_target_project_from_args(console, ["plan", target_root] if target_root else ["plan"])
    workspace = TargetProjectWorkspace(target_root)
    profile, scan, artifacts = write_plan(
        workspace,
        goal=goal or None,
        append=append,
        insert_after=insert_after,
        dry_run=dry_run,
    )

    table = Table(title="Autobots Plan Summary")
    table.add_column("Detected")
    table.add_column("Value")
    table.add_row("Project", profile.project_name)
    table.add_row("Goal", goal or "Prepare the next implementation-ready plan")
    table.add_row("Mode", "Append" if append else "Replace")
    table.add_row("Insert After", insert_after or "End of plan")
    table.add_row("Source Roots", ", ".join(scan.source_roots))
    table.add_row("Test Roots", ", ".join(scan.test_roots) or "None detected")
    table.add_row("Build Files", ", ".join(scan.build_files) or "None detected")
    table.add_row("Env Files", ", ".join(scan.env_files) or "None detected")
    table.add_row("Frameworks", ", ".join(scan.frameworks) or "None detected")
    table.add_row("Phases", str(len(artifacts.phases)))
    console.print(table)
    console.print(
        Panel.fit(
            (
                "Generated a planning preview without writing files."
                if dry_run
                else "Updated context/roadmap.md and context/progress-tracker.md for Phase 3 planning."
            ),
            title="Plan Generated",
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
    _render_registry_summary(console, router.catalog)
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


def _parse_run_args(args: list[str]) -> tuple[str | None, ExecutionMode, int, bool]:
    """Parse run command arguments."""
    target_path: str | None = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    mode = ExecutionMode.SUPERVISED
    milestone_threshold = 3
    dry_run = False

    tokens = args[2:] if target_path else args[1:]
    for token in tokens:
        if token == "--dry-run":
            dry_run = True
        elif token == "--autonomous":
            mode = ExecutionMode.AUTONOMOUS
        elif token == "--milestone":
            mode = ExecutionMode.MILESTONE
        elif token == "--supervised":
            mode = ExecutionMode.SUPERVISED

    return target_path, mode, milestone_threshold, dry_run


def run_run(args: list[str]) -> None:
    """Run phases autonomously or in supervised mode."""
    console = Console()
    target_path, mode, milestone_threshold, dry_run = _parse_run_args(args)
    target_root = _resolve_target_project_from_args(console, ["run", target_path] if target_path else ["run"])
    _require_operational_context(console, target_root, "run")

    console.print(
        Panel.fit(
            f"Running phases in {mode.value} mode",
            title="Autobots Run",
            border_style="cyan",
        )
    )

    workspace = TargetProjectWorkspace(target_root)
    engine = AutonomyEngine(mode=mode, api_key=None)

    def event_handler(message: str):
        console.print(f"[bold cyan]Swarm[/bold cyan] {message}")

    result = engine.execute(workspace, mode=mode, milestone_threshold=milestone_threshold, event_handler=event_handler)

    if dry_run:
        console.print(Panel.fit("Dry run - no changes made", title="Preview", border_style="yellow"))
        return

    table = Table(title="Execution Summary")
    table.add_column("Status")
    table.add_column("Phases Completed")
    table.add_row(result.status, str(len(result.phases_completed)))
    console.print(table)

    if result.phases_completed:
        completed_list = "\n".join(f"- {phase}" for phase in result.phases_completed)
        console.print(Panel.fit(completed_list, title="Completed Phases", border_style="green"))

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

    if result.status == "approval_required":
        console.print(
            Panel.fit(
                f"Approval required before phase: {result.current_phase}",
                title="Approval Gate",
                border_style="yellow",
            )
        )


def run_resume(args: list[str]) -> None:
    """Resume from a checkpoint."""
    console = Console()
    target_path = args[1] if len(args) > 1 else None
    target_root = _resolve_target_project_from_args(console, ["resume", target_path] if target_path else ["resume"])
    _require_operational_context(console, target_root, "resume")

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
    """Show current execution status."""
    console = Console()
    target_path = args[1] if len(args) > 1 else None
    target_root = _resolve_target_project_from_args(console, ["status", target_path] if target_path else ["status"])
    _require_operational_context(console, target_root, "status")

    workspace = TargetProjectWorkspace(target_root)
    from .executor import ExecutionModeManager, StateManager

    mode_manager = ExecutionModeManager()
    checkpoint = mode_manager.load_checkpoint(target_root)
    state_manager = StateManager(target_root)
    session = state_manager.get_session()
    stats = state_manager.get_session_stats()

    if session:
        table = Table(title="Session Status")
        table.add_column("Property")
        table.add_column("Value")
        table.add_row("Session ID", session.session_id)
        table.add_row("Mode", session.mode)
        table.add_row("State", session.state)
        table.add_row("Phases Completed", str(len(session.phases_completed)))
        table.add_row("Files Changed", str(session.total_files_changed))
        table.add_row("Audit Entries", str(stats.get("audit_entries", 0)))
        if session.current_phase:
            table.add_row("Current Phase", session.current_phase)
        console.print(table)

    if checkpoint:
        table = Table(title="Checkpoint Status")
        table.add_column("Property")
        table.add_column("Value")
        table.add_row("Session ID", checkpoint.session_id)
        table.add_row("Mode", checkpoint.mode)
        table.add_row("Current Phase", f"{checkpoint.current_phase_index + 1}: {checkpoint.current_phase_title}")
        table.add_row("Phases Completed", str(len(checkpoint.phases_completed)))
        table.add_row("State", checkpoint.state)
        console.print(table)

        if checkpoint.phases_completed:
            completed_list = "\n".join(f"- {phase}" for phase in checkpoint.phases_completed)
            console.print(Panel.fit(completed_list, title="Completed Phases", border_style="green"))

        console.print(
            Panel.fit(
                f"Run 'autobots resume' to continue from this checkpoint",
                title="Resume Available",
                border_style="cyan",
            )
        )
    else:
        router = AutobotRouter()
        roadmap_text, progress_text = router.read_phase_documents(workspace)
        phases = router.find_next_phase(progress_text)

        if phases:
            console.print(Panel.fit("No checkpoint found but phases are pending. Run 'autobots run' to start.", title="Status", border_style="yellow"))
        else:
            console.print(Panel.fit("No checkpoint found. All phases are complete.", title="Status", border_style="green"))


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args:
        Console().print("Usage: autobots <init|plan|run|resume|status|engage|validate-models> [options]")
        return 1

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
        else:
            Console().print("Usage: autobots <init|plan|run|resume|status|engage|validate-models> [options]")
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
