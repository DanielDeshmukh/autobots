import io
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from autobots.context_gen import generate_from_readme


class ContextGenerationTests(unittest.TestCase):
    def test_generate_from_readme_preserves_existing_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Demo\n\nBuild the demo app.", encoding="utf-8")
            context_root = root / "context"
            context_root.mkdir()
            roadmap = context_root / "roadmap.md"
            roadmap.write_text("# Existing Roadmap\n", encoding="utf-8")
            console = Console(file=io.StringIO(), force_terminal=False)

            written = generate_from_readme(console, root)

            self.assertEqual(roadmap.read_text(encoding="utf-8"), "# Existing Roadmap\n")
            self.assertNotIn(roadmap, written)
            self.assertTrue((context_root / "architecture.md").exists())


if __name__ == "__main__":
    unittest.main()
