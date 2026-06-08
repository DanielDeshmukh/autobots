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

    extra_clusters: dict[str, list[str]] = field(default_factory=dict)

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


def load_config(project_root: Path | None = None) -> AutobotsConfig:
    """Load Autobots configuration."""
    return AutobotsConfig.load(project_root)