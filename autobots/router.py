from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable

from dotenv import load_dotenv

from .catalog import ClusterCatalog, ModelSpec
from .workspace import TargetProjectWorkspace


load_dotenv()


STATUS_PRIORITY = ("IN_PROGRESS", "PENDING")
STATUS_PATTERN = re.compile(r"\b(PENDING|IN_PROGRESS|COMPLETE)\b")
CHECKBOX_PATTERN = re.compile(r"\[( |x|~)\]")
PROGRESS_TRACKER_FILE = "progress-tracker.md"
PROTECTED_PROGRESS_FILES = {PROGRESS_TRACKER_FILE}
COORDINATION_LAWS = """Autobots Coordination Laws:
1. Use pessimistic locks for critical context files: architecture.md and security-auth.md.
2. Never write progress-tracker.md from a specialist, reviewer, or repair cluster.
3. A lightweight Optimus secretary model owns progress-tracker.md updates.
4. If a lock is stale for more than 60 seconds, reclaim it and continue.
5. Report task completion back to Optimus instead of editing shared progress state directly."""


@dataclass
class PhaseRecord:
    line_index: int
    raw_line: str
    title: str
    status: str


@dataclass
class ClusterMessage:
    speaker: str
    objective: str
    summary: str


@dataclass
class ClusterPlan:
    primary_cluster: str
    primary_lead: ModelSpec
    primary_reviewer: ModelSpec
    primary_support: list[ModelSpec]
    command_lead: ModelSpec
    command_reviewer: ModelSpec
    secretary_lead: ModelSpec
    safety_lead: ModelSpec
    repair_lead: ModelSpec


@dataclass
class ExecutionResult:
    cluster_name: str
    summary: str
    raw_response: str
    files_written: list[str]
    journal: list[ClusterMessage]
    plan: ClusterPlan


EventHandler = Callable[[str], None]


