from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MCPClient:
    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None):
        self.command = command
        self.args = args or []
        self.env = env
        self._process: subprocess.Popen | None = None
        self._tools: list[MCPTool] = []
        self._connected = False

    def connect(self) -> bool:
        try:
            import os

            full_env = os.environ.copy()
            if self.env:
                full_env.update(self.env)

            self._process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                text=True,
            )
            self._connected = True
            self._discover_tools()
            return True
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        self._connected = False
        self._tools.clear()

    @property
    def connected(self) -> bool:
        return self._connected and self._process is not None and self._process.poll() is None

    def _send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not self.connected or not self._process or not self._process.stdin or not self._process.stdout:
            return None

        request = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params:
            request["params"] = params

        try:
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline()
            if line:
                return json.loads(line)
        except Exception:
            pass
        return None

    def _discover_tools(self) -> None:
        response = self._send_request("tools/list")
        if response and "result" in response:
            tools_data = response["result"].get("tools", [])
            self._tools = [
                MCPTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                )
                for t in tools_data
            ]

    def list_tools(self) -> list[MCPTool]:
        return list(self._tools)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        response = self._send_request("tools/call", {"name": name, "arguments": arguments})
        if response:
            if "result" in response:
                return {"success": True, "result": response["result"]}
            if "error" in response:
                return {"success": False, "error": response["error"]}
        return {"success": False, "error": "No response from MCP server"}
