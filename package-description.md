# Autobots

**Hierarchical multi-cluster coding swarm CLI powered by NVIDIA NIM**

Autobots is a Python CLI tool that orchestrates multiple AI models as a coding swarm to autonomously plan, implement, review, and repair code in your target repositories. It routes tasks to specialized clusters, injects project context into model prompts, and runs validation loops with automatic repair.

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

1. **Plans** - Parses a roadmap into phases and tasks with dependencies
2. **Routes** - Intelligently assigns tasks to the best-fit AI cluster
3. **Implements** - Specialist models generate code with your project context
4. **Reviews** - A reviewer cluster validates correctness and safety
5. **Repairs** - A repair cluster fixes issues found during review
6. **Validates** - Runs your tests, linters, and build commands

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

- **Supervised** - Approval required before each phase
- **Milestone** - Approval every N phases (configurable)
- **Autonomous** - No approval, runs to completion

### Configurable Models

```toml
# .autobots.toml
[autobots]
model_selection_profile = "balanced"  # fast, balanced, quality
temperature = 0.2
max_tokens = 4096
```

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
| `autobots plan` | Generate implementation roadmap |
| `autobots run <task>` | Execute a specific task |
| `autobots resume` | Resume from last checkpoint |
| `autobots status` | Show current progress |
| `autobots engage` | Interactive mode with startup screen |
| `autobots validate-models` | Verify NVIDIA API connectivity |
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
                                                      [Files Written]
```

---

## Safety Features

- Command whitelist blocks dangerous operations (`rm -rf`, `sudo`, etc.)
- File locking prevents concurrent writes to critical context files
- Atomic writes ensure no partial file corruption
- Path traversal protection keeps writes within allowed directories
- Audit trail logs all actions for debugging

---

## Development Status

- **Version:** 0.1.6
- **Status:** Alpha
- **License:** MIT

---

## Links

- **PyPI:** https://pypi.org/project/autobot-swarm/
- **GitHub:** https://github.com/DanielDeshmukh/autobots
- **Issues:** https://github.com/DanielDeshmukh/autobots/issues
- **NVIDIA NIM:** https://build.nvidia.com

---

## License

MIT License - see LICENSE file for details.
