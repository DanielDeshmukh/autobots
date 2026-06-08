<div align="center">
  <a href="https://pypi.org/project/autobot-swarm/">
    <img src="assets/autobots-banner.png" alt="Autobots Banner" width="100%" />
  </a>
</div>
<br>

<p align="center">
  <a href="https://github.com/DanielDeshmukh/autobots">
    <img src="https://img.shields.io/badge/version-0.1.4-blue" alt="Version">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/python-3.11+-brightgreen" alt="Python">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
  </a>
</p>

Autobots is a Python CLI for running a structured, approval-gated coding swarm against target repositories. It can check target-owned context files, generate phased plans, route implementation work through hierarchical model clusters, and execute autonomous work with validation and repair loops.

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

1. **Optimus** (Command Cluster) - Plans and orchestrates the mission
2. **UltraMagnus** (Backend Cluster) - Implements backend logic and APIs
3. **Jazz** (Frontend Cluster) - Creates UI components and visual elements
4. **RedAlert** (Security Cluster) - Reviews code for safety and correctness
5. **Ratchet** (Repair Cluster) - Fixes validation failures and bugs
6. **Perceptor** (Retrieval Cluster) - Handles document parsing and RAG
7. **Bumblebee** (Media Cluster) - Processes speech, audio, and video
8. **Ironhide** (Simulation Cluster) - Runs physics and optimization tasks
9. **Wheeljack** (Science Cluster) - Handles molecular and research tasks

---

## Features

- **Context Checks** - Auto-detect project type (Python, Node, etc.) and report missing context filenames
- **Phase Planning** - Generate implementation roadmaps with dependencies and acceptance criteria
- **Model Routing** - Intelligent cluster selection based on task keywords
- **Multi-Root File Writing** - Write to `src/`, `app/`, `lib/`, `tests/`, `docs/`, `scripts/`
- **Validation Commands** - Run tests, linters, and build commands automatically
- **Automatic Repair** - Self-healing execution with validation-driven repair loops
- **Session Management** - Durable checkpoints, resumable runs, and audit trails
- **Configurable Modes** - Supervised, milestone, or fully autonomous execution

---

## Architecture

Autobots follows a modular architecture:

```
autobots/
├── cli.py              # CLI entry point and command handlers
├── bootstrap.py        # Project profiling and context filename contract
├── planning.py         # Roadmap and progress tracker generation
├── router/
│   ├── core.py        # Main routing orchestration
│   ├── models.py      # Data models (ClusterPlan, PhaseRecord, etc.)
│   ├── planning.py    # Cluster assignment and model selection
│   ├── stages.py      # Stage execution (command, specialist, review, repair)
│   └── phases.py      # Phase reading and status management
├── executor/
│   ├── autonomy.py    # Autonomous execution engine
│   ├── modes.py       # Execution modes (supervised, milestone, autonomous)
│   ├── state.py       # Session state and checkpoint management
│   ├── commands.py    # Command validation and execution
│   └── validation.py  # Validation result handling
├── catalog.py         # Cluster definitions and model registry
├── config.py         # Configuration management
└── workspace.py       # Target workspace safety and locking
```

---

## Installation

### Prerequisites

- Python 3.11 or higher
- NVIDIA API Key (for model execution)

### Quick Install

```powershell
# Clone the repository
git clone https://github.com/DanielDeshmukh/autobots.git
cd autobots

# Install in development mode
python -m pip install -e . --no-build-isolation

# Verify installation
autobots --help
```

### pip install (when published)

```powershell
pip install autobot-swarm
```

---

## Configuration

### API Key Setup

Create a `.env` file in the project root:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
```

Or set the environment variable:

```powershell
$env:NVIDIA_API_KEY = "your_key_here"
```

### Configuration File

Create a `.autobots.toml` or `autobots.toml` in your project or home directory:

```toml
[autobots]
# Model selection: balanced, speed, or quality
model_selection_profile = "balanced"

# Enable parallel workstream planning
parallel_planning = false

# Use bundled models only (no live catalog)
disable_live_catalog = false

# Safety branch name
safety_branch = "autobots-safety"

# Default execution mode: supervised, milestone, or autonomous
default_mode = "supervised"

# Phases before approval in milestone mode
milestone_threshold = 3

# Max verification attempts per phase
max_verification_attempts = 3

# Optional: custom model registry
# model_registry_path = "./my-registry.json"

