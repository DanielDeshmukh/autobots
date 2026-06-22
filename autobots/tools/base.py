from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolStatus(Enum):
    OK = "ok"
    ERROR = "error"
    DENIED = "denied"


@dataclass
class ToolResult:
    status: ToolStatus
    output: str
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == ToolStatus.OK

    @classmethod
    def success(cls, output: str, **metadata: Any) -> ToolResult:
        return cls(status=ToolStatus.OK, output=output, metadata=metadata)

    @classmethod
    def failure(cls, error: str, **metadata: Any) -> ToolResult:
        return cls(status=ToolStatus.ERROR, error=error, metadata=metadata)

    @classmethod
    def denied(cls, error: str) -> ToolResult:
        return cls(status=ToolStatus.DENIED, error=error)


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        ...

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters(),
        }

    def parameters(self) -> dict[str, Any]:
        return {}
