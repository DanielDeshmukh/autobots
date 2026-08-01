"""Swarm execution view — compact and expanded cluster status."""

from __future__ import annotations

from rich.console import Console, Group
from rich.text import Text

from ..theme import Theme, load_theme
from ..symbols import get_symbols, Symbols


# ─── Cluster Definitions ─────────────────────────────────────────────────────

CLUSTERS = {
    "Optimus":     {"role": "Planning and routing",     "color": "#E25555"},
    "UltraMagnus": {"role": "Backend and architecture", "color": "#68AEE8"},
    "Jazz":        {"role": "Frontend and visual work",  "color": "#A78BFA"},
    "RedAlert":    {"role": "Security and safety",       "color": "#F87171"},
    "Ratchet":     {"role": "Debugging and repair",      "color": "#34D399"},
    "Perceptor":   {"role": "Retrieval and parsing",     "color": "#FBBF24"},
    "Bumblebee":   {"role": "Communication and media",   "color": "#FCD34D"},
    "Ironhide":    {"role": "Simulation and safety",     "color": "#9CA3AF"},
    "Wheeljack":   {"role": "Scientific work",           "color": "#22D3EE"},
}


# ─── Compact View ────────────────────────────────────────────────────────────

def render_swarm_compact(
    console: Console,
    *,
    task_name: str,
    elapsed: str = "",
    clusters: list[dict] = None,
    active_count: int = 0,
    completed_count: int = 0,
    theme: Theme | None = None,
) -> None:
    """Render compact swarm execution view.
    
    Format:
    ● Implementing refresh-token rotation                    1m 42s
      ├─ UltraMagnus  Token architecture                    done
      ├─ RedAlert     Rotation and replay safety            reviewing
      ├─ Ratchet      Test integration                      running
      └─ Optimus      Coordinating dependencies             waiting
    
      2 active · 2 completed · Esc to interrupt
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    # Header
    header = Text()
    header.append(f"{symbols.active} ", style=f"{theme.active}")
    header.append(task_name, style=f"bold {theme.primary}")
    if elapsed:
        padding = max(1, 60 - len(task_name))
        header.append(" " * padding, style=f"dim {theme.secondary}")
        header.append(elapsed, style=f"dim {theme.secondary}")
    console.print(header)
    
    # Cluster rows
    if clusters:
        for i, cluster in enumerate(clusters):
            is_last = i == len(clusters) - 1
            connector = symbols.last if is_last else symbols.branch
            
            name = cluster.get("name", "")
            task = cluster.get("task", "")
            status = cluster.get("status", "waiting")
            
            # Status style
            status_style = {
                "done":     f"{theme.success}",
                "active":   f"{theme.active}",
                "running":  f"{theme.active}",
                "reviewing": f"{theme.warning}",
                "waiting":  f"{theme.secondary}",
                "error":    f"{theme.error}",
            }.get(status, f"{theme.secondary}")
            
            status_icon = {
                "done":     symbols.done,
                "active":   symbols.active,
                "running":  symbols.active,
                "reviewing": symbols.warning,
                "waiting":  symbols.waiting,
                "error":    symbols.failed,
            }.get(status, symbols.waiting)
            
            line = Text()
            line.append(f"  {connector} ", style=f"dim {theme.secondary}")
            
            # Cluster name with role color
            color = CLUSTERS.get(name, {}).get("color", theme.primary)
            line.append(f"{name}", style=f"bold {color}")
            
            # Task description
            if task:
                padding = max(1, 30 - len(name))
                line.append(" " * padding, style=f"dim {theme.secondary}")
                line.append(task, style=f"{theme.secondary}")
            
            # Status
            padding2 = max(1, 55 - len(name) - len(task) - 2)
            line.append(" " * padding2, style=f"dim {theme.secondary}")
            line.append(f"{status_icon} {status}", style=status_style)
            
            console.print(line)
    
    console.print()
    
    # Summary
    summary = Text()
    summary.append("  ", style=f"dim {theme.secondary}")
    if active_count:
        summary.append(f"{active_count} active", style=f"{theme.active}")
    if completed_count:
        if active_count:
            summary.append(" · ", style=f"dim {theme.secondary}")
        summary.append(f"{completed_count} completed", style=f"{theme.success}")
    summary.append(" · Esc to interrupt", style=f"dim {theme.secondary}")
    console.print(summary)
    console.print()


# ─── Expanded View ───────────────────────────────────────────────────────────

def render_swarm_expanded(
    console: Console,
    *,
    task_name: str,
    elapsed: str = "",
    clusters: list[dict] = None,
    theme: Theme | None = None,
) -> None:
    """Render expanded swarm execution view with tool details.
    
    Format:
    ● Implementing refresh-token rotation                    1m 42s
      ├─ UltraMagnus  Token architecture
      │  ├─ Read src/services/tokens.py
      │  ├─ Added src/services/token_store.py              +86
      │  ├─ Updated src/services/tokens.py                 +47 -8
      │  └─ Completed in 48s
      │
      ├─ RedAlert  Rotation and replay safety
      │  ├─ Read src/api/routes/auth.py
      │  └─ Reviewing token invalidation behavior
      │
      └─ Optimus  Coordination
         └─ Waiting for validation results
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    # Header
    header = Text()
    header.append(f"{symbols.active} ", style=f"{theme.active}")
    header.append(task_name, style=f"bold {theme.primary}")
    if elapsed:
        padding = max(1, 60 - len(task_name))
        header.append(" " * padding, style=f"dim {theme.secondary}")
        header.append(elapsed, style=f"dim {theme.secondary}")
    console.print(header)
    
    # Cluster rows with details
    if clusters:
        for i, cluster in enumerate(clusters):
            is_last_cluster = i == len(clusters) - 1
            cluster_connector = symbols.last if is_last_cluster else symbols.branch
            
            name = cluster.get("name", "")
            task = cluster.get("task", "")
            tools = cluster.get("tools", [])
            status = cluster.get("status", "waiting")
            
            color = CLUSTERS.get(name, {}).get("color", theme.primary)
            
            # Cluster header
            line = Text()
            line.append(f"  {cluster_connector} ", style=f"dim {theme.secondary}")
            line.append(f"{name}", style=f"bold {color}")
            if task:
                line.append(f"  {task}", style=f"{theme.secondary}")
            console.print(line)
            
            # Tool details
            for j, tool in enumerate(tools):
                is_last_tool = j == len(tools) - 1 and is_last_cluster
                tool_connector = symbols.last if is_last_tool else symbols.branch
                pipe = "  " if is_last_cluster else f"  {symbols.pipe}"
                
                tool_line = Text()
                action = tool.get("action", "")
                path = tool.get("path", "")
                detail = tool.get("detail", "")
                stat = tool.get("stat", "")
                
                tool_line.append(f"{pipe}{tool_connector} ", style=f"dim {theme.secondary}")
                tool_line.append(f"{action} ", style=f"{theme.primary}")
                tool_line.append(path, style=f"{theme.path}")
                
                if stat:
                    tool_line.append(f"  {stat}", style=f"dim {theme.secondary}")
                elif detail:
                    tool_line.append(f"  {detail}", style=f"dim {theme.secondary}")
                
                console.print(tool_line)
    
    console.print()
