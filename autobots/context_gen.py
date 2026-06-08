from __future__ import annotations

from pathlib import Path

from .bootstrap import CORE_CONTEXT_FILES


def format_missing_context_files(missing_files: list[str] | tuple[str, ...]) -> str:
    return "\n".join(f"- {filename}" for filename in missing_files)


def check_six_file_architecture(console, target_root: Path) -> bool:
    from rich.panel import Panel

    context_dir = target_root / "context"
    missing_files = [filename for filename in CORE_CONTEXT_FILES if not (context_dir / filename).exists()]

    if not missing_files:
        console.print(
            Panel.fit(
                f"Context files detected in {context_dir}.",
                title="Context Check",
                border_style="green",
            )
        )
        return True

    console.print(
        Panel.fit(
            "Autobots did not find the target project's context files.\n\n"
            "Create these files in the target project's context folder:\n"
            f"{format_missing_context_files(missing_files)}",
            title="Context Files Missing",
            border_style="yellow",
        )
    )
    return False
