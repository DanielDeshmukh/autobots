from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autobots.repl.session import ReplSession


class SlashCommand(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, args: str, session: ReplSession) -> str:
        ...


class HelpCommand(SlashCommand):
    name = "/help"
    description = "Show available commands"

    def execute(self, args: str, session: ReplSession) -> str:
        lines = ["Available commands:"]
        for cmd in session.commands.list_commands():
            lines.append(f"  {cmd.name} - {cmd.description}")
        return "\n".join(lines)


class ClearCommand(SlashCommand):
    name = "/clear"
    description = "Clear conversation history"

    def execute(self, args: str, session: ReplSession) -> str:
        count = len(session.messages)
        session.messages.clear()
        return f"Cleared {count} messages."


class CostCommand(SlashCommand):
    name = "/cost"
    description = "Show token usage and estimated cost"

    def execute(self, args: str, session: ReplSession) -> str:
        s = session.stats
        lines = [
            f"Turns: {s.turn_count}",
            f"Input tokens: {s.total_input_tokens:,}",
            f"Output tokens: {s.total_output_tokens:,}",
            f"Estimated cost: ${s.estimated_cost:.4f}",
        ]
        return "\n".join(lines)


class CompactCommand(SlashCommand):
    name = "/compact"
    description = "Summarize conversation to save tokens"

    def execute(self, args: str, session: ReplSession) -> str:
        return session.compact()


class ModelCommand(SlashCommand):
    name = "/model"
    description = "Switch model (e.g., /model meta/llama-3.1-70b-instruct)"

    def execute(self, args: str, session: ReplSession) -> str:
        if not args.strip():
            return f"Current model: {session.model}"
        old = session.model
        session.model = args.strip()
        return f"Model switched: {old} -> {session.model}"


class ExitCommand(SlashCommand):
    name = "/exit"
    description = "Exit the REPL"

    def execute(self, args: str, session: ReplSession) -> str:
        session._running = False
        return "Goodbye!"


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}
        self.register_default()

    def register_default(self) -> None:
        for cmd_cls in [
            HelpCommand,
            ClearCommand,
            CostCommand,
            CompactCommand,
            ModelCommand,
            ExitCommand,
        ]:
            self.register(cmd_cls())

    def register(self, command: SlashCommand) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    def list_commands(self) -> list[SlashCommand]:
        return list(self._commands.values())

    def execute(self, text: str, session: ReplSession) -> str:
        parts = text.split(maxsplit=1)
        name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        cmd = self._commands.get(name)
        if cmd is None:
            return f"Unknown command: {name}. Type /help for available commands."

        return cmd.execute(args, session)
