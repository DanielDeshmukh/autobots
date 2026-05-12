from __future__ import annotations

import json
import time
from pathlib import Path


class WorkspaceIOError(ValueError):
    pass


class TargetProjectWorkspace:
    CRITICAL_CONTEXT_FILES = {"architecture.md", "security-auth.md"}
    LOCK_TTL_SECONDS = 60

    def __init__(self, target_root: str | Path):
        self.target_root = Path(target_root).expanduser().resolve()
        self.src_root = self.target_root / "src"
        self.context_root = self.target_root / "context"
        self.lock_root = self.context_root / ".autobots-locks"

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

    def apply_generated_files(self, files: list[dict], *, lock_owner: str | None = None) -> list[str]:
        written_paths: list[str] = []

        for file_spec in files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip().replace("\\", "/")
            content = file_spec.get("content") or ""

            if root_name == "src":
                written = self.write_src_file(relative_path, content)
            elif root_name == "context":
                written = self.write_context_file(relative_path, content, lock_owner=lock_owner)
            else:
                raise WorkspaceIOError(
                    f"Unsupported write root '{root_name}'. Use 'src' or 'context'."
                )

            written_paths.append(str(written))

        return written_paths

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
