"""Shell completion support for Autobots CLI."""

from __future__ import annotations

# Autobots commands for completion
COMMANDS = [
    "init",
    "plan",
    "run",
    "resume",
    "status",
    "engage",
    "doctor",
    "config",
    "diff",
    "logs",
    "validate-models",
    "publish",
    "undo",
    "snapshots",
    "catalog",
    "list",
]

# Common flags for completion
GLOBAL_FLAGS = [
    "--help",
    "-h",
]

COMMAND_FLAGS = {
    "init": ["--interactive", "--wizard", "--skip-api-key"],
    "run": ["--supervised", "--autonomous", "--milestone", "--dry-run"],
    "engage": ["--supervised", "--autonomous", "--milestone"],
    "doctor": ["--skip-model", "--quiet"],
    "config": ["--validate", "--show"],
    "diff": ["--snapshot"],
    "logs": ["--phase", "--type", "--limit", "--details"],
    "catalog": ["--refresh", "--list", "--cluster"],
    "validate-models": ["--test"],
}


def generate_bash_completion() -> str:
    """Generate bash completion script."""
    return '''#!/bin/bash
# Autobots bash completion

_autobots_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="init plan run resume status engage doctor config diff logs validate-models publish undo snapshots catalog list"

    # Complete commands
    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "--help -h" -- ${cur}) )
        return 0
    fi

    # Complete subcommands based on current command
    case ${COMP_WORDS[1]} in
        init)
            COMPREPLY=( $(compgen -W "--interactive --wizard --skip-api-key --help" -- ${cur}) )
            ;;
        run)
            COMPREPLY=( $(compgen -W "--supervised --autonomous --milestone --dry-run --help" -- ${cur}) )
            ;;
        engage)
            COMPREPLY=( $(compgen -W "--supervised --autonomous --milestone --help" -- ${cur}) )
            ;;
        doctor)
            COMPREPLY=( $(compgen -W "--skip-model --quiet --help" -- ${cur}) )
            ;;
        config)
            COMPREPLY=( $(compgen -W "validate show --help" -- ${cur}) )
            ;;
        diff)
            COMPREPLY=( $(compgen -W "--snapshot --help" -- ${cur}) )
            ;;
        logs)
            COMPREPLY=( $(compgen -W "--phase --type --limit --details --help" -- ${cur}) )
            ;;
        catalog)
            COMPREPLY=( $(compgen -W "refresh list --cluster --help" -- ${cur}) )
            ;;
        *)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            ;;
    esac

    return 0
}

complete -F _autobots_completions autobots
'''


def generate_zsh_completion() -> str:
    """Generate zsh completion script."""
    return '''#compdef autobots

# Autobots zsh completion

_autobots() {
    local -a commands
    commands=(
        'init:Check required context files for a target project'
        'plan:Read roadmap.md and create task IDs'
        'run:Run task by ID'
        'resume:Resume execution from checkpoint'
        'status:Show phase and task statuses'
        'engage:Interactive swarm execution'
        'doctor:Run preflight checks'
        'config:Validate or show configuration'
        'diff:Compare workspace to snapshot'
        'logs:View audit trail'
        'validate-models:Test model contracts'
        'publish:Build and publish to PyPI'
        'undo:Undo task changes'
        'snapshots:List file snapshots'
        'catalog:Manage model catalog'
        'list:Show available commands'
    )

    _arguments -C \
        '1:command:->command' \
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[1] in
                init)
                    _arguments \
                        '--interactive[Run interactive onboarding wizard]' \
                        '--wizard[Run interactive onboarding wizard]' \
                        '--skip-api-key[Skip API key prompt]' \
                        '--help[Show help]'
                    ;;
                run)
                    _arguments \
                        '--supervised[Run in supervised mode]' \
                        '--autonomous[Run in autonomous mode]' \
                        '--milestone[Run in milestone mode]' \
                        '--dry-run[Run without making changes]' \
                        '--help[Show help]'
                    ;;
                engage)
                    _arguments \
                        '--supervised[Run in supervised mode]' \
                        '--autonomous[Run in autonomous mode]' \
                        '--milestone[Run in milestone mode]' \
                        '--help[Show help]'
                    ;;
                doctor)
                    _arguments \
                        '--skip-model[Skip model validation]' \
                        '--quiet[Quiet output]' \
                        '--help[Show help]'
                    ;;
                config)
                    _arguments \
                        '1:subcommand:(validate show)' \
                        '--help[Show help]'
                    ;;
                diff)
                    _arguments \
                        '--snapshot[Specify snapshot ID]' \
                        '--help[Show help]'
                    ;;
                logs)
                    _arguments \
                        '--phase[Filter by phase ID]' \
                        '--type[Filter by change type]' \
                        '--limit[Number of entries]' \
                        '--details[Show detailed info]' \
                        '--help[Show help]'
                    ;;
                catalog)
                    _arguments \
                        '1:subcommand:(refresh list)' \
                        '--cluster[Filter by cluster]' \
                        '--help[Show help]'
                    ;;
                *)
                    _arguments \
                        '--help[Show help]'
                    ;;
            esac
            ;;
    esac
}

_autobots "$@"
'''


