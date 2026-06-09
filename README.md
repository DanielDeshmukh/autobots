<div align="center">
  <a href="https://pypi.org/project/autobot-swarm/">
    <img src="assets/autobots-banner.png" alt="Autobots Banner" width="100%" />
  </a>
</div>
<br>

<p align="center">
  <a href="https://github.com/DanielDeshmukh/autobots">
    <img src="https://img.shields.io/badge/version-0.1.9-blue" alt="Version">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/python-3.11+-brightgreen" alt="Python">
  </a>
</p>

Autobots is a Python CLI for running a structured, approval-gated coding swarm against target repositories. It checks target-owned context files, generates phased plans, routes implementation work through hierarchical model clusters, and executes autonomous work with validation, repair, and rollback loops.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [NVIDIA Models Registry](#nvidia-models-registry)
- [Execution Modes](#execution-modes)
- [Context Architecture](#context-architecture)
- [Cross-Platform Usage](#cross-platform-usage)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

---

## Overview

Autobots transforms your development workflow by orchestrating multiple AI models as a hierarchical swarm:

1. **Optimus** (Command Cluster) — Plans and orchestrates the mission
2. **UltraMagnus** (Backend Cluster) — Implements backend logic and APIs
3. **Jazz** (Frontend Cluster) — Creates UI components and visual elements
4. **RedAlert** (Security Cluster) — Reviews code for safety and correctness
5. **Ratchet** (Repair Cluster) — Fixes validation failures and bugs
6. **Perceptor** (Retrieval Cluster) — Handles document parsing and RAG
7. **Bumblebee** (Media Cluster) — Processes speech, audio, and video
8. **Ironhide** (Simulation Cluster) — Runs physics and optimization tasks
9. **Wheeljack** (Science Cluster) — Handles molecular and research tasks

---

## Features

- **Context Injection** — Reads `context/` files and injects project documentation into model prompts
- **Phase Planning** — Generate implementation roadmaps with dependencies and acceptance criteria
- **Model Routing** — Intelligent cluster selection based on task keywords
- **Multi-Root File Writing** — Write to `src/`, `app/`, `lib/`, `tests/`, `docs/`, `scripts/`
- **Validation Commands** — Run tests, linters, and build commands automatically
- **Automatic Repair** — Self-healing execution with validation-driven repair loops
- **Session Management** — Durable checkpoints, resumable runs, and audit trails
- **Configurable Modes** — Supervised, milestone, or fully autonomous execution
- **Rollback Support** — Snapshots before writes, `autobots undo` reverts changes
- **Response Streaming** — Live character counter during model calls
- **Doctor Preflight** — Health checks before execution (API, git, config, dependencies)
- **Structured Errors** — Contextual error messages with actionable suggestions
- **Test Gate** — Run tests before commit with `autobots gate`
- **Git Integration** — Auto-commit after phase completion
- **Config Validation** — `autobots config validate` checks TOML settings
- **Shell Completions** — bash, zsh, and fish tab completion
- **Context Budget** — Warns and truncates when prompts approach model limits
- **Plugin System** — before/after hooks for custom extensions
- **Skill Marketplace** — Built-in packs for FastAPI, Django, React, Next.js
- **NVIDIA Skills** — 17 NVIDIA-specific skills injected into cluster prompts (RAG, cuOpt, cuDF, Dynamo, Holoscan, CUDA-Q)
- **Web Dashboard** — Real-time status on port 8080
- **Rich Status Output** — Progress bars, estimated time, branch info
- **Explain Command** — `autobots explain P2-T3` shows audit trail details
- **Usage Stats** — `autobots stats` shows totals, averages, costs
- **Verbose Mode** — `--verbose` flag logs full prompts sent to models

---

## Architecture

```
autobots/
├── cli.py              # CLI entry point (20+ commands)
├── bootstrap.py        # Project profiling and context filename contract
├── config.py           # TOML + env config with validation
├── catalog.py          # Cluster definitions and model registry
├── workspace.py        # Target workspace safety and locking
├── errors.py           # Structured error classes
├── costs.py            # Token/cost estimation
├── git_utils.py        # Git auto-commit integration
├── preflight.py        # Doctor health checks
├── onboarding.py       # Interactive setup wizard
├── completions.py      # Shell tab completion
├── context_budget.py   # Context window management
├── plugins.py          # Plugin/hook system
├── marketplace.py      # Skill pack marketplace
├── dashboard.py        # Web dashboard
├── diff.py             # Snapshot comparison
├── router/
│   ├── core.py         # Main routing orchestration
│   ├── models.py       # Data models (ClusterPlan, PhaseRecord, etc.)
│   ├── planning.py     # Cluster assignment and model selection
│   ├── stages.py       # Stage execution (streaming, retry, verbose)
│   └── phases.py       # Phase reading and status management
├── executor/
│   ├── autonomy.py     # Autonomous execution engine
│   ├── modes.py        # Execution modes (supervised, milestone, autonomous)
│   ├── state.py        # Session state, audit trail, and rollback manager
│   ├── commands.py     # Command validation and execution
│   ├── gate.py         # Test-then-commit gate
│   └── validation.py   # Validation result handling
├── planning/
│   ├── core.py         # Plan generation
│   ├── scanner.py      # Repository scanning
│   └── synthesis.py    # Phase synthesis
├── skills/
│   ├── loader.py       # Skill pack loading
│   ├── cluster_prompts.py  # Cluster-specific system prompts
│   └── nvidia/         # 17 NVIDIA-specific skill files
│       ├── agent-skills.md
│       ├── rag-blueprint.md
│       ├── dynamo-router.md
│       ├── skill-evolution.md
│       └── ...         # (17 total skill files)
└── utils/
    └── retry.py        # Exponential backoff decorator
```

---

## Installation

### Prerequisites

- Python 3.11 or higher
- NVIDIA API Key (for model execution)

### pip install

```powershell
pip install autobot-swarm
```

### Development Install

```powershell
git clone https://github.com/DanielDeshmukh/autobots.git
cd autobots
python -m pip install -e . --no-build-isolation
```

---

## Configuration

### API Key Setup

```powershell
# Option 1: .env file
echo NVIDIA_API_KEY=your_key_here > .env

# Option 2: Environment variable
$env:NVIDIA_API_KEY = "your_key_here"
```

### Configuration File

Create `.autobots.toml` or `autobots.toml` in your project root or `$HOME`:

```toml
[autobots]
model_selection_profile = "balanced"   # balanced, speed, or quality
parallel_planning = false
disable_live_catalog = false
safety_branch = "autobots-safety"
default_mode = "supervised"            # supervised, milestone, autonomous
milestone_threshold = 3
max_verification_attempts = 3
temperature = 0.2
max_tokens = 4096

# Optional: custom model registry
# model_registry_path = "./my-registry.json"

# Optional: extra custom clusters
# [autobots.extra_clusters]
# MyCluster = ["nvidia/custom-model-1"]
```

---

## CLI Commands

All commands automatically detect the target project from the current working directory.

| Command | Description |
|---------|-------------|
| `autobots init` | Check context files in target project |
| `autobots init --interactive` | Interactive setup wizard |
| `autobots plan` | Generate implementation roadmap |
| `autobots run [task]` | Execute phases with autonomy mode |
| `autobots resume` | Resume from last checkpoint |
| `autobots engage` | Interactive mode with startup screen |
| `autobots status` | Rich status with progress bars |
| `autobots explain <id>` | Show audit trail for a phase/task |
| `autobots stats` | Usage statistics and costs |
| `autobots undo` | Rollback to previous snapshot |
| `autobots snapshots` | List available snapshots |
| `autobots diff` | Compare workspace to snapshot |
| `autobots logs` | View audit trail |
| `autobots doctor` | Preflight health checks |
| `autobots catalog` | Browse NVIDIA model registry |
| `autobots config validate` | Validate TOML configuration |
| `autobots completions` | Generate shell completions |
| `autobots marketplace` | Browse skill packs |
| `autobots dashboard` | Launch web dashboard |
| `autobots validate-models` | Test NVIDIA API connectivity |
| `autobots publish` | Build and publish to PyPI |

### Plan Options

| Flag | Description |
|------|-------------|
| `--goal "text"` | Set the planning goal |
| `--append` | Append new phases instead of replacing |
| `--dry-run` | Preview without writing files |

### Run Options

| Flag | Description |
|------|-------------|
| `--supervised` | Manual approval per phase (default) |
| `--milestone` | Approval every N phases |
| `--autonomous` | Fully autonomous execution |
| `--verbose` | Log full prompts sent to models |

---

## NVIDIA Models Registry

Autobots includes a comprehensive model registry with 9 clusters:

| Cluster | Role | Models | Keywords |
|---------|------|--------|----------|
| **Optimus** | Command & Routing | 9 | plan, roadmap, phase, orchestrate |
| **UltraMagnus** | Backend & Architecture | 12 | backend, api, database, service |
| **RedAlert** | Security & Safety | 10 | security, auth, guardrail, validation |
| **Jazz** | Frontend & Creative | 11 | ui, ux, css, image, visual |
| **Ratchet** | Debug & Repair | 10 | debug, fix, refactor, patch, repair |
| **Perceptor** | Retrieval & Parsing | 11 | ocr, rag, embedding, document |
| **Bumblebee** | Communication & Media | 9 | speech, voice, translation, audio |
| **Ironhide** | Physical & Simulation | 8 | simulation, physics, autonomous |
| **Wheeljack** | Scientific Specialist | 7 | science, molecule, protein, quantum |

---

## NVIDIA Skills

Autobots injects **17 NVIDIA-specific skills** into cluster system prompts. These are condensed knowledge docs from NVIDIA's official skill library, providing domain expertise for RAG, deployment, optimization, and more.

### Always-Loaded Skills (Tier 1)

| Skill | Cluster(s) | Description |
|-------|------------|-------------|
| `agent-skills.md` | Optimus, UltraMagnus | NemoClaw agent skill architecture and dispatch patterns |
| `autonomous-agent-research.md` | Optimus, Wheeljack | Autonomous research workflow: hypothesis → wire → launch → evaluate |
| `session-memory.md` | Optimus, Jazz | Durable working-session memory and checkpoint strategy |
| `skill-evolution.md` | ALL clusters | Self-improvement protocol: reflect on tasks, propose skill updates |
| `safety-policy.md` | Ironhide | Nemotron safety policy taxonomy and structured security reviews |
| `rag-blueprint.md` | UltraMagnus, Optimus | NVIDIA RAG Blueprint architecture (Milvus, embedding, reranking) |
| `rag-eval.md` | Jazz | RAG evaluation with RAGAS metrics and benchmark harnesses |
| `dynamo-deployment.md` | UltraMagnus, Wheeljack | Dynamo Kubernetes recipes and deployment modes |
| `dynamo-router.md` | UltraMagnus, Optimus | Dynamo router modes (round-robin, KV-aware, least-loaded) |
| `retrieval.md` | UltraMagnus, Bumblebee | Document retrieval pipeline (PDF, image OCR, audio transcription) |

### Conditional Skills (Tier 2)

Loaded automatically when roadmap keywords are detected:

| Skill | Loaded When | Description |
|-------|-------------|-------------|
| `nemotron-customize.md` | fine-tuning, training | Nemotron model customization (SFT, DPO, RLHF) |
| `cuopt-routing.md` | routing, scheduling | cuOpt vehicle routing API (VRP, TSP, PDP) |
| `cuopt-optimization.md` | optimization, LP/MILP/QP | cuOpt numerical optimization (GPU-accelerated) |
| `cudf.md` | pandas, dataframe | cuDF GPU DataFrames (pandas acceleration) |
| `neautomodel-recipe.md` | training at scale | NeMo Automodel distributed training recipes |
| `kubernetes-infra.md` | Kubernetes, K8s | Physical AI infrastructure setup (MicroK8s, OSMO) |
| `holoscan.md` | video, edge AI | Holoscan SDK video analytics pipelines |
| `cudaq.md` | quantum computing | CUDA-Q quantum circuit simulation |

---

## Execution Modes

### Supervised Mode (Default)

```powershell
autobots run --supervised
```

- Requires approval before each phase
- Full human control over execution

### Milestone Mode

```powershell
autobots run --milestone
```

- Requires approval after N phases (configurable)
- Balance between autonomy and control

### Autonomous Mode

```powershell
autobots run --autonomous
```

- No approval gates, fastest execution

---

## Context Architecture

Autobots expects six target-owned context files under `context/`:

| File | Purpose |
|------|---------|
| `architecture.md` | Project architecture and structure |
| `conventions.md` | Code style, naming, formatting rules |
| `testing-strategy.md` | Test framework, coverage, patterns |
| `security-auth.md` | Security and authentication notes |
| `roadmap.md` | Phase definitions with goals and validation |
| `progress-tracker.md` | Phase status tracking (autobots updates this) |

These files are injected into model prompts so generated code matches your project's patterns.

---

## Cross-Platform Usage

### Windows

```powershell
pip install autobot-swarm
$env:NVIDIA_API_KEY = "your_key"
cd C:\path\to\your\project
autobots init
autobots plan
autobots run
```

### macOS / Linux

```bash
pip install autobot-swarm
export NVIDIA_API_KEY="your_key"
cd /path/to/your/project
autobots init
autobots plan
autobots run
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | NVIDIA API key for model access | Required |
| `AUTOBOTS_MODEL_SELECTION_PROFILE` | Model selection: balanced/speed/quality | balanced |
| `AUTOBOTS_ENABLE_PARALLEL_PLANNING` | Enable parallel workstreams | false |
| `AUTOBOTS_DISABLE_LIVE_CATALOG` | Use bundled models only | false |
| `AUTOBOTS_SAFETY_BRANCH` | Required git branch name | autobots-safety |
| `AUTOBOTS_DEFAULT_MODE` | Default execution mode | supervised |
| `AUTOBOTS_MILESTONE_THRESHOLD` | Phases per approval | 3 |
| `AUTOBOTS_MAX_VERIFICATION_ATTEMPTS` | Retry limit | 3 |

---

## Troubleshooting

### Missing NVIDIA API Key

```
RuntimeError: NVIDIA_API_KEY is missing. Cannot execute the swarm.
```

**Solution**: Set `NVIDIA_API_KEY` in `.env` or environment variable.

### Incomplete Context Setup

```
Command: run
Missing: roadmap.md, progress-tracker.md
```

**Solution**: Create the listed files in `context/`, then run `autobots plan`.

### Safety Branch Check Fails

```
Execution blocked. Switch to autobots-safety branch.
```

**Solution**: `git checkout -b autobots-safety`

### Command Policy Violation

```
Command not in safety whitelist: rm -rf /
```

**Solution**: Autobots blocks dangerous commands. Use safe alternatives.

### Resume Without Checkpoint

```
No checkpoint found. Use 'autobots run' to start fresh.
```

**Solution**: Start a new run with `autobots run`.

---

## Development

### Running Tests

```powershell
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_phase_9_config.py -v

# With coverage
python -m pytest tests/ --cov=autobots --cov-report=html
```

### Project Structure

```
autobots/
├── autobots/           # Main package (35 modules)
├── skills/             # Skill injection system
├── utils/              # Utilities (retry decorator)
├── tests/              # Test suite (465 tests)
├── integration/        # Integration tests (10 tests)
├── setup.cfg           # Package configuration
└── README.md           # This file
```

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.9 | 2026-06-09 | NVIDIA Skills: 17 skill files injected into cluster prompts (RAG, cuOpt, cuDF, Dynamo, Holoscan, CUDA-Q), roadmap-based conditional loading, live catalog discovery |
| 0.1.8 | 2026-06-09 | Priority features: rollback, streaming, preflight, onboarding, errors, gate, git, config validation, completions, context budget, plugins, marketplace, dashboard, diff, logs, costs, rich status, explain, stats, verbose |
| 0.1.7 | 2026-06-08 | PyPI description update |
| 0.1.6 | 2026-06-08 | Guide to A+++: retry, safe subprocess, logging, engage screen |
| 0.1.5 | 2026-06-08 | Task ID registry, publish command, skill injection |
| 0.1.4 | 2026-06-08 | Removed Autobots-created context files |
| 0.1.1 | 2026-05-15 | Phase 9-10: config, error handling, failure tests |
| 0.1.0 | 2026-05-14 | Phase 1-8.5: core functionality |

---

## Acknowledgments

- Built with [NVIDIA NIM](https://developer.nvidia.com/nim) for model access
- Powered by [Rich](https://github.com/Textualize/rich) for terminal UI
- Uses [OpenAI](https://openai.com) compatible API interface
