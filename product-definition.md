# Autobots Product Definition

## Product Statement

Autobots is a project-facing CLI orchestration tool that uses model-selected execution stages to plan, implement, review, and refine software work inside a target repository.

## Intended Users

- solo developers who want structured AI-assisted execution
- operators managing repeated code-change workflows across repositories
- teams who want a controlled autonomous coding runner with approval gates

## Core Jobs To Be Done

- prepare a project for AI-driven execution
- transform user intent into executable phases
- apply code and context changes safely
- verify changes against project tooling
- maintain auditable execution state

## Non-Goals For The Current Prototype

- fully independent background multi-agent infrastructure
- unrestricted filesystem mutation across arbitrary directories
- automatic deployment without explicit policy
- replacing human review in high-risk repos by default

## Product Modes

### Supervised Mode

Autobots executes a phase and pauses for approval.

### Milestone Mode

Autobots executes a group of phases and pauses at milestone boundaries.

### Autonomous Mode

Autobots continues through phases and validation loops until complete or blocked, within configured safety rails.

## Safety Boundaries

- branch isolation is mandatory by default
- protected context files require lock coordination
- `progress-tracker.md` remains coordinator-owned
- validation command execution is policy-checked today; broader approval escalation and richer command policy remain future work

## Success Criteria

Autobots is successful as a product when a new user can install the CLI, point it at a repo, initialize context, generate a roadmap, run phased work, inspect evidence, and resume interrupted runs without needing to read source code.
