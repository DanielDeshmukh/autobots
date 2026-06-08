from __future__ import annotations

import subprocess
from pathlib import Path

from .bootstrap import CORE_CONTEXT_FILES
from .context_gen import format_missing_context_files
from .ui import _select, _text, ConsoleInstance

ENGINE_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ENV_PATH = ENGINE_ROOT / ".env"
SAFETY_BRANCH = "autobots-safety"


def detect_git_branch(target_root: Path) -> str | None:
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


def find_sibling_projects() -> list[Path]:
    candidates: list[Path] = []

    for parent in [ENGINE_ROOT.parent, Path.cwd().parent]:
        if not parent.exists():
            continue
        try:
            for path in parent.iterdir():
                if path.is_dir() and path.name != ENGINE_ROOT.name and not path.name.startswith("."):
                    if path not in candidates:
                        candidates.append(path)
        except (PermissionError, OSError):
            pass

    return sorted(candidates, key=lambda item: item.name.lower())


def resolve_target_project(console) -> Path:
    sibling_projects = find_sibling_projects()
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
        cwd = Path.cwd().resolve()
        if cwd.name == "Lib" and cwd.parent.name == ".venv":
            target_root = cwd.parent.parent.resolve()
        else:
            target_root = cwd
    else:
        target_root = Path(
            _text("Enter the absolute path to the target project")
        ).expanduser().resolve()

    if not target_root.exists() or not target_root.is_dir():
        raise FileNotFoundError(f"Target project not found: {target_root}")

    from rich.panel import Panel
    console.print(
        Panel.fit(
            f"Target workspace mapped to:\n{target_root}",
            title="Workspace",
            border_style="cyan",
        )
    )
    return target_root


def resolve_target_project_from_args(console, args: list) -> Path:
    if len(args) > 1:
        target_root = Path(args[1]).expanduser().resolve()
        if not target_root.exists() or not target_root.is_dir():
            raise FileNotFoundError(f"Target project not found: {target_root}")
        from rich.panel import Panel
        console.print(
            Panel.fit(
                f"Target workspace mapped to:\n{target_root}",
                title="Workspace",
                border_style="cyan",
            )
        )
        return target_root
    return resolve_target_project(console)


def require_safety_branch(console, target_root: Path) -> None:
    current_branch = detect_git_branch(target_root)
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
        from rich.panel import Panel
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


def missing_core_context_files(target_root: Path) -> list[str]:
    context_dir = target_root / "context"
    return [filename for filename in CORE_CONTEXT_FILES if not (context_dir / filename).exists()]


def require_operational_context(console, target_root: Path, command_name: str) -> None:
    """Require target-owned context files for operational commands."""
    missing_files = missing_core_context_files(target_root)
    if not missing_files:
        return

    from rich.panel import Panel
    console.print(
        Panel.fit(
            "The target project is missing required Autobots context files.\n"
            f"Command: {command_name}\n"
            "Create these files in the target project's context folder:\n"
            f"{format_missing_context_files(missing_files)}",
            title="Incomplete Context Setup",
            border_style="red",
        )
    )
    raise SystemExit(1)
