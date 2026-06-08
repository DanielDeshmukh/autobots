"""Plugin system for Autobots."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("autobots")

# Plugin hooks that can be implemented
PLUGIN_HOOKS = [
    "pre_phase",      # Before phase execution
    "post_phase",     # After phase completion
    "pre_model_call", # Before model API call
    "post_model_call",# After model API call
    "on_error",       # On error
    "on_validation",  # During validation
]


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    version: str = "0.1.0"
    author: str = ""
    description: str = ""
    hooks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "hooks": self.hooks,
        }


class Plugin:
    """Base class for Autobots plugins."""

    metadata: PluginMetadata

    def __init__(self):
        self.enabled = True

    def pre_phase(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called before phase execution.

        Args:
            context: Dict with phase info (phase_id, phase_title, etc.)

        Returns:
            Modified context or None to continue with original
        """
        return None

    def post_phase(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called after phase completion.

        Args:
            context: Dict with phase result info

        Returns:
            Modified context or None
        """
        return None

    def pre_model_call(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called before model API call.

        Args:
            context: Dict with model_id, messages, etc.

        Returns:
            Modified context or None
        """
        return None

    def post_model_call(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called after model API call.

        Args:
            context: Dict with response, usage, etc.

        Returns:
            Modified context or None
        """
        return None

    def on_error(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called on error.

        Args:
            context: Dict with error info

        Returns:
            Modified context or None
        """
        return None

    def on_validation(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called during validation.

        Args:
            context: Dict with validation info

        Returns:
            Modified context or None
        """
        return None


class PluginManager:
    """Manages loading and executing plugins."""

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}
        self.hooks: dict[str, list[Callable]] = {hook: [] for hook in PLUGIN_HOOKS}

    def register(self, plugin: Plugin) -> bool:
        """Register a plugin."""
        name = plugin.metadata.name
        if name in self.plugins:
            logger.warning("Plugin %s already registered, skipping", name)
            return False

        self.plugins[name] = plugin

        # Register hooks
        for hook_name in plugin.metadata.hooks:
            if hook_name in self.hooks:
                hook_method = getattr(plugin, hook_name, None)
                if hook_method and callable(hook_method):
                    self.hooks[hook_name].append(hook_method)
                    logger.debug("Registered hook %s for plugin %s", hook_name, name)

        logger.info("Registered plugin: %s v%s", name, plugin.metadata.version)
        return True

    def unregister(self, name: str) -> bool:
        """Unregister a plugin."""
        if name not in self.plugins:
            return False

        plugin = self.plugins.pop(name)

        # Unregister hooks
        for hook_name in plugin.metadata.hooks:
            if hook_name in self.hooks:
                hook_method = getattr(plugin, hook_name, None)
                if hook_method in self.hooks[hook_name]:
                    self.hooks[hook_name].remove(hook_method)

        logger.info("Unregistered plugin: %s", name)
        return True

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a plugin by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> list[PluginMetadata]:
        """List all registered plugins."""
        return [p.metadata for p in self.plugins.values()]

    def execute_hook(self, hook_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute all hooks for a given hook name.

        Args:
            hook_name: Name of the hook to execute
            context: Context dict to pass to hooks

        Returns:
            Modified context after all hooks have run
        """
        if hook_name not in self.hooks:
            return context

        for hook_method in self.hooks[hook_name]:
            try:
                result = hook_method(context)
                if result is not None:
                    context = result
            except Exception as exc:
                logger.error(
                    "Error in plugin hook %s: %s",
                    hook_name,
                    exc,
                    exc_info=True,
                )

        return context

    def load_from_path(self, path: Path) -> bool:
        """Load a plugin from a Python file."""
        if not path.exists():
            logger.error("Plugin file not found: %s", path)
            return False

        try:
            spec = importlib.util.spec_from_file_location(
                f"autobots_plugin_{path.stem}",
                str(path),
            )
            if spec is None or spec.loader is None:
                logger.error("Failed to load plugin spec: %s", path)
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[module.__name__] = module
            spec.loader.exec_module(module)

            # Look for a Plugin subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Plugin)
                    and attr is not Plugin
                ):
                    plugin_instance = attr()
                    return self.register(plugin_instance)

            logger.warning("No Plugin subclass found in %s", path)
            return False

        except Exception as exc:
            logger.error("Failed to load plugin from %s: %s", path, exc)
            return False

    def load_from_directory(self, directory: Path) -> int:
        """Load all plugins from a directory."""
        loaded = 0
        if not directory.exists():
            return 0

        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            if self.load_from_path(py_file):
                loaded += 1

        return loaded


# Global plugin manager instance
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def load_plugins_from_config(config_dir: Path | None = None) -> int:
    """Load plugins from configuration directory."""
    manager = get_plugin_manager()

    if config_dir is None:
        from pathlib import Path
        config_dir = Path.home() / ".autobots" / "plugins"

    plugins_dir = config_dir / "plugins"
    if plugins_dir.exists():
        return manager.load_from_directory(plugins_dir)

    return 0


class SimplePlugin(Plugin):
    """Example simple plugin for demonstration."""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="simple-example",
            version="0.1.0",
            author="Autobots",
            description="A simple example plugin",
            hooks=["pre_phase", "post_phase"],
        )

    def pre_phase(self, context: dict[str, Any]) -> dict[str, Any] | None:
        phase_id = context.get("phase_id", "unknown")
        logger.info("[SimplePlugin] Pre-phase: %s", phase_id)
        return None

    def post_phase(self, context: dict[str, Any]) -> dict[str, Any] | None:
        phase_id = context.get("phase_id", "unknown")
        logger.info("[SimplePlugin] Post-phase: %s", phase_id)
        return None
