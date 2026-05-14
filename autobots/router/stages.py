"""Execution stages for cluster workflows."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .utils import PayloadValidator
from ..workspace import TargetProjectWorkspace

if TYPE_CHECKING:
    from .models import ClusterPlan, PhaseRecord


COORDINATION_LAWS = """Autobots Coordination Laws:
1. Use pessimistic locks for critical context files: architecture.md and security-auth.md.
2. Never write progress-tracker.md from a specialist, reviewer, or repair cluster.
3. A lightweight Optimus secretary model owns progress-tracker.md updates.
4. If a lock is stale for more than 60 seconds, reclaim it and continue.
5. Report task completion back to Optimus instead of editing shared progress state directly."""

SECRETARY_SNIPPET_CLUSTERS = {"UltraMagnus", "Jazz"}
PROTECTED_PROGRESS_FILES = {"progress-tracker.md"}


class StageExecutor:
    """Executes different stages of the execution workflow."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.client = self._build_client() if api_key else None

    def run_command_stage(
        self,
        plan: ClusterPlan,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
    ) -> tuple[dict, str]:
        """Run command/planning stage."""
        prompt = f"""
You are the command tier of the Autobots swarm.
Use hierarchical reasoning to prepare a concise execution brief for the specialist cluster.
Treat the coordination rules below as hard laws.

{COORDINATION_LAWS}

Current phase:
{phase.raw_line}

Roadmap:
{roadmap_text}

Progress tracker:
{progress_text}

Selected primary cluster: {plan.primary_cluster}
Primary lead model: {plan.primary_lead.model_id}
Primary reviewer model: {plan.primary_reviewer.model_id}
Support models: {", ".join(model.model_id for model in plan.primary_support) or "None"}

Return strict JSON:
{{
  "summary": "one paragraph mission brief",
  "implementation_goals": ["goal 1", "goal 2"],
  "risks": ["risk 1"],
  "acceptance_checks": ["check 1", "check 2"]
}}
""".strip()
        raw = self._complete(plan.command_lead.model_id, prompt)
        payload = PayloadValidator.parse_json(raw)
        PayloadValidator.validate_command_payload(payload)
        return payload, raw

    def run_specialist_stage(
        self,
        plan: ClusterPlan,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        command_payload: dict,
        event_handler=None,
    ) -> tuple[dict, str]:
        """Run specialist implementation stage."""
        progress_context_label = "Progress tracker"
        progress_context = progress_text
        if plan.primary_cluster in SECRETARY_SNIPPET_CLUSTERS:
            progress_context_label = f"Optimus secretary timeline snippet from progress-tracker.md"
            progress_context = self._build_progress_tracker_snippet(phase, progress_text)
            if event_handler:
                event_handler(
                    f"Optimus secretary {plan.secretary_lead.model_id} injected a timeline snippet for {plan.primary_cluster}."
                )

        prompt = f"""
You are the {plan.primary_cluster} implementation cluster.
The command tier and support models have already coordinated your mission.
Act as a collaborative cluster: the lead writes, the reviewer critiques, and support models fill gaps.
Treat the coordination rules below as hard laws.

{COORDINATION_LAWS}

Workspace constraints:
1. Write to appropriate project roots: src/, app/, lib/, tests/, docs/, scripts/, or context/.
2. Choose the root that matches the file type and project structure.
3. Never write in the Autobots engine repository itself.
4. Return full file contents, not diffs.
5. Never write `progress-tracker.md`; report progress back to Optimus instead.

Target roots available:
- src root: {workspace.src_root}
- app root: {workspace.target_root / "app"}
- lib root: {workspace.target_root / "lib"}
- tests root: {workspace.target_root / "tests"}
- docs root: {workspace.target_root / "docs"}
- scripts root: {workspace.target_root / "scripts"}
- context root: {workspace.context_root}

Phase:
{phase.raw_line}

Roadmap:
{roadmap_text}

{progress_context_label}:
{progress_context}

Execution brief:
{json.dumps(command_payload, indent=2)}

Cluster composition:
- Lead: {plan.primary_lead.model_id}
- Reviewer: {plan.primary_reviewer.model_id}
- Support: {", ".join(model.model_id for model in plan.primary_support) or "None"}

Return strict JSON:
{{
  "summary": "what the cluster changed",
  "implementation_notes": ["note 1", "note 2"],
  "files": [
    {{
      "root": "src",
      "path": "relative/path.ext",
      "content": "full file content"
    }}
  ]
}}
""".strip()
        raw = self._complete(plan.primary_lead.model_id, prompt)
        payload = PayloadValidator.parse_json(raw)
        if "files" not in payload:
            payload["files"] = []
        PayloadValidator.validate_specialist_payload(payload)
        return payload, raw

    def run_safety_stage(
        self,
        plan: ClusterPlan,
        phase: PhaseRecord,
        specialist_payload: dict,
        command_payload: dict,
    ) -> tuple[dict, str]:
        """Run safety review stage."""
        prompt = f"""
You are Red Alert reviewing the specialist cluster output for correctness, safety, and maintainability.
Treat the coordination rules below as hard laws.

{COORDINATION_LAWS}

Phase:
{phase.raw_line}

Command brief:
{json.dumps(command_payload, indent=2)}

Specialist output:
{json.dumps(specialist_payload, indent=2)}

Return strict JSON:
{{
  "status": "pass" or "revise",
  "summary": "review verdict",
  "issues": ["issue 1", "issue 2"]
}}
""".strip()
        raw = self._complete(plan.safety_lead.model_id, prompt)
        payload = PayloadValidator.parse_json(raw)
        payload.setdefault("issues", [])
        payload.setdefault("status", "pass")
        PayloadValidator.validate_review_payload(payload)
        return payload, raw

    def run_repair_stage(
        self,
        plan: ClusterPlan,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        command_payload: dict,
        specialist_payload: dict,
        review_payload: dict,
    ) -> tuple[dict, str]:
        """Run repair/refinement stage."""
        prompt = f"""
You are Ratchet, the repair cluster.
Revise the implementation after autonomous review and feedback from the swarm.
Treat the coordination rules below as hard laws.

{COORDINATION_LAWS}

Workspace constraints:
1. Write to appropriate project roots: src/, app/, lib/, tests/, docs/, scripts/, or context/.
2. Choose the root that matches the file type and project structure.
3. Never write in the Autobots engine repository itself.
4. Return full file contents, not diffs.
5. Never write `progress-tracker.md`; report progress back to Optimus instead.

Target roots available:
- src root: {workspace.src_root}
- app root: {workspace.target_root / "app"}
- lib root: {workspace.target_root / "lib"}
- tests root: {workspace.target_root / "tests"}
- docs root: {workspace.target_root / "docs"}
- scripts root: {workspace.target_root / "scripts"}
- context root: {workspace.context_root}

Phase:
{phase.raw_line}

Roadmap:
{roadmap_text}

Progress tracker:
{progress_text}

Command brief:
{json.dumps(command_payload, indent=2)}

Previous implementation:
{json.dumps(specialist_payload, indent=2)}

Repair instructions:
{json.dumps(review_payload, indent=2)}

Return strict JSON:
{{
  "summary": "what Ratchet improved",
  "files": [
    {{
      "root": "src",
      "path": "relative/path.ext",
      "content": "full file content"
    }}
  ]
}}
""".strip()
        raw = self._complete(plan.repair_lead.model_id, prompt)
        payload = PayloadValidator.parse_json(raw)
        if "files" not in payload:
            payload["files"] = []
        PayloadValidator.validate_repair_payload(payload)
        return payload, raw

    def _complete(self, model_id: str, prompt: str) -> str:
        """Call model for completion."""
        if self.client is None:
            raise RuntimeError("NVIDIA_API_KEY is missing. Cannot execute the swarm.")

        response = self.client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are part of a hierarchical Autobots coding swarm. "
                        "Autobots Coordination Laws are mandatory. "
                        "Never write progress-tracker.md unless you are the Optimus secretary. "
                        "Use pessimistic locks for architecture.md and security-auth.md with a 60 second stale-lock reclaim rule. "
                        "Reply with strict JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    def _build_client(self):
        from openai import OpenAI

        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self.api_key,
        )

    def _build_progress_tracker_snippet(self, phase: PhaseRecord, progress_text: str) -> str:
        """Build a snippet of progress tracker for secretary clusters."""
        lines = progress_text.splitlines()
        if not lines:
            return phase.raw_line

        start = max(0, phase.line_index - 2)
        end = min(len(lines), phase.line_index + 3)
        snippet_lines: list[str] = []
        for index in range(start, end):
            prefix = ">>" if index == phase.line_index else "  "
            snippet_lines.append(f"{prefix} line {index + 1}: {lines[index]}")
        return "\n".join(snippet_lines)
