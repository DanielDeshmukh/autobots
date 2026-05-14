# Autobots Completion Roadmap

## Goal

Turn Autobots from a phase-driven prototype into a reliable CLI tool that can be used against other software projects to:

- inspect project context
- plan work into executable phases
- generate and apply code changes safely
- run verification commands
- iterate on failures
- continue until the requested scope is complete or blocked

## Current Reality

The current codebase already provides:

- a CLI entrypoint: `autobots engage`
- target project selection
- safety branch enforcement
- context file reading from `context/`
- model routing across named clusters
- model-generated file writes across `src/`, `app/`, `lib/`, `tests/`, `docs/`, `scripts/`, and `context/`
- a human approval gate after each phase
- project bootstrap and context initialization (`autobots init`) ✓
- repository scanning and profile detection ✓
- roadmap and progress tracker generation (`autobots plan`) ✓
- phase synthesis with dependencies and acceptance criteria ✓
- plan regeneration and incremental planning ✓
- autonomous phase execution with structured work packets ✓
- multi-root file writing (app/, lib/, tests/, docs/, scripts/) ✓
- terminal command execution with safety policy ✓
- iterative execution loops for phase work ✓
- automatic validation-driven repair loops with structured verification reports ✓

The current codebase does not yet provide:

- full end-to-end autonomous execution without approval gates
- automatic task discovery from repository structure
- durable run state, resumability, and crash recovery
- production-grade observability, packaging, and documentation

## Target End State

Autobots should operate as a project-facing CLI that can be installed and run like:

```powershell
autobots init
autobots plan
autobots run
autobots resume
autobots status
```

In the target end state, Autobots should:

- initialize project context for a target repo
- derive or refine a multi-phase implementation plan
- execute tasks autonomously within configurable safety rails
- run validation commands after each change set
- revise failed work automatically
- keep an auditable state trail
- stop only on completion, explicit approval boundaries, or hard blockers

## Delivery Phases

## Phase 1: Product Definition And CLI Contract

### Objective

Define Autobots as a reusable product instead of a single interactive demo flow.

### Deliverables

- final command surface for the CLI
- command behavior spec for `init`, `plan`, `run`, `resume`, `status`, and `review`
- target project assumptions and compatibility rules
- config model for API keys, model registry, approval modes, and command policies
- root architecture decision record for autonomy boundaries and safety model

### Exit Criteria

- CLI commands and flags are documented and stable enough to implement
- autonomous and approval-gated modes are explicitly defined
- supported project layouts are documented

## Phase 2: Project Bootstrap And Context Initialization

### Objective

Make Autobots able to prepare a target project for use without requiring manual context setup.

### Deliverables

- `autobots init` command
- automatic creation of `context/` and required core files
- starter templates for:
  - `architecture.md`
  - `roadmap.md`
  - `ui-components.md`
  - `progress-tracker.md`
  - `project-briefing.md`
  - `security-auth.md`
- detection of repository language, framework, package manager, and test tools
- initial project summary generation from repo inspection

### Exit Criteria

- a new target repo can be initialized from the CLI in one command
- required context files are created consistently
- generated context reflects real repo structure

## Phase 3: Planning Engine And Phase Synthesis ✓ COMPLETE

### Objective

Generate high-quality executable phases from user intent and repository inspection.

### Deliverables

- `autobots plan` command ✓
- repository scanner for source layout, build files, tests, env files, and docs ✓
- roadmap generator that converts user goals into discrete phases ✓
- phase dependency model ✓
- progress tracker writer that creates `PENDING` tasks automatically ✓
- support for re-planning and inserting new phases during execution ✓

### Exit Criteria

- Autobots can produce a usable roadmap and progress tracker from a target repo ✓
- phases are actionable, ordered, and tied to acceptance checks ✓
- plans can be regenerated without corrupting prior state ✓

## Phase 4: Execution Engine For Real Project Work ✓ COMPLETE

### Deliverables

- autonomous task runner with `PhaseExecutor` and `WorkPacket` dataclass ✓
- multi-root file writing across src/, app/, lib/, tests/, docs/, scripts/ ✓
- iterative execution loop: inspect → generate → apply → validate ✓
- automatic repair cycles on validation failure ✓

### Exit Criteria

- Autobots completes real phases across ordinary project layouts ✓
- execution not limited to `src/` and `context/` ✓
- 40/41 tests pass (1 API unavailable - expected) ✓

## Phase 5: Terminal Command And Verification Layer ✓ COMPLETE

### Deliverables

- safe command execution policy ✓
- command allowlist with safety validation ✓
- automatic verify-repair loop ✓
- structured repair prompts from command output ✓

### Exit Criteria

- validation commands run after implementation ✓
- failed commands trigger automatic repair ✓

## Phase 6: Autonomy Modes And Human Control ✓ COMPLETE

### Objective

Support both supervised and autonomous operation cleanly.

### Deliverables

- execution modes:
  - manual approval per phase ✓
  - approval per milestone ✓
  - fully autonomous within policy ✓
- pause, resume, abort, and checkpoint commands ✓
- blocker detection and escalation behavior ✓
- dry-run mode for planning without writes ✓
- review mode for showing pending changes before apply (via engage) ✓

### Exit Criteria

- users can choose the desired control level at runtime ✓
- long-running execution can resume after interruption ✓
- the system stops safely on blockers instead of silently failing ✓

### Implementation Notes

