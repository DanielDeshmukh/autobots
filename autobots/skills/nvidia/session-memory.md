# Durable Session Memory for Coding Agents

## Session State Model
```json
{
  "session_id": "<unique-id>",
  "created_at": "<timestamp>",
  "context": {
    "active_phase": "<current phase>",
    "completed_tasks": ["<task 1>", "<task 2>"],
    "pending_tasks": ["<task 3>"],
    "key_decisions": [{"decision": "<what>", "reason": "<why>"}]
  },
  "artifacts": {
    "files_modified": ["<path 1>", "<path 2>"],
    "test_results": {"<test>": "pass|fail"},
    "metrics": {"<metric>": <value>}
  }
}
```

## Checkpoint Strategy
1. **Pre-phase**: Save full context before starting a phase
2. **Post-task**: Update state after each completed task
3. **On-error**: Capture failure context for recovery
4. **On-resume**: Restore state, validate consistency, continue

## Recovery Protocol
```
1. Load last checkpoint
2. Validate file hashes match expected state
3. Identify incomplete tasks
4. Resume from last successful task
5. Re-run failed tasks with updated context
```

## Context Handoff Rules
- Pass full context to next phase, not summaries
- Include file diffs, not just file lists
- Preserve error history to avoid repeating mistakes
- Maintain decision log for audit trail
