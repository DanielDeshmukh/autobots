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

**Model Selection (based on NVIDIA benchmarks):**
- Decomposer: `qwen3.5-122b-a10b` — best for agentic/tool-calling (72.2 BFCL-V4)
- UI/Jazz: `nemotron-super-49b` — confirmed 5/5 CSS score (gradient, blur, shadow, transition, animation)
- General: `llama-3.3-70b` — fallback

**Design System:**
- Generic best practices, not hardcoded themes
- Model decides colors/fonts based on project context
- Principles injected into prompts (glass-morphism, motion, contrast)

## Current Standing

**Working:**
- Task Decomposer + Sequencer (parallel/sequential planning)
- Model assignments optimized based on research
- Design principles injected (no hardcoded themes)
- JSON parsing handles multiple formats
- npm install succeeds (395 packages, ~2min)
- All 18 unit tests passing

**Not Working:**
- Full pipeline end-to-end (timeout at 10min)
- Playwright not installed (download too slow)
- `--fix` flag not tested with new models
- Merge logic (Ratchet rewrites files instead of adding tests)
- Parallel execution not implemented

## Next Steps

### Short Term
1. **Test full pipeline end-to-end** — run on a real project (counter app, todo app) and verify it works
2. **Install Playwright** — for screenshots to verify UI output
3. **Test `--fix` flag** — incremental updates with new models

### Medium Term
4. **Fix merge logic** — Ratchet should only add tests, not rewrite files
5. **Add parallel execution** — for independent subtasks
6. **Reduce latency** — optimize API calls, reduce npm install time

### Long Term
7. **Build a real project** — use the system to build something useful
8. **Iterate on design** — user feedback loop, continuous improvement

## Key Decisions

- **Generic principles > hardcoded themes** — model decides colors/fonts based on project context
- **Model selection based on benchmarks** — not guessing, actual research on NVIDIA models
- **qwen3.5-122b for orchestrator** — best for tool-calling/agentic pipelines
- **nemotron-super-49b for UI** — tested 5/5 on CSS features
- **Force dependency versions** — model generates incompatible npm package combos

## Blockers

- **NVIDIA API latency** — nemotron-super-49b ~80s per call
- **npm install time** — ~2min for 395 packages
- **Pipeline timeout** — 10min limit too short for full pipeline
- **Playwright download** — 37MB+ too slow to download

## User Feedback

> "we working isn't enough. The output I see needs to look good. That's the whole point of skills and ui engineering."

> "why are you so fucking bad at explaining? Why is every response defensive?"

> "we have any drawbacks of this hardcoding?"

The user wants honest, direct answers. Not defensive explanations. Not proactive changes. Ask before making changes.

## Git History

```
244014d feat: model-based design system + optimized model assignments
0f00ef7 Wire decomposer + sequencer into router execute_task()
e3668fe Add task sequencer — parallel vs sequential execution planning
2928085 Improve task decomposer with size classification and post-processing
a519d4b Add task decomposer — model-based task splitting with cluster assignments
```

All on main, pushed to GitHub.
