"""Execution stages for cluster workflows."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

from rich.console import Console

from .utils import PayloadValidator
from ..workspace import TargetProjectWorkspace
from ..skills.loader import load_skill_pack
from ..utils.retry import with_retry

if TYPE_CHECKING:
    from .models import ClusterPlan, PhaseRecord
    from ..costs import UsageTracker
    from ..context_budget import ContextBudgetManager

logger = logging.getLogger("autobots")
console = Console()


COORDINATION_LAWS = """Autobots Coordination Laws:
1. Use pessimistic locks for critical context files: architecture.md and security-auth.md.
2. Never write progress-tracker.md from a specialist, reviewer, or repair cluster.
3. A lightweight Optimus secretary model owns progress-tracker.md updates.
4. If a lock is stale for more than 60 seconds, reclaim it and continue.
5. Report task completion back to Optimus instead of editing shared progress state directly."""

SECRETARY_SNIPPET_CLUSTERS = {"UltraMagnus", "Jazz"}
PROTECTED_PROGRESS_FILES = {"progress-tracker.md"}
ROLE_PROMPT_HEADERS = {
    "planner": "You are the command tier of the Autobots swarm.",
    "implementer": "You are the implementation cluster for this phase.",
    "reviewer": "You are Red Alert reviewing the specialist cluster output for correctness, safety, and maintainability.",
    "repair": "You are Ratchet, the repair cluster.",
}


class StageExecutor:
    """Executes different stages of the execution workflow."""

    def __init__(
        self,
        api_key: str | None = None,
        workspace_root: str | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        usage_tracker: "UsageTracker | None" = None,
        context_budget_manager: "ContextBudgetManager | None" = None,
    ):
        self.api_key = api_key
        self.workspace_root = workspace_root
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = self._build_client() if api_key else None
        self.usage_tracker = usage_tracker
        self.context_budget_manager = context_budget_manager

    def run_command_stage(
        self,
        plan: ClusterPlan,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
    ) -> tuple[dict, str]:
        """Run command/planning stage."""
        prompt = self._build_command_prompt(plan, phase, roadmap_text, progress_text)
        raw = self._complete(plan.command_lead.model_id, prompt, "Optimus")
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

        prompt = self._build_specialist_prompt(
            plan,
            workspace,
            phase,
            roadmap_text,
            progress_context_label,
            progress_context,
            command_payload,
        )
        raw = self._complete(plan.primary_lead.model_id, prompt, plan.primary_cluster)
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
        prompt = self._build_review_prompt(plan, phase, specialist_payload, command_payload)
        raw = self._complete(plan.safety_lead.model_id, prompt, "RedAlert")
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
        prompt = self._build_repair_prompt(
            plan,
            workspace,
            phase,
            roadmap_text,
            progress_text,
            command_payload,
            specialist_payload,
            review_payload,
        )
        raw = self._complete(plan.repair_lead.model_id, prompt, "Ratchet")
        payload = PayloadValidator.parse_json(raw)
        if "files" not in payload:
            payload["files"] = []
        PayloadValidator.validate_repair_payload(payload)
        return payload, raw

    def _complete(self, model_id: str, prompt: str, cluster_name: str | None = None) -> str:
        """Call model for completion with retry on transient failures."""
        if self.client is None:
            raise RuntimeError("NVIDIA_API_KEY is missing. Cannot execute the swarm.")

        system_content = (
            "You are part of a hierarchical Autobots coding swarm. "
            "Autobots Coordination Laws are mandatory. "
            "Never write progress-tracker.md unless you are the Optimus secretary. "
            "Use pessimistic locks for architecture.md and security-auth.md with a 60 second stale-lock reclaim rule. "
            "Reply with strict JSON only."
        )

        if self.workspace_root and cluster_name:
            skill_pack = load_skill_pack(self.workspace_root, cluster_name)
            if skill_pack:
                system_content = f"{system_content}\n\n{skill_pack}"

        return self._call_model(model_id, system_content, prompt)

    @with_retry(max_attempts=3, base_delay=1.0)
    def _call_model(self, model_id: str, system_content: str, user_prompt: str) -> str:
        """Single model call with streaming — retried by with_retry on transient errors."""
        logger.debug("Calling %s (temperature=%.2f, max_tokens=%d)", model_id, self.temperature, self.max_tokens)

        # Verbose mode: log full prompts
        try:
            from ..cli import VERBOSE
            if VERBOSE:
                console.print(f"\n[dim]{'='*60} VERBOSE MODE {'='*60}[/dim]")
                console.print(f"[dim]Model: {model_id}[/dim]")
                console.print(f"[dim]System prompt ({len(system_content)} chars):[/dim]")
                console.print(system_content[:2000] + ("..." if len(system_content) > 2000 else ""))
                console.print(f"\n[dim]User prompt ({len(user_prompt)} chars):[/dim]")
                console.print(user_prompt[:2000] + ("..." if len(user_prompt) > 2000 else ""))
                console.print(f"[dim]{'='*60} END VERBOSE {'='*60}[/dim]\n")
        except Exception:
            pass

        # Check context budget if manager is available
        if self.context_budget_manager:
            budget = self.context_budget_manager.create_budget(model_id)
            budget.system_tokens = self.context_budget_manager.estimate_tokens(system_content)
            budget.prompt_tokens = self.context_budget_manager.estimate_tokens(user_prompt)

            warnings = self.context_budget_manager.check_budget(budget)
            for warning in warnings:
                if warning.level == "overflow":
                    logger.warning("Context overflow detected for %s: truncating prompt", model_id)
                    user_prompt, _ = self.context_budget_manager.truncate_to_fit(
                        user_prompt, budget, preserve_start=True
                    )
                elif warning.level == "critical":
                    logger.warning("Context critical for %s: %s", model_id, warning.message)

        return self._call_model_streaming(model_id, system_content, user_prompt)

    def _call_model_streaming(self, model_id: str, system_content: str, user_prompt: str) -> str:
        """Stream model response with live character counter."""
        full_response = []
        start_time = time.time()
        input_tokens = 0
        output_tokens = 0

        with console.status("", spinner="dots") as status:
            for chunk in self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    full_response.append(delta)
                    elapsed = time.time() - start_time
                    char_count = sum(len(r) for r in full_response)
                    status.update(f"[dim]Receiving response · {char_count} chars · {elapsed:.1f}s[/dim]")

                # Extract usage from final chunk
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens or 0
                    output_tokens = chunk.usage.completion_tokens or 0

        # Record usage if tracker is available
        if self.usage_tracker and (input_tokens > 0 or output_tokens > 0):
            duration_ms = (time.time() - start_time) * 1000
            self.usage_tracker.record(
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
            )

        return "".join(full_response)

    def _build_client(self):
        from openai import OpenAI
        import httpx

        return OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=httpx.Client(
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=120.0,
                    write=10.0,
                    pool=5.0,
                )
            ),
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

    def _build_command_prompt(self, plan: ClusterPlan, phase: PhaseRecord, roadmap_text: str, progress_text: str) -> str:
        routing_block = "\n".join(f"- {reason}" for reason in plan.routing_rationale) or "- No routing rationale recorded."
        role_block = self._format_role_assignments(plan)
        parallel_block = self._format_parallel_workstreams(plan)
        return f"""
{ROLE_PROMPT_HEADERS["planner"]}
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