New CLI commands:
- `autobots run [--autonomous|--milestone|--supervised] [target_path]` - Execute phases
- `autobots resume [target_path]` - Resume from checkpoint
- `autobots status [target_path]` - Show execution status

New modules:
- `autobots/executor/modes.py` - ExecutionMode, Blocker, ExecutionModeManager
- `autobots/executor/autonomy.py` - AutonomyEngine, AutonomousResult

## Phase 7: State Management, Locking, And Recovery ✓ COMPLETE

### Objective

Make swarm state durable and trustworthy for repeated runs.

### Deliverables

- run metadata store for active sessions
- persistent checkpointing of phase state and outputs
- stronger lock ownership and stale-lock recovery
- crash-safe progress updates
- resumable execution from the last stable checkpoint
- audit trail for file changes and command history

### Exit Criteria

- interrupted runs can be resumed safely
- state corruption and partial writes are minimized
- users can inspect what happened in a prior run

## Phase 8: Multi-Cluster Orchestration Improvements ✓ COMPLETE

### Objective

Bring the code closer to the swarm model described in the README.

### Deliverables

- explicit planner, implementer, reviewer, and repair roles ✓
- optional parallel work for independent subtasks ✓
- better routing heuristics than keyword matching alone ✓
- configurable model selection by capability and cost ✓
- prompt templates per cluster type ✓
- result-merging strategy for parallel branches ✓

### Exit Criteria

- orchestration behavior is measurable and predictable ✓
- routing quality is improved for diverse tasks ✓
- parallel execution is used only where safe and beneficial ✓

### Implementation Notes

All Phase 8 deliverables are now implemented:

- **explicit planner, implementer, reviewer, and repair role assignments** are attached to cluster plans via `ClusterRoleAssignment` in `router/models.py`
- **routing now records scored rationale** via `route_with_reasoning()` which returns multi-dimensional scoring with reasons (keyword hits, artifact signals, role bias)
- **model selection now supports speed/quality/balanced preferences** via `AUTOBOTS_MODEL_SELECTION_PROFILE` environment variable and `_score_model()` method with cost/latency tier inference
- **prompt templates are separated by stage** in `router/stages.py` with distinct prompts for command, specialist, safety, and repair stages
- **parallel workstream planning** identifies independent branches via `_plan_parallel_workstreams()` when `AUTOBOTS_ENABLE_PARALLEL_PLANNING` is set
- **result-merging strategy** implemented via `MergeStrategy` class with four modes:
  - `sequential_apply`: Apply each branch result in order, later branches override earlier
  - `union_files`: Merge files from all branches without conflicts
  - `best_effort`: Use first successful result, fall back to subsequent
  - `consensus`: Keep file only if all branches agree on content

## Phase 8.5: Operational CLI Reliability And Recovery ✓ COMPLETE

### Objective

Make the new runtime CLI commands behave predictably after the six-file context architecture is in place.

### Deliverables

- enforce six-file context validation for operational commands after setup
- convert missing NVIDIA API credentials into explicit execution blockers instead of raw crashes
- durable blocked or failed session state for interrupted autonomous runs
- resume behavior that re-enters from a stable checkpoint without looping into uncaught exceptions
- command and README behavior aligned with the real shipped CLI surface

### Exit Criteria

- `autobots run`, `autobots resume`, and `autobots status` refuse incomplete context setups clearly ✓
- interrupted autonomous runs persist inspectable blocked or failed state ✓
- `resume` returns controlled status for recoverable blockers instead of crashing ✓
- operator-facing docs match the actual command surface and runtime expectations ✓

### Implementation Notes

Phase 8.5 is now complete:

- operational runtime commands enforce the initialized six-file context before execution
- missing `NVIDIA_API_KEY` now becomes a durable `api_key` blocker instead of an uncaught runtime crash
- blocked autonomous sessions persist inspectable checkpoint and session state for `status`
- `resume` replays blocked runs as controlled blocker results rather than terminating the CLI abruptly
- runtime documentation now matches the actual command surface and expectations

## Phase 9: Packaging, Configuration, And Distribution

### Objective

Ship Autobots as a tool others can actually install and use.

### Deliverables

- polished packaging and installation flow
- example configuration files
- environment variable and config-file support
- versioned release process
- sample target projects for smoke testing
- cross-platform usage guidance for Windows, macOS, and Linux

### Exit Criteria

- users can install and run Autobots without reading source code
- configuration is discoverable and documented
- release artifacts are reproducible

## Phase 10: Quality, Testing, And Documentation

### Objective

Make the tool trustworthy enough for repeated external use.

### Deliverables

- unit tests for routing, parsing, locking, and workspace policies
- integration tests for CLI flows
- fixture repos for Python, Node, and mixed-layout projects
- failure-mode tests for invalid JSON, bad locks, and command failures
- operator documentation
- contributor documentation
- migration of README claims to match implemented behavior

### Exit Criteria

- critical flows are covered by automated tests
- docs match actual behavior
- the project is ready for external trial use

## Suggested Implementation Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7
8. Phase 8 ✓ COMPLETE
9. Phase 8.5
10. Phase 9
11. Phase 10

## Definition Of Done

Autobots is complete enough for external CLI use when all of the following are true:

- a user can point Autobots at a new repo and initialize it
- Autobots can generate a plan from repo context and user intent
- Autobots can execute phases across common repo layouts
- Autobots can run tests or other validation commands in the target repo
- Autobots can repair failures automatically
- Autobots can resume interrupted runs
- documentation matches real behavior
- at least one real sample project can be completed end to end through the CLI
