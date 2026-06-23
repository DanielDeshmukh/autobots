# Claude API Skill

## Purpose
Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration.

## TRIGGER
Read BEFORE opening the target file whenever:
- The prompt names Claude/Anthropic in any form (Claude, Anthropic, Fable, Opus, Sonnet, Haiku, `anthropic`, `@anthropic-ai`, `claude-*`, `us.anthropic.*`, `[1m]`)
- The user asks about an LLM (pricing/model choice/limits/caching) — never answer from memory
- The task is LLM-shaped with provider unstated (agent/MCP/tool-definition/multi-agent/RAG/LLM-judge/computer-use)

## SKIP only when another provider is being worked on (overrides all triggers): OpenAI/GPT/Gemini/Llama/Mistral/Cohere/Ollama named in the query.

## Output Requirement

When the user asks you to add, modify, or implement a Claude feature, your code must call Claude through one of:

1. **The official Anthropic SDK** for the project's language (`anthropic`, `@anthropic-ai/sdk`, `com.anthropic.*`, etc.). This is the default whenever a supported SDK exists for the project.
2. **Raw HTTP** (`curl`, `requests`, `fetch`, `httpx`, etc.) — only when the user explicitly asks for cURL/REST/raw HTTP, the project is a shell/cURL project, or the language has no official SDK.

Never mix the two — don't reach for `requests`/`fetch` in a Python or TypeScript project just because it feels lighter. Never fall back to OpenAI-compatible shims.

**Never guess SDK usage.** Function names, class names, namespaces, method signatures, and import paths must come from explicit documentation.

## Defaults

Unless the user requests otherwise:
- Model: `claude-opus-4-8`
- Thinking: `thinking: {type: "adaptive"}` for anything remotely complicated
- Streaming: For any request that may involve long input, long output, or high `max_tokens`

## Current Models

| Model | Model ID | Context | Input $/1M | Output $/1M |
|-------|----------|---------|------------|-------------|
| Claude Fable 5 | `claude-fable-5` | 1M | $10.00 | $50.00 |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M | $5.00 | $25.00 |
| Claude Opus 4.7 | `claude-opus-4-7` | 1M | $5.00 | $25.00 |
| Claude Opus 4.6 | `claude-opus-4-6` | 1M | $5.00 | $25.00 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M | $3.00 | $15.00 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | $1.00 | $5.00 |

## Thinking & Effort

- **Fable 5 / Opus 4.8 / 4.7 — Adaptive thinking only:** Use `thinking: {type: "adaptive"}`.
- **Effort parameter:** Controls thinking depth via `output_config: {effort: "low"|"medium"|"high"|"max"}`. Default is `high`.

## Architecture

Everything goes through `POST /v1/messages`. Tools and output constraints are features of this single endpoint — not separate APIs.

## Common Pitfalls

- Don't truncate inputs when passing files or content to the API
- Fable 5 / Opus 4.8 / 4.7 thinking: Adaptive only. `thinking: {type: "enabled", budget_tokens: N}` returns 400
- Prefill removed (Fable 5 and the 4.6/4.7/4.8 family)
- `max_tokens` defaults: Don't lowball — default to `~16000` for non-streaming, `~64000` for streaming