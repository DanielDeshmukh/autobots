from __future__ import annotations

import json
import time
from pathlib import Path


class WorkspaceIOError(ValueError):
    pass


class TargetProjectWorkspace:
    CRITICAL_CONTEXT_FILES = {"architecture.md", "security-auth.md"}
    LOCK_TTL_SECONDS = 60
    LOCK_RETRY_DELAY_SECONDS = 2
    LOCK_RETRY_ATTEMPTS = 3
    ALLOWED_WRITE_ROOTS = {"src", "app", "lib", "tests", "docs", "scripts", "context"}

    def __init__(self, target_root: str | Path):
        self.target_root = Path(target_root).expanduser().resolve()
        self.src_root = self.target_root / "src"
        self.context_root = self.target_root / "context"
        self.lock_root = self.context_root / ".autobots-locks"
        # Support common project layout roots
        self._layout_roots = {
            "src": self.target_root / "src",
            "app": self.target_root / "app",
            "lib": self.target_root / "lib",
            "tests": self.target_root / "tests",
            "docs": self.target_root / "docs",
            "scripts": self.target_root / "scripts",
            "context": self.context_root,
        }

    def _resolve(self, root: Path, relative_path: str) -> Path:
        if not relative_path:
            raise WorkspaceIOError("A relative path is required.")

        candidate = (root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise WorkspaceIOError(
                f"Refusing to access '{relative_path}' outside of {root}"
            )
        return candidate

    def read_context_file(self, relative_path: str) -> str:
        path = self._resolve(self.context_root, relative_path)
        return path.read_text(encoding="utf-8")

    def write_context_file(
        self,
        relative_path: str,
        content: str,
        *,
        lock_owner: str | None = None,
    ) -> Path:
        path = self._resolve(self.context_root, relative_path)
        if relative_path in self.CRITICAL_CONTEXT_FILES:
            owner = lock_owner or "Autobots"
            self.acquire_context_lock(relative_path, owner)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(content, encoding="utf-8")
        finally:
            if relative_path in self.CRITICAL_CONTEXT_FILES:
                self.release_context_lock(relative_path, lock_owner or "Autobots")
        return path

    def write_src_file(self, relative_path: str, content: str) -> Path:
        path = self._resolve(self.src_root, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_file(self, root_name: str, relative_path: str, content: str) -> Path:
        """Write a file to any allowed project root (src, app, lib, tests, docs, scripts, context)."""
        root_name_lower = root_name.strip().lower()
        if root_name_lower not in self.ALLOWED_WRITE_ROOTS:
            raise WorkspaceIOError(
                f"Unsupported write root '{root_name}'. Allowed: {', '.join(self.ALLOWED_WRITE_ROOTS)}"
            )

        root = self._layout_roots.get(root_name_lower)
        if not root:
            raise WorkspaceIOError(f"Root '{root_name}' not configured.")

        if root_name_lower == "context":
            return self.write_context_file(relative_path, content)

        path = self._resolve(root, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_file(self, root_name: str, relative_path: str) -> str:
        """Read a file from any allowed project root."""
        root_name_lower = root_name.strip().lower()
        if root_name_lower not in self.ALLOWED_WRITE_ROOTS:
            raise WorkspaceIOError(
                f"Unsupported read root '{root_name}'. Allowed: {', '.join(self.ALLOWED_WRITE_ROOTS)}"
            )

        root = self._layout_roots.get(root_name_lower)
        if not root:
            raise WorkspaceIOError(f"Root '{root_name}' not configured.")

        if root_name_lower == "context":
            return self.read_context_file(relative_path)

        path = self._resolve(root, relative_path)
        if not path.exists():
            raise WorkspaceIOError(f"File does not exist: {path}")
        return path.read_text(encoding="utf-8")

    def apply_generated_files(self, files: list[dict], *, lock_owner: str | None = None) -> list[str]:
        written_paths: list[str] = []

        for file_spec in files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip().replace("\\", "/")
            content = file_spec.get("content") or ""

            if root_name not in self.ALLOWED_WRITE_ROOTS:
                raise WorkspaceIOError(
                    f"Unsupported write root '{root_name}'. Use one of: {', '.join(self.ALLOWED_WRITE_ROOTS)}"
                )

            if root_name == "context":
                written = self.write_context_file(relative_path, content, lock_owner=lock_owner)
            else:
                written = self.write_file(root_name, relative_path, content)

            written_paths.append(str(written))

        return written_paths

    def is_critical_context_file(self, relative_path: str) -> bool:
        return relative_path.replace("\\", "/") in self.CRITICAL_CONTEXT_FILES

    def acquire_context_lock(
        self,
        relative_path: str,
        owner: str,
        *,
        ttl_seconds: int | None = None,
    ) -> Path:
        if not owner:
            raise WorkspaceIOError("A lock owner is required.")

        ttl = ttl_seconds or self.LOCK_TTL_SECONDS
        lock_path = self._lock_path(relative_path)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        if lock_path.exists():
            payload = self._read_lock_payload(lock_path)
            expires_at = float(payload.get("expires_at", 0))
            existing_owner = str(payload.get("owner") or "").strip()
            if expires_at <= time.time() or existing_owner == owner:
                lock_path.unlink(missing_ok=True)
            else:
                raise WorkspaceIOError(
                    f"Context lock for '{relative_path}' is held by '{existing_owner}'."
                )

        payload = {
            "path": relative_path,
            "owner": owner,
            "acquired_at": time.time(),
            "expires_at": time.time() + ttl,
        }
        lock_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return lock_path

    def release_context_lock(self, relative_path: str, owner: str) -> None:
        lock_path = self._lock_path(relative_path)
        if not lock_path.exists():
            return

        payload = self._read_lock_payload(lock_path)
        existing_owner = str(payload.get("owner") or "").strip()
        expires_at = float(payload.get("expires_at", 0))
        if existing_owner == owner or expires_at <= time.time():
            lock_path.unlink(missing_ok=True)
            return

        raise WorkspaceIOError(
            f"Refusing to release lock for '{relative_path}' owned by '{existing_owner}'."
        )

    def _lock_path(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/").strip("/")
        filename = normalized.replace("/", "__") + ".lock.json"
        return self.lock_root / filename

    def _read_lock_payload(self, lock_path: Path) -> dict:
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkspaceIOError(f"Invalid lock file: {lock_path}") from exc
        if not isinstance(payload, dict):
            raise WorkspaceIOError(f"Invalid lock payload: {lock_path}")
        return payload

    def list_files(self, root_name: str, relative_path: str = "", max_depth: int = 2) -> list[dict]:
        """List files in a directory, respecting max_depth for recursion."""
        root_name_lower = root_name.strip().lower()
        if root_name_lower not in self.ALLOWED_WRITE_ROOTS:
            raise WorkspaceIOError(f"Invalid root: {root_name}")

        root = self._layout_roots.get(root_name_lower)
        if not root or not root.exists():
            return []

        target_dir = self._resolve(root, relative_path) if relative_path else root
        if not target_dir.exists():
            return []

        files: list[dict] = []
        for item in sorted(target_dir.iterdir()):
            if item.name.startswith("."):
                continue

            rel = str(item.relative_to(root)).replace("\\", "/")
            if item.is_file():
                try:
                    size = item.stat().st_size
                    files.append({"path": rel, "type": "file", "size": size})
                except (OSError, IOError):
                    pass
            elif item.is_dir() and max_depth > 0:
                files.append({"path": rel, "type": "dir"})
                # Don't recurse too deep
                try:
                    for subitem in sorted(item.iterdir())[:5]:
                        if subitem.name.startswith("."):
                            continue
                        sub_rel = str(subitem.relative_to(root)).replace("\\", "/")
                        if subitem.is_file():
                            files.append({"path": sub_rel, "type": "file", "indent": 1})
                        else:
                            files.append({"path": sub_rel, "type": "dir", "indent": 1})
                except (OSError, IOError):
                    pass

        return files

    def get_file_summary(self, root_name: str, relevant_paths: list[str]) -> str:
        """Generate a text summary of relevant files for the workspace."""
        root_name_lower = root_name.strip().lower()
        root = self._layout_roots.get(root_name_lower)
        if not root or not root.exists():
            return f"Root '{root_name}' does not exist in {self.target_root}"

        summary_lines = [f"## {root_name.upper()} Root Summary"]
        summary_lines.append("")

        if not relevant_paths:
            summary_lines.append("No specific paths specified.")
            return "\n".join(summary_lines)

        for rel_path in relevant_paths[:10]:  # Limit to first 10 paths
            target_path = root / rel_path
            if target_path.exists() and target_path.is_file():
                try:
                    content = target_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")[:10]  # First 10 lines
                    summary_lines.append(f"### {rel_path}")
                    summary_lines.extend(lines)
                    summary_lines.append("")
                except (OSError, IOError):
                    summary_lines.append(f"### {rel_path}")
                    summary_lines.append("[Unable to read file]")
                    summary_lines.append("")

        return "\n".join(summary_lines)

