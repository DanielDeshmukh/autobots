# Autonomous Agent Research Workflow

## Research Agent Lifecycle
```
Understand → Hypothesize → Wire → Launch → Evaluate → Iterate
```

## Phase Breakdown

### 1. Understand
- Parse the task description into atomic requirements
- Identify constraints, dependencies, and success criteria
- Map requirements to available tools and capabilities

### 2. Hypothesize
- Formulate testable hypotheses for each requirement
- Define measurable acceptance criteria
- Identify potential failure modes

### 3. Wire
- Connect components according to architecture
- Implement minimal viable solution first
- Write tests alongside implementation

### 4. Launch
- Execute with instrumentation enabled
- Capture metrics, logs, and error traces
- Monitor for resource exhaustion

### 5. Evaluate
- Compare results against hypotheses
- Measure coverage (code, edge cases, error paths)
- Document learnings for future iterations

## Experiment Tracking Format
```json
{
  "hypothesis": "<what we expect to happen>",
  "method": "<how we test it>",
  "result": "<what actually happened>",
  "learnings": ["<insight 1>", "<insight 2>"],
  "next_steps": ["<action 1>", "<action 2>"]
}
```

## Verifiability Rules
- Every task must produce a testable artifact
- Every hypothesis must have a pass/fail condition
- Every iteration must document what changed and why
