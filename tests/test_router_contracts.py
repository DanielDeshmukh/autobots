import unittest

from autobots.router import AutobotRouter, ModelContractError


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


if __name__ == "__main__":
    unittest.main()
