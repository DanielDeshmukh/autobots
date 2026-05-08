from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .router import AutobotRouter, ExecutionResult, PhaseRecord
from .workspace import TargetProjectWorkspace


ENGINE_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ENV_PATH = ENGINE_ROOT / ".env"
SAFETY_BRANCH = "autobots-safety"


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


def _resolve_target_project(console: Console) -> Path:
    sibling_projects = _find_sibling_projects()
    sibling_hint = ", ".join(project.name for project in sibling_projects) or "none detected"

    is_sibling = Confirm.ask(
        f"Is the target project a sibling directory? Detected siblings: {sibling_hint}",
        default=bool(sibling_projects),
    )

    if is_sibling:
        project_name = Prompt.ask("Enter the sibling directory name")
        target_root = (ENGINE_ROOT.parent / project_name).expanduser().resolve()
    else:
        target_root = Path(
            Prompt.ask("Enter the absolute path to the target project")
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


def _require_safety_branch(console: Console, target_root: Path) -> None:
    current_branch = _detect_git_branch(target_root)
    detected = current_branch or "unknown"

    confirmed = Confirm.ask(
        f"Is the target project on the safety branch '{SAFETY_BRANCH}'? Detected current branch: {detected}",
        default=current_branch == SAFETY_BRANCH,
    )

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

    api_key = Prompt.ask("Enter your NVIDIA_API_KEY", password=True).strip()
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

    confirmed = Confirm.ask(
        f"Does the target include the 6-File Architecture in {context_dir}? Detected {file_count} files",
        default=file_count >= 6,
    )
    if not confirmed:
        console.print(
            Panel.fit(
                "Continuing without the full 6-File Architecture. "
                "Make sure roadmap.md and progress-tracker.md exist in the target context folder.",
                title="Architecture Check",
                border_style="yellow",
            )
        )


def _render_plan(console: Console, result: ExecutionResult) -> None:
    table = Table(title="Hierarchical Cluster Plan")
    table.add_column("Stage")
    table.add_column("Cluster")
    table.add_column("Lead Model")

    table.add_row("Command", "Optimus", result.plan.command_lead.model_id)
    table.add_row("Primary", result.plan.primary_cluster, result.plan.primary_lead.model_id)
    table.add_row("Review", "RedAlert", result.plan.safety_lead.model_id)
    table.add_row("Repair", "Ratchet", result.plan.repair_lead.model_id)
    console.print(table)


def _render_phase_panel(console: Console, result: ExecutionResult) -> None:
    if result.files_written:
        changes = "\n".join(f"- {path}" for path in result.files_written)
    else:
        changes = "- No files were written"

    transcript = "\n".join(
        f"[{entry.speaker}] {entry.summary}" for entry in result.journal
    )
    console.print(
        Panel(
            f"{result.summary}\n\n[bold]Cluster journal[/bold]\n{transcript}\n\n[bold]Files changed[/bold]\n{changes}",
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
    result = router.execute_phase(workspace, phase, roadmap_text, progress_text)
    _render_plan(console, result)

    while True:
        _render_phase_panel(console, result)
        decision = Prompt.ask(
            "Are you satisfied with this phase output? (y/n/feedback)",
            default="y",
        ).strip()

        lowered = decision.lower()
        if lowered == "y":
            updated_progress = router.mark_phase_complete(progress_text, phase)
            workspace.write_context_file("progress-tracker.md", updated_progress)
            console.print(
                Panel.fit(
                    f"Marked '{phase.title}' as COMPLETE.",
                    title="Progress Tracker Updated",
                    border_style="green",
                )
            )
            return

        feedback = "" if lowered == "n" else decision
        result = router.refine_with_ratchet(
            workspace=workspace,
            phase=phase,
            roadmap_text=roadmap_text,
            progress_text=progress_text,
            previous_result=result,
            feedback=feedback,
        )


def run_engage() -> None:
    console = Console()
    router = AutobotRouter()
    console.print(
        Panel.fit(
            "Autobots Engage uses a package-based CLI, a scalable cluster registry, "
            "and hierarchical model handoffs for target-project coding.",
            title="Autobots Engage",
            border_style="blue",
        )
    )
    console.print(
        Panel.fit(
            f"Built-in clustered models: {router.catalog.model_count}\n"
            "Add more models with AUTOBOTS_MODEL_REGISTRY to scale beyond the bundled catalog.",
            title="Swarm Registry",
            border_style="cyan",
        )
    )

    target_root = _resolve_target_project(console)
    _require_safety_branch(console, target_root)
    _ensure_api_key(console)
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


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args or args[0] != "engage":
        Console().print("Usage: autobots engage")
        return 1

    run_engage()
    return 0

