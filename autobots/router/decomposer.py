"""Task decomposer — breaks complex tasks into subtasks with cluster assignments."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("autobots")

DECOMPOSE_PROMPT = """You are a task decomposition expert for a coding swarm with 9 specialized clusters.

CLUSTER ROLES:
- Optimus: Command, planning, orchestration, roadmaps
- UltraMagnus: Backend, APIs, databases, architecture, Python, Node.js
- RedAlert: Security, auth, validation, safety, guardrails
- Jazz: Frontend, UI, CSS, React, visual design, components
- Ratchet: Debugging, fixing, refactoring, testing, repair
- Perceptor: Document parsing, OCR, search, retrieval, embeddings
- Bumblebee: Speech, voice, translation, transcription, media
- Ironhide: Simulation, physics, optimization, prediction
- Wheeljack: Science, research, molecules, proteins, data analysis

YOUR JOB:
Break the user's task into concrete subtasks. Assign each to the BEST cluster.
If a task needs multiple clusters, split it into subtasks.

RULES:
- Each subtask must be ONE clear action
- Assign to the cluster whose role matches best
- Order matters: backend before frontend fixes, security after features
- Return ONLY valid JSON, no explanation

OUTPUT FORMAT:
{"subtasks":[{"task":"specific action description","cluster":"ClusterName","depends_on":[]}],"summary":"one sentence overview"}

depends_on: list of subtask indices (0-based) that must complete first. Empty = can start immediately."""

DECOMPOSE_SYSTEM = "You are an expert task planner. Reply with strict JSON only."


@dataclass
class Subtask:
    task: str
    cluster: str
    depends_on: list[int] = field(default_factory=list)
    index: int = 0


@dataclass
class DecompositionPlan:
    subtasks: list[Subtask]
    summary: str


class TaskDecomposer:
    """Uses Optimus model to decompose complex tasks into cluster-assigned subtasks."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://integrate.api.nvidia.com/v1"):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.base_url = base_url
        self.model = "meta/llama-3.3-70b-instruct"

    def decompose(self, task: str) -> DecompositionPlan:
        """Decompose a task into subtasks with cluster assignments."""
        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DECOMPOSE_SYSTEM},
                {"role": "user", "content": f"{DECOMPOSE_PROMPT}\n\nTASK:\n{task}"},
            ],
            temperature=0.2,
            max_tokens=2048,
            stream=False,
        )

        raw = response.choices[0].message.content or ""
        payload = self._parse_json(raw)

        subtasks = []
        for i, item in enumerate(payload.get("subtasks", [])):
            subtasks.append(Subtask(
                task=item.get("task", ""),
                cluster=item.get("cluster", "UltraMagnus"),
                depends_on=item.get("depends_on", []),
                index=i,
            ))

        return DecompositionPlan(
            subtasks=subtasks,
            summary=payload.get("summary", ""),
        )

    def decompose_simple(self, task: str) -> DecompositionPlan:
        """Fallback: treat the whole task as one subtask for UltraMagnus."""
        return DecompositionPlan(
            subtasks=[Subtask(task=task, cluster="UltraMagnus", index=0)],
            summary=task,
        )

    @staticmethod
    def _parse_json(raw: str) -> dict:
        candidate = raw.strip()
        fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", candidate, re.DOTALL)
        if fenced:
            candidate = fenced.group(1).strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1:
            candidate = candidate[start:end + 1]
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            logger.warning("Failed to parse decomposition response")
            return {}
