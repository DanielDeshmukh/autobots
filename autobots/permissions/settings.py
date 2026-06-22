from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autobots.tools.permissions import PermissionConfig, Permission, PermissionRule


@dataclass
class PermissionSettings:
    global_config: PermissionConfig = field(default_factory=PermissionConfig)
    project_config: PermissionConfig = field(default_factory=PermissionConfig)
    env_allowed: list[str] = field(default_factory=list)
    env_denied: list[str] = field(default_factory=list)

    def merged(self) -> PermissionConfig:
        rules = []

        for rule in self.project_config.rules:
            rules.append(rule)

        for rule in self.global_config.rules:
            if not any(r.tool_pattern == rule.tool_pattern for r in rules):
                rules.append(rule)

        for pattern in self.env_allowed:
            rules.append(PermissionRule(tool_pattern=pattern, permission=Permission.ALLOW))

        for pattern in self.env_denied:
            rules.append(PermissionRule(tool_pattern=pattern, permission=Permission.DENY))

        default = self.project_config.default
        if default == Permission.ASK:
            default = self.global_config.default

        return PermissionConfig(rules=rules, default=default)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _parse_permission_config(data: dict[str, Any]) -> PermissionConfig:
    return PermissionConfig.from_dict(data.get("permissions", {}))


def load_settings(project_root: str | Path | None = None) -> PermissionSettings:
    home = Path.home()
    global_path = home / ".autobots" / "settings.json"
    global_data = _load_json(global_path)
    global_config = _parse_permission_config(global_data)

    project_config = PermissionConfig()
    if project_root:
        project_path = Path(project_root) / ".autobots" / "settings.json"
        project_data = _load_json(project_path)
        project_config = _parse_permission_config(project_data)

    env_allowed = [
        p.strip()
        for p in os.environ.get("AUTOBOTS_ALLOWED_TOOLS", "").split(",")
        if p.strip()
    ]
    env_denied = [
        p.strip()
        for p in os.environ.get("AUTOBOTS_DENIED_TOOLS", "").split(",")
        if p.strip()
    ]

    return PermissionSettings(
        global_config=global_config,
        project_config=project_config,
        env_allowed=env_allowed,
        env_denied=env_denied,
    )
