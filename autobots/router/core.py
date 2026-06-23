"""Main Autobot router orchestrating cluster execution."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING

from ..catalog import ClusterCatalog
from ..executor import PhaseExecutor
from .models import EventHandler, ExecutionResult, ClusterMessage, PhaseRecord
from .phases import PhaseReader
from .planning import ClusterPlanner
from .stages import StageExecutor, PROTECTED_PROGRESS_FILES
from .utils import PayloadValidator, FileEntryHelper
from .decomposer import TaskDecomposer, DecompositionPlan
from .sequencer import TaskSequencer, ExecutionPlan
from ..workspace import TargetProjectWorkspace

if TYPE_CHECKING:
    from .models import ClusterPlan
    from ..costs import UsageTracker
    from ..context_budget import ContextBudgetManager

logger = logging.getLogger("autobots")


class AutobotRouter:
    """Routes phases to appropriate clusters for execution."""

    MAX_VERIFICATION_ATTEMPTS = 3
    PROGRESS_TRACKER_FILE = "progress-tracker.md"

    def __init__(
        self,
        api_key: str | None = None,
        catalog: ClusterCatalog | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        temperature: float = 0.2,
        max_tokens: int = 8192,
        usage_tracker: "UsageTracker | None" = None,
        context_budget_manager: "ContextBudgetManager | None" = None,
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.catalog = catalog or ClusterCatalog(api_key=self.api_key)
        self.executor = PhaseExecutor(api_key=self.api_key)
        self.planner = ClusterPlanner(catalog=self.catalog, api_key=self.api_key)
        self.usage_tracker = usage_tracker
        self.context_budget_manager = context_budget_manager
        self.stage_executor = StageExecutor(
            api_key=self.api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            usage_tracker=usage_tracker,
            context_budget_manager=context_budget_manager,
        )
        self.decomposer = TaskDecomposer(api_key=self.api_key, base_url=base_url)
        self.sequencer = TaskSequencer()

    def read_phase_documents(self, workspace: TargetProjectWorkspace) -> tuple[str, str]:
        """Read roadmap and progress tracker."""
        return PhaseReader.read_phase_documents(workspace)

    def execute_task(
        self,
        workspace: TargetProjectWorkspace,
        task: str,
        event_handler: EventHandler | None = None,
    ) -> ExecutionResult:
        """Execute a task using decomposer + sequencer multi-cluster pipeline."""
        logger.info("Executing task: %s", task)

        # Step 1: Decompose
        self._emit(event_handler, f"Optimus decomposing task into subtasks...")
        plan = self.decomposer.decompose(task)
        logger.info("Decomposed into %d subtasks", len(plan.subtasks))

        # Step 2: Sequence
        exec_plan = self.sequencer.sequence(plan.subtasks)
        logger.info("Sequenced into %d steps (%d parallel)", exec_plan.sequential_steps, exec_plan.parallel_groups)
        self._emit(event_handler, f"Plan: {exec_plan.sequential_steps} steps, {exec_plan.parallel_groups} parallel groups")

        # Step 3: Execute each step
        all_files = []
        all_journal = []
        all_raw = []

        for step_idx, group in enumerate(exec_plan.groups):
            if len(group.subtasks) == 1:
                subtask = group.subtasks[0]
                self._emit(event_handler, f"Step {step_idx+1}: [{subtask.cluster}] {subtask.task}")
                result = self._execute_subtask(workspace, subtask, plan, all_files, event_handler)
            else:
                self._emit(event_handler, f"Step {step_idx+1} (parallel): {len(group.subtasks)} tasks")
                result = self._execute_parallel_group(workspace, group, plan, all_files, event_handler)

            all_files.extend(result.get("files", []))
            all_journal.extend(result.get("journal", []))
            all_raw.append(result.get("raw", ""))

        summary = f"Completed {len(plan.subtasks)} subtasks across {exec_plan.sequential_steps} steps"
        return ExecutionResult(
            cluster_name="multi-cluster",
            summary=summary,
            raw_response="\n\n".join(all_raw),
            files_written=[],
            journal=all_journal,
            plan=None,
            validation_passed=True,
            validation_report="",
            verification_attempts=0,
        )

    def _execute_subtask(
        self,
        workspace: TargetProjectWorkspace,
        subtask,
        decompose_plan: DecompositionPlan,
        existing_files: list[dict],
        event_handler: EventHandler | None = None,
    ) -> dict:
        """Execute a single subtask with its assigned cluster."""
        from openai import OpenAI

        # Get model for this cluster
        lead, reviewer, support = self.catalog.select_models(subtask.cluster, subtask.task)
        model_id = lead.model_id

        # Fallback to known working model if needed
        FALLBACK_MODELS = [
            "meta/llama-3.3-70b-instruct",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-super-120b-a12b",
        ]
        if model_id not in FALLBACK_MODELS and "llama" not in model_id and "nemotron" not in model_id:
            model_id = FALLBACK_MODELS[0]

        self._emit(event_handler, f"  Using {model_id} for {subtask.cluster}")

        # Build context from existing files
        context = ""
        if existing_files:
            context = "\n\nEXISTING FILES:\n" + "\n".join(
                f"--- {f.get('path', '?')} ---\n{f.get('content', '')[:1000]}"
                for f in existing_files[-10:]  # Last 10 files for context
            )

        # Call model
        client = OpenAI(base_url=self.stage_executor.base_url, api_key=self.api_key)
        system = f"""You are a {subtask.cluster} specialist. Complete the task and return JSON with files.

RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with full file content
- Use \\n for newlines inside content strings
- Escape quotes with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation

Return format:
{{"files":[{{"root":"","path":"filename.ext","content":"full file content here"}}],"summary":"what you did"}}"""

        user = f"TASK: {subtask.task}{context}"

        try:
            response = client.chat.completions.create(
                model=lead.model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=8192,
                stream=False,
            )
            raw = response.choices[0].message.content or ""
            payload = self._parse_json_response(raw)
            files = payload.get("files", [])

            # Write files
            for f in files:
                root = f.get("root", "").strip()
                path = f.get("path", "").strip()
                content = f.get("content", "")
                if not path:
                    continue
                target = (workspace.target_root / root / path) if root else (workspace.target_root / path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            return {
                "files": files,
                "journal": [ClusterMessage(
                    speaker=f"{subtask.cluster}/{model_id}",
                    objective=subtask.task,
                    summary=payload.get("summary", "Completed task."),
                )],
                "raw": raw,
            }
        except Exception as exc:
            logger.warning("Subtask failed: %s", exc)
            return {"files": [], "journal": [], "raw": f"Error: {exc}"}

    def _execute_parallel_group(
        self,
        workspace: TargetProjectWorkspace,
        group,
        decompose_plan: DecompositionPlan,
        existing_files: list[dict],
        event_handler: EventHandler | None = None,
    ) -> dict:
        """Execute a group of subtasks (sequential for now, parallel later)."""
        all_files = []
        all_journal = []
        all_raw = []

        for subtask in group.subtasks:
            result = self._execute_subtask(workspace, subtask, decompose_plan, existing_files + all_files, event_handler)
            all_files.extend(result.get("files", []))
            all_journal.extend(result.get("journal", []))
            all_raw.append(result.get("raw", ""))

        return {
            "files": all_files,
            "journal": all_journal,
            "raw": "\n\n".join(all_raw),
        }

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Parse JSON from model response."""
        import re
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
            return {}

    def find_next_phase(self, progress_text: str) -> PhaseRecord | None:
        """Find next phase to execute."""
        return PhaseReader.find_next_phase(progress_text)

    def mark_phase_complete(self, progress_text: str, phase: PhaseRecord) -> str:
        """Mark phase as complete."""
        return PhaseReader.mark_phase_complete(progress_text, phase)

    def build_cluster_plan(self, phase: PhaseRecord, roadmap_text: str):
        """Build cluster plan for phase."""
        return self.planner.build_cluster_plan(phase, roadmap_text)

    def build_work_packet_from_phase(self, phase: PhaseRecord, roadmap_text: str):
        """Build work packet from phase."""
        return self.planner.build_work_packet_from_phase(phase, roadmap_text)

    def execute_phase(
        self,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        event_handler: EventHandler | None = None,
    ) -> ExecutionResult:
        """Execute a phase through the swarm."""
        logger.info("Executing phase: %s", phase.title)
        plan = self.build_cluster_plan(phase, roadmap_text)
        logger.info("Routed to %s (command=%s, primary=%s)", plan.primary_cluster, plan.command_lead.model_id, plan.primary_lead.model_id)
        work_packet = self.build_work_packet_from_phase(phase, roadmap_text)
        progress_text = self.begin_phase(workspace, phase, progress_text, plan, event_handler=event_handler)
        self._emit(event_handler, f"Optimus planning {phase.title} with {plan.command_lead.model_id}.")
        self._emit(event_handler, f"Optimus routing '{phase.title}' to {plan.primary_cluster} with {plan.primary_lead.model_id}.")

        if plan.routing_rationale:
            self._emit(event_handler, f"Routing rationale: {'; '.join(plan.routing_rationale[:3])}")
        if plan.parallel_workstreams:
            self._emit(
                event_handler,
                f"Parallel planning identified {len(plan.parallel_workstreams)} independent workstream candidate(s); merge strategy is {plan.merge_strategy}.",
            )

        self.stage_executor.workspace_root = str(workspace.target_root)
        command_payload, command_raw = self._run_command_stage(plan, phase, roadmap_text, progress_text)
        self._emit(event_handler, f"{plan.primary_cluster} working on {phase.title}.")

        specialist_payload, specialist_raw = self._run_specialist_stage(
            plan, workspace, phase, roadmap_text, progress_text, command_payload, event_handler=event_handler
        )
        self._emit(event_handler, f"{plan.primary_cluster} completed {phase.title} and updated status to Optimus.")

        review_payload, review_raw = self._run_safety_stage(plan, phase, specialist_payload, command_payload)
        self._emit(event_handler, f"RedAlert reviewed {phase.title}. Verdict: {(review_payload.get('status') or 'pass').upper()}")

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
            try:
                repair_payload, repair_raw = self._run_repair_stage(
                    plan, workspace, phase, roadmap_text, progress_text, command_payload, specialist_payload, review_payload
                )
                raw_parts.append(repair_raw)
                journal.append(
                    ClusterMessage(
                        speaker=f"Ratchet/{plan.repair_lead.model_id}",
                        objective="Repair and refinement",
                        summary=(repair_payload.get("summary") or "Applied repairs after review.").strip(),
                    )
                )
                self._emit(event_handler, f"Ratchet repaired {phase.title} and returned the update to Optimus.")
                final_payload = repair_payload
                final_lock_owner = f"Ratchet/{plan.repair_lead.model_id}"
            except Exception as exc:
                logger.warning("Ratchet repair failed, using specialist output: %s", exc)
                self._emit(event_handler, f"Ratchet repair failed ({type(exc).__name__}), using specialist output.")

        safe_files = self._enforce_generated_file_laws(final_payload.get("files", []))
        files_written = self._persist_generated_files(
            workspace, safe_files, lock_owner=final_lock_owner, event_handler=event_handler
        )

        (
            final_payload,
            files_written,
            verification_journal,
            verification_raw_parts,
            validation_passed,
            validation_report,
            verification_attempts,
        ) = self._run_verification_loop(
            workspace=workspace,
            phase=phase,
            roadmap_text=roadmap_text,
            progress_text=progress_text,
            plan=plan,
            work_packet=work_packet,
            command_payload=command_payload,
            implementation_payload=final_payload,
            files_written=files_written,
            event_handler=event_handler,
        )
        journal.extend(verification_journal)
        raw_parts.extend(verification_raw_parts)
        summary = (final_payload.get("summary") or "Phase executed.").strip()
        if validation_report and not validation_passed:
            summary = f"{summary}\n\nValidation is still failing after automatic repair attempts."
        return ExecutionResult(
            cluster_name=plan.primary_cluster,
            summary=summary,
            raw_response="\n\n".join(part for part in raw_parts if part),
            files_written=files_written,
            journal=journal,
            plan=plan,
            validation_passed=validation_passed,
            validation_report=validation_report,
            verification_attempts=verification_attempts,
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
        """Begin a phase and mark it in progress."""
        if phase.status == "IN_PROGRESS":
            return progress_text
        self._emit(event_handler, f"Optimus secretary {plan.secretary_lead.model_id} updating progress-tracker.md for {phase.title}.")
        updated_progress = PhaseReader._update_phase_status(progress_text, phase, "IN_PROGRESS")
        workspace.write_context_file(self.PROGRESS_TRACKER_FILE, updated_progress, lock_owner=f"Optimus/{plan.secretary_lead.model_id}")
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
        """Mark a phase as complete."""
        self._emit(event_handler, f"Optimus secretary {plan.secretary_lead.model_id} updating progress-tracker.md to COMPLETE for {phase.title}.")
        updated_progress = self.mark_phase_complete(progress_text, phase)
        workspace.write_context_file(self.PROGRESS_TRACKER_FILE, updated_progress, lock_owner=f"Optimus/{plan.secretary_lead.model_id}")

        # Clean up steering file after phase completion
        steering_path = workspace.target_root / "context" / ".autobots-steering.md"
        if steering_path.exists():
            try:
                steering_path.unlink()
            except Exception:
                pass

        return updated_progress

    def _run_verification_loop(
        self,
        *,
        workspace: TargetProjectWorkspace,
        phase: PhaseRecord,
        roadmap_text: str,
        progress_text: str,
        plan: ClusterPlan,
        work_packet,
        command_payload: dict,
        implementation_payload: dict,
        files_written: list[str],
        event_handler: EventHandler | None = None,
    ) -> tuple[dict, list[str], list[ClusterMessage], list[str], bool, str, int]:
        """Run verification loop with automatic repairs."""
        if not work_packet.validation_commands:
            return implementation_payload, files_written, [], [], True, "No validation commands specified.", 0

        journal: list[ClusterMessage] = []
        raw_parts: list[str] = []
        current_payload = implementation_payload
        current_files = files_written
        validation_report = ""

        for attempt in range(1, self.MAX_VERIFICATION_ATTEMPTS + 1):
            self._emit(
                event_handler,
                f"Optimus verifying {phase.title} with target toolchain commands (attempt {attempt}/{self.MAX_VERIFICATION_ATTEMPTS}).",
            )
            all_passed, results = self.executor.validate_phase(workspace, work_packet, event_handler=event_handler)
            validation_report = self.executor.format_validation_results(results)
            raw_parts.append(validation_report)
            journal.append(
                ClusterMessage(
                    speaker="Optimus/verification",
                    objective="Toolchain verification",
                    summary=self.executor.summarize_validation_results(results),
                )
            )
            if all_passed:
                return current_payload, current_files, journal, raw_parts, True, validation_report, attempt

            if attempt >= self.MAX_VERIFICATION_ATTEMPTS:
                self._emit(
                    event_handler,
                    f"Validation remained failing after {attempt} attempt(s). Returning control with the latest report.",
                )
                return current_payload, current_files, journal, raw_parts, False, validation_report, attempt

            repair_feedback = self.executor.build_validation_feedback(work_packet, results)
            self._emit(event_handler, f"Validation failed for {phase.title}. Ratchet is preparing an automatic repair pass.")
            repair_payload, repair_raw = self._run_repair_stage(
                plan, workspace, phase, roadmap_text, progress_text, command_payload, current_payload, repair_feedback
            )
            raw_parts.append(repair_raw)
            journal.append(
                ClusterMessage(
                    speaker=f"Ratchet/{plan.repair_lead.model_id}",
                    objective="Validation-driven repair",
                    summary=(repair_payload.get("summary") or "Adjusted the implementation after validation failure.").strip(),
                )
            )
            safe_files = self._enforce_generated_file_laws(repair_payload.get("files", []))
            current_files = self._persist_generated_files(
                workspace, safe_files, lock_owner=f"Ratchet/{plan.repair_lead.model_id}", event_handler=event_handler
            )
            current_payload = repair_payload

        return current_payload, current_files, journal, raw_parts, False, validation_report, self.MAX_VERIFICATION_ATTEMPTS

    def _enforce_generated_file_laws(self, files: list[dict]) -> list[dict]:
        """Enforce file writing laws."""
        safe_files: list[dict] = []
        for file_spec in files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip().replace("\\", "/")
            if root_name == "context" and relative_path in PROTECTED_PROGRESS_FILES:
                continue
            safe_files.append(file_spec)
        return safe_files

    def _persist_generated_files(
        self,
        workspace: TargetProjectWorkspace,
        files: list[dict],
        *,
        lock_owner: str,
        event_handler: EventHandler | None = None,
    ) -> list[str]:
        """Persist generated files with lock handling."""
        attempts = workspace.LOCK_RETRY_ATTEMPTS
        delay = workspace.LOCK_RETRY_DELAY_SECONDS

        for attempt in range(1, attempts + 1):
            try:
                return workspace.apply_generated_files(files, lock_owner=lock_owner)
            except Exception as exc:
                if not self._is_lock_collision_error(exc):
                    raise
                if not self._files_include_critical_context(files):
                    raise
                if attempt >= attempts:
                    raise
                self._emit(event_handler, f"{lock_owner} waiting on a critical file lock. Sleep/retry {attempt}/{attempts - 1}.")
                time.sleep(delay)

        raise RuntimeError(
            f"Lock collision: generated files for {lock_owner} could not be persisted after {attempts} attempts. "
            "Retry with `autobots run --force`."
        )

    def _files_include_critical_context(self, files: list[dict]) -> bool:
        """Check if files include critical context."""
        for file_spec in files:
            root_name = (file_spec.get("root") or "src").strip().lower()
            relative_path = (file_spec.get("path") or "").strip().replace("\\", "/")
            if root_name == "context" and relative_path in TargetProjectWorkspace.CRITICAL_CONTEXT_FILES:
                return True
        return False

    def _is_lock_collision_error(self, exc: Exception) -> bool:
        """Check if exception is due to lock collision."""
        return "Context lock for" in str(exc)

    def run_validation_commands(
        self,
        workspace: TargetProjectWorkspace,
        work_packet,
        event_handler: EventHandler | None = None,
    ) -> tuple[bool, str]:
        """Run validation commands for a work packet using the execution engine."""
        if not work_packet.validation_commands:
            return True, "No validation commands specified."

        all_passed, results = self.executor.validate_phase(workspace, work_packet, event_handler=event_handler)
        validation_report = self.executor.format_validation_results(results)
        return all_passed, validation_report

    # Backward compatibility methods
    def validate_command_payload(self, payload: dict) -> None:
        """Backward compatibility wrapper."""
        return PayloadValidator.validate_command_payload(payload)

    def validate_specialist_payload(self, payload: dict) -> None:
        """Backward compatibility wrapper."""
        return PayloadValidator.validate_specialist_payload(payload)

    def validate_review_payload(self, payload: dict) -> None:
        """Backward compatibility wrapper."""
        return PayloadValidator.validate_review_payload(payload)

    def validate_repair_payload(self, payload: dict) -> None:
        """Backward compatibility wrapper."""
        return PayloadValidator.validate_repair_payload(payload)

    def _parse_phase_line(self, index: int, line: str):
        """Backward compatibility wrapper."""
        return PhaseReader._parse_phase_line(index, line)

    def _file_entries_from_paths(self, file_paths: list[str], workspace: TargetProjectWorkspace) -> list[dict]:
        """Backward compatibility wrapper."""
        return FileEntryHelper.file_entries_from_paths(file_paths, workspace)

    def _extract_phase_id(self, title: str) -> str:
        """Backward compatibility wrapper."""
        return self.planner._extract_phase_id(title)

    def _emit(self, event_handler: EventHandler | None, message: str) -> None:
        if event_handler is not None:
            event_handler(message)

    def _run_command_stage(self, plan, phase, roadmap_text, progress_text):
        """Compatibility wrapper for test doubles and future orchestration hooks."""
        return self.stage_executor.run_command_stage(plan, phase, roadmap_text, progress_text)

    def _run_specialist_stage(self, plan, workspace, phase, roadmap_text, progress_text, command_payload, event_handler=None):
        """Compatibility wrapper for implementation stage."""
        return self.stage_executor.run_specialist_stage(
            plan, workspace, phase, roadmap_text, progress_text, command_payload, event_handler=event_handler
        )

    def _run_safety_stage(self, plan, phase, specialist_payload, command_payload):
        """Compatibility wrapper for review stage."""
        return self.stage_executor.run_safety_stage(plan, phase, specialist_payload, command_payload)

    def _run_repair_stage(self, plan, workspace, phase, roadmap_text, progress_text, command_payload, specialist_payload, review_payload, event_handler=None):
        """Compatibility wrapper for repair stage."""
        return self.stage_executor.run_repair_stage(
            plan, workspace, phase, roadmap_text, progress_text, command_payload, specialist_payload, review_payload
        )
