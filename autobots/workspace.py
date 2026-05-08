from __future__ import annotations

from pathlib import Path


class WorkspaceIOError(ValueError):
    pass


class TargetProjectWorkspace:
    def __init__(self, target_root: str | Path):
        self.target_root = Path(target_root).expanduser().resolve()
        self.src_root = self.target_root / "src"
        self.context_root = self.target_root / "context"

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

    def write_context_file(self, relative_path: str, content: str) -> Path:
        path = self._resolve(self.context_root, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_src_file(self, relative_path: str, content: str) -> Path:
        path = self._resolve(self.src_root, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def apply_generated_files(self, files: list[dict]) -> list[str]:
        written_paths: list[str] = []

        for file_spec in files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip().replace("\\", "/")
            content = file_spec.get("content") or ""

            if root_name == "src":
                written = self.write_src_file(relative_path, content)
            elif root_name == "context":
                written = self.write_context_file(relative_path, content)
            else:
                raise WorkspaceIOError(
                    f"Unsupported write root '{root_name}'. Use 'src' or 'context'."
                )

            written_paths.append(str(written))

        return written_paths

