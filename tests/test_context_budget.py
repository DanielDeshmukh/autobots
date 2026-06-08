"""Tests for context window budget management."""

import unittest

from autobots.context_budget import (
    CRITICAL_THRESHOLD,
    WARN_THRESHOLD,
    MODEL_CONTEXT_WINDOWS,
    BudgetWarning,
    ContextBudgetManager,
    TokenBudget,
    estimate_tokens,
    get_model_context_window,
)


class TestTokenBudget(unittest.TestCase):
    """Tests for TokenBudget dataclass."""

    def test_basic_budget(self):
        budget = TokenBudget(
            model_id="test-model",
            context_window=128000,
            response_reserve=4096,
            system_tokens=1000,
            prompt_tokens=2000,
        )
        self.assertEqual(budget.available, 128000 - 4096)
        self.assertEqual(budget.used, 3000)
        self.assertEqual(budget.remaining, 128000 - 4096 - 3000)

    def test_usage_ratio(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=4500,
            prompt_tokens=0,
        )
        # Available = 9000, used = 4500, ratio = 0.5
        self.assertAlmostEqual(budget.usage_ratio, 0.5)

    def test_usage_ratio_overflow(self):
        budget = TokenBudget(
            model_id="test",
            context_window=1000,
            response_reserve=100,
            system_tokens=1000,
            prompt_tokens=0,
        )
        # Available = 900, used = 1000, ratio >= 1.0 (capped)
        self.assertGreaterEqual(budget.usage_ratio, 1.0)

    def test_is_warning(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=7200,  # 80% of 9000
            prompt_tokens=0,
        )
        self.assertTrue(budget.is_warning)

    def test_is_critical(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=8600,  # ~95.5% of 9000
            prompt_tokens=0,
        )
        self.assertTrue(budget.is_critical)

    def test_is_overflow(self):
        budget = TokenBudget(
            model_id="test",
            context_window=1000,
            response_reserve=100,
            system_tokens=1000,
            prompt_tokens=0,
        )
        self.assertTrue(budget.is_overflow)

    def test_to_dict(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=500,
            prompt_tokens=500,
        )
        d = budget.to_dict()
        self.assertEqual(d["model_id"], "test")
        self.assertEqual(d["available"], 9000)
        self.assertEqual(d["used"], 1000)


class TestContextBudgetManager(unittest.TestCase):
    """Tests for ContextBudgetManager class."""

    def setUp(self):
        self.manager = ContextBudgetManager()

    def test_get_context_window_known(self):
        window = self.manager.get_context_window("nvidia/llama-3.1-nemotron-70b-instruct")
        self.assertEqual(window, 128000)

    def test_get_context_window_unknown(self):
        window = self.manager.get_context_window("unknown-model")
        self.assertEqual(window, MODEL_CONTEXT_WINDOWS["default"])

    def test_create_budget(self):
        budget = self.manager.create_budget("nvidia/llama-3.1-nemotron-70b-instruct")
        self.assertEqual(budget.context_window, 128000)
        self.assertEqual(budget.response_reserve, DEFAULT_RESPONSE_RESERVE)

    def test_check_budget_warning(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=7500,  # ~83%
            prompt_tokens=0,
        )
        warnings = self.manager.check_budget(budget)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, "warning")

    def test_check_budget_critical(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=8700,  # ~96.7%
            prompt_tokens=0,
        )
        warnings = self.manager.check_budget(budget)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, "critical")

    def test_check_budget_overflow(self):
        budget = TokenBudget(
            model_id="test",
            context_window=1000,
            response_reserve=100,
            system_tokens=1000,
            prompt_tokens=0,
        )
        warnings = self.manager.check_budget(budget)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, "overflow")

    def test_check_budget_ok(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=2000,  # ~22%
            prompt_tokens=0,
        )
        warnings = self.manager.check_budget(budget)
        self.assertEqual(len(warnings), 0)

    def test_truncate_to_fit_no_truncation(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=1000,
            prompt_tokens=0,
        )
        text = "short text"
        truncated, was_truncated = self.manager.truncate_to_fit(text, budget, token_estimate=100)
        self.assertFalse(was_truncated)
        self.assertEqual(truncated, text)

    def test_truncate_to_fit_with_truncation(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=5000,
            prompt_tokens=0,
        )
        text = "x" * 40000  # ~10000 tokens
        truncated, was_truncated = self.manager.truncate_to_fit(text, budget, token_estimate=10000)
        self.assertTrue(was_truncated)
        # Should be truncated (either contains "truncated" message or is shortened)
        self.assertLess(len(truncated), len(text))

    def test_estimate_tokens(self):
        tokens = self.manager.estimate_tokens("a" * 100)
        self.assertEqual(tokens, 25)

    def test_get_summary(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=7500,
            prompt_tokens=0,
        )
        self.manager.check_budget(budget)
        summary = self.manager.get_summary()
        self.assertEqual(summary["total_warnings"], 1)
        self.assertEqual(summary["warning_count"], 1)


class TestUtilityFunctions(unittest.TestCase):
    """Tests for utility functions."""

    def test_get_model_context_window(self):
        self.assertEqual(get_model_context_window("nvidia/llama-3.1-nemotron-70b-instruct"), 128000)
        self.assertEqual(get_model_context_window("unknown"), MODEL_CONTEXT_WINDOWS["default"])

    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens("a" * 100), 25)
        self.assertEqual(estimate_tokens(""), 0)


class TestBudgetWarning(unittest.TestCase):
    """Tests for BudgetWarning dataclass."""

    def test_warning_to_dict(self):
        budget = TokenBudget(
            model_id="test",
            context_window=10000,
            response_reserve=1000,
            system_tokens=8000,
            prompt_tokens=0,
        )
        warning = BudgetWarning(
            level="warning",
            message="High usage",
            budget=budget,
            suggestion="Monitor usage",
        )
        d = warning.to_dict()
        self.assertEqual(d["level"], "warning")
        self.assertIn("budget", d)


# Import constant used in test
from autobots.context_budget import DEFAULT_RESPONSE_RESERVE


if __name__ == "__main__":
    unittest.main()
