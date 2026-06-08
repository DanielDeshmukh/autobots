# Autobots User Guide

Autobots helps you prepare, plan, and execute work on another project from a clean starting point. This guide walks from installation through a full completion workflow and deployment-ready handoff.

## 1. Install Autobots

Install the published package:

pip install autobot-swarm

Verify the CLI is available:

autobots --help

If you are working in a virtual environment, activate it first.

## 2. Prerequisites for target projects

Before using Autobots on another project, make sure the target project has the following:

- Python 3.11 or newer
- A Git repository, if you want to use the safety branch workflow
- A writable project directory
- A valid NVIDIA API key if you plan to run or validate model-backed execution

Autobots expects you to point it at the project you want to work on.

## 3. Set up your API key

Autobots stores credentials in the repository root .env file.

When you run Autobots commands that require model access, it will prompt you for NVIDIA_API_KEY if one is missing.

If you already have a key, you can save it in the root .env file before using Autobots.

## 4. Start from complete scratch

Assume your target project is a fresh repository with no Autobots context files.

### Step 1: Check the six-file context architecture

Navigate to the target project and run:

autobots init

You can also point at a specific project path:

autobots init /path/to/your/project

This checks for the Autobots context files used for planning and execution. Autobots does not create target-project context files.

### Step 2: Create any missing context files

If the check reports missing files, create those filenames in the project context folder:

- roadmap.md
- progress-tracker.md
- security-auth.md
- architecture.md
- project-briefing.md
- ui-components.md

These files are the source of truth for Autobots planning and completion tracking.

## 5. Generate a plan for the target project

After the context files exist, build a roadmap and progress tracker:

autobots plan "Implement the missing feature set and prepare the project for release"

You can also target a specific path:

autobots plan /path/to/your/project "Implement the missing feature set and prepare the project for release"

Useful options:

- --append to append new work
- --insert-after to insert content at a specific section
- --dry-run to preview without writing files

The plan step transforms the repository scan into implementation phases and updates the context files.

## 6. Run the work

Autobots supports three execution modes:

- supervised
- milestone
- autonomous

### Recommended path for new projects

Start with supervised mode so you can review progress and approve actions:

autobots run --supervised /path/to/your/project

If you want checkpoints after meaningful milestones:

autobots run --milestone /path/to/your/project

If you are comfortable with fully automated execution:

autobots run --autonomous /path/to/your/project

### Dry run

Preview execution without changing files:

autobots run --autonomous --dry-run /path/to/your/project

## 7. Use the safety branch workflow

Autobots expects a safety branch for execution. The default branch name is:

autobots-safety

Before running work, switch the target project to that branch:

git checkout -b autobots-safety

If the project is not on the safety branch, Autobots will block execution and guide you to switch.

## 8. Track progress and resume later

After the run starts, use status to inspect current progress:

autobots status /path/to/your/project

If a checkpoint exists, you can continue later with:

autobots resume /path/to/your/project

Use resume when you want to continue work after stopping or after a partial run.

## 9. Validate model contracts

If you want to test live model integrations and confirm the runtime contract is healthy, run:

autobots validate-models

This is useful when you want to verify model connectivity and inspect the response structure before large runs.

## 10. Use the interactive engage flow

For a guided workflow with operator approval at each phase:

autobots engage

This flow is helpful when you want to actively review each plan step and approve execution intentionally.

## 11. Full completion checklist

A target project is considered complete when all of the following are true:

- Autobots context files exist and are up to date
- roadmap.md shows all phases completed
- progress-tracker.md reflects completed work
- status shows no pending phases
- no checkpoint is blocking continuation
- the project has the required tests or verification steps completed
- the final project state is ready for handoff or deployment

You can confirm completion with:

autobots status /path/to/your/project

When the tool reports that all phases are complete, the project is ready for the next deployment or handoff stage.

## 12. Recommended workflow for a fresh project

1. Install Autobots
2. Add NVIDIA_API_KEY if needed
3. Run Autobots init in the target project
4. Run Autobots plan
5. Run Autobots run in supervised or milestone mode
6. Review status and checkpoints
7. Resume if needed
8. Confirm completion with status
9. Verify the project manually for deployment readiness

## 13. Example end-to-end usage

Example for a fresh target project:

pip install autobot-swarm

cd /path/to/your/project

autobots init

autobots plan "Build the missing release workflow and prepare the project for deployment"

git checkout -b autobots-safety

autobots run --supervised

autobots status

If execution is interrupted:

autobots resume

When the project is complete:

- inspect the updated context files
- verify tests or release checks manually
- hand the project to your team or deploy it

## 14. Troubleshooting

### Command not found

Reinstall the package and ensure your environment PATH includes the package scripts.

### Missing dotenv or dependency errors

Reinstall Autobots in the active environment:

python -m pip install -e .

### Target project not found

Pass the absolute path explicitly or make sure the directory exists.

### Safety branch required

Create or switch to autobots-safety before continuing.

## 15. Final note

Autobots is most effective when you treat the context files as the operational record for the project. If you keep the plan, progress tracker, and code changes aligned, you can repeatedly use Autobots on new projects and reach a deployment-ready state with a predictable workflow.
