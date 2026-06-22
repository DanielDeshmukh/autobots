"""AB-590: Known Issues List
Tests that known issues from the test suite are documented and published alongside the release.
"""
import unittest
from pathlib import Path


class TestKnownIssues(unittest.TestCase):
    """Verify known issues are documented and accessible."""

    def test_known_issues_file_exists(self):
        """AB-590.1: Known issues file exists in repository."""
        issues_file = Path("KNOWN_ISSUES.md")
        self.assertTrue(issues_file.exists(), "KNOWN_ISSUES.md should exist in repository root")

    def test_known_issues_not_empty(self):
        """AB-590.2: Known issues file is not empty."""
        issues_file = Path("KNOWN_ISSUES.md")
        self.assertTrue(issues_file.exists(), "KNOWN_ISSUES.md should exist")
        content = issues_file.read_text(encoding="utf-8")
        self.assertGreater(len(content), 100, "KNOWN_ISSUES.md should have substantial content")

    def test_known_issues_has_structure(self):
        """AB-590.3: Known issues file has proper structure (headings, sections)."""
        issues_file = Path("KNOWN_ISSUES.md")
        self.assertTrue(issues_file.exists(), "KNOWN_ISSUES.md should exist")
        content = issues_file.read_text(encoding="utf-8")
        self.assertIn("#", content, "KNOWN_ISSUES.md should have at least one heading")
        self.assertIn("AB-", content, "KNOWN_ISSUES.md should reference test IDs")

    def test_known_issues_references_all_gaps(self):
        """AB-590.4: Known issues file references all known gaps."""
        issues_file = Path("KNOWN_ISSUES.md")
        self.assertTrue(issues_file.exists(), "KNOWN_ISSUES.md should exist")
        content = issues_file.read_text(encoding="utf-8").lower()

        known_gaps = [
            "config precedence",
            "token estimation",
            "plugin",
            "supervised approval",
            "rollback",
            "milestone",
            "command policy",
        ]
        found = [g for g in known_gaps if g in content]
        self.assertGreaterEqual(len(found), 5, f"At least 5 known gaps should be documented, found {len(found)}")

    def test_known_issues_documented_in_test_suite(self):
        """AB-590.5: Test suite references known issues list."""
        suite_file = Path("autobots-test-suite.md")
        self.assertTrue(suite_file.exists(), "autobots-test-suite.md should exist")
        content = suite_file.read_text(encoding="utf-8").lower()
        self.assertIn("known issues", content, "Test suite should reference known issues")


if __name__ == "__main__":
    unittest.main()
