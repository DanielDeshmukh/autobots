"""Unit tests for autobots.repl package."""
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from io import StringIO

from autobots.repl.session import ReplSession, Message, SessionStats
from autobots.repl.commands import (
    CommandRegistry,
    HelpCommand,
    ClearCommand,
    CostCommand,
    CompactCommand,
    ModelCommand,
    ExitCommand,
)
from autobots.repl.runner import run_one_shot, run_piped


class TestMessage(unittest.TestCase):
    def test_to_dict(self):
        m = Message(role="user", content="hello")
        d = m.to_dict()
        self.assertEqual(d["role"], "user")
        self.assertEqual(d["content"], "hello")
        self.assertNotIn("tool_calls", d)

    def test_to_dict_with_tool_calls(self):
        m = Message(role="assistant", content="", tool_calls=[{"id": "1"}])
        d = m.to_dict()
        self.assertIn("tool_calls", d)


class TestSessionStats(unittest.TestCase):
    def test_estimated_cost(self):
        s = SessionStats(total_input_tokens=1000, total_output_tokens=500)
        cost = s.estimated_cost
        self.assertGreater(cost, 0)


class TestReplSession(unittest.TestCase):
    def test_add_message(self):
        session = ReplSession()
        msg = session.add_message("user", "hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(len(session.messages), 1)

    def test_get_api_messages(self):
        session = ReplSession(system_prompt="test prompt")
        session.add_message("user", "hi")
        msgs = session.get_api_messages()
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], "test prompt")
        self.assertEqual(msgs[1]["role"], "user")

    def test_send_slash_command(self):
        session = ReplSession()
        response = session.send("/help")
        self.assertIn("Available commands", response)

    def test_compact(self):
        session = ReplSession()
        for i in range(5):
            session.add_message("user", f"q{i}")
            session.add_message("assistant", f"a{i}")
        result = session.compact()
        self.assertIn("compacted", result)
        self.assertEqual(len(session.messages), 1)

    def test_compact_short_conversation(self):
        session = ReplSession()
        session.add_message("user", "hi")
        result = session.compact()
        self.assertIn("Nothing to compact", result)

    def test_save_and_load(self):
        tmp = tempfile.mkdtemp()
        try:
            path = Path(tmp) / "session.json"
            session = ReplSession(model="test-model", system_prompt="test")
            session.add_message("user", "hello")
            session.add_message("assistant", "world")
            session.save(path)

            loaded = ReplSession.load(path)
            self.assertEqual(loaded.model, "test-model")
            self.assertEqual(len(loaded.messages), 2)
            self.assertEqual(loaded.messages[0].content, "hello")
        finally:
            shutil.rmtree(tmp)


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.session = ReplSession()
        self.registry = CommandRegistry()

    def test_help(self):
        r = self.registry.execute("/help", self.session)
        self.assertIn("Available commands", r)

    def test_clear(self):
        self.session.add_message("user", "test")
        r = self.registry.execute("/clear", self.session)
        self.assertIn("Cleared", r)
        self.assertEqual(len(self.session.messages), 0)

    def test_cost(self):
        r = self.registry.execute("/cost", self.session)
        self.assertIn("Turns:", r)

    def test_compact(self):
        r = self.registry.execute("/compact", self.session)
        self.assertIn("Nothing to compact", r)

    def test_model_get(self):
        r = self.registry.execute("/model", self.session)
        self.assertIn("Current model:", r)

    def test_model_set(self):
        r = self.registry.execute("/model new-model", self.session)
        self.assertIn("new-model", r)
        self.assertEqual(self.session.model, "new-model")

    def test_exit(self):
        self.session._running = True
        r = self.registry.execute("/exit", self.session)
        self.assertIn("Goodbye", r)
        self.assertFalse(self.session._running)

    def test_unknown_command(self):
        r = self.registry.execute("/unknown", self.session)
        self.assertIn("Unknown command", r)


class TestRunner(unittest.TestCase):
    def test_one_shot(self):
        r = run_one_shot("hello", client=None)
        self.assertIn("Error", r)

    def test_piped(self):
        stream = StringIO("print('hello')")
        r = run_piped(input_stream=stream, client=None)
        self.assertIn("Error", r)

    def test_piped_empty(self):
        stream = StringIO("")
        r = run_piped(input_stream=stream, client=None)
        self.assertIn("No input", r)


if __name__ == "__main__":
    unittest.main()
