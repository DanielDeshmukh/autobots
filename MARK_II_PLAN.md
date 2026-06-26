# Mark II — Dual-Model Collaboration Pipeline

## Goal
Evolve Mark I's single-model-per-role to Mark II where 2 models collaborate per subtask:
Model A generates code → Model B reviews & iterates → final output.

## Architecture

### Mark I (current)
```
Planner → assigns 1 model per subtask → Worker generates → writes to disk
```

### Mark II (proposed)
```
Planner → assigns 2 models per subtask →
  Model A generates draft →
  Model B reviews + suggests fixes →
  Model A applies fixes (optional 2nd pass) →
  writes to disk
```

## Model Pairing Strategy

Different models have different strengths. Pairing them catches more errors:

| Role | Generator (A) | Reviewer (B) | Why |
|------|---------------|--------------|-----|
| UI Components | qwen3-next-80b | llama-3.3-70b | Qwen strong at CSS/design, Llama catches logic issues |
| Business Logic | llama-3.3-70b | qwen3-next-80b | Llama strong at TS types, Qwen catches edge cases |
| Tests | qwen3-next-80b | llama-3.3-70b | Qwen generates comprehensive tests, Llama validates correctness |
| Config/Boilerplate | qwen3-next-80b | llama-3.3-70b | Quick generation + validation |
| Repair | qwen3-next-80b | llama-3.3-70b | Fast fix + double-check |

## Implementation Plan

### Step 1: Update Model Catalog in `orchestrator.py`
- Add `MODELS_V2` dict with generator/reviewer pairs per role
- Each role has `{"generator": "model-id", "reviewer": "model-id"}`

### Step 2: Add `execute_worker_v2()` function
- Takes both generator and reviewer model IDs
- Step 1: Generator model creates files (same prompt as Mark I)
- Step 2: Reviewer model receives generator's output + shared context
- Step 3: Reviewer returns `{status: "pass", files: [...]}` or `{status: "revise", issues: [...], files: [...]}`
- Step 4: If revise, generator gets one more chance to fix
- Returns final files

### Step 3: Update planner prompt
- Planner now returns `model_pair: {generator: "...", reviewer: "..."}` per subtask
- Or we override planner's assignment with our fixed pairs

### Step 4: Update `orchestrate()` flow
- Use `execute_worker_v2` instead of `execute_worker`
- Keep concurrency at 2 (now 4 API calls per slot, but still within rate limits)

### Step 5: Rate limit adjustments
- Mark I: ~11 API calls for 10 workers + 1 planner = 12 calls
- Mark II: ~22 API calls for 10 workers (gen+review each) + 1 planner = 23 calls
- Still under 40/min limit with min_interval=1.5s
- May need to reduce concurrency to 1 if hitting limits

## Reviewer Prompt Template

```
You are reviewing code generated for a project. Review the following files
for: type errors, missing imports, incorrect prop signatures, broken references,
CSS issues, and logic bugs.

Context: {shared_context}

Files to review:
{generated_files}

Return JSON:
{
  "status": "pass" | "revise",
  "issues": ["issue 1", "issue 2"],
  "files": [{"path": "src/...", "content": "fixed content"}]
}

If files are good, return status "pass" with the original files.
If issues found, return status "revise" with fixed files.
```

## Files to Modify
- `autobots/orchestrator.py` — add MODELS_V2, execute_worker_v2, update orchestrate()

## Testing
- Run on same todo app task
- Compare: Mark I used 11 API calls, Mark II will use ~23
- Verify files generated are correct
- Log both generator and reviewer responses
