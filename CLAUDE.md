# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Autobots (`autobot-swarm` on PyPI) is a Python CLI that orchestrates a hierarchical coding swarm against a **target project** (which is NOT this repo). Operators run Autobots commands from the parent directory of the target project. The target project must contain six `context/` markdown files (defined in `autobots/bootstrap.py:CORE_CONTEXT_FILES`); Autobots does not create them.

The package version is `0.1.4` (see `pyproject.toml` and `autobots/__init__.py`).

## Install / Build

```powershell
# Editable install (this repo is the engine)
python -m pip install -e . --no-build-isolation

# Build distributions (CI does this in .github/workflows/publish.yml on v* tags)
python -m build

# Entry point: autobots = autobots.cli:main (also reachable as python -m autobots via __main__.py)
```

Required runtime: **Python 3.11+** (uses `tomllib`). Dependencies: `openai`, `python-dotenv`, `rich` (`tomli` only for <3.11).

`NVIDIA_API_KEY` is required for any `run`, `resume`, `engage`, or `validate-models` invocation. The CLI prompts for it on first use and writes it to the engine repo's `.env` (`autobots/cli.py:_ensure_api_key`).

## Test

```powershell
# All tests
python -m pytest tests/ -v

# One file
python -m pytest tests/test_router_contracts.py -v

# Coverage
python -m pytest tests/ --cov=autobots --cov-report=html
```

Tests use `unittest.TestCase` (not pytest fixtures) and `tempfile.TemporaryDirectory` to construct scratch workspaces — there is no `conftest.py`. Many test files are named after the development phase that introduced them (`test_phase_4_execution.py`, `test_phase_7_state.py`, etc.) plus domain tests (`test_catalog`, `test_planning`, `test_router_contracts`, `test_bootstrap`, `test_context_gen`, `test_cli_plan_args`, `test_cli_runtime`).

## High-Level Architecture

Five cooperating subsystems, each in its own subpackage:

1. **`autobots/cli.py`** — argparse-less command dispatcher. Each verb (`init`, `plan`, `run`, `resume`, `status`, `engage`, `validate-models`, `list`) has a `run_<verb>(args)` function. `main(argv)` is the entry point. **It is a known mismatch that `pyproject.toml` and `setup.cfg` both declare the entry point as `autobots.cli:main`, but the actual function is `main` — both files reference it correctly, so the entry point works. Note however that `find_endpoints.py` is referenced in `autobots/catalog.py` but does not exist in this repo; live NVIDIA catalog discovery will fall back to the bundled registry when the file is absent (see `_load_discovery_module`).**

2. **`autobots/workspace.py`** — `TargetProjectWorkspace` is the only object that touches the target project's filesystem. Allowed write roots are the fixed set `{"src", "app", "lib", "tests", "docs", "scripts", "context"}`. Critical context files (`architecture.md`, `security-auth.md`) acquire a JSON lock at `context/.autobots-locks/*.lock.json` with a 60s TTL. All writes go through `_atomic_write_text` (tmp-file + rename). Path traversal is blocked by `_resolve` checking the resolved path stays under the root.

3. **`autobots/catalog.py`** — `ClusterCatalog` defines 9 clusters (Optimus/UltraMagnus/RedAlert/Jazz/Ratchet/Perceptor/Bumblebee/Ironhide/Wheeljack), each with `ModelSpec` entries, keywords, and role. `route_with_reasoning(task_signal)` scores clusters by keyword + file-extension + role-bias signals. `select_models(cluster, signal)` picks lead/reviewer/support based on tags and the `AUTOBOTS_MODEL_SELECTION_PROFILE` env var (`balanced`/`speed`/`quality`). The catalog can merge a live NVIDIA model list (via the missing `find_endpoints.py`) with the bundled registry, or stay on the bundled fallback.

