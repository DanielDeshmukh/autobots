# Autobots CLI Contract

## Phase 1 Scope

This document defines the intended command contract for Autobots as a reusable CLI tool for other software projects.

## Implemented Commands

### `autobots engage`

Interactive phase runner for a target project.

Behavior:

- selects a target project
- enforces the `autobots-safety` branch
- checks for the target `context/` folder
- reads `roadmap.md` and `progress-tracker.md`
- executes the next `PENDING` or `IN_PROGRESS` phase
- pauses for approval or revision
- repeats until no active phases remain

### `autobots validate-models`

Live model contract smoke test.

Behavior:

- creates a temporary validation workspace
- generates a synthetic phase
- runs command, specialist, and review stages against live models
- validates each response against the JSON shape expected by the router
- runs the repair stage if review requests revision
- writes a report to `model-validation-report.json`

## Planned Commands

### `autobots init`

Initialize `context/` files and project metadata for a target repo.

### `autobots plan`

Inspect a target repo and generate or refresh `roadmap.md` and `progress-tracker.md`.

### `autobots run`

Execute planned work with configurable approval boundaries.

### `autobots resume`

Continue a previously interrupted run from saved state.

### `autobots status`

Show active phase status, latest run metadata, and blocker state.

### `autobots review`

Display recent changes, validation output, and current phase evidence before approval.

## Global Requirements

- target work must happen in a separate project, not the Autobots engine repo
- safety branch enforcement remains enabled by default
- model responses must conform to strict JSON contracts
- any future command execution in target repos must be policy-controlled

## Exit Criteria For CLI Contract Stability

- implemented commands have documented behavior
- planned commands have defined intent and boundaries
- approval and autonomy modes are separated explicitly
