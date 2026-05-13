from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bootstrap import RepoProfile, detect_repo_profile
from .workspace import TargetProjectWorkspace


BUILD_FILES = (
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
)
ENV_FILES = (".env", ".env.example", ".env.local", ".env.test")
DOC_FILES = ("README.md", "product-definition.md", "PUBLISHING.md")
TEST_DIR_NAMES = {"tests", "test"}
SOURCE_DIR_NAMES = {"src", "app", "lib", "autobots"}


@dataclass(frozen=True)
class RepositoryScan:
    build_files: tuple[str, ...]
    env_files: tuple[str, ...]
    docs: tuple[str, ...]
    source_roots: tuple[str, ...]
    test_roots: tuple[str, ...]


def scan_repository(target_root: str | Path) -> RepositoryScan:
    root = Path(target_root).expanduser().resolve()
    build_files = tuple(name for name in BUILD_FILES if (root / name).exists())
    env_files = tuple(name for name in ENV_FILES if (root / name).exists())
    docs = tuple(name for name in DOC_FILES if (root / name).exists())

    source_roots: list[str] = []
    test_roots: list[str] = []
    for child in root.iterdir():
        if child.name.startswith(".") or not child.exists():
            continue
        if child.is_dir():
            if child.name in TEST_DIR_NAMES:
                test_roots.append(child.name)
                continue
            if child.name in SOURCE_DIR_NAMES:
                source_roots.append(child.name)
            if child.name in {"context", "venv", "__pycache__", "dist"}:
                continue
            if (
                (child / "__init__.py").exists()
                or any(grandchild.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go"} for grandchild in child.iterdir())
            ):
                source_roots.append(child.name)
            continue

        if child.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go"}:
            source_roots.append(".")

    return RepositoryScan(
        build_files=build_files,
        env_files=env_files,
        docs=docs,
        source_roots=tuple(dict.fromkeys(source_roots or ["."])),
        test_roots=tuple(dict.fromkeys(test_roots)),
    )


def default_goal(profile: RepoProfile) -> str:
    primary_language = profile.languages[0] if profile.languages else "project"
    return f"Prepare the next implementation-ready plan for this {primary_language} repository."


def synthesize_plan(
    profile: RepoProfile,
    scan: RepositoryScan,
    *,
    goal: str,
) -> tuple[str, str]:
    source_roots = ", ".join(scan.source_roots)
    test_roots = ", ".join(scan.test_roots) or "None detected"
    build_files = ", ".join(scan.build_files) or "None detected"
    env_files = ", ".join(scan.env_files) or "None detected"
    docs = ", ".join(scan.docs) or "None detected"
    languages = ", ".join(profile.languages)
    package_managers = ", ".join(profile.package_managers)
    test_tools = ", ".join(profile.test_tools)

    roadmap = (
        "# Roadmap\n\n"
        "## Planning Objective\n"
        f"- {goal}\n\n"
        "## Repository Scan\n"
        f"- Languages: {languages}\n"
        f"- Package managers: {package_managers}\n"
        f"- Test tools: {test_tools}\n"
        f"- Source roots: {source_roots}\n"
        f"- Test roots: {test_roots}\n"
        f"- Build files: {build_files}\n"
        f"- Env files: {env_files}\n"
        f"- Docs: {docs}\n\n"
        "## Phase 1: Inspect Current Behavior\n"
        "- Review the main source roots and supporting docs tied to the planning objective.\n"
        "- Identify existing constraints, extension points, and missing information.\n"
        "- Acceptance check: the affected areas and blockers are documented in context.\n\n"
        "## Phase 2: Define Execution Slices\n"
        "- Convert the objective into small implementation-ready phases.\n"
        "- Attach validation checks to each phase using the detected test tools or build files.\n"
        "- Acceptance check: each phase has a clear outcome and at least one verification path.\n\n"
        "## Phase 3: Queue The First Deliverable\n"
        "- Promote the highest-value phase into the progress tracker as the next active work item.\n"
        "- Record dependencies or follow-up phases that must remain pending.\n"
        "- Acceptance check: the progress tracker is ordered and ready for execution.\n"
    )

    progress = (
        "# Progress Tracker\n\n"
        "- [ ] Inspect repository structure and confirm the planning objective\n"
        "- [ ] Break the objective into ordered implementation phases with acceptance checks\n"
        "- [ ] Queue the first implementation-ready phase for execution\n"
    )
    return roadmap, progress


def write_plan(
    workspace: TargetProjectWorkspace,
    *,
    goal: str | None = None,
) -> tuple[RepoProfile, RepositoryScan]:
    profile = detect_repo_profile(workspace.target_root)
    scan = scan_repository(workspace.target_root)
    resolved_goal = (goal or "").strip() or default_goal(profile)
    roadmap, progress = synthesize_plan(profile, scan, goal=resolved_goal)
    workspace.write_context_file("roadmap.md", roadmap, lock_owner="Autobots/plan")
    workspace.write_context_file("progress-tracker.md", progress, lock_owner="Autobots/plan")
    return profile, scan
