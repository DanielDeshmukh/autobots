"""Status screen — compact diagnostic summary."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme


def render_status(
    console: Console,
    *,
    project_dir: str = "",
    branch: str = "",
    workspace_modified: int = 0,
    workspace_untracked: int = 0,
    snapshot: str = "",
    mode: str = "supervised",
    profile: str = "balanced",
    context_pct: float = 0.0,
    cost: str = "",
    duration: str = "",
    api_connected: bool = True,
    mcp_connected: int = 0,
    mcp_total: int = 0,
    hooks_enabled: int = 0,
    context_files: int = 0,
    phase: str = "",
    agents_active: int = 0,
    agents_completed: int = 0,
    validation: str = "",
    theme: Theme | None = None,
) -> None:
    """Render the status screen.
    
    Format:
    Autobots status
    
      Project
      Directory       ~/code/memory-card-flip
      Branch          autobots-safety
      Workspace       4 modified · 2 untracked
      Snapshot        01JAB92M
    
      Session
      Mode            supervised
      Profile         balanced
      Context         42% used
      Cost            $0.18 estimated
      Duration        4m 18s
    
      Integrations
      NVIDIA NIM      connected
      MCP             2 of 2 connected
      Hooks           3 enabled
      Context files   6 loaded
    
      Run
      Phase           Validate
      Agents          2 active · 3 completed
      Validation      43 tests passed
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Autobots status[/]")
    console.print()
    
    # Project section
    console.print(f"  [dim {theme.secondary}]Project[/]")
    if project_dir:
        console.print(f"  [dim]Directory[/]       {project_dir}")
    if branch:
        console.print(f"  [dim]Branch[/]          {branch}")
    if workspace_modified or workspace_untracked:
        parts = []
        if workspace_modified:
            parts.append(f"{workspace_modified} modified")
        if workspace_untracked:
            parts.append(f"{workspace_untracked} untracked")
        console.print(f"  [dim]Workspace[/]       {' · '.join(parts)}")
    if snapshot:
        console.print(f"  [dim]Snapshot[/]        {snapshot}")
    console.print()
    
    # Session section
    console.print(f"  [dim {theme.secondary}]Session[/]")
    console.print(f"  [dim]Mode[/]            {mode}")
    console.print(f"  [dim]Profile[/]         {profile}")
    
    if context_pct:
        if context_pct >= 80:
            ctx_style = f"{theme.error}"
        elif context_pct >= 50:
            ctx_style = f"{theme.warning}"
        else:
            ctx_style = f"{theme.success}"
        console.print(f"  [dim]Context[/]         [{ctx_style}]{context_pct:.0f}% used[/]")
    
    if cost:
        console.print(f"  [dim]Cost[/]            {cost} estimated")
    if duration:
        console.print(f"  [dim]Duration[/]        {duration}")
    console.print()
    
    # Integrations section
    console.print(f"  [dim {theme.secondary}]Integrations[/]")
    
    if api_connected:
        console.print(f"  [dim]NVIDIA NIM[/]      [{theme.success}]connected[/]")
    else:
        console.print(f"  [dim]NVIDIA NIM[/]      [{theme.error}]not connected[/]")
    
    if mcp_total:
        console.print(f"  [dim]MCP[/]             {mcp_connected} of {mcp_total} connected")
    
    if hooks_enabled:
        console.print(f"  [dim]Hooks[/]           {hooks_enabled} enabled")
    
    if context_files:
        console.print(f"  [dim]Context files[/]   {context_files} loaded")
    console.print()
    
    # Run section (if active)
    if phase or agents_active or agents_completed or validation:
        console.print(f"  [dim {theme.secondary}]Run[/]")
        if phase:
            console.print(f"  [dim]Phase[/]           {phase}")
        if agents_active or agents_completed:
            parts = []
            if agents_active:
                parts.append(f"{agents_active} active")
            if agents_completed:
                parts.append(f"{agents_completed} completed")
            console.print(f"  [dim]Agents[/]          {' · '.join(parts)}")
        if validation:
            console.print(f"  [dim]Validation[/]      {validation}")
        console.print()
