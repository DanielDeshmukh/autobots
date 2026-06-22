from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class HookPoint(Enum):
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_PROMPT = "pre_prompt"
    POST_RESPONSE = "post_response"


class HookResult:
    def __init__(
        self,
        success: bool,
        output: str = "",
        error: str = "",
        abort: bool = False,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.abort = abort

    @property
    def ok(self) -> bool:
        return self.success and not self.abort


@dataclass
class Hook:
    name: str
    point: HookPoint
    command: str | None = None
    callback: Callable[..., HookResult] | None = None
    enabled: bool = True


class HookManager:
    def __init__(self) -> None:
        self._hooks: dict[HookPoint, list[Hook]] = {
            point: [] for point in HookPoint
        }

    def register(self, hook: Hook) -> None:
        self._hooks[hook.point].append(hook)

    def unregister(self, name: str) -> bool:
        for point, hooks in self._hooks.items():
            for i, hook in enumerate(hooks):
                if hook.name == name:
                    hooks.pop(i)
                    return True
        return False

    def get_hooks(self, point: HookPoint) -> list[Hook]:
        return [h for h in self._hooks[point] if h.enabled]

    def execute(self, point: HookPoint, **kwargs: Any) -> list[HookResult]:
        results = []
        for hook in self.get_hooks(point):
            result = self._run_hook(hook, **kwargs)
            results.append(result)
            if result.abort:
                break
        return results

    def _run_hook(self, hook: Hook, **kwargs: Any) -> HookResult:
        if hook.callback:
            try:
                return hook.callback(**kwargs)
            except Exception as e:
                return HookResult(success=False, error=str(e))

        if hook.command:
            return self._run_command(hook.command, **kwargs)

        return HookResult(success=True)

    def _run_command(self, command: str, **kwargs: Any) -> HookResult:
        import os

        env = os.environ.copy()
        for key, value in kwargs.items():
            if isinstance(value, str):
                env[f"HOOK_{key.upper()}"] = value

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            return HookResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                abort=result.returncode != 0,
            )
        except subprocess.TimeoutExpired:
            return HookResult(success=False, error="Hook timed out", abort=True)
        except Exception as e:
            return HookResult(success=False, error=str(e), abort=True)
