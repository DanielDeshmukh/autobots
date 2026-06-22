# Autobots Feature Parity Roadmap

Features Claude Code has that Autobots lacks. Organized into 6 phases.

---

## Phase 1: File Operations & Search

Goal: Enable direct file interaction without relying on the swarm.

### Tasks

- [ ] 1.1 Create `autobots/tools/` package with base `Tool` class
- [ ] 1.2 Implement `ReadTool` — read file with offset/limit, return line numbers
- [ ] 1.3 Implement `WriteTool` — create/overwrite files (require prior read)
- [ ] 1.4 Implement `EditTool` — targeted string replacement (oldString → newString)
- [ ] 1.5 Implement `EditTool` with `replaceAll` mode for global replacements
- [ ] 1.6 Implement `GlobTool` — pattern-based file search (`**/*.py`)
- [ ] 1.7 Implement `GrepTool` — regex content search across files
- [ ] 1.8 Add image/PDF reading support to `ReadTool`
- [ ] 1.9 Create `ToolRegistry` to register and dispatch tools
- [ ] 1.10 Add tool permission checks before execution
- [ ] 1.11 Add tool result formatting for terminal output
- [ ] 1.12 Write unit tests for all 5 file tools
- [ ] 1.13 Write integration test: read → edit → verify → read again

### Phase 1 Test

- [ ] **PT-1.1**: `ReadTool` reads file with correct line numbers
- [ ] **PT-1.2**: `WriteTool` creates file, `ReadTool` verifies content
- [ ] **PT-1.3**: `EditTool` replaces exact string, partial match fails
- [ ] **PT-1.4**: `EditTool` with `replaceAll` replaces all occurrences
- [ ] **PT-1.5**: `GlobTool` finds files by pattern
- [ ] **PT-1.6**: `GrepTool` finds content by regex
- [ ] **PT-1.7**: `ReadTool` with offset/limit reads correct lines
- [ ] **PT-1.8**: All tools registered in `ToolRegistry`
- [ ] **PT-1.9**: Permission check blocks unauthorized write
- [ ] **PT-1.10**: Full read → edit → verify cycle passes

---

## Phase 2: REPL & Interactive Mode

Goal: Enable conversational interaction with Claude.

### Tasks

- [ ] 2.1 Create `autobots/repl/` package with `ReplSession` class
- [ ] 2.2 Implement input loop with prompt display
- [ ] 2.3 Implement conversation history (list of messages)
- [ ] 2.4 Implement streaming response display
- [ ] 2.5 Implement tool call handling in REPL loop
- [ ] 2.6 Implement `exit`/`quit` commands
- [ ] 2.7 Implement `/help` command
- [ ] 2.8 Implement `/clear` command
- [ ] 2.9 Implement `/cost` command (show token usage)
- [ ] 2.10 Implement `/model` command (switch model mid-session)
- [ ] 2.11 Implement one-shot mode (`autobots ask "prompt"`)
- [ ] 2.12 Implement piped input (`cat file.py | autobots ask "explain"`)
- [ ] 2.13 Add Ctrl+C interrupt handling
- [ ] 2.14 Add session save/load for resuming conversations
- [ ] 2.15 Write unit tests for REPL session and commands

### Phase 2 Test

- [ ] **PT-2.1**: REPL starts and displays prompt
- [ ] **PT-2.2**: User input sent to Claude, response displayed
- [ ] **PT-2.3**: Tool calls executed in loop, results displayed
- [ ] **PT-2.4**: `exit` terminates session cleanly
- [ ] **PT-2.5**: `/help` lists available commands
- [ ] **PT-2.6**: `/clear` resets conversation history
- [ ] **PT-2.7**: `/cost` shows token usage and estimated cost
- [ ] **PT-2.8**: `/model` switches model mid-session
- [ ] **PT-2.9**: One-shot mode runs and exits
- [ ] **PT-2.10**: Piped input processed correctly
- [ ] **PT-2.11**: Ctrl+C interrupts without crashing
- [ ] **PT-2.12**: Session save/load preserves history

