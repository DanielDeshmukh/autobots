"""Tests for cost estimation module."""

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from autobots.costs import (
    CostEstimate,
    TokenUsage,
    UsageTracker,
    format_cost,
    format_tokens,
)


class TestTokenUsage(unittest.TestCase):
    """Tests for TokenUsage dataclass."""

    def test_total_tokens(self):
        usage = TokenUsage(
            model_id="test-model",
            input_tokens=100,
            output_tokens=50,
        )
        self.assertEqual(usage.total_tokens, 150)

    def test_to_dict(self):
        usage = TokenUsage(
            model_id="test-model",
            input_tokens=100,
            output_tokens=50,
            duration_ms=123.45,
        )
        d = usage.to_dict()
        self.assertEqual(d["model_id"], "test-model")
        self.assertEqual(d["input_tokens"], 100)
        self.assertEqual(d["output_tokens"], 50)
        self.assertEqual(d["total_tokens"], 150)
        self.assertEqual(d["duration_ms"], 123.45)


class TestCostEstimate(unittest.TestCase):
    """Tests for CostEstimate dataclass."""

    def test_total_cost(self):
        estimate = CostEstimate(
            input_cost=0.001,
            output_cost=0.002,
            model_id="test-model",
        )
        self.assertAlmostEqual(estimate.total_cost, 0.003)

    def test_to_dict(self):
        estimate = CostEstimate(
            input_cost=0.001,
            output_cost=0.002,
            model_id="test-model",
        )
        d = estimate.to_dict()
        self.assertEqual(d["model_id"], "test-model")
        self.assertAlmostEqual(d["total_cost"], 0.003)


class TestUsageTracker(unittest.TestCase):
    """Tests for UsageTracker class."""

    def setUp(self):
        self.tracker = UsageTracker()

    def test_record_usage(self):
        usage = self.tracker.record(
            model_id="test-model",
            input_tokens=100,
            output_tokens=50,
            duration_ms=100.0,
        )
        self.assertEqual(len(self.tracker.usages), 1)
        self.assertEqual(usage.model_id, "test-model")

    def test_total_tokens(self):
        self.tracker.record("model1", 100, 50)
        self.tracker.record("model2", 200, 100)
        totals = self.tracker.total_tokens()
        self.assertEqual(totals["input"], 300)
        self.assertEqual(totals["output"], 150)
        self.assertEqual(totals["total"], 450)

    def test_total_cost(self):
        self.tracker.record("nvidia/llama-3.1-8b-instruct", 1000000, 1000000)
        cost = self.tracker.total_cost()
        # Should be approximately $0.04 + $0.04 = $0.08
        self.assertGreater(cost, 0)

    def test_by_model(self):
        self.tracker.record("model1", 100, 50)
        self.tracker.record("model1", 200, 100)
        self.tracker.record("model2", 300, 150)
        by_model = self.tracker.by_model()
        self.assertEqual(len(by_model), 2)
        self.assertEqual(by_model["model1"]["calls"], 2)
        self.assertEqual(by_model["model2"]["calls"], 1)

    def test_summary(self):
        self.tracker.record("model1", 100, 50)
        summary = self.tracker.summary()
        self.assertIn("total_tokens", summary)
        self.assertIn("total_cost_estimate", summary)
        self.assertIn("by_model", summary)
        self.assertEqual(summary["call_count"], 1)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "usage.json"
            self.tracker.record("model1", 100, 50)
            self.tracker.save(path)

            new_tracker = UsageTracker()
            new_tracker.load(path)
            self.assertEqual(len(new_tracker.usages), 1)
            self.assertEqual(new_tracker.usages[0].model_id, "model1")


class TestFormatting(unittest.TestCase):
    """Tests for formatting functions."""

    def test_format_cost_small(self):
        self.assertEqual(format_cost(0.0005), "<$0.001")

    def test_format_cost_medium(self):
        # Costs >= 0.01 are formatted with 2 decimal places
        self.assertEqual(format_cost(0.0123), "$0.01")

    def test_format_cost_large(self):
        self.assertEqual(format_cost(1.234), "$1.23")

    def test_format_tokens_small(self):
        self.assertEqual(format_tokens(500), "500")

    def test_format_tokens_thousands(self):
        self.assertEqual(format_tokens(1500), "1.5K")

    def test_format_tokens_millions(self):
        self.assertEqual(format_tokens(1500000), "1.50M")


if __name__ == "__main__":
    unittest.main()
