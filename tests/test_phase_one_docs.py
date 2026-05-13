import unittest
from pathlib import Path


class PhaseOneDocsTests(unittest.TestCase):
    def test_cli_contract_documents_target_command_surface(self) -> None:
        content = Path("cli-contract.md").read_text(encoding="utf-8")
        for command in ("autobots init", "autobots plan", "autobots run", "autobots resume", "autobots status", "autobots review"):
            self.assertIn(command, content)

    def test_phase_one_supporting_docs_exist(self) -> None:
        for filename in ("config-model.md", "project-compatibility.md", "adr-001-autonomy-boundaries.md", "product-definition.md"):
            self.assertTrue(Path(filename).exists(), msg=f"missing {filename}")


if __name__ == "__main__":
    unittest.main()
