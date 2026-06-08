# autobot-swarm — Guide to A+++

> Current grade: **C+** (B+ scaffolding, D AI integration)  
> Target grade: **A+++** (production-ready autonomous coding swarm)  
> This guide covers three axes: fixing the core, injecting skills, and a stylish CLI entry.

---

## Part 1 — Answering the Two Core Questions

### Q1: Are NVIDIA's models already capable enough, or do we need to inject skills?

**Short answer: Both. NVIDIA models are capable, but skill injection is what separates a demo from a reliable tool.**

Here's the reality of what you're working with on NVIDIA NIM's free tier (as of June 2026):

- **40 requests/minute** hard cap, ~1,000 credits on signup
- **100+ open-weight models** — Llama 4 Maverick, Qwen3 Coder 480B, Mistral Large 3 675B, DeepSeek-R1, Phi-4, Gemma family — all OpenAI-compatible, all on the same `/v1/chat/completions` endpoint
- Qwen3 Coder 480B in particular is **purpose-built for code generation** and is available free through third-party hosting on NIM

For a task like "write a FastAPI login route," Qwen3 Coder 480B or Llama 4 Maverick will produce working code cold, no skill injection needed. But for tasks like "write a FastAPI login route that matches our existing auth pattern, uses our DB session factory, follows our error-response format, and has a test" — the model will hallucinate your conventions unless you give it context.

**That's what Autobots' `context/` directory is supposed to be.** The problem is your current system doesn't inject that context into prompts. It builds prompts in `router/stages.py` with hardcoded templates and ignores everything in `context/architecture.md`, `context/conventions.md`, `context/testing-strategy.md`, etc.

**So the answer is: inject your `context/` files as skills. The models will do the rest.**

---

### Q2: Can we use free skills (like prompt files, docs, context) as model skills inside Autobots?

**Yes. This is exactly what the `context/` directory was designed for — and it's the highest-leverage improvement you can make.**

The concept: each cluster (UltraMagnus, Jazz, etc.) gets a "skill pack" — a bundle of:
1. Your `context/architecture.md` — so it knows the codebase structure
2. Your `context/conventions.md` — so it writes code that matches your style
3. Your `context/testing-strategy.md` — so Jazz writes tests that actually fit
4. A cluster-specific system prompt — so UltraMagnus thinks like a senior backend engineer, Jazz thinks like a test engineer, etc.

This is essentially what Anthropic's own system does with Claude. You're just doing it with open-weight models on NIM.

---

## Part 2 — The A+++ Roadmap

### Phase 1: Fix the Foundation (D → C+)
*Estimated time: 2–3 hours. These are blocking bugs.*

**1.1 — Fix the re-execution guard**
```python
# executor/plan_runner.py:88
# BROKEN
if task["status"] == "task_registry.COMPLETED":

# FIXED
if task["status"] == "completed":
```

**1.2 — Fix silent file loss**
```python
# router/core.py:306 — raise instead of silently returning []
if not files_written:
    raise RuntimeError(
        f"Lock collision: generated files for task {task_id} were discarded. "
        "Retry with `autobots run --force`."
    )
```

**1.3 — Fix the version mismatch**
Your publish command already updates `__init__.py` and `pyproject.toml`. Add `setup.cfg` and `README.md` to the bump targets. One-liner fix in `autobots/cli.py`.

**1.4 — Fix model IDs with spaces**
Audit `catalog.py`. Any model ID with a space (e.g., `"nvidia/NVIDIA AI for Media Relighting"`) must be replaced with the actual API slug. Check `build.nvidia.com` for correct identifiers.

**1.5 — Wire `safety_branch` from config**
```python
# cli.py:49 and selectors.py:12 — replace hardcoded string
# BROKEN
safety_branch = "autobots-safety"

# FIXED
safety_branch = config.get("safety_branch", "autobots-safety")
```

---

### Phase 2: Skill Injection System (C+ → B+)
*The highest-leverage improvement. Estimated time: 1 day.*

