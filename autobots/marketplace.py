"""Skill pack marketplace for Autobots."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Default marketplace registry URL (for future use)
MARKETPLACE_URL = "https://registry.autobots.dev"

# Local registry path
LOCAL_REGISTRY_PATH = Path.home() / ".autobots" / "marketplace" / "registry.json"


@dataclass
class SkillPack:
    """A skill pack that can be shared."""

    name: str
    version: str
    author: str
    description: str
    tags: list[str] = field(default_factory=list)
    context_files: dict[str, str] = field(default_factory=dict)  # filename -> content
    created_at: float = field(default_factory=time.time)
    downloads: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "downloads": self.downloads,
        }

    def save(self, directory: Path) -> Path:
        """Save skill pack to a directory."""
        pack_dir = directory / f"{self.name}-{self.version}"
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        metadata_path = pack_dir / "skill-pack.json"
        metadata_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

        # Save context files
        context_dir = pack_dir / "context"
        context_dir.mkdir(exist_ok=True)
        for filename, content in self.context_files.items():
            (context_dir / filename).write_text(content, encoding="utf-8")

        return pack_dir

    def create_zip(self, output_path: Path) -> Path:
        """Create a zip archive of the skill pack."""
        zip_path = output_path / f"{self.name}-{self.version}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            zf.writestr(
                f"{self.name}-{self.version}/skill-pack.json",
                json.dumps(self.to_dict(), indent=2),
            )

            # Add context files
            for filename, content in self.context_files.items():
                zf.writestr(
                    f"{self.name}-{self.version}/context/{filename}",
                    content,
                )

        return zip_path


@dataclass
class MarketplaceEntry:
    """An entry in the marketplace registry."""

    name: str
    version: str
    author: str
    description: str
    tags: list[str]
    downloads: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    file_path: str | None = None  # Local path or URL

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "downloads": self.downloads,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "file_path": self.file_path,
        }


class Marketplace:
    """Manages the skill pack marketplace."""

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or LOCAL_REGISTRY_PATH
        self.entries: dict[str, MarketplaceEntry] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load registry from file."""
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                for entry_data in data.get("entries", []):
                    entry = MarketplaceEntry(**entry_data)
                    self.entries[entry.name] = entry
            except Exception:
                pass

    def _save_registry(self) -> None:
        """Save registry to file."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entries": [e.to_dict() for e in self.entries.values()],
            "updated_at": time.time(),
        }
        self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
    ) -> list[MarketplaceEntry]:
        """Search for skill packs."""
        results = list(self.entries.values())

        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if query_lower in e.name.lower()
                or query_lower in e.description.lower()
                or query_lower in e.author.lower()
            ]

        if tags:
            tags_set = set(tags)
            results = [
                e for e in results
                if tags_set.intersection(set(e.tags))
            ]

        return sorted(results, key=lambda e: e.downloads, reverse=True)

    def get(self, name: str) -> MarketplaceEntry | None:
        """Get a skill pack by name."""
        return self.entries.get(name)

    def install(self, name: str, target_dir: Path) -> bool:
        """Install a skill pack to a target directory."""
        entry = self.entries.get(name)
        if not entry:
            return False

        if not entry.file_path:
            return False

        source_path = Path(entry.file_path)
        if not source_path.exists():
            return False

        # Load the skill pack
        skill_pack = self._load_skill_pack(source_path)
        if not skill_pack:
            return False

        # Copy context files to target
        context_dir = target_dir / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in skill_pack.context_files.items():
            target_file = context_dir / filename
            if not target_file.exists():
                target_file.write_text(content, encoding="utf-8")

        # Update download count
        entry.downloads += 1
        self._save_registry()

        return True

    def publish(self, skill_pack: SkillPack) -> bool:
        """Publish a skill pack to the local registry."""
        entry = MarketplaceEntry(
            name=skill_pack.name,
            version=skill_pack.version,
            author=skill_pack.author,
            description=skill_pack.description,
            tags=skill_pack.tags,
            downloads=0,
            created_at=skill_pack.created_at,
            updated_at=time.time(),
        )

        # Save the skill pack file
        packs_dir = self.registry_path.parent / "packs"
        packs_dir.mkdir(parents=True, exist_ok=True)
        pack_path = skill_pack.create_zip(packs_dir)
        entry.file_path = str(pack_path)

        self.entries[skill_pack.name] = entry
        self._save_registry()

        return True

    def _load_skill_pack(self, path: Path) -> SkillPack | None:
        """Load a skill pack from a zip file."""
        if not path.exists() or not path.suffix == ".zip":
            return None

        try:
            with zipfile.ZipFile(path, "r") as zf:
                # Find metadata
                metadata_files = [f for f in zf.namelist() if f.endswith("skill-pack.json")]
                if not metadata_files:
                    return None

                metadata = json.loads(zf.read(metadata_files[0]))

                # Find context files
                context_files = {}
                for filename in zf.namelist():
                    if "/context/" in filename and not filename.endswith("/"):
                        content = zf.read(filename).decode("utf-8")
                        # Get just the filename without directory
                        short_name = filename.split("/")[-1]
                        context_files[short_name] = content

                return SkillPack(
                    name=metadata["name"],
                    version=metadata["version"],
                    author=metadata["author"],
                    description=metadata["description"],
                    tags=metadata.get("tags", []),
                    context_files=context_files,
                    created_at=metadata.get("created_at", 0),
                    downloads=metadata.get("downloads", 0),
                )
        except Exception:
            return None

    def list_installed(self, project_dir: Path) -> list[str]:
        """List installed skill packs in a project."""
        context_dir = project_dir / "context"
        if not context_dir.exists():
            return []

        installed = []
        for f in context_dir.glob("*.md"):
            installed.append(f.stem)

        return installed


# Predefined skill packs for the marketplace
BUILTIN_SKILL_PACKS = [
    SkillPack(
        name="python-web",
        version="1.0.0",
        author="Autobots Team",
        description="Skill pack for Python web development (Flask, FastAPI, Django)",
        tags=["python", "web", "api"],
        context_files={
            "architecture.md": """# Python Web Architecture