---

## Phase 3: Permission System & Safety

Goal: Granular tool-level permissions.

### Tasks

- [ ] 3.1 Create `autobots/permissions/` package
- [ ] 3.2 Implement `PermissionRule` dataclass (allow/deny patterns)
- [ ] 3.3 Implement `PermissionChecker` — match tool calls against rules
- [ ] 3.4 Implement interactive approval prompt (y/n/a/Esc)
- [ ] 3.5 Implement "always allow" mode for session
- [ ] 3.6 Implement deny list (block dangerous commands)
- [ ] 3.7 Create `~/.autobots/settings.json` global config
- [ ] 3.8 Create `.autobots/settings.json` project config
- [ ] 3.9 Implement config merge (global + project + env)
- [ ] 3.10 Add permission logging for audit trail
- [ ] 3.11 Implement `/permissions` command to view/edit rules
- [ ] 3.12 Add `--allowedTools` CLI flag for pre-approving tools
- [ ] 3.13 Write unit tests for permission matching
- [ ] 3.14 Write integration test: deny → block → log

### Phase 3 Test

- [ ] **PT-3.1**: `PermissionChecker` matches `Bash(git *)` pattern
- [ ] **PT-3.2**: Deny pattern blocks execution
- [ ] **PT-3.3**: Interactive prompt shows tool name and arguments
- [ ] **PT-3.4**: `y` approves, `n` denies, `a` always allows for session
- [ ] **PT-3.5**: Always-allowed tool skips prompt on subsequent calls
- [ ] **PT-3.6**: Deny list blocks `rm -rf` regardless of user input
- [ ] **PT-3.7**: Global settings loaded from `~/.autobots/settings.json`
- [ ] **PT-3.8**: Project settings override global settings
- [ ] **PT-3.9**: `/permissions` displays current rules
- [ ] **PT-3.10**: `--allowedTools` pre-approves tools for the session
- [ ] **PT-3.11**: Permission denials logged to audit trail

---

## Phase 4: Context Management & Compaction

Goal: Manage long conversations without hitting context limits.

### Tasks