This is the answer to "do we need skills or are the models enough?" — you need both.

**2.1 — Create `autobots/skills/loader.py`**

```python
"""
Loads context files from the target project's context/ directory
and bundles them into skill packs for each cluster.
"""
from pathlib import Path

CONTEXT_FILES = {
    "architecture": "context/architecture.md",
    "conventions": "context/conventions.md",
    "testing": "context/testing-strategy.md",
    "security": "context/security-auth.md",
}

def load_skill_pack(project_root: str, cluster_name: str) -> str:
    """
    Returns a formatted skill pack string to inject into the system prompt.
    Only loads files that exist — silently skips missing ones.
    """
    root = Path(project_root)
    sections = []

    for key, rel_path in CONTEXT_FILES.items():
        full_path = root / rel_path
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8-sig")
            sections.append(f"## Project {key.title()}\n\n{content}")

    skill_pack = "\n\n---\n\n".join(sections)
    cluster_preamble = CLUSTER_SYSTEM_PROMPTS.get(cluster_name, "")
    return f"{cluster_preamble}\n\n{skill_pack}" if skill_pack else cluster_preamble
```

**2.2 — Create `autobots/skills/cluster_prompts.py`**

Each cluster gets a purpose-specific system prompt that shapes how the model reasons:

```python
CLUSTER_SYSTEM_PROMPTS = {
    "UltraMagnus": """You are a senior software engineer specializing in backend architecture.
You write production-grade code that is correct, secure, and maintainable.
You follow the project conventions exactly as documented.
You never make assumptions about the codebase — you work strictly from the context provided.
When asked to implement a feature, you output complete, runnable code files.""",

    "Jazz": """You are a senior test engineer.
You write thorough, meaningful tests — not tests that pass trivially.
You follow the project's testing strategy exactly as documented.
You test edge cases, error paths, and the happy path.
You output pytest-compatible test files unless the project uses a different framework.""",

    "Ironhide": """You are a security-focused code reviewer.
You review code for: injection vulnerabilities, authentication flaws, insecure defaults,
sensitive data exposure, and logic errors that could be exploited.
You output structured reviews with severity levels: CRITICAL, HIGH, MEDIUM, LOW.""",

    "Wheeljack": """You are a refactoring specialist.
You improve code quality without changing behaviour.
You focus on: reducing duplication, improving naming, simplifying logic,
and making code easier to test and maintain.
You explain every change you make.""",

    "Optimus": """You are the orchestrator. You synthesize results from specialist clusters,
resolve conflicts, and produce the final consolidated output.
You prioritize correctness over cleverness.""",
}
```

**2.3 — Inject skill packs into `router/stages.py`**

```python
# In build_specialist_prompt() — add skill injection
from autobots.skills.loader import load_skill_pack

def build_specialist_prompt(task: dict, workspace_root: str, cluster_name: str) -> list:
    skill_pack = load_skill_pack(workspace_root, cluster_name)
    
    return [
        {
            "role": "system",
            "content": skill_pack  # <-- this is the key change
        },
        {
            "role": "user", 
            "content": build_task_prompt(task)
        }
    ]
```

**Why this works:** You're giving Qwen3 Coder or Llama 4 Maverick the exact same information a senior engineer would need on their first day: architecture docs, coding conventions, test strategy. The model's raw capability handles the rest.

---

### Phase 3: Live API Integration + End-to-End Tests (B+ → A)
*The gap between "scaffolding" and "it actually works". Estimated time: 1–2 days.*

**3.1 — End-to-end integration test setup**

Create `tests/integration/` (separate from unit tests, gated by env var):

```python
# tests/integration/conftest.py
import pytest
import os

def pytest_configure(config):
    """Skip all integration tests if no API key is present."""
    pass

def pytest_collection_modifyitems(items):
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    if not api_key:
        skip_marker = pytest.mark.skip(reason="NVIDIA_API_KEY not set — skipping integration tests")
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip_marker)
```