Routing rationale:
{routing_block}

Role assignments:
{role_block}

Parallel workstream candidates:
{parallel_block}

Return strict JSON:
{{
  "summary": "one paragraph mission brief",
  "implementation_goals": ["goal 1", "goal 2"],
  "risks": ["risk 1"],
  "acceptance_checks": ["check 1", "check 2"]
}}
""".strip()

    def _build_specialist_prompt(
        self,
        plan: ClusterPlan,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_context_label: str,
        progress_context: str,
        command_payload: dict,
    ) -> str:
        return f"""
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
- Merge strategy: {plan.merge_strategy}

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

    def _build_review_prompt(self, plan: ClusterPlan, phase: PhaseRecord, specialist_payload: dict, command_payload: dict) -> str:
        return f"""
{ROLE_PROMPT_HEADERS["reviewer"]}
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

    def _build_repair_prompt(
        self,
        plan: ClusterPlan,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        command_payload: dict,
        specialist_payload: dict,
        review_payload: dict,
    ) -> str:
        return f"""
{ROLE_PROMPT_HEADERS["repair"]}
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

    def _format_role_assignments(self, plan: ClusterPlan) -> str:
        lines: list[str] = []
        for assignment in plan.role_assignments:
            lines.append(
                f"- {assignment.role_name}: {assignment.cluster_name} lead={assignment.lead.model_id}"
            )
        return "\n".join(lines) if lines else "- None"

    def _format_parallel_workstreams(self, plan: ClusterPlan) -> str:
        lines: list[str] = []
        for branch in plan.parallel_workstreams:
            lines.append(
                f"- {branch.branch_id}: cluster={branch.assigned_cluster} paths={', '.join(branch.focus_paths)}"
            )
        return "\n".join(lines) if lines else "- None"
