# Autobots

Autobots is a Python CLI for running a structured, approval-gated coding swarm against a target repository. It can initialize project context, generate phased plans, route implementation work through model clusters, and validate model contract behavior.

## Current Status

- Phases 1-8.5 are implemented in the current codebase.
- The shipped CLI surface today includes `autobots init`, `autobots plan`, `autobots run`, `autobots resume`, `autobots status`, `autobots engage`, and `autobots validate-models`.
- Autonomous or milestone execution requires a configured `NVIDIA_API_KEY`; missing credentials now surface as resumable blockers instead of uncaught crashes.

## Next Focus

- Phase 9 is the next delivery target: packaging, configuration, distribution, and installability polish.

## What Works Today

- Initialize a target repo with Autobots context files.
- Scan a repository and generate ordered implementation phases with dependencies and acceptance checks.
- Create durable execution sessions, checkpoints, and audit trail state for runtime commands.
- Execute the next phase through a routed cluster workflow with review and optional repair.
- Write generated files across common repo roots: `src/`, `app/`, `lib/`, `tests/`, `docs/`, `scripts/`, and `context/`.
- Run validation commands through the execution layer and feed failures into automatic repair passes.
- Resume paused or blocked runtime sessions from the last stable checkpoint.
- Use a live NVIDIA model registry when available, with fallback model metadata bundled in the repo.

## Project Layout

- [autobots/cli.py](/d:/Vs%20Code/VS%20code/autobots/autobots/cli.py): CLI entrypoint and command flow
- [autobots/bootstrap.py](/d:/Vs%20Code/VS%20code/autobots/autobots/bootstrap.py): repo profiling and context initialization
- [autobots/planning.py](/d:/Vs%20Code/VS%20code/autobots/autobots/planning.py): roadmap and progress tracker generation
- [autobots/router.py](/d:/Vs%20Code/VS%20code/autobots/autobots/router.py): cluster orchestration, model contracts, and phase execution flow
- [autobots/executor.py](/d:/Vs%20Code/VS%20code/autobots/autobots/executor.py): work packets, file application, and validation commands
- [autobots/workspace.py](/d:/Vs%20Code/VS%20code/autobots/autobots/workspace.py): target workspace safety and locking rules

## Install

```powershell
python -m pip install -e . --no-build-isolation
```

## Configure

Create a repo-local `.env` with:

```env
NVIDIA_API_KEY=your_key_here
```

## Usage

Initialize context in a target project:

```powershell
autobots init D:\path\to\target-project
```

Generate or refresh a plan:

```powershell
autobots plan D:\path\to\target-project --goal "Add a planning workflow"
```

Run the phase executor:

```powershell
autobots run D:\path\to\target-project --supervised
```

Resume from the last checkpoint:

```powershell
autobots resume D:\path\to\target-project
```

Inspect runtime session status:

```powershell
autobots status D:\path\to\target-project
```

Validate live model JSON contracts:

```powershell
autobots validate-models
```

## Context Files

Autobots manages six project context files under `context/`:

- `architecture.md`
- `roadmap.md`
- `ui-components.md`
- `progress-tracker.md`
- `project-briefing.md`
- `security-auth.md`

## Testing

```powershell
python -m unittest discover -s tests -v
```

## Notes

- `engage` remains the interactive approval-gated workflow, while `run`, `resume`, and `status` are the operational runtime commands.
- `run`, `resume`, and `status` require the initialized six-file Autobots context under `context/`.
- Migration commands require an explicit phase constraint such as `allow migrations` before Autobots will execute them.
- The codebase is currently aligned around the real shipped prototype rather than the earlier "100+ NIM" marketing description.
