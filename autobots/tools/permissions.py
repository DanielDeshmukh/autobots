from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from autobots.tools.base import Tool, ToolResult


class Permission(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    tool_pattern: str
    permission: Permission
    args_pattern: str = "*"

    def matches(self, tool_name: str, args: dict[str, Any] | None = None) -> bool:
        if not fnmatch.fnmatch(tool_name, self.tool_pattern):
            return False
        if args is None or self.args_pattern == "*":
            return True
        for key, value in args.items():
            if isinstance(value, str) and fnmatch.fnmatch(value, self.args_pattern):
                return True
        return False


@dataclass
class PermissionConfig:
    rules: list[PermissionRule] = field(default_factory=list)
    default: Permission = Permission.ASK

    def check(self, tool_name: str, args: dict[str, Any] | None = None) -> Permission:
        for rule in self.rules:
            if rule.matches(tool_name, args):
                return rule.permission
        return self.default

    def add_rule(
        self, tool_pattern: str, permission: Permission, args_pattern: str = "*"
    ) -> None:
        self.rules.append(
            PermissionRule(
                tool_pattern=tool_pattern,
                permission=permission,
                args_pattern=args_pattern,
            )
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionConfig:
        rules = []
        for rule_data in data.get("rules", []):
            perm_str = rule_data.get("permission", "ask")
            try:
                perm = Permission(perm_str)
            except ValueError:
                perm = Permission.ASK
            rules.append(
                PermissionRule(
                    tool_pattern=rule_data.get("tool_pattern", "*"),
                    permission=perm,
                    args_pattern=rule_data.get("args_pattern", "*"),
                )
            )
        default_str = data.get("default", "ask")
        try:
            default = Permission(default_str)
        except ValueError:
            default = Permission.ASK
        return cls(rules=rules, default=default)


class PermissionChecker:
    def __init__(self, config: PermissionConfig | None = None):
        self.config = config or PermissionConfig()
        self._session_always: set[str] = set()

    def check(self, tool_name: str, args: dict[str, Any] | None = None) -> Permission:
        if tool_name in self._session_always:
            return Permission.ALLOW
        return self.config.check(tool_name, args)

    def always_allow(self, tool_name: str) -> None:
        self._session_always.add(tool_name)

    def revoke_always(self, tool_name: str) -> None:
        self._session_always.discard(tool_name)

    def clear_session(self) -> None:
        self._session_always.clear()
