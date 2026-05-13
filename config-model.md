# Autobots Configuration Model

## Purpose

This document defines the Phase 1 configuration model for Autobots. It is intentionally small and implementation-oriented so later phases can build on stable concepts.

## Configuration Sources

Autobots will read configuration from these sources in descending precedence:

1. CLI flags
2. environment variables
3. future config file support
4. built-in defaults

## Core Settings

### API Credentials

- `NVIDIA_API_KEY`
  - required for live model execution and model validation
  - may be stored in `.env` for local development

### Model Registry

- `AUTOBOTS_MODEL_REGISTRY`
  - optional path to a JSON file that appends or overrides cluster model IDs
- `AUTOBOTS_DISABLE_LIVE_CATALOG`
  - disables live endpoint discovery when set to `1`

### Approval Mode

Conceptual values for later execution commands:

- `supervised`
- `milestone`
- `autonomous`

Phase 1 decision:

- `engage` is the supervised baseline
- future `run` will accept an explicit approval mode

### Command Policy

Conceptual controls for later execution phases:

- allowlisted validation commands
- approval-required destructive or side-effecting commands
- workspace write roots
- timeout limits

Phase 1 decision:

- command execution inside target repos is not yet enabled
- command policy must exist before Phase 5 validation loops are considered complete

## Compatibility With Current Code

Current code already reads:

- `NVIDIA_API_KEY`
- `AUTOBOTS_MODEL_REGISTRY`
- `AUTOBOTS_DISABLE_LIVE_CATALOG`

These settings are consumed by:

- [autobots/cli.py](/d:/Vs%20Code/VS%20code/autobots/autobots/cli.py:220)
- [autobots/catalog.py](/d:/Vs%20Code/VS%20code/autobots/autobots/catalog.py:263)

## Future Config File Shape

Planned direction:

```toml
[models]
registry_path = "autobots-model-registry.json"
disable_live_catalog = false

[execution]
mode = "supervised"
approval_boundary = "phase"

[policy]
allowed_write_roots = ["src", "context", "tests", "docs"]
allowed_commands = ["pytest -q"]
```
