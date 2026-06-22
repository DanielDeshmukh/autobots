"""Unit tests for autobots.review package."""
import os
import unittest

from autobots.review.git_review import (
    DiffSummary,
    DiffHunk,
    _parse_diff,
    review_diff,
)
from autobots.review.diagnostics import (
    DiagnosticCheck,
    check_api_key,
    check_python_version,
    run_doctor,
    format_doctor_results,
)


class TestDiffSummary(unittest.TestCase):
    def test_empty_diff(self):
        summary = DiffSummary()
        self.assertEqual(summary.files_changed, 0)

    def test_parse_diff(self):
        raw = (
            "diff --git a/a.py b/a.py\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n"
            "+added\n"
            " line2\n"
            "-removed\n"
        )
        summary = _parse_diff(raw)
        self.assertEqual(summary.files_changed, 1)
        self.assertEqual(summary.insertions, 1)
        self.assertEqual(summary.deletions, 1)

    def test_parse_multi_file_diff(self):
        raw = (
            "diff --git a/a.py b/a.py\n"
            "+added1\n"
            "diff --git a/b.py b/b.py\n"
            "+added2\n"
            "-removed2\n"
        )
        summary = _parse_diff(raw)
        self.assertEqual(summary.files_changed, 2)


class TestReviewDiff(unittest.TestCase):
    def test_no_changes(self):
        result = review_diff(DiffSummary())
        self.assertIn("No changes", result)

    def test_large_change(self):
        diff = DiffSummary(files_changed=1, insertions=600)
        result = review_diff(diff)
        self.assertIn("Large change", result)

    def test_many_files(self):
        diff = DiffSummary(files_changed=25, insertions=10)
        result = review_diff(diff)
        self.assertIn("Many files", result)

    def test_ok_diff(self):
        diff = DiffSummary(files_changed=2, insertions=10, deletions=5)
        result = review_diff(diff)
        self.assertIn("No issues", result)


class TestDiagnostics(unittest.TestCase):
    def test_check_api_key_set(self):
        old = os.environ.get("NVIDIA_API_KEY")
        try:
            os.environ["NVIDIA_API_KEY"] = "nvapi-test12345"
            check = check_api_key()
            self.assertTrue(check.passed)
        finally:
            if old is None:
                os.environ.pop("NVIDIA_API_KEY", None)
            else:
                os.environ["NVIDIA_API_KEY"] = old

    def test_check_api_key_missing(self):
        old = os.environ.get("NVIDIA_API_KEY")
        try:
            os.environ.pop("NVIDIA_API_KEY", None)
            check = check_api_key()
            self.assertFalse(check.passed)
        finally:
            if old is not None:
                os.environ["NVIDIA_API_KEY"] = old

    def test_check_python_version(self):
        check = check_python_version()
        self.assertTrue(check.passed)

    def test_run_doctor(self):
        checks = run_doctor()
        self.assertGreater(len(checks), 0)

    def test_format_results(self):
        checks = [DiagnosticCheck("Test", True, "ok"), DiagnosticCheck("Test2", False, "bad")]
        result = format_doctor_results(checks)
        self.assertIn("PASS", result)
        self.assertIn("FAIL", result)
        self.assertIn("1/2", result)


if __name__ == "__main__":
    unittest.main()