4. **`autobots/router/`** — The swarm orchestrator. `core.py:AutobotRouter.execute_phase` is the main entry: it builds a `ClusterPlan` (via `planning.ClusterPlanner`), runs four sequential stages through `stages.StageExecutor`:
   - **command** (Optimus planner) → writes a mission brief
   - **specialist** (primary cluster) → returns a JSON `{summary, implementation_notes, files: [{root, path, content}]}` — the swarm's "language"
   - **safety** (RedAlert) → returns `{status: pass|revise, summary, issues}`
   - **repair** (Ratchet) → only when review returns `revise`

   The router then runs a `_run_verification_loop` of up to `MAX_VERIFICATION_ATTEMPTS=3` (env: `AUTOBOTS_MAX_VERIFICATION_ATTEMPTS`) that re-validates and triggers Ratchet repair on failure. The result is persisted to the workspace and returned as `ExecutionResult`.

   `phases.py:PhaseReader` parses `progress-tracker.md` lines that look like `- [ ] P3 | Title | depends on: ...` or `- [~]` (in progress) or `- [x]` (complete). `utils.PayloadValidator` enforces the JSON contracts each stage must return.

5. **`autobots/executor/`** — The execution engine. `autonomy.AutonomyEngine` drives the autonomous loop with three modes from `modes.ExecutionMode`: `SUPERVISED` (approval per phase), `MILESTONE` (approval every N phases — `AUTOBOTS_MILESTONE_THRESHOLD`, default 3), `AUTONOMOUS` (no approval). `core.PhaseExecutor` runs validation commands from a `WorkPacket`. `commands.CommandValidator` enforces a safety whitelist (test/lint/format/type/build/utility patterns) and rejects dangerous patterns (`rm -rf`, `sudo`, `kill -9`, `dd if=`, etc.) and migration commands unless `allow_migrations=True` (signaled by an `allow migration` token in the phase's constraints). `state.StateManager` writes durable state to `<target>/.autobots-state/` (audit log, session, per-phase snapshots, recovery point). `modes.ExecutionModeManager` saves/loads `.autobots-checkpoint.json` for `resume`.

Other modules:
- `autobots/planning/` — `write_plan` (in `core.py`) is the entry point for `autobots plan`. Calls `scanner.RepositoryScanner` to detect language/test/source roots, then `synthesis.PlanSynthesizer` to build a 3- or 4-phase plan (Inspect → Implement → Validate → optional Docs). `utils.py` renders `roadmap.md` and `progress-tracker.md` markdown formats.
- `autobots/config.py` — `AutobotsConfig.load()` reads `.autobots.toml`/`autobots.toml`/`.autobotsrc` from project root or `$HOME`, then merges env vars prefixed `AUTOBOTS_`. `apply_env_vars()` then writes them back as env vars (subprocesses pick them up).
- `autobots/bootstrap.py` — `detect_repo_profile(target_root)` produces a `RepoProfile` used by both `init` and `plan`. `CORE_CONTEXT_FILES` is the canonical six-file list.
- `autobots/context_gen.py` — `check_six_file_architecture` and `format_missing_context_files` for the missing-context warning UI.
- `autobots/selectors.py` — Interactive target-project picker (`resolve_target_project`) and safety-branch enforcer (`require_safety_branch`). The default safety branch is `autobots-safety` (env: `AUTOBOTS_SAFETY_BRANCH`).
- `autobots/ui.py` — Rich-based renderers (`render_plan`, `render_phase_panel`, `render_session_status`, etc.) and the cross-platform raw-key menu (`_read_menu_key` uses `msvcrt` on Windows, `termios`/`tty` elsewhere).

## Autobots Coordination Laws

Hard rules baked into `autobots/router/stages.py:COORDINATION_LAWS` and embedded in every prompt sent to models:
1. Pessimistic locks for `architecture.md` and `security-auth.md` (60s stale-lock reclaim).
2. Only the Optimus secretary model writes `progress-tracker.md`; specialist/reviewer/repair clusters must not.
3. Report completion back to Optimus instead of mutating shared progress state.
4. `PROTECTED_PROGRESS_FILES = {"progress-tracker.md"}` — `_enforce_generated_file_laws` in `router/core.py` strips these from any model output before writing.

The router enforces (2) by checking `SECRETARY_SNIPPET_CLUSTERS = {"UltraMagnus", "Jazz"}` — these clusters get a snippet of the progress tracker instead of the full text, reducing the chance they try to rewrite it.

## Cluster & Stage Flow

```
[PhaseRecord] → ClusterPlanner → ClusterPlan (primary, command, secretary, safety, repair leads)
            ↓
[StageExecutor.run_command_stage]    → {summary, implementation_goals, risks, acceptance_checks}
            ↓
[StageExecutor.run_specialist_stage]  → {summary, implementation_notes, files:[{root,path,content}]}
            ↓
[StageExecutor.run_safety_stage]      → {status: pass|revise, summary, issues}
            ↓ (if revise)
[StageExecutor.run_repair_stage]      → {summary, files:[...]}
            ↓
[_run_verification_loop]              → up to 3 attempts of validate → Ratchet repair on failure
            ↓
[AutobotRouter] writes files (workspace.apply_generated_files) with lock handling, returns ExecutionResult
```

Models are called via the OpenAI SDK pointed at `https://integrate.api.nvidia.com/v1` (NVIDIA NIM). All prompts end with `"Reply with strict JSON only."` — `PayloadValidator.parse_json` strips optional ` ```json ` fences.

## Configuration

Copy `autobots.toml.example` to `.autobots.toml` in this engine repo (or `$HOME`). All keys live under the `[autobots]` section. Key flags:

- `model_selection_profile` — `balanced` | `speed` | `quality` (drives `_score_model` weights)
- `parallel_planning` — when true, `_plan_parallel_workstreams` emits up to 3 `ParallelWorkstream` candidates grouped by path root
- `disable_live_catalog` — skip NVIDIA registry discovery; use bundled only
- `safety_branch` — git branch the target must be on
- `default_mode` — `supervised` | `milestone` | `autonomous`
- `milestone_threshold`, `max_verification_attempts`
- `model_registry_path` — JSON file `{cluster: [model_ids]}` merged into `ClusterCatalog._load_extra_registry`
- `extra_clusters` — TOML map of cluster name → model IDs

Every config key is also overridable via `AUTOBOTS_*` env vars (see `autobots/config.py:ENV_PREFIX`).

## Test Conventions

- `unittest.TestCase`, no pytest fixtures. Use `tempfile.TemporaryDirectory()` and `Path(tmpdir)` to build a fake target project, then call `TargetProjectWorkspace(root)` directly.
- Tests that exercise the swarm without API access construct `AutobotRouter(api_key="test-key")` and use the payload validators (`validate_command_payload`, `validate_specialist_payload`, `validate_review_payload`, `validate_repair_payload`) plus `ModelContractError` to assert JSON contract behavior.
- For model-free stage testing, use `_run_command_stage`, `_run_specialist_stage`, etc. on the router — but note these will hit the NVIDIA endpoint when `api_key` is real; pass a fake one only when you've stubbed the OpenAI client.

## Where to Look

| Task | File |
|---|---|
| Add a new CLI command | `autobots/cli.py` (`run_<verb>` + dispatch in `main`) |
| Add a cluster or models | `autobots/catalog.py` (`CLUSTER_DEFINITIONS`, `CLUSTER_MATCH_TOKENS`, `GENERAL_TEXT_MODEL_TOKENS`) |
| Change cluster routing logic | `autobots/catalog.py` (`_score_cluster_route`) or `router/planning.py` |
| Change model prompt for a stage | `autobots/router/stages.py` (`_build_*_prompt` methods) |
| Change JSON contract for a stage | `autobots/router/utils.py` (`PayloadValidator.validate_*_payload`) |
| Add a new write root | `autobots/workspace.py:ALLOWED_WRITE_ROOTS` |
| Change progress-tracker parsing | `autobots/router/phases.py` |
| Add a new validation command category | `autobots/executor/commands.py:SAFE_COMMAND_PATTERNS` |
| Change phase plan shape (3-phase → N-phase) | `autobots/planning/synthesis.py:build_phase_specs` |
| Change execution mode behavior | `autobots/executor/modes.py:ExecutionModeManager` |
| Change durable state layout | `autobots/executor/state.py:StateManager` |
