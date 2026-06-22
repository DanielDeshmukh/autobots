from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import OpenAI

from autobots.repl.commands import CommandRegistry


@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class SessionStats:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    turn_count: int = 0

    @property
    def estimated_cost(self) -> float:
        return (self.total_input_tokens * 0.003 + self.total_output_tokens * 0.015) / 1000


class ReplSession:
    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = "meta/llama-3.1-8b-instruct",
        system_prompt: str = "",
        commands: CommandRegistry | None = None,
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt or "You are a helpful coding assistant."
        self.messages: list[Message] = []
        self.stats = SessionStats()
        self.commands = commands or CommandRegistry()
        self._running = False

    def add_message(self, role: str, content: str, **kwargs: Any) -> Message:
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        return msg

    def get_api_messages(self) -> list[dict[str, Any]]:
        result = [{"role": "system", "content": self.system_prompt}]
        for msg in self.messages:
            result.append(msg.to_dict())
        return result

    def send(self, user_input: str) -> str:
        if user_input.startswith("/"):
            return self.commands.execute(user_input, self)

        self.add_message("user", user_input)
        self.stats.turn_count += 1

        if self.client is None:
            return "Error: No API client configured. Set NVIDIA_API_KEY."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.get_api_messages(),
                temperature=0.7,
                max_tokens=4096,
            )
            choice = response.choices[0]
            content = choice.message.content or ""

            if choice.message.usage:
                self.stats.total_input_tokens += choice.message.usage.prompt_tokens
                self.stats.total_output_tokens += choice.message.usage.completion_tokens

            self.add_message("assistant", content)
            return content

        except Exception as e:
            return f"Error: {e}"

    def compact(self) -> str:
        if len(self.messages) < 4:
            return "Nothing to compact yet."

        summary_parts = []
        for msg in self.messages:
            if msg.role == "user":
                summary_parts.append(f"User asked: {msg.content[:200]}")
            elif msg.role == "assistant":
                summary_parts.append(f"Assistant said: {msg.content[:200]}")

        summary = "\n".join(summary_parts)
        self.messages = [Message(role="system", content=f"Previous conversation summary:\n{summary}")]
        return f"Conversation compacted. {len(summary_parts)} messages summarized."

    def save(self, path: str | Path) -> None:
        p = Path(path)
        data = {
            "model": self.model,
            "system_prompt": self.system_prompt,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.messages
            ],
            "stats": {
                "total_input_tokens": self.stats.total_input_tokens,
                "total_output_tokens": self.stats.total_output_tokens,
                "total_tool_calls": self.stats.total_tool_calls,
                "turn_count": self.stats.turn_count,
            },
        }
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path, client: OpenAI | None = None) -> ReplSession:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        session = cls(client=client, model=data["model"], system_prompt=data["system_prompt"])
        for m in data.get("messages", []):
            session.messages.append(
                Message(role=m["role"], content=m["content"], timestamp=m.get("timestamp", 0))
            )
        stats = data.get("stats", {})
        session.stats.total_input_tokens = stats.get("total_input_tokens", 0)
        session.stats.total_output_tokens = stats.get("total_output_tokens", 0)
        session.stats.total_tool_calls = stats.get("total_tool_calls", 0)
        session.stats.turn_count = stats.get("turn_count", 0)
        return session
