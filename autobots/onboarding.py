"""Interactive onboarding wizard for Autobots."""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import AutobotsConfig, CONFIG_FILE_NAMES


# Default templates for context files (must match CORE_CONTEXT_FILES in bootstrap.py)
CONTEXT_TEMPLATES = {
    "architecture.md": """# Architecture

## Overview

{project_name} is a {description} application.

## Directory Structure

```
{project_name}/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
└── context/       # Autobots context files
```

## Key Components

- **Main Application**: Entry point and core logic
- **API Layer**: HTTP endpoints and request handling
- **Data Layer**: Database models and queries
- **Tests**: Unit and integration tests

## Technology Stack

- **Language**: {languages}
- **Framework**: {framework}
- **Test Framework**: {test_framework}
""",

    "roadmap.md": """# Roadmap

Project phases and milestone tracking.

## Project Phases

### Phase 1: Project Setup

**Goal**: Initialize project structure and core components

**Duration**: Week 1

- [ ] Set up project repository
- [ ] Configure development environment
- [ ] Create basic project structure
- [ ] Set up CI/CD pipeline

**Acceptance checks:**
  - [ ] src/ directory exists
  - [ ] pyproject.toml configured

### Phase 2: Core Implementation

**Goal**: Implement main application features

**Duration**: Week 2-3

- [ ] Implement core business logic
- [ ] Create API endpoints
- [ ] Set up database models
- [ ] Write initial tests

**Acceptance checks:**
  - [ ] All API endpoints respond correctly
  - [ ] Database models are verified

### Phase 3: Testing & Documentation

**Goal**: Ensure quality and document the project

**Duration**: Week 4

- [ ] Write comprehensive tests
- [ ] Create user documentation
- [ ] Performance testing
- [ ] Security audit

**Acceptance checks:**
  - [ ] Test coverage > 80%
  - [ ] Documentation complete

## Timeline

| Phase | Start | End    | Status        |
| ----- | ----- | ------ | ------------- |
| P1    | W1    | W1     | Not Started   |
| P2    | W2    | W3     | Not Started   |
| P3    | W4    | W4     | Not Started   |

## Blockers

- [List any blockers here]

## Next Steps

- Complete project setup
- Define detailed requirements
""",

    "ui-components.md": """# UI Components

## Component Library

- **Framework**: {framework}
- **Styling**: CSS/Styled Components/Tailwind

## Component Structure

- Layout components (Header, Footer, Sidebar)
- Form components (Input, Button, Select)
- Display components (Card, Table, Modal)
- Navigation components (Tabs, Breadcrumb)

## Design System

- Color palette
- Typography
- Spacing
- Shadows and borders
""",

    "progress-tracker.md": """# Progress Tracker

Current phase and task status for Autobots execution.

## Current Status

- **Phase**: Not started
- **Last Updated**: (auto-updated by Autobots)

## Phase Progress

| Phase | Status | Notes |
| ----- | ------ | ----- |
| P1    | - [ ] Not started | |
| P2    | - [ ] Not started | |
| P3    | - [ ] Not started | |

## Task Log

(Updated automatically by Autobots during execution)
""",

    "project-briefing.md": """# Project Briefing

## Overview

{project_name} is a {description} application.

## Goals

- Build a reliable, well-tested application
- Follow best practices for {languages} development
- Ensure security and performance

## Constraints

- Must work on modern browsers/operating systems
- Follow coding standards and conventions
- Maintain backward compatibility

## Stakeholders

- Development team
- End users
- Operations team

## Success Criteria

- All features implemented and tested
- Documentation complete
- Performance benchmarks met
- Security audit passed
""",

    "security-auth.md": """# Security & Authentication

## Authentication

- Use environment variables for secrets
- Never commit API keys or passwords
- Rotate credentials regularly

## Authorization

- Implement role-based access control
- Validate user permissions before operations
- Log all authentication attempts

## Data Protection

- Encrypt sensitive data at rest
- Use HTTPS for all API calls
- Validate and sanitize all user input

## Security Checklist

- [ ] No hardcoded secrets
- [ ] Input validation on all endpoints
- [ ] Rate limiting enabled
- [ ] CORS properly configured
""",
}


