# ADR-001: Autonomy Boundaries And Safety Model

## Status

Accepted for implementation guidance in Phase 1.

## Context

The current Autobots prototype can route model calls and write project files, but it does not yet operate as a trustworthy autonomous CLI for external repositories. The project needs a clear decision on where autonomy begins, where human approval remains mandatory, and how high-risk actions are constrained.

## Decision

Autobots will evolve as a bounded-autonomy CLI with explicit control modes instead of a fully unrestricted autonomous agent.

The product will support:

- supervised execution with per-phase approval
- milestone execution with periodic approval
- autonomous execution within a configurable safety policy

High-risk actions must remain policy-gated, including:

- command execution in target repositories
- writes outside approved project roots
- destructive git or filesystem actions
- deployment or migration actions with external side effects

## Consequences

Positive consequences:

- the CLI can become useful early without pretending to solve unrestricted autonomy
- users can adopt it incrementally
- future verification loops can be added safely

Tradeoffs:

- the README vision must be brought into alignment with real capabilities
- some workflows will remain slower until command execution and resumability are implemented

## Implementation Notes

- `engage` remains the supervised baseline
- `validate-models` is the first contract test for live model reliability
- future `run` mode should only become fully autonomous after command policy and checkpointing exist
