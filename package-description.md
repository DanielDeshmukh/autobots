# Autobots

**Hierarchical multi-cluster coding swarm CLI powered by NVIDIA NIM**

Autobots is a Python CLI tool that orchestrates multiple AI models as a coding swarm to autonomously plan, implement, review, repair, and validate code in your target repositories. It routes tasks to specialized clusters, injects project context into model prompts, and runs validation loops with automatic repair and rollback support.

---

## Quick Start

```bash
pip install autobot-swarm
```

```bash
# Check context files in your project
autobots init /path/to/your/project

# Generate an implementation roadmap
autobots plan /path/to/your/project

# Execute a task through the swarm
autobots run P1-T1

# Launch the interactive mode
autobots engage
```

---

## What Autobots Does

1. **Plans** — Parses a roadmap into phases and tasks with dependencies
2. **Routes** — Intelligently assigns tasks to the best-fit AI cluster
3. **Implements** — Specialist models generate code with your project context
4. **Reviews** — A reviewer cluster validates correctness and safety
5. **Repairs** — A repair cluster fixes issues found during review
6. **Validates** — Runs your tests, linters, and build commands
7. **Rolls Back** — Snapshots before writes, `autobots undo` reverts changes

---

## Key Features

### Skill Injection

Autobots reads your `context/` directory (architecture, conventions, testing strategy, security docs) and injects them into model prompts. Models see your project's actual documentation before writing code.

### Nine Specialized Clusters

| Cluster | Role | Use Case |
|---------|------|----------|
| Optimus | Planner | Mission briefs and orchestration |
| UltraMagnus | Backend | APIs, databases, server logic |
| Jazz | Frontend | UI components, React, CSS |
| RedAlert | Reviewer | Code review, security checks |
| Ratchet | Repair | Bug fixes, validation failures |
| Perceptor | Retrieval | Document parsing, RAG |
| Bumblebee | Media | Speech, audio, video |
| Ironhide | Simulation | Physics, optimization |
| Wheeljack | Science | Molecular, research |

### Execution Modes

- **Supervised** — Approval required before each phase
- **Milestone** — Approval every N phases (configurable)
- **Autonomous** — No approval, runs to completion

### Configurable Models

```toml
# .autobots.toml
[autobots]
model_selection_profile = "balanced"  # fast, balanced, quality
temperature = 0.2
max_tokens = 4096
```

### Additional Features

- **Rollback/Undo** — Snapshot system with `autobots undo` and `autobots snapshots`
- **Response Streaming** — Live character counter during model calls
- **Doctor Preflight** — Health checks for API, git, config, and dependencies
- **Structured Errors** — Contextual messages with actionable suggestions
- **Test Gate** — Run tests before commit
- **Git Integration** — Auto-commit after phase completion
- **Config Validation** — `autobots config validate` checks TOML settings
- **Shell Completions** — bash, zsh, and fish tab completion
- **Context Budget** — Warns and truncates when prompts approach model limits
- **Plugin System** — before/after hooks for custom extensions
- **Skill Marketplace** — Built-in packs for FastAPI, Django, React, Next.js
- **Web Dashboard** — Real-time status on port 8080
- **Rich Status Output** — Progress bars, estimated time, branch info
- **Explain Command** — `autobots explain P2-T3` shows audit trail details
- **Usage Stats** — `autobots stats` shows totals, averages, costs
- **Verbose Mode** — `--verbose` flag logs full prompts sent to models

---

## Requirements

- Python 3.11+
- NVIDIA NIM API key (free tier available at build.nvidia.com)

---

## Configuration

```toml
# .autobots.toml (place in project root or $HOME)
[autobots]
model_selection_profile = "balanced"
safety_branch = "autobots-safety"
default_mode = "supervised"
milestone_threshold = 3
max_verification_attempts = 3
temperature = 0.2
max_tokens = 4096
```

All settings can also be set via environment variables:

```bash
export AUTOBOTS_MODEL_SELECTION_PROFILE=quality
export AUTOBOTS_SAFETY_BRANCH=main
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `autobots init` | Check context files in target project |
| `autobots init --interactive` | Interactive setup wizard |
| `autobots plan` | Generate implementation roadmap |
| `autobots run <task>` | Execute a specific task |
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

---

## Context Architecture

Create these files in your project's `context/` directory:

```
context/
  architecture.md       # System design, tech stack, patterns
  conventions.md        # Code style, naming, formatting rules
  testing-strategy.md   # Test framework, coverage, patterns
  security-auth.md      # Auth patterns, OWASP checklist
  roadmap.md            # Implementation plan (autobots reads this)
  progress-tracker.md   # Current status (autobots updates this)
```

These files are injected into model prompts so generated code matches your project's patterns.

---

## How It Works

```
[Your Task] → [Optimus Planner] → [Specialist Cluster] → [RedAlert Reviewer]
                                          ↓                      ↓
                                    [Code Output]         [Pass / Revise]
                                                              ↓
                                                      [Ratchet Repair]
                                                              ↓
                                                      [Validation Loop]
                                                              ↓
                                                      [Snapshot + Write]
```

---

## Safety Features

- Command whitelist blocks dangerous operations (`rm -rf`, `sudo`, etc.)
- File locking prevents concurrent writes to critical context files
- Atomic writes ensure no partial file corruption
- Path traversal protection keeps writes within allowed directories
- Audit trail logs all actions for debugging
- Test gate runs tests before commit
- Pre-commit snapshots enable rollback

---

## Development Status

- **Version:** 0.1.8
- **Status:** Production-ready
- **Tests:** 465 passing
- **License:** MIT

---

## Links

- **PyPI:** https://pypi.org/project/autobot-swarm/
- **GitHub:** https://github.com/DanielDeshmukh/autobots
- **Issues:** https://github.com/DanielDeshmukh/autobots/issues
- **NVIDIA NIM:** https://build.nvidia.com

---

## License

MIT License — see LICENSE file for details.