# Optional: extra custom clusters
# [autobots.extra_clusters]
# MyCluster = ["nvidia/custom-model-1"]
```

---

## CLI Commands

All commands automatically detect the target project from the current working directory.

### Check Project Context

```powershell
autobots init
```

Checks for the required context filenames and detects the project profile. Autobots does not create these files for target projects.

### Generate/Refresh Plan

```powershell
autobots plan [options]
```

Generates roadmap and progress tracker from project context.

| Flag | Description |
|------|-------------|
| `--goal "text"` | Set the planning goal |
| `--append` | Append new phases instead of replacing |
| `--insert-after "phase"` | Insert after specific phase |
| `--dry-run` | Preview without writing files |

### Execute Phases

```powershell
autobots run [options]
```

Execute phases with specified autonomy mode.

| Flag | Description |
|------|-------------|
| `--supervised` | Manual approval per phase (default) |
| `--milestone` | Approval every N phases |
| `--autonomous` | Fully autonomous execution |
| `--dry-run` | Preview without executing |

### Resume Execution

```powershell
autobots resume
```

Resume from the last checkpoint after interruption.

### Show Status

```powershell
autobots status
```

Display current execution status, session details, and checkpoint information.

### Interactive Mode

```powershell
autobots engage
```

Launch the interactive approval-gated workflow with full cluster orchestration.

### Validate Models

```powershell
autobots validate-models
```

Test model contracts and JSON responses against the live NVIDIA API.

---

## NVIDIA Models Registry

Autobots includes a comprehensive model registry with 9 clusters:

### Cluster Overview

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

### Model List by Cluster

#### Optimus (Command & Planning)
- nvidia/nemotron-3-super-120b-a12b
- nvidia/llama-3.3-nemotron-super-49b-v1.5
- nvidia/mistral-large-3-675b-instruct-2512
- nvidia/kimi-k2-thinking
- nvidia/step-3.5-flash
- nvidia/gpt-oss-120b
- nvidia/glm-5.1
- nvidia/llama-4-maverick-17b-128e-instruct
- nvidia/stockmark-2-100b-instruct

#### UltraMagnus (Backend & Architecture)
- nvidia/kimi-k2.6
- nvidia/deepseek-v4-pro
- nvidia/qwen3.5-397b-a17b
- nvidia/mistral-medium-3.5-128b
- nvidia/gemma-4-31b-it
- nvidia/qwen3-next-80b-a3b-thinking
- nvidia/dracarys-llama-3.1-70b-instruct
- nvidia/mixtral-8x22b-instruct-v0.1
- nvidia/evo2-40b
- nvidia/boltz-2
- nvidia/alphafold2-multimer
- nvidia/msa-search

#### RedAlert (Security & Safety)
- nvidia/llama-3.1-nemotron-70b-instruct
- nvidia/nemotron-4-340b-instruct
- deepseek-ai/deepseek-v4-pro
- nvidia/llama-3.1-nemotron-51b-instruct
- meta/llama-3.1-405b-instruct
- deepseek-ai/deepseek-v4-flash
- nvidia/llama-3.3-nemotron-super-49b-v1.5
- nvidia/mistral-large-3-675b-instruct-2512
- nvidia/qwen3.5-397b-a17b
- nvidia/mistral-medium-3.5-128b

#### Jazz (Frontend & Creative)
- nvidia/qwen-image-edit
- nvidia/qwen-image
- nvidia/flux.2-klein-4b
- nvidia/flux.1-dev
- nvidia/flux.1-schnell
- nvidia/stable-diffusion-3.5-large
- nvidia/FLUX.1-Kontext-dev
- nvidia/phi-4-multimodal-instruct
- nvidia/NVIDIA AI for Media Relighting
- nvidia/TRELLIS
- nvidia/vista-3d

#### Ratchet (Debug & Repair)
- nvidia/deepseek-v4-flash
- nvidia/qwen3.5-coder-480b-a35b-instruct
- nvidia/qwen2.5-coder-32b-instruct
- nvidia/mistral-small-4-119b-2603
- nvidia/devstral-2-123b-instruct-2512
- nvidia/magistral-small-2506
- nvidia/phi-4-mini-instruct
- nvidia/llama-3.2-3b-instruct
- nvidia/llama-3.2-1b-instruct
- nvidia/nemotron-mini-4b-instruct

#### Perceptor (Retrieval & Parsing)
- nvidia/nemotron-ocr-v1
- nvidia/nemotron-parse
- nvidia/paddleocr
- nvidia/nemotron-table-structure-v1
- nvidia/nemotron-page-elements-v3
- nvidia/nemotron-graphic-elements-v1
- nvidia/llama-3.2-nemoretriever-300m-embed-v2
- nvidia/llama-3.2-nv-embedqa-1b-v2
- nvidia/llama-3.2-nv-rerankqa-1b-v2
- nvidia/nv-embedcode-7b-v1
- nvidia/bge-m3

#### Bumblebee (Communication & Media)
- nvidia/whisper-large-v3
- nvidia/canary-1b-asr
- nvidia/riva-translate-4b-instruct-v1_1
- nvidia/magpie-tts-zeroshot
- nvidia/nemotron-voicechat
- nvidia/LipSync
- nvidia/Background Noise Removal
- nvidia/Active Speaker Detection
- nvidia/parakeet-1.1b-rnnt-multilingual-asr

#### Ironhide (Simulation & Optimization)
- nvidia/cosmos-reason2-8b
- nvidia/cosmos-transfer2.5-2b
- nvidia/cosmos-predict1-5b
- nvidia/streampetr
- nvidia/sparsedrive
- nvidia/bevformer
- nvidia/fourcastnet
- nvidia/cuopt

#### Wheeljack (Scientific Specialist)
- nvidia/ising-calibration-1-35b-a3b
- nvidia/genmol
- nvidia/molmim
- nvidia/rfdiffusion
- nvidia/proteinmpnn
- nvidia/esm2-650m
- nvidia/openfold3

---

## Execution Modes

### Supervised Mode (Default)

```powershell
autobots run --supervised
```

- Requires approval before each phase
- Full human control over execution
- Best for critical or unfamiliar tasks

### Milestone Mode

```powershell
autobots run --milestone
```

- Requires approval after N phases (default: 3)
- Balance between autonomy and control
- Good for well-understood workflows

### Autonomous Mode

```body
autobots run --autonomous
```

- No approval gates
- Fastest execution
- Best for trusted, well-tested workflows

---

## Context Architecture

Autobots expects six target-owned context files under `context/`:

| File | Purpose |
|------|---------|
| `architecture.md` | Project architecture and structure |
| `roadmap.md` | Phase definitions with goals and validation |
| `progress-tracker.md` | Phase status tracking (PENDING/IN_PROGRESS/COMPLETE) |
| `ui-components.md` | UI component inventory |
| `project-briefing.md` | Project overview and metadata |
| `security-auth.md` | Security and authentication notes |

---

## Cross-Platform Usage

All commands automatically use the current working directory as the target project.

### Windows

```powershell
# Install
python -m pip install -e .

