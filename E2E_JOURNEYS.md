# End-to-End Journey Tests

This document provides E2E journey test scripts for 2 independent testers.

## Prerequisites

1. Python 3.11+ installed
2. `NVIDIA_API_KEY` environment variable set
3. Package installed: `pip install -e . --no-build-isolation`

---

## Journey 1: New User (Tester 1)

**Goal**: Verify a new user can install, configure, and run their first task.

### Checklist

- [ ] **1.1** Package is installed: `pip show autobot-swarm`
- [ ] **1.2** CLI help works: `python -m autobots --help`
- [ ] **1.3** Version flag works: `python -m autobots --version`
- [ ] **1.4** Init command creates project structure: `python -m autobots init`
- [ ] **1.5** Plan command generates roadmap: `python -m autobots plan --goal 'Add login'`
- [ ] **1.6** Status command shows project status: `python -m autobots status`
- [ ] **1.7** Explain command explains architecture: `python -m autobots explain`
- [ ] **1.8** Stats command shows statistics: `python -m autobots stats`
- [ ] **1.9** Catalog command shows available models: `python -m autobots catalog`
- [ ] **1.10** Config validate checks configuration: `python -m autobots config validate`
- [ ] **1.11** Completions command generates shell completions: `python -m autobots completions bash`
- [ ] **1.12** Doctor command checks environment: `python -m autobots doctor`

### Expected Results

- All commands should succeed (exit code 0)
- Init should create `context/` directory with 6 files
- Plan should create `roadmap.md` and `progress-tracker.md`
- Status should show current phase and progress
- Explain should show architecture overview
- Stats should show token usage and costs

---

## Journey 2: Experienced User (Tester 2)

**Goal**: Verify an experienced user can run a full supervised task with all features.

### Checklist

- [ ] **2.1** Prerequisites are met (Python 3.11+, NVIDIA_API_KEY set)
- [ ] **2.2** Environment variables are accessible
- [ ] **2.3** Test project is set up (src/, tests/, src/main.py)
- [ ] **2.4** Init creates context files: `python -m autobots init`
- [ ] **2.5** Plan with specific goal: `python -m autobots plan --goal 'Add user authentication with JWT tokens'`
- [ ] **2.6** Plan with append mode: `python -m autobots plan --goal 'Add rate limiting' --append`
- [ ] **2.7** Plan dry run: `python -m autobots plan --goal 'Add caching' --dry-run`
- [ ] **2.8** Run in supervised mode: `python -m autobots run --supervised --yes`
- [ ] **2.9** Run in milestone mode: `python -m autobots run --milestone --yes`
- [ ] **2.10** Run in autonomous mode: `python -m autobots run --autonomous --yes`
- [ ] **2.11** Status shows plan after planning: `python -m autobots status`
- [ ] **2.12** Snapshots command works: `python -m autobots snapshots`
- [ ] **2.13** Logs command works: `python -m autobots logs`
- [ ] **2.14** Explain shows architecture: `python -m autobots explain architecture`
- [ ] **2.15** Explain shows security: `python -m autobots explain security`
- [ ] **2.16** Stats shows usage after work: `python -m autobots stats`
- [ ] **2.17** Undo command works: `python -m autobots undo`
- [ ] **2.18** Diff command works: `python -m autobots diff`
- [ ] **2.19** Validate models works: `python -m autobots validate-models`
- [ ] **2.20** Ask command answers questions: `python -m autobots ask 'What is this project?'`
- [ ] **2.21** Steer command adds instructions: `python -m autobots steer 'Use type hints'`

### Expected Results

- All commands should succeed (exit code 0)
- Plan with append should add to existing plan
- Plan dry run should show what would be done without executing
- Run commands should complete (may fail due to API, but should not crash)
- Status should show updated progress
- Snapshots should list any snapshots taken
- Logs should show recent activity
- Explain should show detailed architecture/security info
- Stats should show token usage and costs
- Undo should restore previous state
- Diff should show changes made
- Validate models should check NVIDIA API connectivity
- Ask should answer questions about the project
- Steer should add steering instructions

---

## Test Execution Instructions

### For Tester 1 (Journey 1)

1. Create a fresh test directory
2. Navigate to the directory
3. Run each command in the checklist
4. Verify expected results
5. Document any issues found

### For Tester 2 (Journey 2)

1. Create a test directory with src/, tests/, src/main.py
2. Navigate to the directory
3. Set NVIDIA_API_KEY environment variable
4. Run each command in the checklist
5. Verify expected results
6. Document any issues found

---

## Known Issues

See `KNOWN_ISSUES.md` for known issues and limitations.

---

## Sign-off

| Journey | Tester | Date | Status |
|---------|--------|------|--------|
| Journey 1 | _____________ | _____________ | [ ] PASS |
| Journey 2 | _____________ | _____________ | [ ] PASS |