def generate_fish_completion() -> str:
    """Generate fish completion script."""
    return '''# Autobots fish completion

# Commands
complete -c autobots -f
complete -c autobots -n "__fish_use_subcommand" -a "init" -d "Check required context files"
complete -c autobots -n "__fish_use_subcommand" -a "plan" -d "Read roadmap and create tasks"
complete -c autobots -n "__fish_use_subcommand" -a "run" -d "Run task by ID"
complete -c autobots -n "__fish_use_subcommand" -a "resume" -d "Resume from checkpoint"
complete -c autobots -n "__fish_use_subcommand" -a "status" -d "Show phase statuses"
complete -c autobots -n "__fish_use_subcommand" -a "engage" -d "Interactive execution"
complete -c autobots -n "__fish_use_subcommand" -a "doctor" -d "Run preflight checks"
complete -c autobots -n "__fish_use_subcommand" -a "config" -d "Validate or show config"
complete -c autobots -n "__fish_use_subcommand" -a "diff" -d "Compare to snapshot"
complete -c autobots -n "__fish_use_subcommand" -a "logs" -d "View audit trail"
complete -c autobots -n "__fish_use_subcommand" -a "validate-models" -d "Test model contracts"
complete -c autobots -n "__fish_use_subcommand" -a "publish" -d "Build and publish"
complete -c autobots -n "__fish_use_subcommand" -a "undo" -d "Undo changes"
complete -c autobots -n "__fish_use_subcommand" -a "snapshots" -d "List snapshots"
complete -c autobots -n "__fish_use_subcommand" -a "catalog" -d "Manage catalog"
complete -c autobots -n "__fish_use_subcommand" -a "list" -d "Show commands"

# Global flags
complete -c autobots -l help -s h -d "Show help"

# init flags
complete -c autobots -n "__fish_seen_subcommand_from init" -l interactive -d "Run onboarding wizard"
complete -c autobots -n "__fish_seen_subcommand_from init" -l wizard -d "Run onboarding wizard"
complete -c autobots -n "__fish_seen_subcommand_from init" -l skip-api-key -d "Skip API key prompt"

# run flags
complete -c autobots -n "__fish_seen_subcommand_from run" -l supervised -d "Supervised mode"
complete -c autobots -n "__fish_seen_subcommand_from run" -l autonomous -d "Autonomous mode"
complete -c autobots -n "__fish_seen_subcommand_from run" -l milestone -d "Milestone mode"
complete -c autobots -n "__fish_seen_subcommand_from run" -l dry-run -d "Dry run"

# engage flags
complete -c autobots -n "__fish_seen_subcommand_from engage" -l supervised -d "Supervised mode"
complete -c autobots -n "__fish_seen_subcommand_from engage" -l autonomous -d "Autonomous mode"
complete -c autobots -n "__fish_seen_subcommand_from engage" -l milestone -d "Milestone mode"

# doctor flags
complete -c autobots -n "__fish_seen_subcommand_from doctor" -l skip-model -d "Skip model check"
complete -c autobots -n "__fish_seen_subcommand_from doctor" -l quiet -d "Quiet output"

# config subcommands
complete -c autobots -n "__fish_seen_subcommand_from config" -a "validate" -d "Validate configuration"
complete -c autobots -n "__fish_seen_subcommand_from config" -a "show" -d "Show configuration"

# logs flags
complete -c autobots -n "__fish_seen_subcommand_from logs" -l phase -d "Filter by phase"
complete -c autobots -n "__fish_seen_subcommand_from logs" -l type -d "Filter by type"
complete -c autobots -n "__fish_seen_subcommand_from logs" -l limit -d "Entry limit"
complete -c autobots -n "__fish_seen_subcommand_from logs" -l details -d "Show details"

# catalog subcommands
complete -c autobots -n "__fish_seen_subcommand_from catalog" -a "refresh" -d "Refresh catalog"
complete -c autobots -n "__fish_seen_subcommand_from catalog" -a "list" -d "List models"
complete -c autobots -n "__fish_seen_subcommand_from catalog" -l cluster -d "Filter by cluster"
'''


COMPLETION_FORMATS = {
    "bash": generate_bash_completion,
    "zsh": generate_zsh_completion,
    "fish": generate_fish_completion,
}


def get_completion_script(shell: str) -> str | None:
    """Get completion script for specified shell."""
    generator = COMPLETION_FORMATS.get(shell)
    if generator:
        return generator()
    return None


def get_available_shells() -> list[str]:
    """Get list of supported shells."""
    return list(COMPLETION_FORMATS.keys())
