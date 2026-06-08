# Skill Evolution Protocol

## After Each Non-Trivial Task

### 1. Detect Generalizable Learnings
- What patterns emerged that could apply to future tasks?
- What assumptions were wrong? What corrections were needed?
- What tools or APIs were discovered that aren't documented?

### 2. Propose Skill Updates
```json
{
  "skill_file": "<which skill to update>",
  "update_type": "add|modify|remove",
  "section": "<which section>",
  "content": "<new or updated content>",
  "rationale": "<why this improves the skill>"
}
```

### 3. Validate Proposals
- Does the update conflict with existing knowledge?
- Is the pattern generalizable beyond this specific task?
- Can it be expressed concisely (30-50 lines max)?

### 4. Apply Updates
- Write to `context/conventions.md` for project-specific learnings
- Write to skill files for cross-project patterns
- Version control all changes

## Learning Categories
- **API Patterns**: New endpoints, authentication flows, error handling
- **Architecture Patterns**: Directory structures, naming conventions, module boundaries
- **Testing Patterns**: Edge cases, performance benchmarks, regression tests
- **Tool Patterns**: CLI flags, configuration options, workflow shortcuts

## Anti-Patterns to Avoid
- Don't capture one-off hacks as patterns
- Don't duplicate existing documentation
- Don't add without removing outdated content
- Don't propose changes without rationale
