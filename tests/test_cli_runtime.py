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

    @patch("autobots.cli._ensure_api_key")
    def test_run_run_no_task_shows_error(self, mock_ensure_key, console_cls=None) -> None:
        from autobots.cli import run_run

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "context").mkdir()

            with self.assertRaises(SystemExit):
                run_run(["run", str(root)])

    def test_status_no_tasks_shows_message(self) -> None:
        from autobots.cli import run_status

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "context").mkdir()

            run_status(["status", str(root)])


if __name__ == "__main__":
    unittest.main()
