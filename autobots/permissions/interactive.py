from __future__ import annotations

import sys
from typing import Any

from autobots.tools.permissions import Permission


def prompt_permission(
    tool_name: str,
    args: dict[str, Any],
    description: str = "",
) -> tuple[Permission, str]:
    lines = [f"\nAllow {tool_name}?"]
    if description:
        lines.append(f"  {description}")
    if args:
        for key, value in args.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            lines.append(f"  {key}: {val_str}")
    lines.append("  [y]es / [n]o / [a]lways / [Esc] cancel")
    print("\n".join(lines))

    try:
        if sys.platform == "win32":
            import msvcrt

            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b"\r", b"\n"):
                        return Permission.ASK, ""
                    if ch == b"\x1b":
                        return Permission.DENY, "cancelled"
                    if ch in (b"y", b"Y"):
                        return Permission.ALLOW, "yes"
                    if ch in (b"n", b"N"):
                        return Permission.DENIED, "no"
                    if ch in (b"a", b"A"):
                        return Permission.ALLOW, "always"
        else:
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == "\r" or ch == "\n":
                    return Permission.ASK, ""
                if ch == "\x1b":
                    return Permission.DENY, "cancelled"
                if ch in ("y", "Y"):
                    return Permission.ALLOW, "yes"
                if ch in ("n", "N"):
                    return Permission.DENIED, "no"
                if ch in ("a", "A"):
                    return Permission.ALLOW, "always"
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    except (ImportError, OSError):
        pass

    return Permission.ASK, ""
