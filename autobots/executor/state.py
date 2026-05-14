"""Persistent state management, audit trails, and recovery for Autobots execution sessions."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SessionState(Enum):
    """State of an execution session."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class ChangeType(Enum):
    """Type of change recorded in audit trail."""

    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    REPAIR_PERFORMED = "repair_performed"
    COMMAND_EXECUTED = "command_executed"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_LOADED = "checkpoint_loaded"
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    ERROR_ENCOUNTERED = "error_encountered"


@dataclass
class AuditEntry:
    """A single audit trail entry."""

    timestamp: float
    change_type: str
    phase_id: str | None
    description: str
    file_path: str | None = None
    command: str | None = None
    user: str = "autobots"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            timestamp=data["timestamp"],
            change_type=data["change_type"],
            phase_id=data.get("phase_id"),
            description=data["description"],
            file_path=data.get("file_path"),
            command=data.get("command"),
            user=data.get("user", "autobots"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionMetadata:
    """Metadata for a session."""

    session_id: str
    target_root: str
    mode: str
    created_at: float
    updated_at: float
    state: str
    phases_completed: list[str] = field(default_factory=list)
    current_phase: str | None = None
    last_checkpoint_at: float | None = None
    total_commands_run: int = 0
    total_files_changed: int = 0
    errors_encountered: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMetadata":
        return cls(**data)


@dataclass
class PhaseSnapshot:
    """Snapshot of phase execution state for crash recovery."""

    phase_id: str
    phase_title: str
    started_at: float
    completed_at: float | None = None
    status: str = "in_progress"
    files_written: list[str] = field(default_factory=list)
    validation_attempts: int = 0
    last_validation_output: str | None = None
    repair_count: int = 0
    commands_executed: list[dict] = field(default_factory=list)
    error_log: list[str] = field(default_factory=list)
    result_summary: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PhaseSnapshot":
        return cls(
            phase_id=data["phase_id"],
            phase_title=data["phase_title"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            status=data.get("status", "in_progress"),
            files_written=data.get("files_written", []),
            validation_attempts=data.get("validation_attempts", 0),
            last_validation_output=data.get("last_validation_output"),
            repair_count=data.get("repair_count", 0),
            commands_executed=data.get("commands_executed", []),
            error_log=data.get("error_log", []),
            result_summary=data.get("result_summary"),
        )


class StateManager:
    """Manages persistent state, audit trails, and recovery for Autobots sessions."""

    STATE_DIR = ".autobots-state"
    AUDIT_FILE = "audit.jsonl"
    SESSION_FILE = "session.json"
    PHASES_DIR = "phases"
    RECOVERY_FILE = "recovery.json"

    def __init__(self, target_root: str | Path):
        self.target_root = Path(target_root).resolve()
        self.state_root = self.target_root / self.STATE_DIR
        self.audit_path = self.state_root / self.AUDIT_FILE
        self.session_path = self.state_root / self.SESSION_FILE
        self.phases_dir = self.state_root / self.PHASES_DIR
        self.recovery_path = self.state_root / self.RECOVERY_FILE

    def ensure_state_dir(self) -> None:
        """Ensure state directory structure exists."""
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.phases_dir.mkdir(parents=True, exist_ok=True)

    def _get_phase_path(self, phase_id: str) -> Path:
        safe_id = phase_id.replace("/", "__").replace("\\", "__")
        return self.phases_dir / f"{safe_id}.json"

    def _atomic_write_json(self, path: Path, payload: dict) -> None:
        """Write JSON atomically to avoid partially-written state files."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    # --- Audit Trail Operations ---

    def log_audit(
        self,
        change_type: ChangeType,
        description: str,
        *,
        phase_id: str | None = None,
        file_path: str | None = None,
        command: str | None = None,
        metadata: dict | None = None,
    ) -> AuditEntry:
        """Log an audit entry to the audit trail."""
        self.ensure_state_dir()
        entry = AuditEntry(
            timestamp=time.time(),
            change_type=change_type.value,
            phase_id=phase_id,
            description=description,
            file_path=file_path,
            command=command,
            metadata=metadata or {},
        )
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return entry

    def get_audit_trail(self, phase_id: str | None = None, limit: int = 100) -> list[AuditEntry]:
        """Retrieve audit trail entries, optionally filtered by phase."""
        if not self.audit_path.exists():
            return []

        entries = []
        try:
            with self.audit_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = AuditEntry.from_dict(json.loads(line))
                        if phase_id is None or entry.phase_id == phase_id:
                            entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except FileNotFoundError:
            return []

        return entries[-limit:]

    def get_file_change_history(self, file_path: str | None = None) -> list[AuditEntry]:
        """Get audit entries for file changes, optionally filtered by path."""
        if not self.audit_path.exists():
            return []

        entries = []
        target = file_path.replace("\\", "/") if file_path else None
        try:
            with self.audit_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = AuditEntry.from_dict(json.loads(line))
                        if entry.file_path:
                            entry_normalized = entry.file_path.replace("\\", "/")
                            if target is None or entry_normalized.endswith(target):
                                entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except FileNotFoundError:
            return []
        return entries

    # --- Session Operations ---

    def create_session(
        self,
        session_id: str,
        target_root: str,
        mode: str,
    ) -> SessionMetadata:
        """Create a new session."""
        self.ensure_state_dir()
        now = time.time()
        metadata = SessionMetadata(
            session_id=session_id,
            target_root=str(target_root),
            mode=mode,
            created_at=now,
            updated_at=now,
            state=SessionState.RUNNING.value,
        )
        self._save_session(metadata)
        self.log_audit(
            ChangeType.CHECKPOINT_SAVED,
            f"Session {session_id} created in {mode} mode",
            metadata={"target_root": str(target_root)},
        )
        return metadata

    def update_session(self, metadata: SessionMetadata) -> None:
        """Update session metadata."""
        self.ensure_state_dir()
        metadata.updated_at = time.time()
        self._save_session(metadata)

    def get_session(self) -> SessionMetadata | None:
        """Get current session metadata."""
        if not self.session_path.exists():
            return None
        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
            return SessionMetadata.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_session(self, metadata: SessionMetadata) -> None:
        """Save session metadata to disk atomically."""
        self._atomic_write_json(self.session_path, metadata.to_dict())

    def increment_command_count(self, count: int = 1) -> None:
        """Increment the total commands run counter."""
        session = self.get_session()
        if session:
            session.total_commands_run += count
            self.update_session(session)

    def increment_file_count(self, count: int = 1) -> None:
        """Increment the total files changed counter."""
        session = self.get_session()
        if session:
            session.total_files_changed += count
            self.update_session(session)

    def increment_error_count(self) -> None:
        """Increment the errors encountered counter."""
        session = self.get_session()
        if session:
            session.errors_encountered += 1
            self.update_session(session)

    # --- Phase Snapshot Operations ---

    def save_phase_snapshot(self, snapshot: PhaseSnapshot) -> None:
        """Save a phase snapshot for crash recovery."""
        self.ensure_state_dir()
        path = self._get_phase_path(snapshot.phase_id)
        self._atomic_write_json(path, snapshot.to_dict())

    def get_phase_snapshot(self, phase_id: str) -> PhaseSnapshot | None:
        """Get a phase snapshot if it exists."""
        path = self._get_phase_path(phase_id)
        if not path.exists():
            return None
        try:
            return PhaseSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError):
            return None

    def get_all_phase_snapshots(self) -> list[PhaseSnapshot]:
        """Get all phase snapshots for the session."""
        if not self.phases_dir.exists():
            return []

        snapshots = []
        for path in self.phases_dir.glob("*.json"):
            try:
                snapshots.append(PhaseSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(snapshots, key=lambda s: s.started_at)

    def delete_phase_snapshot(self, phase_id: str) -> None:
        """Delete a phase snapshot after successful completion."""
        path = self._get_phase_path(phase_id)
        if path.exists():
            path.unlink()

    # --- Recovery Operations ---

    def save_recovery_point(
        self,
        session_id: str,
        phase_id: str,
        phase_title: str,
        files_written: list[str],
        command_history: list[dict],
    ) -> None:
        """Save a recovery point for crash-safe progress updates."""
        self.ensure_state_dir()
        recovery = {
            "session_id": session_id,
            "phase_id": phase_id,
            "phase_title": phase_title,
            "saved_at": time.time(),
            "files_written": files_written,
            "command_history": command_history,
        }
        self._atomic_write_json(self.recovery_path, recovery)

    def get_recovery_point(self) -> dict | None:
        """Get the last recovery point if it exists."""
        if not self.recovery_path.exists():
            return None
        try:
            return json.loads(self.recovery_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def clear_recovery_point(self) -> None:
        """Clear recovery point after successful recovery."""
        if self.recovery_path.exists():
            self.recovery_path.unlink(missing_ok=True)

    # --- Cleanup Operations ---

    def cleanup_completed_session(self) -> dict:
        """Clean up state files for a completed session. Returns cleanup summary."""
        summary = {"files_removed": 0, "bytes_freed": 0}

        for path in [self.recovery_path, self.session_path]:
            if path.exists():
                size = path.stat().st_size
                path.unlink()
                summary["files_removed"] += 1
                summary["bytes_freed"] += size

        for path in self.phases_dir.glob("*.json"):
            if path.exists():
                size = path.stat().st_size
                path.unlink()
                summary["files_removed"] += 1
                summary["bytes_freed"] += size

        if self.phases_dir.exists() and not any(self.phases_dir.iterdir()):
            self.phases_dir.rmdir()

        return summary

    def get_session_stats(self) -> dict:
        """Get session statistics."""
        stats = {
            "audit_entries": 0,
            "phase_snapshots": 0,
            "session_exists": self.session_path.exists(),
            "recovery_exists": self.recovery_path.exists(),
        }

        if self.audit_path.exists():
            try:
                with self.audit_path.open("r", encoding="utf-8") as f:
                    stats["audit_entries"] = sum(1 for line in f if line.strip())
            except FileNotFoundError:
                pass

        if self.phases_dir.exists():
            stats["phase_snapshots"] = len(list(self.phases_dir.glob("*.json")))

        session = self.get_session()
        if session:
            stats["session_state"] = session.state
            stats["total_commands_run"] = session.total_commands_run
            stats["total_files_changed"] = session.total_files_changed
            stats["errors_encountered"] = session.errors_encountered

        return stats


class StaleLockRecovery:
    """Recovery mechanism for stale locks in the workspace."""

    @staticmethod
    def find_stale_locks(workspace: "TargetProjectWorkspace") -> list[dict]:
        """Find all stale locks in the workspace."""
        stale = []
        lock_root = workspace.lock_root

        if not lock_root.exists():
            return stale

        current_time = time.time()
        for lock_file in lock_root.glob("*.lock.json"):
            try:
                payload = json.loads(lock_file.read_text(encoding="utf-8"))
                expires_at = float(payload.get("expires_at", 0))
                if expires_at <= current_time:
                    stale.append({
                        "path": str(lock_file),
                        "file": lock_file.name,
                        "owner": payload.get("owner", "unknown"),
                        "expired_at": datetime.fromtimestamp(expires_at).isoformat(),
                        "held_for_seconds": int(current_time - expires_at),
                    })
            except (json.JSONDecodeError, KeyError, ValueError):
                stale.append({
                    "path": str(lock_file),
                    "file": lock_file.name,
                    "error": "Invalid lock file format",
                })

        return stale

    @staticmethod
    def recover_stale_lock(lock_file: Path) -> bool:
        """Attempt to recover a stale lock by removing it."""
        try:
            if lock_file.exists():
                lock_file.unlink()
                return True
        except OSError:
            return False
        return False

    @staticmethod
    def auto_recover_stale_locks(workspace: "TargetProjectWorkspace") -> dict:
        """Automatically recover all stale locks. Returns recovery summary."""
        stale_locks = StaleLockRecovery.find_stale_locks(workspace)
        recovered = []
        failed = []

        for lock_info in stale_locks:
            path = Path(lock_info["path"])
            if StaleLockRecovery.recover_stale_lock(path):
                recovered.append(lock_info["file"])
            else:
                failed.append(lock_info["file"])

        return {
            "found": len(stale_locks),
            "recovered": recovered,
            "failed": failed,
        }
