"""Repository scanning and framework detection."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import RepositoryScan

if TYPE_CHECKING:
    from ..bootstrap import RepoProfile


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


class RepositoryScanner:
    """Scans repositories for structure and framework information."""

    @staticmethod
    def scan_repository(target_root: str | Path) -> RepositoryScan:
        """Scan a repository and return structure information."""
        root = Path(target_root).expanduser().resolve()
        build_files = tuple(name for name in BUILD_FILES if (root / name).exists())
        env_files = tuple(name for name in ENV_FILES if (root / name).exists())
        docs = tuple(name for name in DOC_FILES if (root / name).exists())
        frameworks = RepositoryScanner._detect_frameworks(root)

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
            frameworks=frameworks,
        )

    @staticmethod
    def _detect_frameworks(root: Path) -> tuple[str, ...]:
        """Detect frameworks used in the project."""
        detected: list[str] = []
        package_json = root / "package.json"
        pyproject = root / "pyproject.toml"
        if package_json.exists():
            payload = package_json.read_text(encoding="utf-8", errors="ignore").lower()
            if '"react"' in payload:
                detected.append("React")
            if '"next"' in payload:
                detected.append("Next.js")
            if '"vue"' in payload:
                detected.append("Vue")
        if pyproject.exists():
            payload = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
            if "django" in payload:
                detected.append("Django")
            if "fastapi" in payload:
                detected.append("FastAPI")
            if "flask" in payload:
                detected.append("Flask")
        return tuple(dict.fromkeys(detected))