## Framework Selection
- **FastAPI** for async APIs and microservices
- **Flask** for simple web apps
- **Django** for full-featured applications

## Project Structure
```
src/
├── api/          # API endpoints
├── models/       # Data models
├── services/     # Business logic
├── utils/        # Helper functions
└── config.py     # Configuration
```

## Best Practices
- Use type hints everywhere
- Follow PEP 8 style guide
- Write docstrings for all public functions
- Use async/await for I/O operations
""",
            "testing-strategy.md": """# Python Testing Strategy

## Framework
- **pytest** as the test runner
- **pytest-cov** for coverage
- **pytest-asyncio** for async tests

## Test Structure
```
tests/
├── unit/          # Pure function tests
├── integration/   # API and database tests
├── e2e/           # End-to-end tests
└── conftest.py    # Shared fixtures
```

## Best Practices
- Aim for 80%+ coverage
- Mock external dependencies
- Use fixtures for setup/teardown
- Test edge cases and error paths
""",
        },
    ),
    SkillPack(
        name="react-typescript",
        version="1.0.0",
        author="Autobots Team",
        description="Skill pack for React + TypeScript development",
        tags=["react", "typescript", "frontend", "javascript"],
        context_files={
            "architecture.md": """# React TypeScript Architecture

## Project Structure
```
src/
├── components/    # Reusable UI components
├── pages/         # Route components
├── hooks/         # Custom React hooks
├── services/      # API and business logic
├── types/         # TypeScript type definitions
└── utils/         # Helper functions
```

## Best Practices
- Use functional components with hooks
- Define props interfaces for all components
- Keep components small and focused
- Use custom hooks for shared logic
""",
            "testing-strategy.md": """# React Testing Strategy

## Framework
- **Vitest** or **Jest** for unit tests
- **React Testing Library** for component tests
- **Cypress** or **Playwright** for E2E tests

## Test Structure
```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── Button.test.tsx
```

## Best Practices
- Test behavior, not implementation
- Use screen queries by role/text
- Mock API calls in tests
- Test accessibility
""",
        },
    ),
    SkillPack(
        name="devops",
        version="1.0.0",
        author="Autobots Team",
        description="Skill pack for DevOps and infrastructure",
        tags=["devops", "docker", "kubernetes", "ci-cd"],
        context_files={
            "architecture.md": """# DevOps Architecture

## Container Strategy
- Use multi-stage Docker builds
- Keep images small (Alpine base)
- Non-root user for security

## CI/CD Pipeline
1. Lint and format
2. Unit tests
3. Integration tests
4. Build and push image
5. Deploy to staging
6. E2E tests
7. Deploy to production
""",
            "security-auth.md": """# DevOps Security

## Secrets Management
- Never commit secrets to git
- Use environment variables
- Rotate credentials regularly
- Use secret managers (Vault, AWS SM)

## Container Security
- Scan images for vulnerabilities
- Use minimal base images
- Run as non-root user
- Enable read-only filesystem
""",
        },
    ),
]


def get_builtin_skill_packs() -> list[SkillPack]:
    """Get list of built-in skill packs."""
    return BUILTIN_SKILL_PACKS.copy()
