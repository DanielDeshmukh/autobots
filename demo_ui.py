"""Demo script — showcase all UI components."""

from rich.console import Console
from rich.text import Text

from autobots.ui import (
    load_theme,
    render_welcome,
    render_help,
    render_command_palette,
    render_swarm_compact,
    render_validation_start,
    render_validation_check,
    render_validation_summary,
    render_repair_start,
    render_repair_action,
    render_completion,
    render_status,
    render_model_picker,
    render_session_picker,
    render_file_edit_prompt,
    render_shell_command_prompt,
)


def main():
    console = Console(width=80)
    theme = load_theme()
    
    # 1. Welcome screen
    console.print("\n" + "=" * 80)
    console.print("  1. WELCOME SCREEN")
    console.print("=" * 80)
    render_welcome(
        console,
        theme=theme,
        username='Daniel',
        project_name='memory-card-flip',
        project_path='~/code/memory-card-flip',
        branch='autobots-safety',
        git_clean=True,
        context_files=6,
        mode='supervised',
        profile='balanced',
        api_connected=True,
    )
    
    # 2. Keyboard shortcuts
    console.print("\n" + "=" * 80)
    console.print("  2. KEYBOARD SHORTCUTS")
    console.print("=" * 80)
    render_help(console, theme=theme)
    
    # 3. Command palette
    console.print("\n" + "=" * 80)
    console.print("  3. COMMAND PALETTE")
    console.print("=" * 80)
    render_command_palette(console, theme=theme)
    
    # 4. Swarm execution
    console.print("\n" + "=" * 80)
    console.print("  4. SWARM EXECUTION")
    console.print("=" * 80)
    render_swarm_compact(
        console,
        task_name='Build a calculator application',
        elapsed='1m 42s',
        clusters=[
            {'name': 'Optimus', 'task': 'Planning', 'status': 'done'},
            {'name': 'Jazz', 'task': 'UI components', 'status': 'done'},
            {'name': 'Ratchet', 'task': 'Calc logic', 'status': 'done'},
            {'name': 'RedAlert', 'task': 'Security review', 'status': 'active'},
        ],
        active_count=1,
        completed_count=3,
        theme=theme,
    )
    
    # 5. Validation
    console.print("\n" + "=" * 80)
    console.print("  5. VALIDATION")
    console.print("=" * 80)
    render_validation_start(console, theme=theme)
    render_validation_check(console, name='Lint', status='passed', elapsed='0.8s', theme=theme)
    render_validation_check(console, name='Type checking', status='passed', elapsed='2.1s', theme=theme)
    render_validation_check(console, name='Tests', status='passed', detail='43 passed', elapsed='4.7s', theme=theme)
    render_validation_check(console, name='Security review', status='passed', elapsed='6.2s', theme=theme)
    render_validation_summary(console, passed=4, failed=0, theme=theme)
    
    # 6. Completion
    console.print("\n" + "=" * 80)
    console.print("  6. COMPLETION")
    console.print("=" * 80)
    render_completion(
        console,
        summary='Built calculator application',
        changes=[
            'Added calculator UI with buttons and display',
            'Implemented arithmetic operations',
            'Added keyboard support',
            'Created unit tests',
        ],
        validation=[
            {'status': 'passed', 'label': '43 tests passed'},
            {'status': 'passed', 'label': 'Linting passed'},
            {'status': 'passed', 'label': 'Type checking passed'},
        ],
        files_changed=8,
        lines_added=342,
        lines_removed=12,
        snapshot='01JAB92M',
        duration='2m 18s',
        cost='$0.18',
        theme=theme,
    )
    
    # 7. Status screen
    console.print("\n" + "=" * 80)
    console.print("  7. STATUS SCREEN")
    console.print("=" * 80)
    render_status(
        console,
        project_dir='~/code/memory-card-flip',
        branch='autobots-safety',
        workspace_modified=4,
        workspace_untracked=2,
        snapshot='01JAB92M',
        mode='supervised',
        profile='balanced',
        context_pct=42.0,
        cost='$0.18',
        duration='4m 18s',
        api_connected=True,
        mcp_connected=2,
        mcp_total=2,
        hooks_enabled=3,
        context_files=6,
        theme=theme,
    )
    
    # 8. Model picker
    console.print("\n" + "=" * 80)
    console.print("  8. MODEL PICKER")
    console.print("=" * 80)
    render_model_picker(
        console,
        current_profile='balanced',
        current_planner='qwen3-next-80b',
        theme=theme,
    )
    
    # 9. Permission prompts
    console.print("\n" + "=" * 80)
    console.print("  9. PERMISSION PROMPTS")
    console.print("=" * 80)
    render_file_edit_prompt(
        console,
        path='src/services/tokens.py',
        description='Adds refresh-token identifiers, rotation, and replay detection.',
        changes_added=47,
        changes_removed=8,
        theme=theme,
    )
    render_shell_command_prompt(
        console,
        command='python -m pytest tests/test_auth.py -q',
        working_dir='~/code/api',
        policy='Allowed command · approval required',
        theme=theme,
    )
    
    console.print("\n" + "=" * 80)
    console.print("  DEMO COMPLETE")
    console.print("=" * 80)


if __name__ == "__main__":
    main()
