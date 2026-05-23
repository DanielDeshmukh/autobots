import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CliRuntimeGuardTests(unittest.TestCase):
    def test_parse_init_file_args_accepts_single_file(self) -> None:
        from autobots.cli import _parse_init_file_args

        self.assertEqual(_parse_init_file_args(["--file", "roadmap.md"]), ("roadmap.md",))

    def test_parse_init_file_args_defaults_to_prompt(self) -> None:
        from autobots.cli import _parse_init_file_args

        self.assertIsNone(_parse_init_file_args([]))

    @patch("autobots.cli.Console")
    def test_run_rejects_incomplete_context_setup(self, console_cls) -> None:
        from autobots.cli import run_run

        console = console_cls.return_value
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "context").mkdir()

            with patch("autobots.cli._resolve_target_project_from_args", return_value=root):
                with self.assertRaises(SystemExit):
                    run_run(["run", str(root)])

        self.assertTrue(console.print.called)

    @patch("autobots.cli.Console")
    def test_status_rejects_incomplete_context_setup(self, console_cls) -> None:
        from autobots.cli import run_status

        console = console_cls.return_value
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "context").mkdir()

            with patch("autobots.cli._resolve_target_project_from_args", return_value=root):
                with self.assertRaises(SystemExit):
                    run_status(["status", str(root)])

        self.assertTrue(console.print.called)


if __name__ == "__main__":
    unittest.main()
