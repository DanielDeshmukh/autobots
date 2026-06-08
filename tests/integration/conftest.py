"""
Shared fixtures for integration tests.

These tests hit the live NVIDIA NIM API and require a valid NVIDIA_API_KEY.
They auto-skip when the key is missing so the regular test suite stays fast.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from openai import OpenAI


API_KEY = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests when the API key is absent."""
    if not API_KEY:
        skip_marker = pytest.mark.skip(reason="NVIDIA_API_KEY not set — skipping integration tests")
        for item in items:
            fspath = str(item.fspath)
            if "tests\\integration" in fspath or "tests/integration" in fspath:
                item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def api_key() -> str:
    assert API_KEY, "NVIDIA_API_KEY must be set to run integration tests"
    return API_KEY


@pytest.fixture(scope="session")
def nim_client(api_key: str) -> OpenAI:
    """Shared OpenAI client pointed at NVIDIA NIM."""
    return OpenAI(api_key=api_key, base_url=NIM_BASE_URL)


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """
    Creates a minimal target project workspace with the context/ directory.
    Tests can add files to this workspace to control skill injection.
    """
    ctx = tmp_path / "context"
    ctx.mkdir(parents=True, exist_ok=True)

    # Write a minimal conventions.md so skill injection has something to load
    (ctx / "conventions.md").write_text(
        "Use Python 3.11+.\nUse type hints.\nUse snake_case for functions.\n",
        encoding="utf-8",
    )

    # Create standard project roots
    for root in ("src", "tests", "docs"):
        (tmp_path / root).mkdir(exist_ok=True)

    return tmp_path
