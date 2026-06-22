<div align="center">
  <a href="https://pypi.org/project/autobot-swarm/">
    <img src="assets/autobots-banner.png" alt="Autobots Banner" width="100%" />
  </a>
</div>
<br>

<p align="center">
  <a href="https://github.com/DanielDeshmukh/autobots">
    <img src="https://img.shields.io/badge/version-0.2.0-blue" alt="Version">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/python-3.11+-brightgreen" alt="Python">
  </a>
  <a href="https://pypi.org/project/autobot-swarm/">
    <img src="https://img.shields.io/pypi/v/autobot-swarm" alt="PyPI">
  </a>
  <a href="https://github.com/DanielDeshmukh/autobots/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  </a>
</p>

Autobots is a hierarchical multi-cluster coding swarm CLI that orchestrates multiple AI models to plan, implement, validate, and repair code against target repositories. It features a full tool system (Read, Write, Edit, Glob, Grep), interactive REPL mode, granular permissions, context management, hooks, MCP integration, and code review — all built on NVIDIA NIM models.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Tool System](#tool-system)
- [REPL Mode](#repl-mode)
- [Permissions](#permissions)
- [Context Management](#context-management)
- [Hooks & MCP](#hooks--mcp)
- [Code Review & Diagnostics](#code-review--diagnostics)
- [NVIDIA Models & Clusters](#nvidia-models--clusters)
- [NVIDIA Skills](#nvidia-skills)
- [Execution Modes](#execution-modes)
- [Context Architecture](#context-architecture)
- [Cross-Platform Usage](#cross-platform-usage)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

---

## Features

### Core Swarm

- **Hierarchical Model Routing** — 9 specialized clusters (Optimus, UltraMagnus, Jazz, RedAlert, Ratchet, Perceptor, Bumblebee, Ironhide, Wheeljack)
- **Phase-Based Execution** — Inspect → Implement → Validate → Repair pipeline
- **Context Injection** — Reads `context/` files and injects project documentation into model prompts
- **Model Routing** — Intelligent cluster selection based on task keywords and file extensions
- **Automatic Repair** — Self-healing execution with validation-driven repair loops
- **Rollback Support** — Snapshots before writes, `autobots undo` reverts changes
- **Response Streaming** — Live character counter during model calls
- **Rich Status Output** — Progress bars, estimated time, branch info via Rich

### File Operations & Search

- **ReadTool** — Read files with offset/limit, line numbers, binary/image support
- **WriteTool** — Atomic writes (tmp + rename), directory creation, path sandboxing
- **EditTool** — Targeted string replacement with exact match, replaceAll mode
- **GlobTool** — Pattern-based file search (`**/*.py`, `src/**/*.ts`)
- **GrepTool** — Regex content search across files, include filters
- **ToolRegistry** — Register, dispatch, and manage tools

### REPL & Interactive Mode

- **Interactive REPL** — Conversational session with history and streaming
- **One-Shot Mode** — `autobots ask "question"` for quick queries
- **Piped Input** — `cat file.py | autobots ask "explain this"`
- **Slash Commands** — `/help`, `/clear`, `/cost`, `/compact`, `/model`, `/exit`
- **Session Persistence** — Save and restore conversations from JSON

### Permissions & Safety

- **Tool-Level Permissions** — Allow/deny/ask per tool call
- **Interactive Approval** — y/n/a/Esc prompt for tool execution
- **Session Whitelisting** — "Always allow" for trusted tools
- **Config Merge** — Global (`~/.autobots/settings.json`) + project + env vars
- **Audit Logging** — JSON-lines log of all permission decisions
- **Command Policy** — Whitelist-based command validation, blocks dangerous patterns

### Context Management

- **Token Estimation** — `len(text) // 4` with tiktoken fallback
- **Auto-Compaction** — Summarizes conversation when approaching context limit
- **CLAUDE.md Hierarchy** — Global → project → subdirectory instruction loading
- **Budget Tracking** — Remaining context display, usage ratios

### Hooks & Extensions

- **Pre/Post Tool Hooks** — Run scripts or callbacks before/after tool execution
- **Abort on Failure** — Hook failure stops the tool chain
- **MCP Integration** — Connect to Model Context Protocol servers for custom tools
- **Command Hooks** — Shell commands with env injection and 30s timeout

### Code Review & Diagnostics

- **Git Diff Review** — Analyze changes for large PRs, many files, patterns
- **Doctor Command** — Health checks: API key, connectivity, Python version, package
- **PR Review** — Review pull requests by number or diff

### Workflow

- **Session Management** — Durable checkpoints, resumable runs, audit trails
- **Configurable Modes** — Supervised, milestone, or fully autonomous execution
- **Multi-Root File Writing** — Write to `src/`, `app/`, `lib/`, `tests/`, `docs/`, `scripts/`
- **Validation Commands** — Run tests, linters, and build commands automatically
- **Shell Completions** — bash, zsh, and fish tab completion
- **Plugin System** — before/after hooks for custom extensions
- **Skill Marketplace** — Built-in packs for FastAPI, Django, React, Next.js
- **Web Dashboard** — Real-time status on port 8080

---

## Architecture

```
autobots/
├── cli.py                  # CLI entry point (22+ commands)
├── bootstrap.py            # Project profiling and context contract
├── config.py               # TOML + env config with validation
├── catalog.py              # Cluster definitions and model registry
├── workspace.py            # Target workspace safety and locking
├── errors.py               # Structured error classes
├── costs.py                # Token/cost estimation
├── git_utils.py            # Git auto-commit integration
├── preflight.py            # Doctor health checks
├── onboarding.py           # Interactive setup wizard
├── completions.py          # Shell tab completion
├── context_budget.py       # Context window management
├── plugins.py              # Plugin/hook system
├── marketplace.py          # Skill pack marketplace
├── dashboard.py            # Web dashboard
├── diff.py                 # Snapshot comparison
├── tools/                  # File operation tools
│   ├── base.py             # Tool ABC and ToolResult
│   ├── read.py             # ReadTool (offset/limit, binary)
│   ├── write.py            # WriteTool (atomic, sandboxed)
│   ├── edit.py             # EditTool (exact match, replaceAll)
│   ├── glob.py             # GlobTool (pattern search)
│   ├── grep.py             # GrepTool (regex search)
│   ├── registry.py         # ToolRegistry (dispatch)
│   ├── permissions.py      # PermissionRule, PermissionChecker
│   └── formatting.py       # Tool result formatting
├── repl/                   # Interactive REPL
│   ├── session.py          # ReplSession, Message, SessionStats
│   ├── commands.py         # SlashCommand registry
│   └── runner.py           # run_repl, run_one_shot, run_piped
├── permissions/            # Permission system
│   ├── settings.py         # PermissionSettings (global/project/env)
│   ├── logging.py          # PermissionLogger (audit trail)
│   └── interactive.py      # Interactive approval prompt
├── context/                # Context management
│   ├── manager.py          # ContextManager (token tracking)
│   ├── tokenizer.py        # estimate_tokens, count_tokens
│   └── claude_md.py        # CLAUDE.md hierarchy loader
├── hooks/                  # Hook system
│   └── manager.py          # HookManager, HookPoint, HookResult
├── mcp/                    # MCP integration
│   └── client.py           # MCPClient, MCPTool
├── review/                 # Code review
│   ├── git_review.py       # Diff parsing, review
│   └── diagnostics.py      # Doctor checks
├── router/                 # Swarm orchestration
│   ├── core.py             # Main routing orchestration
│   ├── models.py           # Data models
│   ├── planning.py         # Cluster assignment
│   ├── stages.py           # Stage execution
│   └── phases.py           # Phase reading
├── executor/               # Execution engine
│   ├── autonomy.py         # Autonomous loop
│   ├── modes.py            # Execution modes
│   ├── state.py            # Session state and rollback
│   ├── commands.py         # Command validation
│   ├── gate.py             # Test-then-commit gate
│   └── validation.py       # Validation handling
├── planning/               # Plan generation
│   ├── core.py             # Plan entry point
│   ├── scanner.py          # Repository scanning
│   └── synthesis.py        # Phase synthesis
├── skills/                 # Skill injection
│   ├── loader.py           # Skill pack loading
│   ├── cluster_prompts.py  # Cluster-specific prompts
│   └── nvidia/             # 17 NVIDIA skill files
└── utils/
    └── retry.py            # Exponential backoff
```

---

## Installation

### Prerequisites

- Python 3.11 or higher
- NVIDIA API Key (for model execution)

### PyPI Install

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

## Quick Start

```powershell
# 1. Set your API key
$env:NVIDIA_API_KEY = "your_key_here"

# 2. Navigate to your project
cd C:\path\to\your\project

# 3. Initialize (creates context/ directory)
autobots init

# 4. Generate a plan
autobots plan --goal "Add user authentication"

# 5. Run the swarm
autobots run --supervised
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

### Permission Settings

Create `~/.autobots/settings.json` (global) or `.autobots/settings.json` (project):

```json
{
  "permissions": {
    "default": "ask",
    "rules": [
      {"tool_pattern": "Read", "permission": "allow"},
      {"tool_pattern": "Glob", "permission": "allow"},
      {"tool_pattern": "Grep", "permission": "allow"},
      {"tool_pattern": "Write", "permission": "ask"},
      {"tool_pattern": "Edit", "permission": "ask"},
      {"tool_pattern": "Bash", "permission": "ask"}
    ]
  }
}
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `autobots init` | Check context files in target project |
| `autobots init --interactive` | Interactive setup wizard |
| `autobots plan` | Generate implementation roadmap |
| `autobots plan --goal "text"` | Plan with specific goal |
| `autobots plan --append` | Append to existing plan |
| `autobots plan --dry-run` | Preview without writing |
| `autobots run [task]` | Execute phases with autonomy mode |
| `autobots run --supervised` | Manual approval per phase (default) |
| `autobots run --milestone` | Approval every N phases |
| `autobots run --autonomous` | Fully autonomous execution |
| `autobots resume` | Resume from last checkpoint |
| `autobots engage` | Interactive mode with startup screen |
| `autobots ask "question"` | One-shot question answering |
| `autobots steer "instruction"` | Add mid-task steering instructions |
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

---

## Tool System

Autobots includes a full file operation tool system:

### ReadTool

```python
# Read with line numbers
ReadTool.run(file_path="/path/to/file.py")

# Read with offset and limit
ReadTool.run(file_path="/path/to/file.py", offset=10, limit=50)
```

### WriteTool

```python
# Atomic write (creates parent directories automatically)
WriteTool.run(file_path="/path/to/file.py", content="print('hello')")

# Sandboxed write (only allowed paths)
WriteTool(allowed_paths=["/project/src"]).run(file_path="...", content="...")
```

### EditTool

```python
# Exact string replacement
EditTool.run(file_path="main.py", old_string="old_code", new_string="new_code")

# Replace all occurrences
EditTool.run(file_path="main.py", old_string="foo", new_string="bar", replace_all=True)
```

### GlobTool

```python
# Find files by pattern
GlobTool.run(pattern="**/*.py", path="/project")

# Find TypeScript files
GlobTool.run(pattern="src/**/*.tsx", path="/project")
```

### GrepTool

```python
# Regex search
GrepTool.run(pattern=r"def \w+", path="/project/src")

# Search specific file types
GrepTool.run(pattern="TODO", path="/project", include="*.py")
```

---

## REPL Mode

### Interactive Session

```powershell
autobots
# Autobots REPL (model: meta/llama-3.1-8b-instruct)
# Type /help for commands, /exit to quit.
#
# You> What is this project about?
# Assistant: This project is...
```

### One-Shot Mode

```powershell
autobots ask "What does the main.py file do?"
```

### Piped Input

```powershell
cat main.py | autobots ask "Explain this code"
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/cost` | Show token usage and estimated cost |
| `/compact` | Summarize conversation to save tokens |
| `/model <name>` | Switch model mid-session |
| `/exit` | Exit the REPL |

---

## Permissions

### Permission Levels

- **allow** — Auto-approved, no prompt
- **ask** — Interactive approval required
- **deny** — Blocked, cannot execute

### Interactive Approval

When a tool requires approval:

```
Allow Write?
  file_path: /project/src/main.py
  content: print('hello')
  [y]es / [n]o / [a]lways / [Esc] cancel
```

- `y` — Approve this once
- `n` — Deny this call
- `a` — Always allow this tool for the session
- `Esc` — Cancel

### Configuration

**Global** (`~/.autobots/settings.json`):
```json
{
  "permissions": {
    "default": "ask",
    "rules": [
      {"tool_pattern": "Read", "permission": "allow"},
      {"tool_pattern": "Write", "permission": "ask"}
    ]
  }
}
```

**Project** (`.autobots/settings.json`):
```json
{
  "permissions": {
    "rules": [
      {"tool_pattern": "Bash(npm test)", "permission": "allow"},
      {"tool_pattern": "Bash(rm *)", "permission": "deny"}
    ]
  }
}
```

**Environment Variables**:
```powershell
$env:AUTOBOTS_ALLOWED_TOOLS = "Read,Glob,Grep"
$env:AUTOBOTS_DENIED_TOOLS = "Bash(rm *)"
```

---

## Context Management

### Token Tracking

- Tracks token usage per message
- Estimates remaining context budget
- Auto-compacts at 80% threshold

### CLAUDE.md Hierarchy

Instructions loaded from multiple locations:
```
~/.autobots/CLAUDE.md           (global)
./CLAUDE.md                     (project root)
./src/CLAUDE.md                 (subdirectory)
```

### Compaction

```
You> /compact
Compacted 24 messages into summary.
```

---

## Hooks & MCP

### Pre/Post Tool Hooks

Register callbacks that run before or after tool execution:

```python
from autobots.hooks import HookManager, Hook, HookPoint

mgr = HookManager()
mgr.register(Hook(
    name="lint",
    point=HookPoint.POST_TOOL,
    command="ruff check {file_path}"
))
```

### MCP Integration

Connect to Model Context Protocol servers:

```python
from autobots.mcp import MCPClient

client = MCPClient(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"])
client.connect()
tools = client.list_tools()
result = client.call_tool("read_file", {"path": "/etc/hosts"})
```

---

## Code Review & Diagnostics

### Git Diff Review

```powershell
# Review current changes
autobots review

# Review PR by number
autobots pr-review 42
```

### Doctor Command

```powershell
autobots doctor
# Autobots Doctor Results:
#   [PASS] Python Version: Python 3.13 (OK)
#   [PASS] API Key: NVIDIA_API_KEY set (ends with ...abc1)
#   [PASS] Connectivity: NVIDIA API reachable
#   [PASS] Package: autobot-swarm installed
#   4/4 checks passed
```

---

## NVIDIA Models & Clusters

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

### Tier 1 (Always Loaded)

| Skill | Cluster(s) | Description |
|-------|------------|-------------|
| `agent-skills.md` | Optimus, UltraMagnus | NemoClaw agent architecture |
| `autonomous-agent-research.md` | Optimus, Wheeljack | Autonomous research workflow |
| `session-memory.md` | Optimus, Jazz | Durable session memory |
| `skill-evolution.md` | ALL | Self-improvement protocol |
| `safety-policy.md` | Ironhide | Safety taxonomy |
| `rag-blueprint.md` | UltraMagnus, Optimus | RAG architecture |
| `rag-eval.md` | Jazz | RAG evaluation metrics |
| `dynamo-deployment.md` | UltraMagnus, Wheeljack | Dynamo K8s recipes |
| `dynamo-router.md` | UltraMagnus, Optimus | Dynamo router modes |
| `retrieval.md` | UltraMagnus, Bumblebee | Document retrieval pipeline |

### Tier 2 (Conditional)

| Skill | Loaded When | Description |
|-------|-------------|-------------|
| `nemotron-customize.md` | fine-tuning, training | Nemotron customization |
| `cuopt-routing.md` | routing, scheduling | cuOpt vehicle routing |
| `cuopt-optimization.md` | optimization, LP/MILP/QP | cuOpt numerical optimization |
| `cudf.md` | pandas, dataframe | cuDF GPU DataFrames |
| `neautomodel-recipe.md` | training at scale | Distributed training |
| `kubernetes-infra.md` | Kubernetes, K8s | Physical AI infra |
| `holoscan.md` | video, edge AI | Holoscan video analytics |
| `cudaq.md` | quantum computing | CUDA-Q quantum simulation |

---

## Execution Modes

### Supervised (Default)

```powershell
autobots run --supervised
```

Requires approval before each phase. Full human control.

### Milestone

```powershell
autobots run --milestone
```

Requires approval after N phases (configurable via `milestone_threshold`).

### Autonomous

```powershell
autobots run --autonomous
```

No approval gates. Fastest execution.

---

## Context Architecture

Autobots expects six context files under `context/`:

| File | Purpose |
|------|---------|
| `architecture.md` | Project architecture and structure |
| `roadmap.md` | Phase definitions with goals and validation |
| `progress-tracker.md` | Phase status tracking |
| `project-briefing.md` | Project overview and goals |
| `security-auth.md` | Security and authentication notes |
| `ui-components.md` | UI component documentation |

---

## Cross-Platform Usage

### Windows

```powershell
pip install autobot-swarm
$env:NVIDIA_API_KEY = "your_key"
cd C:\path\to\your\project
autobots init
autobots plan --goal "Add feature X"
autobots run --supervised
```

### macOS / Linux

```bash
pip install autobot-swarm
export NVIDIA_API_KEY="your_key"
cd /path/to/your/project
autobots init
autobots plan --goal "Add feature X"
autobots run --supervised
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
| `AUTOBOTS_ALLOWED_TOOLS` | Comma-separated allowed tools | (none) |
| `AUTOBOTS_DENIED_TOOLS` | Comma-separated denied tools | (none) |

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `NVIDIA_API_KEY is missing` | Set `NVIDIA_API_KEY` in `.env` or environment variable |
| `Missing: roadmap.md` | Run `autobots plan` to generate context files |
| `Switch to autobots-safety branch` | `git checkout -b autobots-safety` |
| `Command not in safety whitelist` | Autobots blocks dangerous commands. Use safe alternatives |
| `No checkpoint found` | Start fresh with `autobots run` |
| `old_string not found` | Provide exact surrounding lines for unique match |
| `old_string found N times` | Add more context or use `replace_all=true` |

---

## Development

### Running Tests

```powershell
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_tools.py -v

# With coverage
python -m pytest tests/ --cov=autobots --cov-report=html
```

### Test Suite

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_tools.py` | 46 | File operations (Read, Write, Edit, Glob, Grep, Registry, Permissions, Formatting) |
| `test_tools_integration.py` | 5 | Integration: read → edit → verify → read |
| `test_repl.py` | 20 | REPL session, commands, runner |
| `test_permissions.py` | 12 | Permission settings, logging, merge |
| `test_context.py` | 18 | Token estimation, compaction, CLAUDE.md |
| `test_hooks_mcp.py` | 13 | Hooks, MCP client |
| `test_review.py` | 12 | Git review, diagnostics |
| `test_final_decision.py` | 10 | Release readiness |
| **Total** | **136** | |

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Built with [NVIDIA NIM](https://developer.nvidia.com/nim) for model access
- Powered by [Rich](https://github.com/Textualize/rich) for terminal UI
- Uses [OpenAI](https://openai.com) compatible API interface
