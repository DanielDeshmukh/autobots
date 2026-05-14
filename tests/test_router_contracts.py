import tempfile
import unittest
from pathlib import Path

from autobots.router import AutobotRouter, ModelContractError
from autobots.workspace import TargetProjectWorkspace


class RouterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = AutobotRouter(api_key="test-key")

    def test_validate_command_payload_accepts_expected_shape(self) -> None:
        payload = {
            "summary": "Prepared a mission brief.",
            "implementation_goals": ["Add the CLI contract."],
            "risks": ["Model returns invalid JSON."],
            "acceptance_checks": ["CLI docs exist."],
        }
        self.router.validate_command_payload(payload)

    def test_validate_specialist_payload_requires_file_shape(self) -> None:
        payload = {
            "summary": "Created a file.",
            "implementation_notes": ["Added the target file."],
            "files": [{"root": "src", "path": "main.py", "content": "print('ok')"}],
        }
        self.router.validate_specialist_payload(payload)

    def test_validate_specialist_payload_accepts_multi_root_files(self) -> None:
        payload = {
            "summary": "Created project files.",
            "implementation_notes": ["Added documentation and app code."],
            "files": [
                {"root": "app", "path": "main.tsx", "content": "export const App = () => null;"},
                {"root": "docs", "path": "guide.md", "content": "# Guide"},
            ],
        }
        self.router.validate_specialist_payload(payload)

    def test_validate_review_payload_rejects_unknown_status(self) -> None:
        payload = {
            "status": "hold",
            "summary": "Need another pass.",
            "issues": ["Unsupported status."],
        }
        with self.assertRaises(ModelContractError):
            self.router.validate_review_payload(payload)

    def test_validate_repair_payload_rejects_invalid_file_root(self) -> None:
        payload = {
            "summary": "Repaired the implementation.",
            "files": [{"root": "repo", "path": "main.py", "content": "print('ok')"}],
        }
        with self.assertRaises(ModelContractError):
            self.router.validate_repair_payload(payload)

    def test_parse_phase_line_supports_checkbox_status(self) -> None:
        phase = self.router._parse_phase_line(0, "- [ ] Build validation workflow")
        self.assertIsNotNone(phase)
        assert phase is not None
        self.assertEqual(phase.status, "PENDING")
        self.assertEqual(phase.title, "Build validation workflow")

    def test_file_entries_from_paths_supports_multi_root_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "app").mkdir()
            (root / "docs").mkdir()
            (root / "app" / "main.tsx").write_text("export const App = () => null;", encoding="utf-8")
            (root / "docs" / "guide.md").write_text("# Guide", encoding="utf-8")

            workspace = TargetProjectWorkspace(root)
            entries = self.router._file_entries_from_paths(
                [
                    str(root / "app" / "main.tsx"),
                    str(root / "docs" / "guide.md"),
                ],
                workspace,
            )

            self.assertEqual(
                entries,
                [
                    {"root": "app", "path": "main.tsx", "content": "export const App = () => null;"},
                    {"root": "docs", "path": "guide.md", "content": "# Guide"},
                ],
            )


if __name__ == "__main__":
    unittest.main()
