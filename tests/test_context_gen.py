import io
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from autobots.context_gen import check_six_file_architecture


class ContextGenerationTests(unittest.TestCase):
    def test_context_check_reports_missing_files_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context_root = root / "context"
            context_root.mkdir()
            roadmap = context_root / "roadmap.md"
            roadmap.write_text("# Existing Roadmap\n", encoding="utf-8")
            output = io.StringIO()
            console = Console(file=output, force_terminal=False)

            complete = check_six_file_architecture(console, root)

            self.assertFalse(complete)
            self.assertEqual(roadmap.read_text(encoding="utf-8"), "# Existing Roadmap\n")
            self.assertFalse((context_root / "architecture.md").exists())
            self.assertIn("architecture.md", output.getvalue())


if __name__ == "__main__":
    unittest.main()