- [ ] 4.1 Create `autobots/context/` package
- [ ] 4.2 Implement `ContextManager` — track conversation token usage
- [ ] 4.3 Implement token estimation (len // 4 or tiktoken)
- [ ] 4.4 Implement `/compact` command — summarize conversation
- [ ] 4.5 Implement compaction strategy (keep key facts, discard noise)
- [ ] 4.6 Implement CLAUDE.md hierarchy (global → project → subdir)
- [ ] 4.7 Implement `/memory` command to edit CLAUDE.md
- [ ] 4.8 Implement auto-compaction when approaching context limit
- [ ] 4.9 Add compaction quality checks (verify key facts preserved)
- [ ] 4.10 Implement context budget display (`/cost` shows remaining)
- [ ] 4.11 Write unit tests for token estimation and compaction
- [ ] 4.12 Write integration test: long conversation → compact → verify

### Phase 4 Test

- [ ] **PT-4.1**: `ContextManager` tracks token usage correctly
- [ ] **PT-4.2**: Token estimation returns reasonable values
- [ ] **PT-4.3**: `/compact` reduces message count
- [ ] **PT-4.4**: Compacted conversation preserves key decisions
- [ ] **PT-4.5**: CLAUDE.md loaded from global, project, and subdir
- [ ] **PT-4.6**: `/memory` edits CLAUDE.md file
- [ ] **PT-4.7**: Auto-compaction triggers at 80% context limit
- [ ] **PT-4.8**: `/cost` shows remaining context budget
- [ ] **PT-4.9**: Long conversation (100+ turns) compacts without data loss

---

## Phase 5: Hooks, MCP & Extensions

Goal: Extensibility layer for custom workflows.

### Tasks

- [ ] 5.1 Create `autobots/hooks/` package
- [ ] 5.2 Implement `HookManager` — register pre/post tool hooks
- [ ] 5.3 Implement hook execution before tool calls
- [ ] 5.4 Implement hook execution after tool calls
- [ ] 5.5 Implement hook failure handling (abort or warn)
- [ ] 5.6 Create `autobots/mcp/` package
- [ ] 5.7 Implement MCP client connection
- [ ] 5.8 Implement MCP tool discovery
- [ ] 5.9 Implement MCP tool invocation
- [ ] 5.10 Implement MCP server configuration in settings
- [ ] 5.11 Add hook configuration in settings.json
- [ ] 5.12 Write unit tests for hook lifecycle
- [ ] 5.13 Write integration test: hook → tool → hook → verify

### Phase 5 Test

- [ ] **PT-5.1**: Pre-hook runs before tool execution
- [ ] **PT-5.2**: Post-hook runs after tool execution
- [ ] **PT-5.3**: Hook failure aborts tool execution
- [ ] **PT-5.4**: MCP client connects to server
- [ ] **PT-5.5**: MCP tools discovered and registered
- [ ] **PT-5.6**: MCP tool invocation returns results
- [ ] **PT-5.7**: MCP server configured in settings.json
- [ ] **PT-5.8**: Hooks configured in settings.json
- [ ] **PT-5.9**: Full hook → tool → hook cycle passes

---

## Phase 6: Code Review & Diagnostics

Goal: PR review, code review, and system health checks.

### Tasks

- [ ] 6.1 Create `autobots/review/` package
- [ ] 6.2 Implement `/review` — review recent git changes
- [ ] 6.3 Implement `/pr-review` — review a PR by number or URL
- [ ] 6.4 Implement diff parsing and summarization
- [ ] 6.5 Implement review quality scoring
- [ ] 6.6 Implement `/doctor` — check API key, connectivity, config
- [ ] 6.7 Implement `/login` — authenticate with provider
- [ ] 6.8 Implement `/logout` — sign out
- [ ] 6.9 Implement `/terminal-setup` — shell integration
- [ ] 6.10 Implement budget limits in settings
- [ ] 6.11 Implement cost alerts when approaching budget
- [ ] 6.12 Write unit tests for review and diagnostics
- [ ] 6.13 Write integration test: review → feedback → verify

### Phase 6 Test

- [ ] **PT-6.1**: `/review` shows diff summary and feedback
- [ ] **PT-6.2**: `/pr-review` fetches PR and reviews changes
- [ ] **PT-6.3**: `/doctor` checks API key validity
- [ ] **PT-6.4**: `/doctor` checks network connectivity
- [ ] **PT-6.5**: `/doctor` checks config file validity
- [ ] **PT-6.6**: `/login` stores credentials securely
- [ ] **PT-6.7**: `/logout` clears stored credentials
- [ ] **PT-6.8**: Budget limit blocks execution when exceeded
- [ ] **PT-6.9**: Cost alert warns when approaching budget
- [ ] **PT-6.10**: Full review cycle (git diff → review → output) passes

---

## Summary

| Phase | Feature Area | Tasks | Tests |
|-------|-------------|-------|-------|
| 1 | File Operations & Search | 13 | 10 |
| 2 | REPL & Interactive Mode | 15 | 12 |
| 3 | Permission System & Safety | 14 | 11 |
| 4 | Context Management & Compaction | 12 | 9 |
| 5 | Hooks, MCP & Extensions | 13 | 9 |
| 6 | Code Review & Diagnostics | 13 | 10 |
| **Total** | | **80** | **61** |

## Execution Order

```
Phase 1 (File Ops) → Phase 2 (REPL) → Phase 3 (Permissions)
                                        ↓
                               Phase 4 (Context)
                                        ↓
                               Phase 5 (Hooks/MCP)
                                        ↓
                               Phase 6 (Review/Diagnostics)
```

Phase 1 must complete first (REPL needs file tools). Phases 3-6 can be parallelized after Phase 2.
