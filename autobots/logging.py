"""Logging configuration for autobots."""
from __future__ import annotations

import logging
import os

_CONFIGURED = False


def setup_logging(level: int | None = None) -> None:
    """Configure root autobots logger.

    Call once at CLI startup. Subsequent calls are no-ops.
    Set AUTOBOTS_LOG_LEVEL=DEBUG to override the default INFO level.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    if level is None:
        env_level = os.getenv("AUTOBOTS_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, env_level, logging.INFO)

    root = logging.getLogger("autobots")
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
