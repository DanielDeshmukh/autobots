"""Unit tests for autobots.context package."""
import tempfile
import shutil
import unittest
from pathlib import Path

from autobots.context.tokenizer import estimate_tokens, count_tokens
from autobots.context.manager import ContextManager, ContextMessage
from autobots.context.claude_md import load_claude_md


class TestTokenizer(unittest.TestCase):
    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("a" * 100), 25)

    def test_count_tokens(self):
        tokens = count_tokens("hello world")
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 20)


class TestContextMessage(unittest.TestCase):
    def test_auto_tokens(self):
        msg = ContextMessage(role="user", content="hello")
        self.assertEqual(msg.tokens, 1)

    def test_explicit_tokens(self):
        msg = ContextMessage(role="user", content="hello", tokens=10)
        self.assertEqual(msg.tokens, 10)


class TestContextManager(unittest.TestCase):
    def test_add_message(self):
        mgr = ContextManager()
        msg = mgr.add("user", "hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(len(mgr.messages), 1)

    def test_total_tokens(self):
        mgr = ContextManager()
        mgr.add("user", "a" * 100)
        mgr.add("assistant", "b" * 100)
        self.assertEqual(mgr.total_tokens, 50)

    def test_remaining_tokens(self):
        mgr = ContextManager(max_tokens=100)
        mgr.add("user", "a" * 100)
        self.assertEqual(mgr.remaining_tokens, 75)

    def test_usage_ratio(self):
        mgr = ContextManager(max_tokens=100)
        mgr.add("user", "a" * 100)
        self.assertAlmostEqual(mgr.usage_ratio, 0.25)

    def test_should_compact(self):
        mgr = ContextManager(max_tokens=100, compact_threshold=0.5)
        mgr.add("user", "a" * 200)
        self.assertTrue(mgr.should_compact)

    def test_should_not_compact(self):
        mgr = ContextManager(max_tokens=1000)
        mgr.add("user", "hello")
        self.assertFalse(mgr.should_compact)

    def test_compact(self):
        mgr = ContextManager()
        for i in range(20):
            mgr.add("user", f"question {i}")
            mgr.add("assistant", f"answer {i}")
        result = mgr.compact(keep_recent=4)
        self.assertIn("Compacted", result)
        self.assertEqual(len(mgr.messages), 5)

    def test_compact_short(self):
        mgr = ContextManager()
        mgr.add("user", "hi")
        result = mgr.compact()
        self.assertIn("Nothing to compact", result)

    def test_get_messages(self):
        mgr = ContextManager()
        mgr.add("user", "hello")
        msgs = mgr.get_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["role"], "user")

    def test_clear(self):
        mgr = ContextManager()
        mgr.add("user", "hello")
        mgr.clear()
        self.assertEqual(len(mgr.messages), 0)

    def test_save_load(self):
        mgr = ContextManager(max_tokens=64000)
        mgr.add("user", "hello")
        data = mgr.to_dict()
        loaded = ContextManager.from_dict(data)
        self.assertEqual(loaded.max_tokens, 64000)
        self.assertEqual(len(loaded.messages), 1)


class TestClaudeMd(unittest.TestCase):
    def test_load_claude_md_no_file(self):
        tmp = tempfile.mkdtemp()
        try:
            result = load_claude_md(tmp)
            self.assertEqual(result, "")
        finally:
            shutil.rmtree(tmp)

    def test_load_claude_md_found(self):
        tmp = tempfile.mkdtemp()
        try:
            (Path(tmp) / "CLAUDE.md").write_text("test instructions")
            result = load_claude_md(tmp)
            self.assertIn("test instructions", result)
        finally:
            shutil.rmtree(tmp)

    def test_load_claude_md_hierarchy(self):
        tmp = tempfile.mkdtemp()
        try:
            root = Path(tmp)
            sub = root / "project"
            sub.mkdir()
            (root / "CLAUDE.md").write_text("root instructions")
            (sub / "CLAUDE.md").write_text("project instructions")
            result = load_claude_md(sub)
            self.assertIn("root instructions", result)
            self.assertIn("project instructions", result)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
