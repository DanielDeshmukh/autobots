"""Configuration management for Autobots."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("autobots")


CONFIG_FILE_NAMES = (".autobots.toml", "autobots.toml", ".autobotsrc")
ENV_PREFIX = "AUTOBOTS_"

# Valid values for enum-like fields
VALID_MODEL_PROFILES = {"balanced", "speed", "quality"}
VALID_EXECUTION_MODES = {"supervised", "milestone", "autonomous"}


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = ["Configuration validation failed:"]
        for error in self.errors:
            field_name = error.get("field", "unknown")
            message = error.get("message", "invalid value")
            suggestion = error.get("suggestion", "")
            lines.append(f"  • {field_name}: {message}")
            if suggestion:
                lines.append(f"    → {suggestion}")
        return "\n".join(lines)


@dataclass
class ConfigValidationResult:
    """Result of configuration validation."""

    valid: bool
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class AutobotsConfig:
    """Main configuration for Autobots CLI."""

    api_key: str | None = None
    model_selection_profile: str = "balanced"
    parallel_planning: bool = False
    disable_live_catalog: bool = False
    safety_branch: str = "autobots-safety"
    default_mode: str = "supervised"
    milestone_threshold: int = 3
    max_verification_attempts: int = 3
    model_registry_path: str | None = None

    # Test gate settings
    test_gate: bool = False
    test_command: str = "pytest tests/ -q"
    test_timeout: int = 120

    # Auto-commit settings
    auto_commit: bool = True
    auto_commit_message_template: str = "autobots: complete phase {phase_id} - {phase_title}"

    extra_clusters: dict[str, list[str]] = field(default_factory=dict)

    def validate(self) -> ConfigValidationResult:
        """Validate configuration values."""
        errors = []
        warnings = []

        # Validate model_selection_profile
        if self.model_selection_profile not in VALID_MODEL_PROFILES:
            errors.append({
                "field": "model_selection_profile",
                "message": f"invalid value '{self.model_selection_profile}'",
                "suggestion": f"must be one of: {', '.join(sorted(VALID_MODEL_PROFILES))}",
            })

        # Validate default_mode
        if self.default_mode not in VALID_EXECUTION_MODES:
            errors.append({
                "field": "default_mode",
                "message": f"invalid value '{self.default_mode}'",
                "suggestion": f"must be one of: {', '.join(sorted(VALID_EXECUTION_MODES))}",
            })

        # Validate milestone_threshold
        if self.milestone_threshold < 1:
            errors.append({
                "field": "milestone_threshold",
                "message": f"must be at least 1, got {self.milestone_threshold}",
                "suggestion": "set to 3 for standard milestone mode",
            })

        # Validate max_verification_attempts
        if self.max_verification_attempts < 1:
            errors.append({
                "field": "max_verification_attempts",
                "message": f"must be at least 1, got {self.max_verification_attempts}",
                "suggestion": "set to 3 for standard verification",
            })

        # Validate test_timeout
        if self.test_timeout < 10:
            errors.append({
                "field": "test_timeout",
                "message": f"must be at least 10 seconds, got {self.test_timeout}",
                "suggestion": "set to 120 for standard test runs",
            })

        # Validate model_registry_path exists if set
        if self.model_registry_path:
            registry_path = Path(self.model_registry_path)
            if not registry_path.exists():
                warnings.append({
                    "field": "model_registry_path",
                    "message": f"file not found: {self.model_registry_path}",
                    "suggestion": "file will be ignored, using bundled registry",
                })

        # Validate safety_branch is not empty
        if not self.safety_branch or not self.safety_branch.strip():
            errors.append({
                "field": "safety_branch",
                "message": "cannot be empty",
                "suggestion": "set to 'autobots-safety' for default behavior",
            })

        # Validate auto_commit_message_template has placeholders
        if self.auto_commit:
            if "{phase_id}" not in self.auto_commit_message_template:
                warnings.append({
                    "field": "auto_commit_message_template",
                    "message": "missing {phase_id} placeholder",
                    "suggestion": "include {phase_id} for proper commit messages",
                })

        return ConfigValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @classmethod
    def load(cls, project_root: Path | None = None) -> "AutobotsConfig":
        """Load configuration from file and environment."""
        config = cls()

        project_root = project_root or Path.cwd()
        config_file = cls._find_config_file(project_root)
        if config_file:
            cls._load_from_file(config, config_file)

        cls._load_from_env(config)

        return config

    @classmethod
    def _find_config_file(cls, project_root: Path) -> Path | None:
        """Find config file in project root or home directory."""
        for name in CONFIG_FILE_NAMES:
            path = project_root / name
            if path.exists():
                return path

        home = Path.home()
        for name in CONFIG_FILE_NAMES:
            path = home / name
            if path.exists():
                return path

        return None

    @classmethod
    def _load_from_file(cls, config: "AutobotsConfig", path: Path) -> None:
        """Load configuration from TOML file."""
        try:
            import tomllib

            with open(path, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            try:
                import tomli as tomllib

                with open(path, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                logger.warning("No TOML parser available (install tomllib or tomli) — skipping config file %s", path)
                return
        except Exception as exc:
            logger.warning("Failed to load config from %s: %s — using defaults", path, exc)
            return

        if "autobots" in data:
            section = data["autobots"]
            config.model_selection_profile = section.get("model_selection_profile", config.model_selection_profile)
            config.parallel_planning = section.get("parallel_planning", config.parallel_planning)
            config.disable_live_catalog = section.get("disable_live_catalog", config.disable_live_catalog)
            config.safety_branch = section.get("safety_branch", config.safety_branch)
            config.default_mode = section.get("default_mode", config.default_mode)
            config.milestone_threshold = section.get("milestone_threshold", config.milestone_threshold)
            config.max_verification_attempts = section.get("max_verification_attempts", config.max_verification_attempts)
            config.model_registry_path = section.get("model_registry_path", config.model_registry_path)

            # Test gate settings
            config.test_gate = section.get("test_gate", config.test_gate)
            config.test_command = section.get("test_command", config.test_command)
            config.test_timeout = section.get("test_timeout", config.test_timeout)

            if "extra_clusters" in section:
                config.extra_clusters = section["extra_clusters"]

    @classmethod
    def _load_from_env(cls, config: "AutobotsConfig") -> None:
        """Load configuration from environment variables."""
        if api_key := os.getenv("NVIDIA_API_KEY"):
            config.api_key = api_key

        if profile := os.getenv(f"{ENV_PREFIX}MODEL_SELECTION_PROFILE"):
            config.model_selection_profile = profile

        if parallel := os.getenv(f"{ENV_PREFIX}ENABLE_PARALLEL_PLANNING"):
            config.parallel_planning = parallel.lower() in ("1", "true", "yes")

        if disable := os.getenv(f"{ENV_PREFIX}DISABLE_LIVE_CATALOG"):
            config.disable_live_catalog = disable.lower() in ("1", "true", "yes")

        if branch := os.getenv(f"{ENV_PREFIX}SAFETY_BRANCH"):
            config.safety_branch = branch

        if mode := os.getenv(f"{ENV_PREFIX}DEFAULT_MODE"):
            config.default_mode = mode

        if threshold := os.getenv(f"{ENV_PREFIX}MILESTONE_THRESHOLD"):
            try:
                config.milestone_threshold = int(threshold)
            except ValueError:
                pass

        if attempts := os.getenv(f"{ENV_PREFIX}MAX_VERIFICATION_ATTEMPTS"):
            try:
                config.max_verification_attempts = int(attempts)
            except ValueError:
                pass

        if registry := os.getenv(f"{ENV_PREFIX}MODEL_REGISTRY"):
            config.model_registry_path = registry

        # Test gate settings
        if test_gate := os.getenv(f"{ENV_PREFIX}TEST_GATE"):
            config.test_gate = test_gate.lower() in ("1", "true", "yes")

        if test_command := os.getenv(f"{ENV_PREFIX}TEST_COMMAND"):
            config.test_command = test_command

        if test_timeout := os.getenv(f"{ENV_PREFIX}TEST_TIMEOUT"):
            try:
                config.test_timeout = int(test_timeout)
            except ValueError:
                pass

    def apply_env_vars(self) -> None:
        """Apply configuration as environment variables."""
        os.environ[f"{ENV_PREFIX}MODEL_SELECTION_PROFILE"] = self.model_selection_profile
        os.environ[f"{ENV_PREFIX}ENABLE_PARALLEL_PLANNING"] = "1" if self.parallel_planning else "0"
        os.environ[f"{ENV_PREFIX}DISABLE_LIVE_CATALOG"] = "1" if self.disable_live_catalog else "0"
        os.environ[f"{ENV_PREFIX}SAFETY_BRANCH"] = self.safety_branch
        os.environ[f"{ENV_PREFIX}DEFAULT_MODE"] = self.default_mode
        os.environ[f"{ENV_PREFIX}MILESTONE_THRESHOLD"] = str(self.milestone_threshold)
        os.environ[f"{ENV_PREFIX}MAX_VERIFICATION_ATTEMPTS"] = str(self.max_verification_attempts)
        if self.model_registry_path:
            os.environ[f"{ENV_PREFIX}MODEL_REGISTRY"] = self.model_registry_path

        # Test gate settings
        os.environ[f"{ENV_PREFIX}TEST_GATE"] = "1" if self.test_gate else "0"
        os.environ[f"{ENV_PREFIX}TEST_COMMAND"] = self.test_command
        os.environ[f"{ENV_PREFIX}TEST_TIMEOUT"] = str(self.test_timeout)


def load_config(project_root: Path | None = None) -> AutobotsConfig:
    """Load Autobots configuration."""
    return AutobotsConfig.load(project_root)