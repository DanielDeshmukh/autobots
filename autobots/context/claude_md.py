from __future__ import annotations

from pathlib import Path


def load_claude_md(start_dir: str | Path | None = None) -> str:
    parts = []
    visited: set[str] = set()

    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)

    current = start_dir.resolve()
    parents = [current] + list(current.parents)

    for directory in parents:
        claude_file = directory / "CLAUDE.md"
        key = str(claude_file)
        if key not in visited and claude_file.exists():
            visited.add(key)
            try:
                content = claude_file.read_text(encoding="utf-8")
                parts.append(f"# From {claude_file}\n\n{content}")
            except OSError:
                pass

    return "\n\n---\n\n".join(parts) if parts else ""