**3.2 — Model health check test**

```python
# tests/integration/test_api_connectivity.py
import pytest
from openai import OpenAI
import os

@pytest.fixture
def nim_client():
    return OpenAI(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url="https://integrate.api.nvidia.com/v1"
    )

def test_primary_model_responds(nim_client):
    """Verify the primary coding model is accessible and returns coherent output."""
    response = nim_client.chat.completions.create(
        model="qwen/qwen3-coder-480b-a35b-instruct",
        messages=[{"role": "user", "content": "Write a Python function that adds two numbers."}],
        max_tokens=200,
        temperature=0.1,
    )
    content = response.choices[0].message.content
    assert "def " in content, "Model did not return a function definition"
    assert len(content) > 50, "Model response is suspiciously short"

def test_model_follows_conventions(nim_client, tmp_path):
    """Verify that skill-injected prompts produce convention-compliant output."""
    conventions = "Always use type hints. Always add docstrings. Use snake_case."
    
    response = nim_client.chat.completions.create(
        model="qwen/qwen3-coder-480b-a35b-instruct",
        messages=[
            {"role": "system", "content": f"Follow these conventions:\n{conventions}"},
            {"role": "user", "content": "Write a function that validates an email address."}
        ],
        max_tokens=400,
        temperature=0.1,
    )
    content = response.choices[0].message.content
    assert "def " in content
    assert '"""' in content or "'''" in content, "Missing docstring"
    assert "-> " in content, "Missing type hint on return"
```

**3.3 — Full pipeline smoke test**

```python
# tests/integration/test_full_pipeline.py

def test_plan_then_execute_single_task(nim_client, tmp_workspace):
    """
    The 'it actually works' test.
    Creates a minimal project, runs a single task end-to-end,
    verifies a file was written with real code.
    """
    # Setup
    (tmp_workspace / "context" / "conventions.md").write_text("Use Python 3.11+. Type hints required.")
    roadmap = """# Roadmap\n## Phase 1: Hello World\n- [ ] P1-T1: Create a hello.py that prints Hello World"""
    (tmp_workspace / "context" / "roadmap.md").write_text(roadmap)
    
    # Execute
    result = run_task_against_cluster(
        task="Create a hello.py that prints Hello World",
        cluster="UltraMagnus",
        workspace=str(tmp_workspace),
        api_key=os.getenv("NVIDIA_API_KEY"),
    )
    
    # Assert
    assert result["status"] == "success"
    assert len(result["files"]) > 0
    
    written_file = tmp_workspace / "hello.py"
    assert written_file.exists(), "Model did not write hello.py"
    content = written_file.read_text()
    assert "print" in content, "hello.py has no print statement"
```

**3.4 — Run integration tests separately**

```bash
# Unit tests only (no API key needed)
pytest tests/ --ignore=tests/integration

# Full end-to-end (requires NVIDIA_API_KEY)
NVIDIA_API_KEY=nvapi-xxx pytest tests/integration/ -v
```

---

### Phase 4: Hardening (A → A+)
*Polish and production-readiness. Estimated time: 1–2 days.*

**4.1 — Replace `shell=True` with safe subprocess**

```python
# executor/commands.py — the security fix
import shlex

# UNSAFE (current)
subprocess.run(command, shell=True, ...)

# SAFE
subprocess.run(shlex.split(command), shell=False, ...)
```

**4.2 — Retry with exponential backoff**

```python
# autobots/utils/retry.py
import time
import functools
from typing import Callable, TypeVar

T = TypeVar("T")

def with_retry(max_attempts: int = 3, base_delay: float = 1.0):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
```

**4.3 — Wire `.autobots.toml` to `router/stages.py`**

