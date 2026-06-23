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

TASK SIZE: {task_size}

SIZE RULES:
- TINY (1-2 words like "fix bug", "make faster"): 1-2 subtasks only. Do NOT over-decompose.
- SMALL (simple request like "add dark mode"): 2-4 subtasks max.
- MEDIUM (multi-part like "build REST API with auth"): 4-7 subtasks.
- LARGE (complex like "build e-commerce platform"): 7-13 subtasks.
- Do NOT exceed the max subtasks for the size class.

DECOMPOSITION RULES:
1. Each subtask = ONE clear action by ONE cluster
2. Only split when the task genuinely needs different cluster specialties
3. Do NOT create redundant steps (e.g., "analyze" then "fix" then "verify fix" is 3 steps for 1 action)
4. Security (RedAlert) only when there's actual auth/validation involved — not as a generic "check"
5. Testing (Ratchet) only when there's actual code to test — not as a generic "verify"
6. If the task is vague, ASK what to build by returning a simple plan with clarification
7. Backend before frontend. Security after features. Testing last.

OUTPUT FORMAT:
{"subtasks":[{"task":"specific action description","cluster":"ClusterName","depends_on":[]}],"summary":"one sentence overview"}

depends_on: list of subtask indices (0-based) that must complete first. Empty = can start immediately."""

DECOMPOSE_SYSTEM = "You are an expert task planner. Reply with strict JSON only."


def classify_task_size(task: str) -> str:
    """Classify task complexity based on heuristics."""
    task_lower = task.lower()
    word_count = len(task.split())

    # Count complexity signals
    signals = 0
    multi_cluster_keywords = [
        "and", "with", "including", "also", "plus", "then",
        "frontend", "backend", "database", "api", "auth", "security",
        "test", "deploy", "migrate", "integrate",
    ]
    for kw in multi_cluster_keywords:
        if kw in task_lower:
            signals += 1

    # Check for multiple feature requests
    feature_markers = task_lower.count(",") + task_lower.count(" and ")
    signals += feature_markers * 2

    if word_count <= 4 and signals <= 1:
        return "TINY"
    elif word_count <= 12 and signals <= 2:
        return "SMALL"
    elif word_count <= 30 and signals <= 5:
        return "MEDIUM"
    else:
        return "LARGE"


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

        task_size = classify_task_size(task)
        logger.info("Task size: %s (%d words)", task_size, len(task.split()))

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)

        prompt = DECOMPOSE_PROMPT.replace("{task_size}", task_size)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DECOMPOSE_SYSTEM},
                {"role": "user", "content": f"{prompt}\n\nTASK:\n{task}"},
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

        plan = DecompositionPlan(
            subtasks=subtasks,
            summary=payload.get("summary", ""),
        )

        # Post-process: enforce size limits and clean up
        plan = self._postprocess(plan, task_size)
        return plan

    def decompose_simple(self, task: str) -> DecompositionPlan:
        """Fallback: treat the whole task as one subtask for UltraMagnus."""
        return DecompositionPlan(
            subtasks=[Subtask(task=task, cluster="UltraMagnus", index=0)],
            summary=task,
        )

    def _postprocess(self, plan: DecompositionPlan, task_size: str) -> DecompositionPlan:
        """Clean up the decomposition plan."""
        max_tasks = {"TINY": 2, "SMALL": 4, "MEDIUM": 7, "LARGE": 13}.get(task_size, 7)

        if len(plan.subtasks) <= max_tasks:
            return plan

        # Truncate to max and fix dependency indices
        truncated = plan.subtasks[:max_tasks]
        valid_indices = {s.index for s in truncated}

        for s in truncated:
            s.depends_on = [d for d in s.depends_on if d in valid_indices]

        logger.warning(
            "Truncated plan from %d to %d subtasks (size: %s)",
            len(plan.subtasks), len(truncated), task_size,
        )

        return DecompositionPlan(subtasks=truncated, summary=plan.summary)

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
