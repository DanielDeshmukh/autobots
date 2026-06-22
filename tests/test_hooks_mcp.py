"""Unit tests for autobots.hooks and autobots.mcp packages."""
import unittest

from autobots.hooks.manager import HookManager, Hook, HookPoint, HookResult
from autobots.mcp.client import MCPClient, MCPTool


class TestHookResult(unittest.TestCase):
    def test_ok(self):
        r = HookResult(success=True)
        self.assertTrue(r.ok)

    def test_not_ok_abort(self):
        r = HookResult(success=True, abort=True)
        self.assertFalse(r.ok)

    def test_not_ok_failure(self):
        r = HookResult(success=False)
        self.assertFalse(r.ok)


class TestHookManager(unittest.TestCase):
    def test_register_and_get(self):
        mgr = HookManager()
        hook = Hook(name="test", point=HookPoint.PRE_TOOL, command="echo hello")
        mgr.register(hook)
        hooks = mgr.get_hooks(HookPoint.PRE_TOOL)
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].name, "test")

    def test_unregister(self):
        mgr = HookManager()
        hook = Hook(name="test", point=HookPoint.PRE_TOOL)
        mgr.register(hook)
        self.assertTrue(mgr.unregister("test"))
        self.assertEqual(len(mgr.get_hooks(HookPoint.PRE_TOOL)), 0)

    def test_unregister_not_found(self):
        mgr = HookManager()
        self.assertFalse(mgr.unregister("nonexistent"))

    def test_disabled_hook_not_executed(self):
        mgr = HookManager()
        called = []

        def callback(**kwargs):
            called.append(True)
            return HookResult(success=True)

        hook = Hook(name="test", point=HookPoint.PRE_TOOL, callback=callback, enabled=False)
        mgr.register(hook)
        mgr.execute(HookPoint.PRE_TOOL)
        self.assertEqual(len(called), 0)

    def test_callback_hook(self):
        mgr = HookManager()
        called = []

        def callback(**kwargs):
            called.append(kwargs.get("tool_name"))
            return HookResult(success=True, output="done")

        hook = Hook(name="test", point=HookPoint.PRE_TOOL, callback=callback)
        mgr.register(hook)
        results = mgr.execute(HookPoint.PRE_TOOL, tool_name="Read")
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertEqual(called[0], "Read")

    def test_abort_stops_chain(self):
        mgr = HookManager()
        call_order = []

        def hook1(**kwargs):
            call_order.append(1)
            return HookResult(success=True, abort=True)

        def hook2(**kwargs):
            call_order.append(2)
            return HookResult(success=True)

        mgr.register(Hook(name="h1", point=HookPoint.PRE_TOOL, callback=hook1))
        mgr.register(Hook(name="h2", point=HookPoint.PRE_TOOL, callback=hook2))
        mgr.execute(HookPoint.PRE_TOOL)
        self.assertEqual(call_order, [1])

    def test_exception_in_hook(self):
        mgr = HookManager()

        def bad_hook(**kwargs):
            raise ValueError("boom")

        hook = Hook(name="bad", point=HookPoint.PRE_TOOL, callback=bad_hook)
        mgr.register(hook)
        results = mgr.execute(HookPoint.PRE_TOOL)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("boom", results[0].error)


class TestMCPTool(unittest.TestCase):
    def test_to_dict(self):
        tool = MCPTool(name="test", description="desc", input_schema={"type": "object"})
        d = tool.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["description"], "desc")
        self.assertIn("inputSchema", d)


class TestMCPClient(unittest.TestCase):
    def test_init(self):
        client = MCPClient(command="echo", args=["hello"])
        self.assertEqual(client.command, "echo")
        self.assertFalse(client.connected)

    def test_list_tools_empty(self):
        client = MCPClient(command="echo")
        self.assertEqual(client.list_tools(), [])


if __name__ == "__main__":
    unittest.main()