```toml
# .autobots.toml — everything currently hardcoded
[autobots]
nvidia_endpoint = "https://integrate.api.nvidia.com/v1"
temperature = 0.2
max_tokens = 4096
safety_branch = "autobots-safety"

[autobots.model_profiles]
# "fast" = cheap models for simple tasks, "quality" = big models for hard tasks
fast = "meta/llama-3.1-8b-instruct"
balanced = "meta/llama-3.3-70b-instruct"
quality = "qwen/qwen3-coder-480b-a35b-instruct"
```

**4.4 — Structured logging (replace silent swallows)**

```python
import logging
logger = logging.getLogger("autobots")

# Instead of bare except: pass
except Exception as exc:
    logger.warning("Config load failed: %s — using defaults", exc)
```

---

### Phase 5: The Stylish CLI (A+ → A+++)
*See Part 3 below — the `autobots engage` startup screen.*

---

## Part 3 — Stylish `autobots engage` Startup (Like Claude Code)

### What Claude Code does that you should copy

Claude Code's startup is memorable because it:
1. Renders an ASCII wordmark — identity first
2. Shows system info inline (model, workspace, git branch)
3. Uses a minimal color palette — one accent, not a rainbow
4. Streams the entry animation — it doesn't just appear
5. Has a prompt that feels like a terminal, not a chatbot

### Implementation: `autobots/ui/engage.py`

```python
"""
autobots engage — startup screen and interactive loop.
Renders wordmark, system status, then drops into the task prompt.
"""
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.table import Table
import time
import subprocess
import os

console = Console()

WORDMARK = r"""
   ___   __  ______________  ____  __________
  / _ | / / / /_  __/ __ \ / __ )/ _____  __/
 / __ |/ /_/ / / / / / / // __  / /_   / /   
/_/ |_|\____/ /_/ /_/ /_//_____/\__/  /_/    
"""

ACCENT = "bold cyan"          # the one accent colour — keep it one
DIM    = "dim white"
WARN   = "bold yellow"
OK     = "bold green"


def get_git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip() or "detached"
    except Exception:
        return "no git"


def get_model_display(config: dict) -> str:
    profile = config.get("model_selection_profile", "balanced")
    profiles = {
        "fast": "llama-3.1-8b",
        "balanced": "llama-3.3-70b",
        "quality": "qwen3-coder-480b",
    }
    return profiles.get(profile, profile)


def render_status_row(config: dict) -> Table:
    table = Table.grid(padding=(0, 3))
    table.add_column(style=DIM)
    table.add_column(style="white")
    
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    key_status = f"[{OK}]set[/{OK}]" if api_key else f"[{WARN}]missing[/{WARN}]"
    
    table.add_row("model",     f"[{ACCENT}]{get_model_display(config)}[/{ACCENT}]")
    table.add_row("branch",    get_git_branch())
    table.add_row("api key",   key_status)
    table.add_row("workspace", config.get("workspace", os.getcwd()))
    
    return table


def animate_wordmark():
    """Stream the wordmark line by line with a small delay — same feel as Claude Code."""
    lines = WORDMARK.strip("\n").split("\n")
    for line in lines:
        console.print(line, style=ACCENT, highlight=False)
        time.sleep(0.04)


def render_engage_screen(config: dict):
    """Full startup sequence."""
    console.clear()
    
    # 1. Wordmark
    animate_wordmark()
    console.print()
    
    # 2. Tagline
    console.print(
        "  hierarchical coding swarm  ·  v" + config.get("version", "0.1.5"),
        style=DIM
    )
    console.print()
    
    # 3. Status row
    status = render_status_row(config)
    console.print(status)
    console.print()
    
    # 4. Divider
    console.rule(style="dim")
    console.print()


def engage_prompt() -> str:
    """The task input prompt — minimal, terminal-native feel."""
    console.print("[dim]What should the swarm build?[/dim]")
    console.print()
    return console.input(f"[{ACCENT}]autobots[/{ACCENT}] [dim]>[/dim] ").strip()
```

**Wire it into `cli.py`:**

