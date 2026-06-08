# autobot-swarm — Refactor Changeset

## Overview

This document covers all changes required to make `autobots plan` read-only against `roadmap.md`, dispatch tasks in parallel per phase, and write results via a safe append-only queue writer.

---

## Files at a Glance

| Action | File |
|---|---|
| Modify | `autobots/planning.py` |
| Modify | `autobots/router/planning.py` |
| Modify | `autobots/cli.py` |
| **Create** | `autobots/executor/queue_writer.py` |
| **Create** | `autobots/executor/plan_runner.py` |
| **Create** | `tests/test_plan_readonly.py` |
| Reference | `CLI_PATCH_INSTRUCTIONS.py` |

---

## 1. `autobots/planning.py` — Make roadmap read-only

### Current behaviour
- Scans the repo
- Generates and **overwrites** both `roadmap.md` and `progress-tracker.md`

### New behaviour
- `roadmap.md` → **read-only**, never touched by this module
- `progress-tracker.md` → **append-only**, never overwritten

### Key addition: `parse_roadmap(path)`
A new function that reads `roadmap.md` and returns a structured list of phases and their tasks. This is the only way the rest of the system consumes roadmap data going forward.

```python
def parse_roadmap(path: str) -> list[dict]:
    """
    Reads roadmap.md (utf-8-sig to handle BOM on Windows) and returns
    a list of phase dicts: [{"phase": str, "tasks": [str], "complete": bool}]
    """
```

All code that previously wrote `roadmap.md` is removed. `route_task()` and `build_cluster_dispatch()` are added here to keep dispatch logic co-located with parsing.

---

## 2. `autobots/router/planning.py` — Parallel-within-phase dispatch

### Current behaviour
- Routes tasks **sequentially**, one at a time

### New behaviour
- Accepts a **full phase** (list of tasks) at once
- Dispatches **all tasks in the phase simultaneously** via `asyncio.gather`
- Returns all results before the caller advances to the next phase

```python
async def dispatch_phase(tasks: list[str], cluster_map: dict) -> list[dict]:
    """
    Fires all tasks in `tasks` concurrently.
    Returns results in the same order as input tasks.
    """
    coroutines = [route_to_cluster(task, cluster_map) for task in tasks]
    return await asyncio.gather(*coroutines)
```

---

## 3. `autobots/cli.py` — Rewire the `plan` command

### Current behaviour
- `autobots plan` generates/overwrites both `roadmap.md` and `progress-tracker.md`

### New behaviour (4-line handler)

```
1. Check for API key — block immediately if missing
2. Read roadmap.md (read-only via parse_roadmap)
3. Find the first incomplete phase
4. Call plan_runner.run_phase(phase) → results appended by queue_writer
```

Refer to `CLI_PATCH_INSTRUCTIONS.py` for the exact three surgical edits. The plan command handler shrinks to 4 lines; everything else in `cli.py` stays untouched.

---

## 4. NEW — `autobots/executor/queue_writer.py`

**Purpose:** Optimus's exclusive interface for writing cluster results to `progress-tracker.md`. Never overwrites — append-only, with a file lock to prevent race conditions when parallel tasks complete simultaneously.

```python
import fcntl  # portalocker on Windows

def append_result(path: str, phase: str, task: str, result: str) -> None:
    """
    Acquires an exclusive lock, appends a formatted result block,
    releases the lock. Safe to call from concurrent asyncio tasks
    via loop.run_in_executor.
    """
```

Result block format written to `progress-tracker.md`:

```
## [Phase Name] — [Task]
> Completed: 2025-xx-xx HH:MM:SS

[result text]

---
```

---

## 5. NEW — `autobots/executor/plan_runner.py`

**Purpose:** The execution engine called by `autobots plan`. Orchestrates the full loop:

1. Parse `roadmap.md` via `parse_roadmap()`
2. Find first incomplete phase
3. Call `dispatch_phase()` for parallel task execution
4. Hand results to `queue_writer.append_result()` in queue order
5. Repeat until all phases complete or a phase fails

---

## 6. NEW — `tests/test_plan_readonly.py`

20 tests covering:

- `parse_roadmap` correctly parses phases and tasks
- `parse_roadmap` handles BOM-prefixed files (Windows `utf-8-sig`)
- `roadmap.md` is never opened in write mode during `autobots plan`
- `progress-tracker.md` is only ever appended to, never truncated
- `dispatch_phase` fires all tasks concurrently (verified via mock timing)
- `queue_writer` is safe under concurrent writes (stress test with 10 parallel appends)
- CLI blocks immediately when `ANTHROPIC_API_KEY` is absent
- CLI correctly identifies the first incomplete phase
- Results appear in queue order regardless of task completion order

---

## End-to-End Behaviour After This Changeset

```
$ autobots plan
```

1. **API key check** — exits with a clear error if `ANTHROPIC_API_KEY` is not set
2. **Reads** `roadmap.md` — never writes it
3. **Finds** the first phase where `complete: false`
4. **Dispatches** all pending tasks in that phase to their clusters **in parallel** via `asyncio.gather`
5. **Appends** each result to `progress-tracker.md` in queue order — never overwrites
6. **Advances** to the next phase only after the current phase fully resolves
7. **BOM-prefixed files on Windows** work correctly (`utf-8-sig` encoding used throughout)

---

## Drop-in vs Replace vs Patch

| File | Action | Notes |
|---|---|---|
| `autobots/executor/queue_writer.py` | **Drop in** (new file) | Optimus uses this exclusively |
| `autobots/executor/plan_runner.py` | **Drop in** (new file) | New execution engine |
| `tests/test_plan_readonly.py` | **Drop in** (new file) | 20 tests |
| `autobots/planning.py` | **Replace entirely** | Removes all roadmap-write code; adds `parse_roadmap()`, `route_task()`, `build_cluster_dispatch()` |
| `autobots/router/planning.py` | **Replace entirely** | Sequential → parallel dispatch |
| `autobots/cli.py` | **Surgical patch** | Follow `CLI_PATCH_INSTRUCTIONS.py` — exactly 3 edits |
