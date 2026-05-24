from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .workspace import TargetProjectWorkspace


CORE_CONTEXT_FILES = (
    "architecture.md",
    "roadmap.md",
    "ui-components.md",
    "progress-tracker.md",
    "project-briefing.md",
    "security-auth.md",
)


@dataclass(frozen=True)
class RepoProfile:
    project_name: str
    languages: tuple[str, ...]
    package_managers: tuple[str, ...]
    test_tools: tuple[str, ...]
    source_roots: tuple[str, ...]
    config_signals: tuple[str, ...]


def detect_repo_profile(target_root: str | Path) -> RepoProfile:
    root = Path(target_root).expanduser().resolve()

    languages: list[str] = []
    package_managers: list[str] = []
    test_tools: list[str] = []
    source_roots: list[str] = []
    config_signals: list[str] = []

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        languages.append("Python")
    if (root / "package.json").exists():
        languages.append("JavaScript/TypeScript")
    if (root / "Cargo.toml").exists():
        languages.append("Rust")
    if (root / "go.mod").exists():
        languages.append("Go")

    if (root / "pyproject.toml").exists():
        package_managers.append("pip/pyproject")
        config_signals.append("pyproject.toml")
    if (root / "requirements.txt").exists():
        package_managers.append("pip/requirements")
        config_signals.append("requirements.txt")
    if (root / "package-lock.json").exists():
        package_managers.append("npm")
        config_signals.append("package-lock.json")
    elif (root / "package.json").exists():
        package_managers.append("npm-compatible")
        config_signals.append("package.json")
    if (root / "pnpm-lock.yaml").exists():
        package_managers.append("pnpm")
        config_signals.append("pnpm-lock.yaml")
    if (root / "yarn.lock").exists():
        package_managers.append("yarn")
        config_signals.append("yarn.lock")
    if (root / "Cargo.toml").exists():
        package_managers.append("cargo")
        config_signals.append("Cargo.toml")
    if (root / "go.mod").exists():
        package_managers.append("go")
        config_signals.append("go.mod")

    if (root / "pytest.ini").exists() or (root / "tests").exists():
        test_tools.append("pytest")
    if (root / "package.json").exists():
        package_json = _read_json_file(root / "package.json")
        script_names = tuple((package_json.get("scripts") or {}).keys())
        deps = {
            **(package_json.get("dependencies") or {}),
            **(package_json.get("devDependencies") or {}),
        }
        if "test" in script_names:
            test_tools.append("npm test")
        if "vitest" in deps:
            test_tools.append("vitest")
        if "jest" in deps:
            test_tools.append("jest")

    for candidate in ("src", "app", "lib", "tests", "docs", "scripts"):
        if (root / candidate).exists():
            source_roots.append(candidate)

    for child in root.iterdir():
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in {"context", "venv", "__pycache__"}:
            continue
        if (child / "__init__.py").exists() or any(grandchild.suffix == ".py" for grandchild in child.iterdir()):
            source_roots.append(child.name)

    source_roots = list(dict.fromkeys(source_roots))

    if not languages:
        languages.append("Unknown")
    if not package_managers:
        package_managers.append("Unknown")
    if not test_tools:
        test_tools.append("Unknown")
    if not source_roots:
        source_roots.append(".")

    return RepoProfile(
        project_name=root.name,
        languages=tuple(languages),
        package_managers=tuple(package_managers),
        test_tools=tuple(test_tools),
        source_roots=tuple(source_roots),
        config_signals=tuple(config_signals),
    )


def initialize_context(workspace: TargetProjectWorkspace, profile: RepoProfile) -> list[Path]:
    written_paths: list[Path] = []
    templates = build_context_templates(profile)
    for filename, content in templates.items():
        if (workspace.context_root / filename).exists():
            continue
        written_paths.append(workspace.write_context_file(filename, content, lock_owner="Autobots/init"))
    return written_paths


def build_context_templates(profile: RepoProfile) -> dict[str, str]:
    languages = ", ".join(profile.languages)
    package_managers = ", ".join(profile.package_managers)
    test_tools = ", ".join(profile.test_tools)
    source_roots = ", ".join(profile.source_roots)
    config_signals = ", ".join(profile.config_signals) or "None detected"

    return {
        "architecture.md": (
            f"# Architecture\n\n"
            f"## Project\n{profile.project_name}\n\n"
            f"## Detected Stack\n"
            f"- Languages: {languages}\n"
            f"- Package managers: {package_managers}\n"
            f"- Source roots: {source_roots}\n\n"
            f"## Notes\n"
            f"- Fill in runtime architecture, service boundaries, and dependency flow.\n"
        ),
        "roadmap.md": (
            "# Roadmap\n\n"
            "## Phase 1\n"
            "- Confirm scope and constraints for the target repository.\n\n"
            "## Phase 2\n"
            "- Inspect existing code, tests, and delivery expectations.\n\n"
            "## Phase 3\n"
            "- Implement the first prioritized feature or fix.\n"
        ),
        "ui-components.md": (
            "# UI Components\n\n"
            "## Current State\n"
            "- Record any design system, CSS framework, component library, and interaction rules here.\n\n"
            "## TODO\n"
            "- Add typography, layout, color, and component conventions.\n"
        ),
        "progress-tracker.md": (
            "# Progress Tracker\n\n"
            "- [ ] Confirm project objective and success criteria\n"
            "- [ ] Audit repository structure and toolchain\n"
            "- [ ] Define the first implementation-ready execution phase\n"
        ),
        "project-briefing.md": (
            f"# Project Briefing\n\n"
            f"## Project Name\n{profile.project_name}\n\n"
            f"## Repository Signals\n"
            f"- Languages: {languages}\n"
            f"- Package managers: {package_managers}\n"
            f"- Test tools: {test_tools}\n"
            f"- Source roots: {source_roots}\n"
            f"- Config files: {config_signals}\n\n"
            f"## Operator Notes\n"
            f"- Replace this starter summary with the actual product goal, user request, and constraints.\n"
        ),
        "security-auth.md": (
            "# Security And Auth\n\n"
            "## Baseline Questions\n"
            "- What secrets or credentials does this project use?\n"
            "- What authentication flows exist today?\n"
            "- What actions require explicit operator approval?\n\n"
            "## TODO\n"
            "- Document auth boundaries, secret handling, and risky command policies.\n"
        ),
    }


def _read_json_file(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
