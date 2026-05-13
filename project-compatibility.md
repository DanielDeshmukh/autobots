# Autobots Project Compatibility

## Purpose

This document captures the supported project assumptions and compatibility rules required by Phase 1.

## Supported Repository Shape

Autobots is designed to operate against a target repository that:

- is separate from the Autobots engine repository
- can be addressed by an absolute path or sibling directory selection
- allows creation of a `context/` directory at the project root
- has a working tree that the operator can place on a safety branch for execution flows

## Supported Source Layout Signals

Current repository inspection recognizes these common roots:

- `src/`
- `app/`
- `lib/`
- `tests/`
- `docs/`
- `scripts/`
- top-level language files such as `*.py`, `*.js`, `*.ts`, `*.rs`, and `*.go`

## Supported Stack Detection Signals

Languages:

- Python
- JavaScript/TypeScript
- Rust
- Go

Package managers and build signals:

- `pyproject.toml`
- `requirements.txt`
- `package.json`
- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `Cargo.toml`
- `go.mod`

Test tool signals:

- `tests/`
- `pytest.ini`
- `package.json` scripts and dependencies for `npm test`, `vitest`, and `jest`

## Compatibility Boundaries

Current prototype limits:

- execution writes are still limited to `src/` and `context/`
- generic command execution inside target repos is not enabled yet
- repos without detectable stack signals are supported only as `Unknown` during bootstrap
- framework detection is currently heuristic and not yet first-class

## Operator Expectations

- the operator is responsible for choosing the correct target repository
- the operator is responsible for supplying required credentials for live model calls
- the operator must review generated context and plans before trusting downstream execution
