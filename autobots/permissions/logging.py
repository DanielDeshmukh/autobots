from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autobots.tools.permissions import Permission


@dataclass
class PermissionEntry:
    timestamp: float
    tool_name: str
    args: dict[str, Any]
    permission: Permission
    allowed: bool
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "args": self.args,
            "permission": self.permission.value,
            "allowed": self.allowed,
            "session_id": self.session_id,
        }


class PermissionLogger:
    def __init__(self, log_path: str | Path | None = None):
        self.log_path = Path(log_path) if log_path else None
        self._entries: list[PermissionEntry] = []

    def log(
        self,
        tool_name: str,
        args: dict[str, Any],
        permission: Permission,
        allowed: bool,
        session_id: str = "",
    ) -> None:
        entry = PermissionEntry(
            timestamp=time.time(),
            tool_name=tool_name,
            args=args,
            permission=permission,
            allowed=allowed,
            session_id=session_id,
        )
        self._entries.append(entry)

        if self.log_path:
            self._append_to_file(entry)

    def _append_to_file(self, entry: PermissionEntry) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except OSError:
            pass

    def get_entries(self) -> list[PermissionEntry]:
        return list(self._entries)

    def get_denied(self) -> list[PermissionEntry]:
        return [e for e in self._entries if not e.allowed]

    def get_allowed(self) -> list[PermissionEntry]:
        return [e for e in self._entries if e.allowed]

    def clear(self) -> None:
        self._entries.clear()

    @classmethod
    def load_from_file(cls, log_path: str | Path) -> PermissionLogger:
        path = Path(log_path)
        logger = cls(log_path=path)
        if not path.exists():
            return logger
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    data = json.loads(line)
                    perm_str = data.get("permission", "ask")
                    try:
                        perm = Permission(perm_str)
                    except ValueError:
                        perm = Permission.ASK
                    logger._entries.append(
                        PermissionEntry(
                            timestamp=data.get("timestamp", 0),
                            tool_name=data.get("tool_name", ""),
                            args=data.get("args", {}),
                            permission=perm,
                            allowed=data.get("allowed", False),
                            session_id=data.get("session_id", ""),
                        )
                    )
        except (OSError, json.JSONDecodeError):
            pass
        return logger