def run_onboarding_wizard(
    target_root: Path,
    console: Console | None = None,
    skip_api_key: bool = False,
) -> bool:
    """Run the interactive onboarding wizard.

    Args:
        target_root: Path to the target project
        console: Rich console instance
        skip_api_key: Skip API key prompting

    Returns:
        True if onboarding completed successfully
    """
    if console is None:
        console = Console()

    # Welcome message
    console.print(
        Panel.fit(
            "[bold cyan]Welcome to Autobots![/bold cyan]\n\n"
            "Let's set up your project for AI-powered development.\n"
            "This wizard will configure everything you need.\n\n"
            "[dim]Press Ctrl+C at any time to cancel.[/dim]",
            title="Onboarding Wizard",
            border_style="cyan",
        )
    )

    # Get project information
    project_name = Prompt.ask(
        "\n[bold]Project name[/bold]",
        default=target_root.name,
    )

    languages = Prompt.ask(
        "[bold]Programming languages[/bold] (comma-separated)",
        default="Python",
    )

    test_framework = Prompt.ask(
        "[bold]Test framework[/bold]",
        default="pytest",
    )

    # Get API key if needed
    api_key = None
    if not skip_api_key:
        api_key = _get_or_prompt_api_key(console)

    # Confirm before proceeding
    console.print()
    table = Table(title="Project Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_row("Project", project_name)
    table.add_row("Languages", languages)
    table.add_row("Test Framework", test_framework)
    table.add_row("API Key", "***configured***" if api_key else "[dim]not set[/dim]")
    console.print(table)

    if not Confirm.ask("\n[bold]Proceed with this configuration?[/bold]", default=True):
        console.print("[yellow]Onboarding cancelled.[/yellow]")
        return False

    # Write configuration
    _write_config(target_root, project_name, languages, test_framework, api_key, console)

    # Scaffold context files
    _scaffold_context_files(target_root, project_name, languages, test_framework, console)

    # Success message
    console.print(
        Panel.fit(
            "[green]Setup complete![/green]\n\n"
            "Next steps:\n"
            "  1. Run [bold]autobots doctor[/bold] to verify configuration\n"
            "  2. Run [bold]autobots plan[/bold] to create a development plan\n"
            "  3. Run [bold]autobots engage[/bold] to start the swarm",
            title="Ready to Go!",
            border_style="green",
        )
    )

    return True


def _get_or_prompt_api_key(console: Console) -> str | None:
    """Get API key from environment or prompt user.

    Checks in order:
    1. NVIDIA_API_KEY environment variable
    2. .env file in engine root
    3. Prompt user for input
    """
    # Check environment variable
    env_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if env_key:
        console.print("[dim]Found NVIDIA_API_KEY in environment.[/dim]")
        return env_key

    # Check .env file
    from .cli import ENGINE_ENV_PATH
    from dotenv import dotenv_values

    if ENGINE_ENV_PATH.exists():
        env_values = dotenv_values(ENGINE_ENV_PATH)
        file_key = (env_values.get("NVIDIA_API_KEY") or "").strip()
        if file_key:
            console.print("[dim]Found NVIDIA_API_KEY in .env file.[/dim]")
            return file_key

    # Prompt user
    console.print(
        "\n[yellow]NVIDIA API key is required for Autobots to function.[/yellow]\n"
        "[dim]Get your key at: https://build.nvidia.com/[/dim]\n"
    )

    api_key = Prompt.ask("[bold]NVIDIA API key[/bold]", password=True)

    if not api_key.strip():
        console.print("[yellow]No API key provided. You can set it later with:[/yellow]")
        console.print("  export NVIDIA_API_KEY=your-key-here")
        return None

    return api_key.strip()


def _write_config(
    target_root: Path,
    project_name: str,
    languages: str,
    test_framework: str,
    api_key: str | None,
    console: Console,
) -> None:
    """Write .autobots.toml configuration file."""
    config_path = target_root / ".autobots.toml"

    # Parse languages into list
    lang_list = [l.strip() for l in languages.split(",")]

    # Determine test command based on framework
    test_commands = {
        "pytest": "pytest tests/ -q",
        "unittest": "python -m unittest discover tests/",
        "jest": "npm test",
        "vitest": "npx vitest run",
        "go test": "go test ./...",
        "cargo test": "cargo test",
    }
    test_command = test_commands.get(test_framework, f"{test_framework} tests/")

    config_content = f"""[autobots]
# Autobots configuration for {project_name}

# NVIDIA API key is stored in .env (gitignored), not here.
# Set via: autobots init --interactive or manually in .env file

# Model selection: balanced | speed | quality
model_selection_profile = "balanced"

# Execution mode: supervised | milestone | autonomous
default_mode = "supervised"

# Test gate: run tests before/after changes
test_gate = false
test_command = "{test_command}"
test_timeout = 120

[project]
name = "{project_name}"
languages = {lang_list}
test_framework = "{test_framework}"
"""

    config_path.write_text(config_content.strip() + "\n", encoding="utf-8")
    console.print(f"[green]OK[/green] Wrote configuration to {config_path.name}")

    # Save API key to .env if provided
    if api_key:
        _save_api_key_to_env(api_key, console)


def _save_api_key_to_env(api_key: str, console: Console) -> None:
    """Save API key to .env file in engine root."""
    from .cli import ENGINE_ENV_PATH

    lines: list[str] = []
    if ENGINE_ENV_PATH.exists():
        lines = ENGINE_ENV_PATH.read_text(encoding="utf-8").splitlines()

    # Update or add API key
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("NVIDIA_API_KEY="):
            lines[index] = f"NVIDIA_API_KEY={api_key}"
            updated = True
            break

    if not updated:
        lines.append(f"NVIDIA_API_KEY={api_key}")

    content = "\n".join(lines).strip() + "\n"
    ENGINE_ENV_PATH.write_text(content, encoding="utf-8")
    console.print("[green]OK[/green] Saved API key to .env")


def _scaffold_context_files(
    target_root: Path,
    project_name: str,
    languages: str,
    test_framework: str,
    console: Console,
) -> None:
    """Create context directory and template files."""
    context_dir = target_root / "context"
    context_dir.mkdir(exist_ok=True)

    # Parse first language for templates
    primary_language = languages.split(",")[0].strip()

    created_files = []
    for filename, template in CONTEXT_TEMPLATES.items():
        file_path = context_dir / filename
        if file_path.exists():
            continue  # Don't overwrite existing files

        content = template.format(
            project_name=project_name,
            languages=primary_language,
            framework=primary_language,  # Use language as default framework
            test_framework=test_framework,
            description=f"{primary_language} {test_framework}",
        )

        file_path.write_text(content, encoding="utf-8")
        created_files.append(filename)

    if created_files:
        console.print(f"[green]OK[/green] Created {len(created_files)} context files:")
        for f in created_files:
            console.print(f"  - context/{f}")
    else:
        console.print("[dim]Context files already exist, skipping.[/dim]")


def check_and_prompt_api_key(
    target_root: Path,
    console: Console,
    force_prompt: bool = False,
) -> str | None:
    """Check for API key and prompt if not found.

    Checks in order:
    1. NVIDIA_API_KEY environment variable
    2. .env file in engine root
    3. .autobots.toml in target project
    4. Prompt user (if force_prompt or not found)

    Returns:
        API key if found/prompted, None otherwise
    """
    # Check environment variable
    env_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if env_key and not force_prompt:
        return env_key

    # Check .env file
    from .cli import ENGINE_ENV_PATH
    from dotenv import dotenv_values

    if ENGINE_ENV_PATH.exists() and not force_prompt:
        env_values = dotenv_values(ENGINE_ENV_PATH)
        file_key = (env_values.get("NVIDIA_API_KEY") or "").strip()
        if file_key:
            return file_key

    # Check target project config
    if not force_prompt:
        for config_name in CONFIG_FILE_NAMES:
            config_path = target_root / config_name
            if config_path.exists():
                try:
                    import tomllib
                    with open(config_path, "rb") as f:
                        data = tomllib.load(f)
                    config_key = data.get("autobots", {}).get("api_key", "")
                    if config_key:
                        return config_key
                except Exception:
                    pass

    # Prompt user
    console.print(
        "\n[yellow]NVIDIA API key is required.[/yellow]\n"
        "[dim]Get your key at: https://build.nvidia.com/[/dim]\n"
    )

    api_key = Prompt.ask("[bold]NVIDIA API key[/bold]", password=True)

    if not api_key.strip():
        console.print("[yellow]No API key provided.[/yellow]")
        return None

    api_key = api_key.strip()

    # Save to .env for future use
    _save_api_key_to_env(api_key, console)

    return api_key
