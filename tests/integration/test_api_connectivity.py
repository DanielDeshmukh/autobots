"""API connectivity and model health checks against NVIDIA NIM."""
from __future__ import annotations

import json

import pytest
from openai import OpenAI


PRIMARY_MODEL = "qwen/qwen3-coder-480b-a35b-instruct"
FAST_MODEL = "meta/llama-3.1-8b-instruct"


class TestAPIConnectivity:
    """Verify that the NVIDIA NIM endpoint is reachable and models respond."""

    def test_primary_model_responds(self, nim_client: OpenAI) -> None:
        """The main coding model returns a coherent Python function."""
        response = nim_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": "Write a Python function that adds two numbers."}],
            max_tokens=200,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        assert content is not None, "Model returned empty content"
        assert "def " in content, "Model did not return a function definition"
        assert len(content) > 50, "Model response is suspiciously short"

    def test_fast_model_responds(self, nim_client: OpenAI) -> None:
        """The cheap/fast model is also accessible."""
        response = nim_client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": "Say hello in one sentence."}],
            max_tokens=50,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        assert content is not None, "Fast model returned empty content"
        assert len(content) > 5, "Fast model response is suspiciously short"

    def test_model_respects_json_instruction(self, nim_client: OpenAI) -> None:
        """Model can return valid JSON when instructed — the core contract for all stages."""
        response = nim_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": "Reply with strict JSON only."},
                {"role": "user", "content": 'Return {"status": "ok", "count": 1}'},
            ],
            max_tokens=100,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        assert content is not None
        # Strip markdown fences if present
        cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(cleaned)
        assert parsed["status"] == "ok"
        assert parsed["count"] == 1


class TestSkillInjection:
    """Verify that skill packs in the system prompt influence model output."""

    def test_conventions_affect_output(self, nim_client: OpenAI) -> None:
        """When conventions.md is injected, the model should follow the rules."""
        conventions = (
            "Coding conventions:\n"
            "- Use Python 3.11+\n"
            "- Always add type hints\n"
            "- Always add a docstring\n"
            "- Use snake_case\n"
        )
        response = nim_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": f"Follow these conventions:\n{conventions}"},
                {"role": "user", "content": "Write a function that validates an email address."},
            ],
            max_tokens=400,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        assert content is not None
        assert "def " in content, "No function definition"
        # Check for docstring
        assert '"""' in content or "'''" in content, "Missing docstring"
        # Check for type hints
        assert "-> " in content, "Missing return type hint"

    def test_json_only_output_with_system_prompt(self, nim_client: OpenAI) -> None:
        """The full system prompt used by the swarm still produces valid JSON."""
        system = (
            "You are part of a hierarchical Autobots coding swarm. "
            "Reply with strict JSON only."
        )
        response = nim_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "Create a command payload for the task: Add login page."},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        assert content is not None
        cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(cleaned)
        assert "summary" in parsed or "implementation_goals" in parsed
