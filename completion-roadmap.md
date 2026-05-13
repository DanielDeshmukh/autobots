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
- model-generated file writes into `src/` and `context/`
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

### Objective

Replace the current narrow file-generation loop with a true project execution engine.

### Deliverables

- autonomous task runner for phase execution ✓
  - `PhaseExecutor` class with structured `WorkPacket` dataclass
  - Execution loop: inspect → generate → apply → validate
  - `execute_command()` with timeout and error handling
  
- support for writing beyond `src/` through a safe workspace policy ✓
  - `ALLOWED_WRITE_ROOTS` set: src, app, lib, tests, docs, scripts, context
  - Expanded `TargetProjectWorkspace` with `write_file()` and `read_file()` methods
  - `apply_generated_files()` supports all layout roots
  
- file read/write policy for common layouts ✓
  - src/: Source code files
  - app/: Application components
  - lib/: Libraries and utilities
  - tests/: Test files
  - docs/: Documentation
  - scripts/: Build and utility scripts
  - context/: Protected Autobots coordination files
  
- structured work packets that include ✓
  - goal: Phase objective
  - relevant files: Files to inspect and modify
  - constraints: Implementation constraints
  - validation commands: Automated checks
  - `PhaseExecutor.build_work_packet()` creates these packets
  
- iterative execution loop that can ✓
  - inspect files: `inspect_phase_files()` reads and reports file contents
  - generate edits: Router models generate file changes
  - apply edits: `apply_generated_changes()` writes files to workspace
  - evaluate results: `validate_phase()` runs validation commands

### Exit Criteria

- Autobots can complete real phases that touch ordinary project layouts ✓
  - Tested with app/, lib/, tests/, docs/, scripts/ directories
  - 17 new Phase 4 tests validate all functionality
  - `test_phase_4_execution.py` proves end-to-end execution
  
- execution is not limited to `src/` and `context/` ✓
  - `ALLOWED_WRITE_ROOTS` expands to 7 project layout directories
  - `workspace.write_file()` method routes writes to correct root
  - Router prompts now mention all available roots
  
- phase work can be repeated until acceptance conditions are met or blocked ✓
  - Iterative execution loop supports repair cycles
  - Command execution with safety policy enables validation feedback
  - Phase files can be regenerated and re-applied without corruption

## Phase 5: Terminal Command And Verification Layer

### Objective

Allow Autobots to validate and refine changes using the target project’s actual toolchain.

### Deliverables

- safe command execution policy for target repos
- support for running:
  - tests
  - linters
  - formatters
  - builds
  - type checks
  - migrations when explicitly allowed
- command allowlist and approval escalation model
- parsing of command output into structured repair prompts
- automatic verify-repair loop

### Exit Criteria

- Autobots can run validation commands after implementation
- failed commands trigger repair cycles automatically
- command execution is logged and bounded by safety policy

## Phase 6: Autonomy Modes And Human Control

### Objective

Support both supervised and autonomous operation cleanly.

### Deliverables

- execution modes:
  - manual approval per phase
  - approval per milestone
  - fully autonomous within policy
- pause, resume, abort, and checkpoint commands
- blocker detection and escalation behavior
- dry-run mode for planning without writes
- review mode for showing pending changes before apply

### Exit Criteria

- users can choose the desired control level at runtime
- long-running execution can resume after interruption
- the system stops safely on blockers instead of silently failing

## Phase 7: State Management, Locking, And Recovery

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

## Phase 8: Multi-Cluster Orchestration Improvements

### Objective

Bring the code closer to the swarm model described in the README.

### Deliverables

- explicit planner, implementer, reviewer, and repair roles
- optional parallel work for independent subtasks
- better routing heuristics than keyword matching alone
- configurable model selection by capability and cost
- prompt templates per cluster type
- result-merging strategy for parallel branches

### Exit Criteria

- orchestration behavior is measurable and predictable
- routing quality is improved for diverse tasks
- parallel execution is used only where safe and beneficial

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
8. Phase 8
9. Phase 9
10. Phase 10

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
