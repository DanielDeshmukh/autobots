"""Event bus — pipeline-to-UI communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class EventType(Enum):
    """All events the pipeline can emit."""
    # Session
    SESSION_STARTED = "session.started"
    SESSION_RESUMED = "session.resumed"
    
    # Request
    REQUEST_SUBMITTED = "request.submitted"
    
    # Plan
    PLAN_STARTED = "plan.started"
    PLAN_COMPLETED = "plan.completed"
    
    # Phase
    PHASE_STARTED = "phase.started"
    PHASE_COMPLETED = "phase.completed"
    
    # Agent (cluster)
    AGENT_STARTED = "agent.started"
    AGENT_UPDATED = "agent.updated"
    AGENT_COMPLETED = "agent.completed"
    
    # Tool
    TOOL_REQUESTED = "tool.requested"
    TOOL_APPROVED = "tool.approved"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    
    # Validation
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    
    # Repair
    REPAIR_STARTED = "repair.started"
    REPAIR_COMPLETED = "repair.completed"
    
    # Permission
    PERMISSION_REQUESTED = "permission.requested"
    
    # Snapshot
    SNAPSHOT_CREATED = "snapshot.created"
    
    # Context
    CONTEXT_COMPACTED = "context.compacted"
    
    # Run
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    
    # File
    FILE_WRITTEN = "file.written"
    
    # Build
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"
    
    # Healing
    HEALING_STARTED = "healing.started"
    HEALING_COMPLETED = "healing.completed"
    
    # Error
    ERROR = "error"
    
    # Log
    LOG = "log"


@dataclass
class Event:
    """An event with type and payload."""
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """Simple event bus for pipeline-to-UI communication.
    
    Usage:
        bus = EventBus()
        bus.on(EventType.AGENT_STARTED, my_handler)
        bus.emit(EventType.AGENT_STARTED, {"cluster": "Jazz", "task": "UI"})
    """
    
    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
    
    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def on_all(self, handler: EventHandler) -> None:
        """Register a handler for all events."""
        self._global_handlers.append(handler)
    
    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """Unregister a handler."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
    
    def emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all registered handlers."""
        import time
        event = Event(
            type=event_type,
            data=data or {},
            timestamp=time.time(),
        )
        
        # Call type-specific handlers
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass  # Never let handler errors break the pipeline
        
        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception:
                pass
    
    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
        self._global_handlers.clear()


# Global event bus instance
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
