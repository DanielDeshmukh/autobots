"""Unit tests for autobots.tools package."""
import os
import tempfile
import shutil
import unittest
from pathlib import Path

from autobots.tools.base import Tool, ToolResult, ToolStatus
from autobots.tools.read import ReadTool
from autobots.tools.write import WriteTool
from autobots.tools.edit import EditTool
from autobots.tools.glob import GlobTool
from autobots.tools.grep import GrepTool
from autobots.tools.registry import ToolRegistry
from autobots.tools.permissions import PermissionConfig, PermissionChecker, Permission, PermissionRule
from autobots.tools.formatting import format_tool_result, format_tool_call


class TestToolResult(unittest.TestCase):
    def test_success(self):
        r = ToolResult.success("ok")
        self.assertTrue(r.ok)
        self.assertEqual(r.output, "ok")
        self.assertEqual(r.status, ToolStatus.OK)

    def test_failure(self):
        r = ToolResult.failure("bad")
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "bad")
        self.assertEqual(r.status, ToolStatus.ERROR)

    def test_denied(self):
        r = ToolResult.denied("no")
        self.assertFalse(r.ok)
        self.assertEqual(r.status, ToolStatus.DENIED)

    def test_metadata(self):
        r = ToolResult.success("ok", key="val")
        self.assertEqual(r.metadata["key"], "val")


class TestReadTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tool = ReadTool()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_read_file(self):
        p = Path(self.tmp) / "test.txt"
        p.write_text("line1\nline2\nline3")
        r = self.tool.run(file_path=str(p))
        self.assertTrue(r.ok)
        self.assertIn("1: line1", r.output)
        self.assertIn("2: line2", r.output)

    def test_read_offset_limit(self):
        p = Path(self.tmp) / "test.txt"
        p.write_text("a\nb\nc\nd\ne")
        r = self.tool.run(file_path=str(p), offset=2, limit=2)
        self.assertTrue(r.ok)
        self.assertIn("2: b", r.output)
        self.assertIn("3: c", r.output)
        self.assertNotIn("1: a", r.output)

    def test_read_not_found(self):
        r = self.tool.run(file_path="/nonexistent/file.txt")
        self.assertFalse(r.ok)

    def test_read_directory(self):
        r = self.tool.run(file_path=self.tmp)
        self.assertFalse(r.ok)

    def test_read_binary_image(self):
        p = Path(self.tmp) / "test.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        r = self.tool.run(file_path=str(p))
        self.assertTrue(r.ok)
        self.assertIn("Image file", r.output)


class TestWriteTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tool = WriteTool()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_write_file(self):
        p = Path(self.tmp) / "out.txt"
        r = self.tool.run(file_path=str(p), content="hello")
        self.assertTrue(r.ok)
        self.assertEqual(p.read_text(), "hello")

    def test_write_creates_dirs(self):
        p = Path(self.tmp) / "a" / "b" / "c.txt"
        r = self.tool.run(file_path=str(p), content="deep")
        self.assertTrue(r.ok)
        self.assertEqual(p.read_text(), "deep")

    def test_write_overwrite(self):
        p = Path(self.tmp) / "out.txt"
        self.tool.run(file_path=str(p), content="first")
        r = self.tool.run(file_path=str(p), content="second")
        self.assertTrue(r.ok)
        self.assertEqual(p.read_text(), "second")

    def test_write_missing_content(self):
        r = self.tool.run(file_path=str(Path(self.tmp) / "x.txt"))
        self.assertFalse(r.ok)

    def test_write_allowed_paths(self):
        allowed = WriteTool(allowed_paths=[self.tmp])
        p = Path(self.tmp) / "ok.txt"
        r = allowed.run(file_path=str(p), content="yes")
        self.assertTrue(r.ok)

    def test_write_denied_outside_paths(self):
        allowed = WriteTool(allowed_paths=["/other/dir"])
        p = Path(self.tmp) / "no.txt"
        r = allowed.run(file_path=str(p), content="no")
        self.assertEqual(r.status, ToolStatus.DENIED)


class TestEditTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tool = EditTool()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_edit_replace(self):
        p = Path(self.tmp) / "test.txt"
        p.write_text("hello world")
        r = self.tool.run(file_path=str(p), old_string="world", new_string="python")
        self.assertTrue(r.ok)
        self.assertEqual(p.read_text(), "hello python")
        self.assertEqual(r.metadata["replacements"], 1)

    def test_edit_not_found(self):
        p = Path(self.tmp) / "test.txt"
        p.write_text("hello")
        r = self.tool.run(file_path=str(p), old_string="xyz", new_string="abc")
        self.assertFalse(r.ok)

    def test_edit_multiple_without_flag(self):
        p = Path(self.tmp) / "test.txt"
        p.write_text("a b a b a")
        r = self.tool.run(file_path=str(p), old_string="a", new_string="x")
        self.assertFalse(r.ok)

    def test_edit_replace_all(self):
        p = Path(self.tmp) / "test.txt"
        p.write_text("a b a b a")
        r = self.tool.run(
            file_path=str(p), old_string="a", new_string="x", replace_all=True
        )
        self.assertTrue(r.ok)
        self.assertEqual(p.read_text(), "x b x b x")
        self.assertEqual(r.metadata["replacements"], 3)

    def test_edit_same_strings(self):
        r = self.tool.run(file_path="x", old_string="a", new_string="a")
        self.assertFalse(r.ok)

    def test_edit_file_not_found(self):
        r = self.tool.run(file_path="/no/such/file", old_string="a", new_string="b")
        self.assertFalse(r.ok)


class TestGlobTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tool = GlobTool()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_glob_find(self):
        Path(self.tmp, "a.py").write_text("")
        Path(self.tmp, "b.py").write_text("")
        r = self.tool.run(pattern="*.py", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 2)

    def test_glob_recursive(self):
        sub = Path(self.tmp) / "sub"
        sub.mkdir()
        Path(sub, "deep.py").write_text("")
        r = self.tool.run(pattern="**/*.py", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 1)

    def test_glob_no_match(self):
        r = self.tool.run(pattern="*.xyz", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 0)

    def test_glob_invalid_path(self):
        r = self.tool.run(pattern="*", path="/nonexistent")
        self.assertFalse(r.ok)


class TestGrepTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tool = GrepTool()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_grep_find(self):
        p = Path(self.tmp) / "test.py"
        p.write_text("def foo():\n    pass\ndef bar():\n    pass")
        r = self.tool.run(pattern=r"def \w+", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 2)

    def test_grep_with_include(self):
        Path(self.tmp, "a.py").write_text("hello")
        Path(self.tmp, "b.txt").write_text("hello")
        r = self.tool.run(pattern="hello", path=self.tmp, include="*.py")
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 1)

    def test_grep_no_match(self):
        Path(self.tmp, "a.py").write_text("hello")
        r = self.tool.run(pattern="xyz", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 0)

    def test_grep_invalid_regex(self):
        r = self.tool.run(pattern="[invalid", path=self.tmp)
        self.assertFalse(r.ok)


class TestToolRegistry(unittest.TestCase):
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = ReadTool()
        reg.register(tool)
        self.assertIs(reg.get("read"), tool)

    def test_list_names(self):
        reg = ToolRegistry()
        reg.register(ReadTool())
        reg.register(WriteTool())
        self.assertEqual(sorted(reg.list_names()), ["read", "write"])

    def test_run_tool(self):
        reg = ToolRegistry()
        reg.register(ReadTool())
        r = reg.run("read", file_path="/nonexistent")
        self.assertFalse(r.ok)

    def test_run_unknown(self):
        reg = ToolRegistry()
        r = reg.run("unknown")
        self.assertFalse(r.ok)

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register(ReadTool())
        t = reg.unregister("read")
        self.assertIsNotNone(t)
        self.assertIsNone(reg.get("read"))

    def test_schemas(self):
        reg = ToolRegistry()
        reg.register(ReadTool())
        schemas = reg.to_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["name"], "read")

    def test_contains(self):
        reg = ToolRegistry()
        reg.register(ReadTool())
        self.assertIn("read", reg)
        self.assertNotIn("write", reg)

    def test_len(self):
        reg = ToolRegistry()
        reg.register(ReadTool())
        reg.register(WriteTool())
        self.assertEqual(len(reg), 2)


class TestPermissions(unittest.TestCase):
    def test_allow_rule(self):
        config = PermissionConfig(
            rules=[PermissionRule("Read", Permission.ALLOW)]
        )
        checker = PermissionChecker(config)
        self.assertEqual(checker.check("Read"), Permission.ALLOW)

    def test_deny_rule(self):
        config = PermissionConfig(
            rules=[PermissionRule("Bash", Permission.DENY, args_pattern="rm *")]
        )
        checker = PermissionChecker(config)
        self.assertEqual(
            checker.check("Bash", {"command": "rm -rf /"}), Permission.DENY
        )

    def test_default_ask(self):
        config = PermissionConfig()
        checker = PermissionChecker(config)
        self.assertEqual(checker.check("anything"), Permission.ASK)

    def test_session_always_allow(self):
        config = PermissionConfig()
        checker = PermissionChecker(config)
        checker.always_allow("Read")
        self.assertEqual(checker.check("Read"), Permission.ALLOW)

    def test_clear_session(self):
        config = PermissionConfig()
        checker = PermissionChecker(config)
        checker.always_allow("Read")
        checker.clear_session()
        self.assertEqual(checker.check("Read"), Permission.ASK)


class TestFormatting(unittest.TestCase):
    def test_format_ok(self):
        r = ToolResult.success("output")
        self.assertEqual(format_tool_result(r, "tool"), "[tool] output")

    def test_format_error(self):
        r = ToolResult.failure("err")
        self.assertIn("ERROR: err", format_tool_result(r, "t"))

    def test_format_denied(self):
        r = ToolResult.denied("no")
        self.assertIn("DENIED: no", format_tool_result(r, "t"))

    def test_format_tool_call(self):
        s = format_tool_call("read", {"file_path": "/a/b.txt"})
        self.assertIn("read", s)
        self.assertIn("file_path=/a/b.txt", s)


if __name__ == "__main__":
    unittest.main()
