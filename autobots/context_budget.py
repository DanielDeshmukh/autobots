"""Context window budget management for Autobots."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("autobots")

# Model context window sizes (approximate)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # NVIDIA models
    "nvidia/llama-3.1-nemotron-70b-instruct": 128000,
    "nvidia/llama-3.1-405b-instruct": 128000,
    "nvidia/llama-3.1-8b-instruct": 128000,
    "nvidia/mistral-nemo-12b-instruct": 128000,
    # Meta models
    "meta/llama-3.1-405b-instruct": 128000,
    "meta/llama-3.1-70b-instruct": 128000,
    "meta/llama-3.1-8b-instruct": 128000,
    # Default (conservative)
    "default": 32000,
}

# Reserved tokens for response generation
DEFAULT_RESPONSE_RESERVE = 4096

# Warning thresholds
WARN_THRESHOLD = 0.8  # Warn at 80% usage
CRITICAL_THRESHOLD = 0.95  # Critical at 95% usage


@dataclass
class TokenBudget:
    """Token budget for a model call."""

    model_id: str
    context_window: int
    response_reserve: int
    system_tokens: int = 0
    prompt_tokens: int = 0

    @property
    def available(self) -> int:
        """Available tokens for prompt after reserves."""
        return self.context_window - self.response_reserve

    @property
    def used(self) -> int:
        """Total tokens used (system + prompt)."""
        return self.system_tokens + self.prompt_tokens

    @property
    def remaining(self) -> int:
        """Remaining tokens before hitting limit."""
        return self.available - self.used

    @property
    def usage_ratio(self) -> float:
        """Ratio of used to available tokens."""
        if self.available <= 0:
            return 1.0
        return min(1.0, self.used / self.available)

    @property
    def is_warning(self) -> bool:
        """Check if usage is above warning threshold."""
        return self.usage_ratio >= WARN_THRESHOLD

    @property
    def is_critical(self) -> bool:
        """Check if usage is above critical threshold."""
        return self.usage_ratio >= CRITICAL_THRESHOLD

    @property
    def is_overflow(self) -> bool:
        """Check if usage exceeds available tokens."""
        return self.used > self.available

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "context_window": self.context_window,
            "response_reserve": self.response_reserve,
            "system_tokens": self.system_tokens,
            "prompt_tokens": self.prompt_tokens,
            "available": self.available,
            "used": self.used,
            "remaining": self.remaining,
            "usage_ratio": self.usage_ratio,
        }


@dataclass
class BudgetWarning:
    """Warning about context window usage."""

    level: str  # "warning", "critical", "overflow"
    message: str
    budget: TokenBudget
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "budget": self.budget.to_dict(),
            "suggestion": self.suggestion,
        }


class ContextBudgetManager:
    """Manages context window budgets for model calls."""

    def __init__(
        self,
        response_reserve: int = DEFAULT_RESPONSE_RESERVE,
        warn_threshold: float = WARN_THRESHOLD,
        critical_threshold: float = CRITICAL_THRESHOLD,
    ):
        self.response_reserve = response_reserve
        self.warn_threshold = warn_threshold
        self.critical_threshold = critical_threshold
        self.warnings: list[BudgetWarning] = []

    def get_context_window(self, model_id: str) -> int:
        """Get context window size for a model."""
        return MODEL_CONTEXT_WINDOWS.get(model_id, MODEL_CONTEXT_WINDOWS["default"])

    def create_budget(self, model_id: str) -> TokenBudget:
        """Create a token budget for a model."""
        context_window = self.get_context_window(model_id)
        return TokenBudget(
            model_id=model_id,
            context_window=context_window,
            response_reserve=self.response_reserve,
        )

    def check_budget(self, budget: TokenBudget) -> list[BudgetWarning]:
        """Check budget and generate warnings."""
        warnings = []

        if budget.is_overflow:
            warnings.append(BudgetWarning(
                level="overflow",
                message=f"Context overflow: {budget.used} tokens used, {budget.available} available",
                budget=budget,
                suggestion="Reduce prompt size or use a model with larger context window",
            ))
        elif budget.is_critical:
            warnings.append(BudgetWarning(
                level="critical",
                message=f"Context nearly full: {budget.usage_ratio:.0%} used ({budget.remaining} tokens remaining)",
                budget=budget,
                suggestion="Consider truncating or summarizing older content",
            ))
        elif budget.is_warning:
            warnings.append(BudgetWarning(
                level="warning",
                message=f"Context usage high: {budget.usage_ratio:.0%} used ({budget.remaining} tokens remaining)",
                budget=budget,
                suggestion="Monitor usage to avoid overflow",
            ))

        self.warnings.extend(warnings)
        return warnings

    def truncate_to_fit(
        self,
        text: str,
        budget: TokenBudget,
        preserve_start: bool = True,
        token_estimate: int | None = None,
    ) -> tuple[str, bool]:
        """Truncate text to fit within budget.

        Args:
            text: Text to truncate
            budget: Token budget to fit within
            preserve_start: If True, preserve start (truncate end); if False, preserve end
            token_estimate: Optional pre-computed token count (chars // 4 estimate used if None)

        Returns:
            Tuple of (truncated_text, was_truncated)
        """
        if token_estimate is None:
            # Rough estimate: 1 token ≈ 4 characters
            token_estimate = len(text) // 4

        remaining = budget.remaining

        if token_estimate <= remaining:
            return text, False

        # Calculate how many characters we can keep
        # Leave some buffer for safety
        chars_to_keep = (remaining - 100) * 4

        if chars_to_keep <= 0:
            # Budget is essentially full, return minimal text
            return "...", True

        if preserve_start:
            truncated = text[:chars_to_keep] + "\n\n[Context truncated to fit token budget]"
        else:
            truncated = f"[Context truncated to fit token budget]\n\n{text[-chars_to_keep:]}"

        logger.warning(
            "Truncated context from %d to ~%d tokens for %s",
            token_estimate,
            remaining,
            budget.model_id,
        )

        return truncated, True

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough estimate)."""
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all warnings."""
        return {
            "total_warnings": len(self.warnings),
            "warning_count": sum(1 for w in self.warnings if w.level == "warning"),
            "critical_count": sum(1 for w in self.warnings if w.level == "critical"),
            "overflow_count": sum(1 for w in self.warnings if w.level == "overflow"),
        }


def get_model_context_window(model_id: str) -> int:
    """Get context window size for a model."""
    return MODEL_CONTEXT_WINDOWS.get(model_id, MODEL_CONTEXT_WINDOWS["default"])


def estimate_tokens(text: str) -> int:
    """Quick token estimation."""
    return len(text) // 4
