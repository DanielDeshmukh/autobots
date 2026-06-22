# Autobots

**Hierarchical multi-cluster coding swarm CLI powered by NVIDIA NIM models.**

Autobots orchestrates multiple AI models as a hierarchical swarm to plan, implement, validate, and repair code against your target repositories. It features a complete tool system (Read, Write, Edit, Glob, Grep), interactive REPL mode, granular permissions, context management, hooks, MCP integration, and code review.

## Installation

```bash
pip install autobot-swarm
```

## Quick Start

```bash
# Set your API key
export NVIDIA_API_KEY="your_key_here"

# Navigate to your project
cd /path/to/your/project

# Initialize, plan, and run
autobots init
autobots plan --goal "Add user authentication"
autobots run --supervised
```

## Features

### Core Swarm

- **9 Specialized Clusters** — Optimus (planning), UltraMagnus (backend), Jazz (frontend), RedAlert (security), Ratchet (repair), Perceptor (retrieval), Bumblebee (media), Ironhide (simulation), Wheeljack (science)
- **Phase-Based Execution** — Inspect, Implement, Validate, Repair pipeline
- **Context Injection** — Reads project documentation and injects into model prompts
- **Automatic Repair** — Self-healing with validation-driven repair loops
- **Rollback Support** — Snapshots before writes, undo reverts changes

### File Operations

- **Read** — Read files with offset/limit, line numbers, binary/image support
- **Write** — Atomic writes with directory creation and path sandboxing
- **Edit** — Targeted string replacement with exact match, replaceAll mode
- **Glob** — Pattern-based file search (`**/*.py`)
- **Grep** — Regex content search across files

### Interactive Mode

- **REPL** — Conversational session with history and streaming
- **One-Shot** — `autobots ask "question"` for quick queries
- **Piped Input** — `cat file.py | autobots ask "explain"`
- **Slash Commands** — `/help`, `/clear`, `/cost`, `/compact`, `/model`, `/exit`

### Permissions

- **Tool-Level Control** — Allow/deny/ask per tool call
- **Interactive Approval** — y/n/a/Esc prompt
- **Config Merge** — Global + project + environment settings
- **Audit Logging** — JSON-lines log of all decisions

### Context Management

- **Token Tracking** — Real-time token usage and budget display
- **Auto-Compaction** — Summarizes conversation at 80% threshold
- **CLAUDE.md Hierarchy** — Global, project, and subdirectory instructions

### Extensions

- **Hooks** — Pre/post tool execution callbacks
- **MCP** — Model Context Protocol server integration
- **Plugins** — Custom extensions via hook system

### Code Review

- **Git Diff Review** — Analyze changes for issues
- **Doctor Command** — Health checks for API, connectivity, Python, package

## CLI Commands

| Command | Description |
|---------|-------------|
| `autobots init` | Initialize context files |
| `autobots plan` | Generate implementation roadmap |
| `autobots run` | Execute with autonomy mode |
| `autobots resume` | Resume from checkpoint |
| `autobots ask` | One-shot question |
| `autobots steer` | Add steering instructions |
| `autobots status` | Rich status display |
| `autobots explain` | Show audit trail |
| `autobots stats` | Usage statistics |
| `autobots undo` | Rollback changes |
| `autobots doctor` | Health checks |
| `autobots catalog` | Browse model registry |

## Configuration

Create `.autobots.toml` in your project root:

```toml
[autobots]
model_selection_profile = "balanced"
default_mode = "supervised"
milestone_threshold = 3
temperature = 0.2
max_tokens = 4096
```

## Execution Modes

- **Supervised** — Manual approval per phase (default)
- **Milestone** — Approval every N phases
- **Autonomous** — No approval gates

## Requirements

- Python 3.11+
- NVIDIA API Key

## Links

- **GitHub**: https://github.com/DanielDeshmukh/autobots
- **Issues**: https://github.com/DanielDeshmukh/autobots/issues
- **PyPI**: https://pypi.org/project/autobot-swarm/

## License

MIT