class AutobotRouter:
    def __init__(self, api_key: str | None = None, catalog: ClusterCatalog | None = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.client = self._build_client() if self.api_key else None
        self.catalog = catalog or ClusterCatalog()

    def read_phase_documents(self, workspace: TargetProjectWorkspace) -> tuple[str, str]:
        roadmap = workspace.read_context_file("roadmap.md")
        progress = workspace.read_context_file("progress-tracker.md")
        return roadmap, progress

    def find_next_phase(self, progress_text: str) -> PhaseRecord | None:
        lines = progress_text.splitlines()
        parsed = [self._parse_phase_line(index, line) for index, line in enumerate(lines)]
        parsed = [phase for phase in parsed if phase is not None]

        for status in STATUS_PRIORITY:
            for phase in parsed:
                if phase.status == status:
                    return phase
        return None

    def mark_phase_complete(self, progress_text: str, phase: PhaseRecord) -> str:
        return self._update_phase_status(progress_text, phase, "COMPLETE")

    def _update_phase_status(self, progress_text: str, phase: PhaseRecord, status: str) -> str:
        lines = progress_text.splitlines()
        original = lines[phase.line_index]
        updated = STATUS_PATTERN.sub(status, original, count=1)

        if updated == original:
            checkbox = {"PENDING": "[ ]", "IN_PROGRESS": "[~]", "COMPLETE": "[x]"}[status]
            updated = CHECKBOX_PATTERN.sub(checkbox, original, count=1)
        if updated == original:
            updated = f"{original} {status}"

        lines[phase.line_index] = updated
        return "\n".join(lines) + ("\n" if progress_text.endswith("\n") else "")

    def build_cluster_plan(self, phase: PhaseRecord, roadmap_text: str) -> ClusterPlan:
        signal = f"{phase.title}\n{roadmap_text}"
        primary_cluster = self.catalog.route(signal)
        primary_lead, primary_reviewer, primary_support = self.catalog.select_models(primary_cluster, signal)
        command_lead, command_reviewer, _ = self.catalog.select_models("Optimus", signal)
        secretary_lead = self._select_secretary_model()
        safety_lead, _, _ = self.catalog.select_models("RedAlert", signal)
        repair_lead, _, _ = self.catalog.select_models("Ratchet", signal)
        return ClusterPlan(
            primary_cluster=primary_cluster,
            primary_lead=primary_lead,
            primary_reviewer=primary_reviewer,
            primary_support=primary_support,
            command_lead=command_lead,
            command_reviewer=command_reviewer,
            secretary_lead=secretary_lead,
            safety_lead=safety_lead,
            repair_lead=repair_lead,
        )

    def execute_phase(
        self,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        event_handler: EventHandler | None = None,
    ) -> ExecutionResult:
        plan = self.build_cluster_plan(phase, roadmap_text)
        progress_text = self.begin_phase(workspace, phase, progress_text, plan, event_handler=event_handler)
        self._emit(
            event_handler,
            f"Optimus planning {phase.title} with {plan.command_lead.model_id}.",
        )
        self._emit(
            event_handler,
            f"Optimus routing '{phase.title}' to {plan.primary_cluster} with {plan.primary_lead.model_id}.",
        )
        command_payload, command_raw = self._run_command_stage(plan, phase, roadmap_text, progress_text)
        self._emit(
            event_handler,
            f"{plan.primary_cluster} working on {phase.title}.",
        )
        specialist_payload, specialist_raw = self._run_specialist_stage(
            plan,
            workspace,
            phase,
            roadmap_text,
            progress_text,
            command_payload,
        )
        self._emit(
            event_handler,
            f"{plan.primary_cluster} completed {phase.title} and updated status to Optimus.",
        )
        review_payload, review_raw = self._run_safety_stage(
            plan,
            phase,
            specialist_payload,
            command_payload,
        )
        self._emit(
            event_handler,
            f"RedAlert reviewed {phase.title}. Verdict: {(review_payload.get('status') or 'pass').upper()}",
        )

        raw_parts = [command_raw, specialist_raw, review_raw]
        journal = [
            ClusterMessage(
                speaker=f"Optimus/{plan.command_lead.model_id}",
                objective="Hierarchical planning",
                summary=(command_payload.get("summary") or "Created the execution brief.").strip(),
            ),
            ClusterMessage(
                speaker=f"{plan.primary_cluster}/{plan.primary_lead.model_id}",
                objective="Primary implementation",
                summary=(specialist_payload.get("summary") or "Generated files.").strip(),
            ),
            ClusterMessage(
                speaker=f"RedAlert/{plan.safety_lead.model_id}",
                objective="Safety and quality review",
                summary=(review_payload.get("summary") or "Reviewed generated output.").strip(),
            ),
        ]

        final_payload = specialist_payload
        final_lock_owner = f"{plan.primary_cluster}/{plan.primary_lead.model_id}"
        if (review_payload.get("status") or "").lower() == "revise":
            repair_payload, repair_raw = self._run_repair_stage(
                plan,
                workspace,
                phase,
                roadmap_text,
                progress_text,
                command_payload,
                specialist_payload,
                review_payload,
            )
            raw_parts.append(repair_raw)
            journal.append(
                ClusterMessage(
                    speaker=f"Ratchet/{plan.repair_lead.model_id}",
                    objective="Repair and refinement",
                    summary=(repair_payload.get("summary") or "Applied repairs after review.").strip(),
                )
            )
            self._emit(
                event_handler,
                f"Ratchet repaired {phase.title} and returned the update to Optimus.",
            )
            final_payload = repair_payload
            final_lock_owner = f"Ratchet/{plan.repair_lead.model_id}"

        safe_files = self._enforce_generated_file_laws(final_payload.get("files", []))
        files_written = workspace.apply_generated_files(
            safe_files,
            lock_owner=final_lock_owner,
        )
        summary = (final_payload.get("summary") or "Phase executed.").strip()
        return ExecutionResult(
            cluster_name=plan.primary_cluster,
            summary=summary,
            raw_response="\n\n".join(part for part in raw_parts if part),
            files_written=files_written,
            journal=journal,
            plan=plan,
        )

    def refine_with_ratchet(
        self,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        previous_result: ExecutionResult,
        feedback: str,
        event_handler: EventHandler | None = None,
    ) -> ExecutionResult:
        self._emit(
            event_handler,
            f"Ratchet revising {phase.title} with feedback from Optimus.",
        )
        repair_payload, repair_raw = self._run_repair_stage(
            previous_result.plan,
            workspace,
            phase,
            roadmap_text,
            progress_text,
            {"summary": previous_result.summary},
            {
                "summary": previous_result.summary,
                "files": self._file_entries_from_paths(previous_result.files_written, workspace),
            },
            {
                "status": "revise",
                "summary": feedback or "User requested another pass.",
                "issues": [feedback or "User requested another pass."],
            },
        )
        safe_files = self._enforce_generated_file_laws(repair_payload.get("files", []))
        files_written = workspace.apply_generated_files(
            safe_files,
            lock_owner=f"Ratchet/{previous_result.plan.repair_lead.model_id}",
        )
        journal = previous_result.journal + [
            ClusterMessage(
                speaker=f"Ratchet/{previous_result.plan.repair_lead.model_id}",
                objective="User-directed refinement",
                summary=(repair_payload.get("summary") or "Applied user feedback.").strip(),
            )
        ]
        self._emit(
            event_handler,
            f"Ratchet completed the revision for {phase.title} and returned it to Optimus.",
        )
        return ExecutionResult(
            cluster_name="Ratchet",
            summary=(repair_payload.get("summary") or "Phase refined.").strip(),
            raw_response=repair_raw,
            files_written=files_written,
            journal=journal,
            plan=previous_result.plan,
        )

    def begin_phase(
        self,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        progress_text: str,
        plan: ClusterPlan,
        *,
        event_handler: EventHandler | None = None,
    ) -> str:
        if phase.status == "IN_PROGRESS":
            return progress_text

        self._emit(
            event_handler,
            f"Optimus secretary {plan.secretary_lead.model_id} updating progress-tracker.md for {phase.title}.",
        )
        updated_progress = self._update_phase_status(progress_text, phase, "IN_PROGRESS")
        workspace.write_context_file(
            PROGRESS_TRACKER_FILE,
            updated_progress,
            lock_owner=f"Optimus/{plan.secretary_lead.model_id}",
        )
        return updated_progress

    def complete_phase(
        self,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        progress_text: str,
        plan: ClusterPlan,
        *,
        event_handler: EventHandler | None = None,
    ) -> str:
        self._emit(
            event_handler,
            f"Optimus secretary {plan.secretary_lead.model_id} updating progress-tracker.md to COMPLETE for {phase.title}.",
        )
        updated_progress = self._update_phase_status(progress_text, phase, "COMPLETE")
        workspace.write_context_file(
            PROGRESS_TRACKER_FILE,
            updated_progress,
            lock_owner=f"Optimus/{plan.secretary_lead.model_id}",
        )
        return updated_progress

    def _run_command_stage(
        self,
        plan: ClusterPlan,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
    ) -> tuple[dict, str]:
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
        payload = self._parse_json(raw)
        return payload, raw

    def _run_specialist_stage(
        self,
        plan: ClusterPlan,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        command_payload: dict,
    ) -> tuple[dict, str]:
        prompt = f"""
You are the {plan.primary_cluster} implementation cluster.
The command tier and support models have already coordinated your mission.
Act as a collaborative cluster: the lead writes, the reviewer critiques, and support models fill gaps.
Treat the coordination rules below as hard laws.

{COORDINATION_LAWS}

Workspace constraints:
1. Write only under src/ or context/.
2. Never write in the Autobots engine repository.
3. Return full file contents, not diffs.
4. Never write `progress-tracker.md`; report progress back to Optimus instead.

Target roots:
- src root: {workspace.src_root}
- context root: {workspace.context_root}

Phase:
{phase.raw_line}

Roadmap:
{roadmap_text}

Progress tracker:
{progress_text}

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
        payload = self._parse_json(raw)
        if "files" not in payload:
            payload["files"] = []
        return payload, raw

    def _run_safety_stage(
        self,
        plan: ClusterPlan,
        phase: PhaseRecord,
        specialist_payload: dict,
        command_payload: dict,
    ) -> tuple[dict, str]:
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
        payload = self._parse_json(raw)
        payload.setdefault("issues", [])
        payload.setdefault("status", "pass")
        return payload, raw

    def _run_repair_stage(
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
        prompt = f"""
You are Ratchet, the repair cluster.
Revise the implementation after autonomous review and feedback from the swarm.
Treat the coordination rules below as hard laws.

{COORDINATION_LAWS}

Workspace constraints:
1. Write only under src/ or context/.
2. Never write in the Autobots engine repository.
3. Return full file contents, not diffs.
4. Never write `progress-tracker.md`; report progress back to Optimus instead.

Target roots:
- src root: {workspace.src_root}
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
        payload = self._parse_json(raw)
        if "files" not in payload:
            payload["files"] = []
        return payload, raw

    def _complete(self, model_id: str, prompt: str) -> str:
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

    def _select_secretary_model(self) -> ModelSpec:
        optimus = self.catalog.get_cluster("Optimus")
        for model in optimus.models:
            if model.model_id == "step-3.5-flash":
                return model
        return optimus.models[0]

    def _enforce_generated_file_laws(self, files: list[dict]) -> list[dict]:
        safe_files: list[dict] = []
        for file_spec in files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip().replace("\\", "/")
            if root_name == "context" and relative_path in PROTECTED_PROGRESS_FILES:
                continue
            safe_files.append(file_spec)
        return safe_files

    def _emit(self, event_handler: EventHandler | None, message: str) -> None:
        if event_handler is not None:
            event_handler(message)

    def _parse_phase_line(self, index: int, line: str) -> PhaseRecord | None:
        status_match = STATUS_PATTERN.search(line)
        if status_match:
            status = status_match.group(1)
            title = STATUS_PATTERN.sub("", line, count=1)
            title = self._clean_phase_title(title)
            return PhaseRecord(index, line, title or f"Phase {index + 1}", status)

        checkbox_match = CHECKBOX_PATTERN.search(line)
        if checkbox_match:
            marker = checkbox_match.group(0)
            status = {"[ ]": "PENDING", "[~]": "IN_PROGRESS", "[x]": "COMPLETE"}.get(
                marker
            )
            title = self._clean_phase_title(CHECKBOX_PATTERN.sub("", line, count=1))
            return PhaseRecord(index, line, title or f"Phase {index + 1}", status)

        return None

    def _clean_phase_title(self, raw_title: str) -> str:
        cleaned = raw_title.strip()
        cleaned = cleaned.strip("|")
        parts = [part.strip() for part in cleaned.split("|") if part.strip()]
        if parts:
            cleaned = " | ".join(parts)
        cleaned = re.sub(r"^[\-\*\d\.\)\s#:]+", "", cleaned)
        return cleaned.strip()

    def _parse_json(self, raw_content: str) -> dict:
        candidate = raw_content.strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if fenced_match:
            candidate = fenced_match.group(1)

        payload = json.loads(candidate)
        if not isinstance(payload, dict):
            raise ValueError("Model response must be a JSON object.")
        return payload

    def _file_entries_from_paths(
        self,
        file_paths: list[str],
        workspace: TargetProjectWorkspace,
    ) -> list[dict]:
        entries: list[dict] = []
        for file_path in file_paths:
            path = os.path.abspath(file_path)
            if path.startswith(str(workspace.src_root)):
                root = "src"
                relative = os.path.relpath(path, workspace.src_root)
            elif path.startswith(str(workspace.context_root)):
                root = "context"
                relative = os.path.relpath(path, workspace.context_root)
            else:
                continue
            entries.append(
                {
                    "root": root,
                    "path": relative.replace("\\", "/"),
                    "content": open(path, encoding="utf-8").read(),
                }
            )
        return entries
