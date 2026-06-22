from __future__ import annotations

import sys
from typing import TextIO

from openai import OpenAI

from autobots.repl.session import ReplSession


def run_repl(
    client: OpenAI | None = None,
    model: str = "meta/llama-3.1-8b-instruct",
    system_prompt: str = "",
    prompt: str = "You> ",
) -> None:
    session = ReplSession(client=client, model=model, system_prompt=system_prompt)
    session._running = True

    print(f"Autobots REPL (model: {model})")
    print("Type /help for commands, /exit to quit.\n")

    while session._running:
        try:
            user_input = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input.strip():
            continue

        response = session.send(user_input)
        print(f"\n{response}\n")


def run_one_shot(
    prompt: str,
    client: OpenAI | None = None,
    model: str = "meta/llama-3.1-8b-instruct",
    system_prompt: str = "",
) -> str:
    session = ReplSession(client=client, model=model, system_prompt=system_prompt)
    return session.send(prompt)


def run_piped(
    input_stream: TextIO | None = None,
    prompt: str = "Explain this code:",
    client: OpenAI | None = None,
    model: str = "meta/llama-3.1-8b-instruct",
    system_prompt: str = "",
) -> str:
    stream = input_stream or sys.stdin
    content = stream.read()
    if not content.strip():
        return "No input provided."

    full_prompt = f"{prompt}\n\n```\n{content}\n```"
    session = ReplSession(client=client, model=model, system_prompt=system_prompt)
    return session.send(full_prompt)