```python
@app.command()
def engage(
    ctx: typer.Context,
    task: Optional[str] = typer.Argument(None),
):
    """Engage the swarm. Interactive mode if no task given."""
    from autobots.ui.engage import render_engage_screen, engage_prompt
    
    config = load_config()
    render_engage_screen(config)
    
    if not task:
        task = engage_prompt()
    
    if not task:
        console.print("[dim]No task given. Exiting.[/dim]")
        raise typer.Exit()
    
    # Hand off to the plan runner
    run_task_interactive(task, config)
```

### What the terminal looks like

```
   ___   __  ______________  ____  __________
  / _ | / / / /_  __/ __ \ / __ )/ _____  __/
 / __ |/ /_/ / / / / / / // __  / /_   / /   
/_/ |_|\____/ /_/ /_/ /_//_____/\__/  /_/    

  hierarchical coding swarm  ·  v0.1.5

  model       qwen3-coder-480b
  branch      main
  api key     set
  workspace   /Users/daniel/projects/my-app

──────────────────────────────────────────────

What should the swarm build?

autobots > _
```

Exactly like Claude Code — wordmark, status, clean prompt. No banners, no ASCII art robots, no color explosion. The cyan accent is the only decoration.

---

## Part 4 — Skill Files You Can Ship With Autobots

### The concept: bundled starter skills

Instead of expecting users to write `context/conventions.md` themselves, ship default skill templates inside the package:

```
autobots/
  skills/
    __init__.py
    loader.py
    cluster_prompts.py
    templates/
      conventions.md        ← sensible Python defaults
      architecture.md       ← blank template with prompts
      testing-strategy.md   ← pytest defaults
      security-auth.md      ← OWASP top 10 checklist
```

When `autobots init` runs, it copies these templates into the target project's `context/` directory. The user edits them to match their project. The clusters read them on every task.

**This is the free skill layer.** No API cost, no extra setup — just markdown files that give the models context they would otherwise have to guess.

```python
# autobots/bootstrap.py — add to init command
def copy_skill_templates(project_root: str):
    templates_dir = Path(__file__).parent / "skills" / "templates"
    context_dir = Path(project_root) / "context"
    context_dir.mkdir(exist_ok=True)
    
    for template in templates_dir.glob("*.md"):
        dest = context_dir / template.name
        if not dest.exists():  # never overwrite user's edited files
            shutil.copy(template, dest)
            console.print(f"  [dim]created[/dim] context/{template.name}")
```

---

## Summary Table

| Phase | Change | Grade Lift | Effort |
|---|---|---|---|
| 1 | Fix 4 critical bugs + stale versions | C+ → B- | 2–3 hrs |
| 2 | Skill injection from `context/` files | B- → B+ | 1 day |
| 3 | Live API integration + E2E tests | B+ → A | 1–2 days |
| 4 | Retry, safe subprocess, config wiring | A → A+ | 1–2 days |
| 5 | Stylish `autobots engage` CLI screen | A+ → A+++ | 3–4 hrs |

**Total: ~5–7 days of focused work to go from C+ to A+++.**

The biggest unlock is Phase 3 — once you have a single passing end-to-end test that proves a NVIDIA model actually wrote a file, the project stops being a framework demo and becomes a real tool. Everything else is polish on top of that proof.

---

## Quick Reference: NVIDIA Free Tier (June 2026)

| Thing | Limit |
|---|---|
| Sign-up | build.nvidia.com, free, no credit card |
| Rate limit | 40 requests/minute |
| Credits on signup | ~1,000 |
| Best free coding model | Qwen3 Coder 480B (third-party hosted) |
| Best free general model | Llama 4 Maverick / Mistral Large 3 |
| API compatibility | OpenAI-compatible (`/v1/chat/completions`) |
| Data privacy | Stateless, no training on prompts |
| Production use | Not recommended on free tier — 40 RPM too low |
| Self-hosted path | NIM containers, free for ≤16 GPUs |
