"""File mention picker — @files inline fuzzy search."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.text import Text

from .theme import Theme, load_theme


def render_file_mention_picker(
    console: Console,
    *,
    query: str = "",
    matches: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render the file mention picker.
    
    Format:
    > Explain how refresh tokens work in @auth
    
      Files
    > src/api/routes/auth.py
      src/services/auth.py
      tests/test_auth.py
      context/security-auth.md
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [dim {theme.secondary}]Files[/]")
    
    if matches:
        for i, match in enumerate(matches):
            is_first = i == 0
            path = match.get("path", "")
            file_type = match.get("type", "")
            
            line = Text()
            if is_first:
                line.append(f"> ", style=f"bold {theme.brand}")
            else:
                line.append(f"  ", style=f"dim {theme.secondary}")
            
            line.append(path, style=f"{theme.path}")
            
            if file_type:
                line.append(f"  ({file_type})", style=f"dim {theme.secondary}")
            
            console.print(line)
    else:
        console.print(f"  [dim {theme.secondary}]No matches found[/]")
    
    console.print()


def search_files(
    root: Path,
    query: str,
    max_results: int = 8,
    ignore_gitignore: bool = True,
) -> list[dict]:
    """Search for files matching a query.
    
    Returns list of dicts with path, type, and score.
    """
    results = []
    query_lower = query.lower()
    
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        
        # Skip hidden and gitignored
        relative = path.relative_to(root)
        parts = relative.parts
        
        if any(p.startswith(".") for p in parts):
            continue
        if "node_modules" in parts:
            continue
        if ignore_gitignore and any(p == "dist" or p == "build" for p in parts):
            continue
        
        # Score
        name_lower = path.name.lower()
        rel_lower = str(relative).lower()
        
        score = 0
        if query_lower in name_lower:
            score += 10
            if name_lower.startswith(query_lower):
                score += 5
        if query_lower in rel_lower:
            score += 3
        
        if score > 0:
            # Determine file type
            ext = path.suffix.lower()
            file_type = {
                ".py": "Python",
                ".js": "JavaScript",
                ".ts": "TypeScript",
                ".tsx": "React",
                ".jsx": "React",
                ".css": "CSS",
                ".html": "HTML",
                ".json": "JSON",
                ".md": "Markdown",
                ".yaml": "YAML",
                ".yml": "YAML",
                ".toml": "TOML",
                ".sh": "Shell",
                ".go": "Go",
                ".rs": "Rust",
                ".java": "Java",
            }.get(ext, ext.lstrip(".").upper() if ext else "")
            
            results.append({
                "path": str(relative),
                "type": file_type,
                "score": score,
            })
    
    # Sort by score descending, return top N
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]
