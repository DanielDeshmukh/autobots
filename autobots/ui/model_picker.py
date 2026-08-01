"""Model and cluster picker."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme


# ─── Cluster Definitions ─────────────────────────────────────────────────────

CLUSTER_MODELS = {
    "Optimus":     {"role": "Planning and routing",     "model": "qwen3-next-80b"},
    "UltraMagnus": {"role": "Backend and architecture", "model": "qwen3.5-122b"},
    "Jazz":        {"role": "Frontend and visual work",  "model": "llama-3.3-70b"},
    "RedAlert":    {"role": "Security and safety",       "model": "qwen3-next-80b"},
    "Ratchet":     {"role": "Debugging and repair",      "model": "qwen3.5-122b"},
    "Perceptor":   {"role": "Retrieval and parsing",     "model": "qwen3-next-80b"},
    "Bumblebee":   {"role": "Communication and media",   "model": "llama-3.3-70b"},
    "Ironhide":    {"role": "Simulation and safety",     "model": "qwen3-next-80b"},
    "Wheeljack":   {"role": "Scientific work",           "model": "qwen3.5-122b"},
}

MODEL_PROFILES = {
    "balanced": "Strong quality with moderate latency",
    "speed": "Prefer low-latency models",
    "quality": "Prefer highest-quality models",
    "custom": "Configure models per cluster",
}


def render_model_picker(
    console: Console,
    *,
    current_profile: str = "balanced",
    current_planner: str = "",
    theme: Theme | None = None,
) -> None:
    """Render the model configuration picker.
    
    Format:
    Model configuration
    
      Selection profile
    > Balanced     Strong quality with moderate latency
      Speed        Prefer low-latency models
      Quality      Prefer highest-quality models
      Custom       Configure models per cluster
    
      Current planner
      Optimus · qwen3-next-80b
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Model configuration[/]")
    console.print()
    console.print(f"  [dim {theme.secondary}]Selection profile[/]")
    
    for profile, desc in MODEL_PROFILES.items():
        is_current = profile == current_profile
        if is_current:
            console.print(f"[bold {theme.brand}]>{[/bold {theme.brand}] [bold]{profile}[/]  {desc}")
        else:
            console.print(f"  [dim]{profile}[/]  [dim {theme.secondary}]{desc}[/]")
    
    console.print()
    console.print(f"  [dim {theme.secondary}]Current planner[/]")
    if current_planner:
        console.print(f"  Optimus · {current_planner}")
    else:
        console.print(f"  [dim]Not configured[/]")
    
    console.print()


def render_agents_picker(
    console: Console,
    *,
    active_clusters: dict[str, str] = None,
    theme: Theme | None = None,
) -> None:
    """Render the agents/cluster picker.
    
    Format:
    Swarm configuration
    
      Cluster        Role                         Current model
      Optimus        Planning and routing         qwen3-next-80b
      UltraMagnus    Backend and architecture     qwen3.5-122b
      ...
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Swarm configuration[/]")
    console.print()
    
    # Header
    console.print(
        f"  [dim {theme.secondary}]{'Cluster':<16} {'Role':<30} {'Current model'}[/]"
    )
    
    for name, info in CLUSTER_MODELS.items():
        role = info["role"]
        model = info["model"]
        
        # Override with active if provided
        if active_clusters and name in active_clusters:
            model = active_clusters[name]
        
        console.print(f"  {name:<16} [dim]{role:<30}[/] {model}")
    
    console.print()
