# NemoClaw Agent Skills Architecture

## Skill Pack Structure
```
.agents/skills/
├── <skill-name>/
│   ├── skill.md          # Skill definition (name, description, triggers)
│   ├── instructions.md   # Detailed workflow instructions
│   ├── references/       # Code examples, API docs
│   └── templates/        # Output templates
```

## Skill Definition Format (skill.md)
```yaml
name: <skill-name>
description: <one-line purpose>
triggers:
  - <keyword or pattern that activates this skill>
tools_required:
  - <list of tools this skill uses>
```

## Agent Dispatch Patterns
- **Sequential**: Agent A → Agent B → Agent C (dependency chain)
- **Parallel**: Agent A + Agent B simultaneously → Agent C (fan-in)
- **Hierarchical**: Orchestrator → Specialist agents → Review agent

## Integration Pattern
```python
# Load skill pack for a cluster
skill_pack = load_skill_pack(workspace_root, cluster_name)
# Inject into system prompt
system_prompt = f"{base_prompt}\n\n{skill_pack}"
```

## Key Principles
1. Skills are composable — one agent can use multiple skills
2. Skills declare dependencies — loader resolves before execution
3. Skills produce structured output — JSON contracts between agents
4. Skills are idempotent — re-running produces identical results
