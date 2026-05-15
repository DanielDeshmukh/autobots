from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

ConsoleInstance = Console()


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


def render_plan(console: Console, result) -> None:
    from .router import ExecutionResult
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


def render_registry_summary(console: Console, catalog) -> None:
    from .catalog import ClusterCatalog
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


def render_stage_event(console: Console, message: str) -> None:
    console.print(f"[bold cyan]Swarm[/bold cyan] {message}")


def render_phase_panel(console: Console, result) -> None:
    from .router import ExecutionResult
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


def render_session_status(console: Console, session, checkpoint, stats) -> None:
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


def render_execution_result(console: Console, result) -> None:
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


def render_model_validation_report(console: Console, rows: list, report_path: Path) -> None:
    table = Table(title="Model Contract Validation")
    table.add_column("Stage")
    table.add_column("Model")
    table.add_column("Validated Fields")
    for stage_name, model_id, payload in rows:
        table.add_row(stage_name, model_id, ", ".join(sorted(payload.keys())))
    console.print(table)
    console.print(
        Panel.fit(
            f"Validated live model responses successfully.\nSaved report to:\n{report_path}",
            title="Validation Complete",
            border_style="green",
        )
    )