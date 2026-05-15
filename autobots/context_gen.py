from __future__ import annotations

from pathlib import Path

from .bootstrap import detect_repo_profile
from .ui import _select, _text


def check_six_file_architecture(console, target_root: Path) -> None:
    from rich.panel import Panel
    context_dir = target_root / "context"
    context_files = [path for path in context_dir.iterdir()] if context_dir.exists() else []
    existing_files = {path.name for path in context_files if path.is_file()}

    required_files = {"architecture.md", "roadmap.md", "ui-components.md", "progress-tracker.md", "project-briefing.md", "security-auth.md"}
    missing_files = required_files - existing_files

    if not missing_files:
        console.print(
            Panel.fit(
                f"6-File Architecture detected in {context_dir}: all 6 context files present.",
                title="Architecture Check",
                border_style="green",
            )
        )
        return

    console.print(
        Panel.fit(
            f"6-File Architecture incomplete in {context_dir}.\n"
            f"Missing: {', '.join(sorted(missing_files))}",
            title="Context Files Missing",
            border_style="yellow",
        )
    )

    generation_choice = _select(
        console,
        "How would you like to generate the 6-File Context?",
        choices=[
            "Generate from README (Recommended)",
            "Generate from autobots benchmarks (Ask questions)",
            "Continue without 6-File Context",
        ],
        default="Generate from README (Recommended)",
    )

    if generation_choice == "Generate from README (Recommended)":
        generate_from_readme(console, target_root)
    elif generation_choice == "Generate from autobots benchmarks (Ask questions)":
        generate_from_benchmarks(console, target_root)
    else:
        console.print(
            Panel.fit(
                "Continuing without the full 6-File Architecture. "
                "Make sure roadmap.md and progress-tracker.md exist in the target context folder.",
                title="Architecture Check",
                border_style="yellow",
            )
        )


def generate_from_readme(console, target_root: Path) -> None:
    from rich.panel import Panel
    readme_paths = [
        target_root / "README.md",
        target_root / "readme.md",
        target_root / "README.TXT",
    ]
    readme_path = None
    for path in readme_paths:
        if path.exists():
            readme_path = path
            break

    if not readme_path:
        console.print(
            Panel.fit(
                "No README file found in target root. Falling back to autobots benchmarks.",
                title="No README Found",
                border_style="yellow",
            )
        )
        generate_from_benchmarks(console, target_root)
        return

    readme_content = readme_path.read_text(encoding="utf-8")
    profile = detect_repo_profile(target_root)

    context_dir = target_root / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    (context_dir / "architecture.md").write_text(
        f"# Architecture\n\n## Project\n{profile.project_name}\n\n## From README\n{readme_content[:2000]}\n\n## TODO\n- Expand architecture details based on README",
        encoding="utf-8",
    )
    (context_dir / "roadmap.md").write_text(
        "# Roadmap\n\n## Phase 1\n- Analyze README and project structure\n## Phase 2\n- Implement core features from README\n## Phase 3\n- Verify against README requirements",
        encoding="utf-8",
    )
    (context_dir / "ui-components.md").write_text(
        "# UI Components\n\n## From README\n- Review README for UI/UX requirements\n\n## TODO\n- Document UI framework and component needs",
        encoding="utf-8",
    )
    (context_dir / "progress-tracker.md").write_text(
        "# Progress Tracker\n\n- [ ] Analyze README requirements\n- [ ] Implement core features\n- [ ] Verify against README\n",
        encoding="utf-8",
    )
    (context_dir / "project-briefing.md").write_text(
        f"# Project Briefing\n\n## Project Name\n{profile.project_name}\n\n## Source\nREADME.md\n\n## From README\n{readme_content[:1500]}\n",
        encoding="utf-8",
    )
    (context_dir / "security-auth.md").write_text(
        "# Security And Auth\n\n## From README\n- Review README for security requirements\n\n## TODO\n- Document authentication and security needs",
        encoding="utf-8",
    )

    console.print(
        Panel.fit(
            f"Generated 6-File Context from README at {context_dir}",
            title="Context Generated",
            border_style="green",
        )
    )


def generate_from_benchmarks(console, target_root: Path) -> None:
    from rich.panel import Panel
    console.print(
        Panel.fit(
            "Generating 6-File Context using autobots benchmarks.\n"
            "Answer a few questions to help autobots understand your project.",
            title="Project Discovery",
            border_style="cyan",
        )
    )

    project_goal = _text("What is the main goal of this project? (one-line description)")
    target_users = _text("Who are the target users? (e.g., developers, end-users, enterprises)")
    key_features = _text("What are the 3 most important features? (comma-separated)")
    security_needs = _text("Any specific security requirements? (e.g., auth, encryption, compliance)")
    ui_framework = _text("Preferred UI framework? (or 'none' for backend-only)")

    profile = detect_repo_profile(target_root)

    context_dir = target_root / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    (context_dir / "architecture.md").write_text(
        f"# Architecture\n\n## Project\n{profile.project_name}\n\n## Goal\n{project_goal}\n\n## Target Users\n{target_users}\n\n## Key Features\n{key_features}\n\n## Security Requirements\n{security_needs or 'None specified'}\n\n## UI Framework\n{ui_framework or 'Not specified'}",
        encoding="utf-8",
    )
    (context_dir / "roadmap.md").write_text(
        f"# Roadmap\n\n## Goal\n{project_goal}\n\n## Phase 1\n- Setup project structure and dependencies\n\n## Phase 2\n- Implement core features: {key_features}\n\n## Phase 3\n- Add security and authentication\n\n## Phase 4\n- Finalize UI/UX ({ui_framework or 'none'})",
        encoding="utf-8",
    )
    (context_dir / "ui-components.md").write_text(
        f"# UI Components\n\n## Framework\n{ui_framework or 'Not specified'}\n\n## Requirements\n- User-facing interface needed: {'Yes' if ui_framework != 'none' else 'No (backend-only)'}\n\n## TODO\n- Define component library and design system",
        encoding="utf-8",
    )
    (context_dir / "progress-tracker.md").write_text(
        f"# Progress Tracker\n\n- [ ] Setup project structure\n- [ ] Implement core features: {key_features}\n- [ ] Add security: {security_needs or 'basic'}\n- [ ] Finalize UI\n",
        encoding="utf-8",
    )
    (context_dir / "project-briefing.md").write_text(
        f"# Project Briefing\n\n## Project Name\n{profile.project_name}\n\n## Goal\n{project_goal}\n\n## Target Users\n{target_users}\n\n## Key Features\n{key_features}\n\n## Security Requirements\n{security_needs or 'None'}\n\n## UI Framework\n{ui_framework or 'None'}\n\n## Detected Stack\n- Languages: {', '.join(profile.languages)}\n- Package managers: {', '.join(profile.package_managers)}\n- Source roots: {', '.join(profile.source_roots)}",
        encoding="utf-8",
    )
    (context_dir / "security-auth.md").write_text(
        f"# Security And Auth\n\n## Requirements\n{security_needs or 'To be determined based on project goals'}\n\n## TODO\n- Define authentication approach\n- Document secret handling\n- Set up security policies",
        encoding="utf-8",
    )

    console.print(
        Panel.fit(
            f"Generated 6-File Context from benchmark answers at {context_dir}",
            title="Context Generated",
            border_style="green",
        )
    )