# Set API key
$env:NVIDIA_API_KEY = "your_key"

# Run commands (from your project directory)
cd C:\path\to\your\project
autobots init
autobots plan
autobots run
```

### macOS / Linux

```bash
# Install
python3 -m pip install -e .

# Set API key
export NVIDIA_API_KEY="your_key"

# Run commands (from your project directory)
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
| `AUTOBOTS_MODEL_REGISTRY` | Custom model registry path | None |

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

**Solution**: Create the listed files in the target project's `context/` folder, then run `autobots plan` if you need to refresh roadmap/progress content.

### Safety Branch Check Fails

```
Execution blocked. Switch to autobots-safety branch.
```

**Solution**: Create and checkout the safety branch:
```powershell
git checkout -b autobots-safety
```

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
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_phase_9_config.py -v

# Run with coverage
python -m pytest tests/ --cov=autobots --cov-report=html
```

### Project Structure

```
autobots/
├── autobots/           # Main package
│   ├── cli.py         # CLI entry point
│   ├── config.py      # Configuration
│   ├── catalog.py     # Model registry
│   ├── bootstrap.py    # Project profiling
│   ├── planning.py     # Roadmap generation
│   ├── router/         # Routing orchestration
│   ├── executor/       # Execution engine
│   └── workspace.py    # Workspace management
├── tests/             # Test suite
├── context/           # Project context (for this repo)
├── setup.cfg          # Package configuration
└── README.md          # This file
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.4 | 2026-06-08 | Removed Autobots-created starter context files; missing context now reports filenames only |
| 0.1.1 | 2026-05-15 | Phase 9-10 complete: config, error handling, failure tests |
| 0.1.0 | 2026-05-14 | Phase 1-8.5 complete: core functionality |

---

## Acknowledgments

- Built with [NVIDIA NIM](https://developer.nvidia.com/nim) for model access
- Powered by [Rich](https://github.com/Textualize/rich) for terminal UI
- Uses [OpenAI](https://openai.com) compatible API interface
