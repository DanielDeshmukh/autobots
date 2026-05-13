# Autobots CLI Contract

## Phase 1 Scope

This document defines the command surface, behavior boundaries, and implementation expectations for Autobots as a reusable CLI for other software projects.

## Command Surface

### `autobots init [target_path]`

Purpose:

- initialize `context/` for a target repository in one command

Behavior:

- resolves the target repository from `target_path` or interactive selection
- inspects repository language, package manager, test tools, source roots, and config files
- creates or refreshes the six core context files
- writes starter content that reflects the detected repository structure

Current status:

- implemented

### `autobots plan [target_path] [goal...]`

Purpose:

- inspect a target repository and synthesize an execution-ready roadmap and progress tracker

Behavior:

- resolves the target repository from `target_path`
- scans source roots, tests, build files, env files, and docs
- converts the operator goal into ordered planning phases
- writes `context/roadmap.md`
- writes `context/progress-tracker.md`
- preserves matching completed tasks when regenerating a plan

Current status:

- implemented for Phase 3 baseline

### `autobots run [target_path]`

Purpose:

- execute planned work against a target repository

Behavior contract:

- loads the latest roadmap, progress tracker, and run policy
- selects the next actionable phase with satisfied dependencies
- prepares a work packet with goal, relevant files, constraints, and validation commands
- executes according to the selected approval mode
- records outputs, validation results, and blockers in durable run state

Current status:

- planned

### `autobots resume [target_path]`

Purpose:

- continue a previously interrupted run from the last stable checkpoint

Behavior contract:

- loads persisted run metadata
- restores the active phase, mode, and pending validations
- resumes only when the stored target repo and policy are still valid
- refuses to resume corrupted or incompatible state without operator intervention

Current status:

- planned

### `autobots status [target_path]`

Purpose:

- report current planning or execution state for a target repository

Behavior contract:

- shows the active phase and dependency status
- shows the most recent run result, blocker, or checkpoint
- indicates approval mode and pending operator actions
- reports whether required context files are missing or stale

Current status:

- planned

### `autobots review [target_path]`

Purpose:

- show evidence for approval before changes are accepted

Behavior contract:

- displays the proposed or recent file changes
- shows validation command results and repair attempts
- surfaces review notes, blockers, and acceptance checks
- supports approval, rejection, or revision feedback workflows

Current status:

- planned

### `autobots engage`

Purpose:

- supervised interactive phase runner for the current prototype

Behavior:

- selects a target project
- enforces the `autobots-safety` branch
- checks for the target `context/` folder
- reads `roadmap.md` and `progress-tracker.md`
- executes the next `PENDING` or `IN_PROGRESS` phase
- pauses for approval or revision
- repeats until no active phases remain

Current status:

- implemented as the legacy supervised runner

### `autobots validate-models`

Purpose:

- smoke-test live model contract compliance

Behavior:

- creates a temporary validation workspace
- generates a synthetic phase
- runs command, specialist, review, and optional repair stages against live models
- validates response JSON contracts
- writes a report to `model-validation-report.json`

Current status:

- implemented as an internal verification command

## Global Flags And Inputs

Current baseline:

- `target_path` is the only supported positional input for `init` and `plan`

Reserved for later phases:

- `--mode <supervised|milestone|autonomous>`
- `--approval-boundary <phase|milestone|never>`
- `--dry-run`
- `--config <path>`

## Approval Modes

### Supervised

- pause after every phase for explicit approval

### Milestone

- pause after a configured group of phases

### Autonomous

- continue until completion or a hard blocker within policy limits

## Command Policy Boundaries

- target work must happen in a separate project, not the Autobots engine repo
- safety branch enforcement remains enabled by default for execution commands
- model responses must conform to strict JSON contracts
- future command execution in target repos must be policy-controlled
- destructive git or filesystem actions must remain explicitly gated

## Exit Criteria For CLI Contract Stability

- implemented commands have documented behavior
- planned commands have concrete behavior contracts, not just names
- approval and autonomy modes are separated explicitly
- the command surface is stable enough to implement without redefining core semantics
