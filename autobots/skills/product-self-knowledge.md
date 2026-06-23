# Product Self-Knowledge Skill

## Purpose
Accurate facts about Claude API, Claude Code, and claude.ai. Required before any agent writes Anthropic SDK code or quotes pricing.

## Claude API Models

| Model | Model ID | Context | Input $/1M | Output $/1M |
|-------|----------|---------|------------|-------------|
| Claude Fable 5 | `claude-fable-5` | 1M | $10.00 | $50.00 |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M | $5.00 | $25.00 |
| Claude Opus 4.7 | `claude-opus-4-7` | 1M | $5.00 | $25.00 |
| Claude Opus 4.6 | `claude-opus-4-6` | 1M | $5.00 | $25.00 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M | $3.00 | $15.00 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | $1.00 | $5.00 |

## Key Facts

### API Surface
- All requests go through `POST /v1/messages`
- Tools and output constraints are features of this single endpoint
- SDKs available: Python, TypeScript, Java, Go, Ruby, C#, PHP

### Thinking
- Adaptive thinking: `thinking: {type: "adaptive"}`
- Fable 5 / Opus 4.8 / 4.7: Adaptive only (no budget_tokens)
- Effort: `output_config: {effort: "low"|"medium"|"high"|"max"}`

### Managed Agents
- Server-managed stateful agents with Anthropic-hosted tool execution
- Available on first-party API and Claude Platform on AWS
- Not available on Bedrock, Vertex, or Foundry

### Prompt Caching
- Prefix match: any byte change invalidates everything after
- Render order: tools → system → messages
- Max 4 breakpoints per request

## Claude Code Features
- Agentic coding assistant
- File editing, terminal access, web search
- MCP server integration
- Skills system for specialized tasks

## Claude.ai Features
- Web interface for Claude
- Artifacts for code/document generation
- Skills for specialized workflows
- File upload and analysis

## Common Mistakes to Avoid
1. Don't use `budget_tokens` on Fable 5 / Opus 4.8 / 4.7
2. Don't use assistant prefill on 4.6+ models
3. Don't mix SDK and raw HTTP in the same project
4. Don't guess model IDs — use exact strings from the table