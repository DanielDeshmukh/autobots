"""Autobots UI — Terminal interface components."""

from .theme import Theme, ThemeName, load_theme, THEMES
from .symbols import Symbols, AsciiSymbols, get_symbols
from .welcome import render_welcome, render_prompt_hint
from .prompt import render_status_line, render_prompt_symbol
from .transcript import (
    render_user_message,
    render_assistant_message,
    render_inspection,
    render_plan,
    render_completion_summary,
)
from .approval import (
    render_file_edit_prompt,
    render_shell_command_prompt,
    render_dangerous_command_prompt,
    render_feedback_prompt,
)
from .activity import render_swarm_compact, render_swarm_expanded, CLUSTERS
from .tool_call import (
    render_tool_compact,
    render_tool_read_expanded,
    render_tool_search_expanded,
    render_tool_edit_expanded,
)
from .validation import (
    render_validation_start,
    render_validation_check,
    render_validation_summary,
    render_repair_start,
    render_repair_action,
    render_revalidation,
    render_validation_error,
)
from .completion import render_completion
from .commands import render_command_palette, render_command_help, COMMANDS
from .file_mentions import render_file_mention_picker, search_files
from .sessions import render_session_picker, render_session_preview
from .help import render_help, render_mode_switch
from .context import (
    render_context_usage,
    render_compaction_start,
    render_compaction_done,
)
from .model_picker import render_model_picker, render_agents_picker
from .status import render_status
from .rewind import render_rewind_picker, render_undo_confirmation
from .layout import get_layout_mode, LayoutMode
from .renderers import PlainRenderer, JsonRenderer

__all__ = [
    # Theme & Symbols
    "Theme", "ThemeName", "load_theme", "THEMES",
    "Symbols", "AsciiSymbols", "get_symbols",
    
    # Welcome
    "render_welcome", "render_prompt_hint",
    
    # Prompt
    "render_status_line", "render_prompt_symbol",
    
    # Transcript
    "render_user_message", "render_assistant_message",
    "render_inspection", "render_plan", "render_completion_summary",
    
    # Approval
    "render_file_edit_prompt", "render_shell_command_prompt",
    "render_dangerous_command_prompt", "render_feedback_prompt",
    
    # Activity
    "render_swarm_compact", "render_swarm_expanded", "CLUSTERS",
    
    # Tool calls
    "render_tool_compact", "render_tool_read_expanded",
    "render_tool_search_expanded", "render_tool_edit_expanded",
    
    # Validation
    "render_validation_start", "render_validation_check",
    "render_validation_summary", "render_repair_start",
    "render_repair_action", "render_revalidation",
    "render_validation_error",
    
    # Completion
    "render_completion",
    
    # Commands
    "render_command_palette", "render_command_help", "COMMANDS",
    
    # File mentions
    "render_file_mention_picker", "search_files",
    
    # Sessions
    "render_session_picker", "render_session_preview",
    
    # Help
    "render_help", "render_mode_switch",
    
    # Context
    "render_context_usage", "render_compaction_start", "render_compaction_done",
    
    # Model picker
    "render_model_picker", "render_agents_picker",
    
    # Status
    "render_status",
    
    # Rewind
    "render_rewind_picker", "render_undo_confirmation",
    
    # Layout
    "get_layout_mode", "LayoutMode",
    
    # Renderers
    "PlainRenderer", "JsonRenderer",
]
