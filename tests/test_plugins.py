"""Tests for plugin system."""

import tempfile
import unittest
from pathlib import Path

from autobots.plugins import (
    PLUGIN_HOOKS,
    Plugin,
    PluginManager,
    PluginMetadata,
    SimplePlugin,
    get_plugin_manager,
)


class TestPluginMetadata(unittest.TestCase):
    """Tests for PluginMetadata dataclass."""

    def test_metadata_creation(self):
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test Author",
            description="A test plugin",
            hooks=["pre_phase"],
        )
        self.assertEqual(metadata.name, "test-plugin")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertIn("pre_phase", metadata.hooks)

    def test_metadata_to_dict(self):
        metadata = PluginMetadata(name="test", hooks=["pre_phase"])
        d = metadata.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertIn("hooks", d)


class TestPlugin(unittest.TestCase):
    """Tests for Plugin base class."""

    def test_plugin_defaults(self):
        plugin = Plugin()
        self.assertTrue(plugin.enabled)

    def test_plugin_hooks_return_none(self):
        plugin = Plugin()
        context = {"test": "value"}
        self.assertIsNone(plugin.pre_phase(context))
        self.assertIsNone(plugin.post_phase(context))
        self.assertIsNone(plugin.pre_model_call(context))
        self.assertIsNone(plugin.post_model_call(context))
        self.assertIsNone(plugin.on_error(context))
        self.assertIsNone(plugin.on_validation(context))


class TestSimplePlugin(unittest.TestCase):
    """Tests for SimplePlugin example."""

    def test_simple_plugin_metadata(self):
        plugin = SimplePlugin()
        self.assertEqual(plugin.metadata.name, "simple-example")
        self.assertIn("pre_phase", plugin.metadata.hooks)
        self.assertIn("post_phase", plugin.metadata.hooks)

    def test_simple_plugin_hooks(self):
        plugin = SimplePlugin()
        context = {"phase_id": "P1"}
        self.assertIsNone(plugin.pre_phase(context))
        self.assertIsNone(plugin.post_phase(context))


class TestPluginManager(unittest.TestCase):
    """Tests for PluginManager class."""

    def setUp(self):
        self.manager = PluginManager()

    def test_register_plugin(self):
        plugin = SimplePlugin()
        result = self.manager.register(plugin)
        self.assertTrue(result)
        self.assertEqual(len(self.manager.plugins), 1)

    def test_register_duplicate_plugin(self):
        plugin = SimplePlugin()
        self.manager.register(plugin)
        result = self.manager.register(plugin)
        self.assertFalse(result)
        self.assertEqual(len(self.manager.plugins), 1)

    def test_unregister_plugin(self):
        plugin = SimplePlugin()
        self.manager.register(plugin)
        result = self.manager.unregister("simple-example")
        self.assertTrue(result)
        self.assertEqual(len(self.manager.plugins), 0)

    def test_unregister_nonexistent(self):
        result = self.manager.unregister("nonexistent")
        self.assertFalse(result)

    def test_get_plugin(self):
        plugin = SimplePlugin()
        self.manager.register(plugin)
        retrieved = self.manager.get_plugin("simple-example")
        self.assertIs(retrieved, plugin)

    def test_list_plugins(self):
        plugin = SimplePlugin()
        self.manager.register(plugin)
        plugins = self.manager.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].name, "simple-example")

    def test_execute_hook(self):
        plugin = SimplePlugin()
        self.manager.register(plugin)
        context = {"phase_id": "P1"}
        result = self.manager.execute_hook("pre_phase", context)
        self.assertEqual(result, context)

    def test_execute_nonexistent_hook(self):
        context = {"test": "value"}
        result = self.manager.execute_hook("nonexistent_hook", context)
        self.assertEqual(result, context)

    def test_register_custom_plugin(self):
        class CustomPlugin(Plugin):
            def __init__(self):
                super().__init__()
                self.metadata = PluginMetadata(
                    name="custom",
                    hooks=["pre_phase"],
                )

            def pre_phase(self, context):
                context["custom"] = True
                return context

        plugin = CustomPlugin()
        self.manager.register(plugin)

        context = {"phase_id": "P1"}
        result = self.manager.execute_hook("pre_phase", context)
        self.assertTrue(result.get("custom"))

    def test_hook_error_handling(self):
        class ErrorPlugin(Plugin):
            def __init__(self):
                super().__init__()
                self.metadata = PluginMetadata(
                    name="error-plugin",
                    hooks=["pre_phase"],
                )

            def pre_phase(self, context):
                raise ValueError("Test error")

        plugin = ErrorPlugin()
        self.manager.register(plugin)

        context = {"phase_id": "P1"}
        # Should not raise, just log error
        result = self.manager.execute_hook("pre_phase", context)
        self.assertEqual(result, context)


class TestLoadFromPath(unittest.TestCase):
    """Tests for loading plugins from files."""

    def test_load_from_path(self):
        plugin_code = '''
from autobots.plugins import Plugin, PluginMetadata

class TestFilePlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="file-plugin",
            version="1.0.0",
            hooks=["pre_phase"],
        )
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "test_plugin.py"
            plugin_file.write_text(plugin_code)

            manager = PluginManager()
            result = manager.load_from_path(plugin_file)
            self.assertTrue(result)
            self.assertIn("file-plugin", manager.plugins)

    def test_load_from_nonexistent_path(self):
        manager = PluginManager()
        result = manager.load_from_path(Path("/nonexistent/plugin.py"))
        self.assertFalse(result)

    def test_load_from_directory(self):
        plugin_code = '''
from autobots.plugins import Plugin, PluginMetadata

class DirPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="dir-plugin",
            hooks=["pre_phase"],
        )
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            plugins_dir.mkdir()
            plugin_file = plugins_dir / "test_plugin.py"
            plugin_file.write_text(plugin_code)

            manager = PluginManager()
            loaded = manager.load_from_directory(plugins_dir)
            self.assertEqual(loaded, 1)
            self.assertIn("dir-plugin", manager.plugins)


class TestGlobalPluginManager(unittest.TestCase):
    """Tests for global plugin manager."""

    def test_get_plugin_manager_singleton(self):
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        self.assertIs(manager1, manager2)


class TestAvailableHooks(unittest.TestCase):
    """Tests for available hooks."""

    def test_plugin_hooks_not_empty(self):
        self.assertGreater(len(PLUGIN_HOOKS), 0)

    def test_plugin_hooks_contain_essential(self):
        essential = ["pre_phase", "post_phase", "pre_model_call", "post_model_call"]
        for hook in essential:
            self.assertIn(hook, PLUGIN_HOOKS)


if __name__ == "__main__":
    unittest.main()
