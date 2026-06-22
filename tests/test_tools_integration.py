"""Integration test: read → edit → verify → read again."""
import tempfile
import shutil
import unittest
from pathlib import Path

from autobots.tools.read import ReadTool
from autobots.tools.write import WriteTool
from autobots.tools.edit import EditTool
from autobots.tools.glob import GlobTool
from autobots.tools.grep import GrepTool
from autobots.tools.registry import ToolRegistry


class TestToolsIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.registry = ToolRegistry()
        self.registry.register(ReadTool())
        self.registry.register(WriteTool())
        self.registry.register(EditTool())
        self.registry.register(GlobTool())
        self.registry.register(GrepTool())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_read_edit_verify_read(self):
        file_path = str(Path(self.tmp) / "project" / "main.py")
        Path(file_path).parent.mkdir(parents=True)
        Path(file_path).write_text("def hello():\n    print('hello')\n")

        r = self.registry.run("read", file_path=file_path)
        self.assertTrue(r.ok)
        self.assertIn("def hello", r.output)

        r = self.registry.run(
            "edit",
            file_path=file_path,
            old_string="print('hello')",
            new_string="print('world')",
        )
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["replacements"], 1)

        r = self.registry.run("read", file_path=file_path)
        self.assertTrue(r.ok)
        self.assertIn("print('world')", r.output)
        self.assertNotIn("print('hello')", r.output)

    def test_write_glob_grep(self):
        for name in ["a.py", "b.py", "c.txt"]:
            Path(self.tmp, name).write_text(f"# {name}\nvalue = 1\n")

        r = self.registry.run("glob", pattern="*.py", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 2)

        r = self.registry.run("grep", pattern=r"value = \d+", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 3)

    def test_edit_replace_all_workflow(self):
        file_path = str(Path(self.tmp) / "config.py")
        Path(file_path).write_text("DEBUG = True\nLOG_LEVEL = DEBUG\nDEBUG = False\n")

        r = self.registry.run(
            "edit",
            file_path=file_path,
            old_string="DEBUG",
            new_string="VERBOSE",
            replace_all=True,
        )
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["replacements"], 3)

        r = self.registry.run("read", file_path=file_path)
        self.assertTrue(r.ok)
        self.assertNotIn("DEBUG", r.output)
        self.assertIn("VERBOSE", r.output)

    def test_write_create_nested_dirs(self):
        file_path = str(Path(self.tmp) / "a" / "b" / "c" / "deep.txt")
        r = self.registry.run("write", file_path=file_path, content="nested content")
        self.assertTrue(r.ok)
        self.assertEqual(Path(file_path).read_text(), "nested content")

    def test_full_project_workflow(self):
        src = Path(self.tmp) / "src"
        src.mkdir()
        (src / "utils.py").write_text("def add(a, b):\n    return a + b\n")
        (src / "main.py").write_text("from utils import add\nresult = add(1, 2)\n")

        r = self.registry.run("glob", pattern="**/*.py", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 2)

        r = self.registry.run("grep", pattern=r"def add", path=self.tmp)
        self.assertTrue(r.ok)
        self.assertEqual(r.metadata["count"], 1)

        r = self.registry.run(
            "edit",
            file_path=str(src / "utils.py"),
            old_string="return a + b",
            new_string="return a + b + 0",
        )
        self.assertTrue(r.ok)

        r = self.registry.run("read", file_path=str(src / "utils.py"))
        self.assertTrue(r.ok)
        self.assertIn("return a + b + 0", r.output)


if __name__ == "__main__":
    unittest.main()
