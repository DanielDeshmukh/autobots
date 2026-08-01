"""Context and compaction views."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..theme import Theme, load_theme


def render_context_usage(
    console: Console,
    *,
    system_instructions: int = 0,
    project_instructions: int = 0,
    tool_definitions: int = 0,
    conversation: int = 0,
    reserved_response: int = 0,
    remaining: int = 0,
    used_pct: float = 0.0,
    auto_compact_pct: float = 80.0,
    theme: Theme | None = None,
) -> None:
    """Render context usage breakdown.
    
    Format:
    Context usage
    
      System instructions       6,420 tokens
      Project instructions      4,180 tokens
      Tool definitions          3,240 tokens
      Conversation             28,910 tokens
      Reserved response          8,192 tokens
      Remaining                 61,058 tokens
    
      Used 42% · automatic compaction at 80%
    """
    if theme is None:
        theme = load_theme()
    
    console.print()
    console.print(f"  [bold {theme.primary}]Context usage[/]")
    console.print()
    
    fields = [
        ("System instructions", system_instructions),
        ("Project instructions", project_instructions),
        ("Tool definitions", tool_definitions),
        ("Conversation", conversation),
        ("Reserved response", reserved_response),
        ("Remaining", remaining),
    ]
    
    for label, tokens in fields:
        if tokens:
            formatted = f"{tokens:,}"
            console.print(f"  [dim {theme.secondary}]{label:<24}[/] {formatted} tokens")
    
    console.print()
    
    # Usage bar
    if used_pct >= 80:
        pct_style = f"{theme.error}"
    elif used_pct >= 50:
        pct_style = f"{theme.warning}"
    else:
        pct_style = f"{theme.success}"
    
    console.print(
        f"  [dim {theme.secondary}]Used [/][{pct_style}]{used_pct:.0f}%[/]"
        f"[dim {theme.secondary}] · automatic compaction at {auto_compact_pct:.0f}%[/]"
    )
    console.print()


def render_compaction_start(
    console: Console,
    *,
    theme: Theme | None = None,
) -> None:
    """Render compaction start message.
    
    Format:
    ● Compacting conversation context
      Summarized 31 messages and preserved active file references.
    
      Context usage reduced from 81% to 38%.
    """
    if theme is None:
        theme = load_theme()
    symbols = get_symbols()
    
    console.print(f"{symbols.active} [bold {theme.primary}]Compacting conversation context[/]")


def render_compaction_done(
    console: Console,
    *,
    messages_summarized: int = 0,
    from_pct: float = 0.0,
    to_pct: float = 0.0,
    theme: Theme | None = None,
) -> None:
    """Render compaction completion.
    
    Format:
      Summarized 31 messages and preserved active file references.
    
      Context usage reduced from 81% to 38%.
    """
    if theme is None:
        theme = load_theme()
    
    if messages_summarized:
        console.print(
            f"  [dim {theme.secondary}]Summarized {messages_summarized} messages "
            f"and preserved active file references.[/]"
        )
    
    if from_pct and to_pct:
        console.print()
        console.print(
            f"  [dim {theme.secondary}]Context usage reduced from "
            f"[{theme.warning}]{from_pct:.0f}%[/][dim {theme.secondary}] to "
            f"[{theme.success}]{to_pct:.0f}%[/][dim {theme.secondary}].[/]"
        )
    
    console.print()
