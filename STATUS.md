# Autobots: Current Status

## What We Built

A Python CLI that orchestrates a swarm of AI models to generate complete, runnable projects from a single prompt.

## Our Approach

**Phase 1-6 Pipeline:**
1. **Decompose** — break a task into parallel/sequential subtasks
2. **Sequence** — plan execution order based on dependencies
3. **Route** — assign each subtask to the best cluster (Jazz, Bumblebee, etc.)
4. **Execute** — run the subtask, generate code
5. **Review** — RedAlert validates the output
6. **Merge** — combine results into a complete project

**Model Selection (tested on NVIDIA NIM):**
- Generation: `qwen3.5-397b-a17b` — all design features (gradient, blur, shadow, transition, animation), proper JSON
- Decomposer: `qwen3.5-122b-a10b` — best for agentic/tool-calling (72.2 BFCL-V4)
- Fallback: `qwen3-next-80b-a3b-instruct` — fast, 256K context
- Broken: `nemotron-super-49b` — returns None on all prompts (API issue)

**Design System:**
- Generic best practices, not hardcoded themes
- Model decides colors/fonts based on project context
- Principles injected into prompts (glass-morphism, motion, contrast)

## Current Standing

**Working:**
- Task Decomposer + Sequencer (parallel/sequential planning)
- Full pipeline end-to-end — counter app generated, validated, running
- qwen3.5-397b generates working React apps with design features
- npm install succeeds (395 packages, ~2min)
- Design principles injected (no hardcoded themes)
- JSON parsing handles multiple formats
- Auto-updating NVIDIA model catalog (121 models, daily GitHub Action)
- All 18 unit tests passing

**Not Working:**
- Playwright not installed (download too slow)
- CSS not landing on components (model claims glass-morphism but outputs plain HTML)
- Merge logic (Ratchet rewrites files instead of adding tests)
- Parallel execution not implemented

## Next Steps

### Short Term
1. **Fix CSS delivery** — model generates CSS but it doesn't land on components
2. **Test `--fix` flag** — incremental updates with qwen3.5-397b
3. **Install Playwright** — for screenshots to verify UI output

### Medium Term
4. **Fix merge logic** — Ratchet should only add tests, not rewrite files
5. **Add parallel execution** — for independent subtasks
6. **Reduce latency** — optimize API calls, reduce npm install time

### Long Term
7. **Build a real project** — use the system to build something useful
8. **Iterate on design** — user feedback loop, continuous improvement

## Key Decisions

- **Generic principles > hardcoded themes** — model decides colors/fonts based on project context
- **qwen3.5-397b for generation** — all design features, proper JSON, 256K context
- **qwen3.5-122b for orchestrator** — best for tool-calling/agentic pipelines
- **Force dependency versions** — model generates incompatible npm package combos
- **Auto-update model catalog** — daily GitHub Action fetches from NVIDIA NIM API

## Blockers

- **CSS not landing** — model generates CSS but components don't use it
- **npm install time** — ~2min for 395 packages
- **Playwright download** — 37MB+ too slow to download
- **nemotron-super-49b broken** — returns None on all prompts (API issue)

## User Feedback

> "we working isn't enough. The output I see needs to look good. That's the whole point of skills and ui engineering."

> "why are you so fucking bad at explaining? Why is every response defensive?"

> "we have any drawbacks of this hardcoding?"

The user wants honest, direct answers. Not defensive explanations. Not proactive changes. Ask before making changes.

## Git History

```
e16f67f feat: auto-updating NVIDIA model catalog + switch to qwen3.5-397b for UI
244014d feat: model-based design system + optimized model assignments
0f00ef7 Wire decomposer + sequencer into router execute_task()
e3668fe Add task sequencer — parallel vs sequential execution planning
2928085 Improve task decomposer with size classification and post-processing
a519d4b Add task decomposer — model-based task splitting with cluster assignments
```

All on main, pushed to GitHub.
