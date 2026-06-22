from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autobots.context.tokenizer import estimate_tokens


@dataclass
class ContextMessage:
    role: str
    content: str
    tokens: int = 0

    def __post_init__(self) -> None:
        if self.tokens == 0:
            self.tokens = estimate_tokens(self.content)


@dataclass
class ContextManager:
    max_tokens: int = 128000
    compact_threshold: float = 0.8
    messages: list[ContextMessage] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(m.tokens for m in self.messages)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.total_tokens)

    @property
    def usage_ratio(self) -> float:
        return self.total_tokens / self.max_tokens if self.max_tokens > 0 else 0

    @property
    def should_compact(self) -> bool:
        return self.usage_ratio >= self.compact_threshold

    def add(self, role: str, content: str) -> ContextMessage:
        msg = ContextMessage(role=role, content=content)
        self.messages.append(msg)
        return msg

    def compact(self, keep_recent: int = 10) -> str:
        if len(self.messages) <= keep_recent:
            return "Nothing to compact."

        old = self.messages[:-keep_recent]
        recent = self.messages[-keep_recent:]

        summary_parts = []
        for msg in old:
            if msg.role == "user":
                summary_parts.append(f"User: {msg.content[:200]}")
            elif msg.role == "assistant":
                summary_parts.append(f"Assistant: {msg.content[:200]}")

        summary = "\n".join(summary_parts)
        summary_msg = ContextMessage(
            role="system",
            content=f"Previous conversation summary:\n{summary}",
        )

        self.messages = [summary_msg] + recent
        return f"Compacted {len(old)} messages into summary."

    def get_messages(self) -> list[dict[str, Any]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self) -> None:
        self.messages.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "compact_threshold": self.compact_threshold,
            "messages": [
                {"role": m.role, "content": m.content, "tokens": m.tokens}
                for m in self.messages
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextManager:
        mgr = cls(
            max_tokens=data.get("max_tokens", 128000),
            compact_threshold=data.get("compact_threshold", 0.8),
        )
        for m in data.get("messages", []):
            mgr.messages.append(
                ContextMessage(
                    role=m["role"],
                    content=m["content"],
                    tokens=m.get("tokens", 0),
                )
            )
        return mgr
