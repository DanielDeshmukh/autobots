"""Token usage tracking and cost estimation for Autobots."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# NVIDIA NIM pricing (per 1M tokens) - as of June 2026
# These are approximate costs; actual pricing may vary
MODEL_PRICING: dict[str, dict[str, float]] = {
    # NVIDIA models
    "nvidia/llama-3.1-nemotron-70b-instruct": {"input": 0.36, "output": 0.36},
    "nvidia/llama-3.1-405b-instruct": {"input": 2.70, "output": 2.70},
    "nvidia/llama-3.1-8b-instruct": {"input": 0.04, "output": 0.04},
    "nvidia/mistral-nemo-12b-instruct": {"input": 0.02, "output": 0.02},
    # Meta models
    "meta/llama-3.1-405b-instruct": {"input": 2.70, "output": 2.70},
    "meta/llama-3.1-70b-instruct": {"input": 0.36, "output": 0.36},
    "meta/llama-3.1-8b-instruct": {"input": 0.04, "output": 0.04},
    # Default fallback
    "default": {"input": 0.50, "output": 0.50},
}


@dataclass
class TokenUsage:
    """Token usage for a single API call."""

    model_id: str
    input_tokens: int
    output_tokens: int
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class CostEstimate:
    """Cost estimate for token usage."""

    input_cost: float
    output_cost: float
    model_id: str

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost,
        }


class UsageTracker:
    """Track token usage across a session."""

    def __init__(self, session_dir: Path | None = None):
        self.usages: list[TokenUsage] = []
        self.session_dir = session_dir
        self._start_time = time.time()

    def record(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float = 0.0,
    ) -> TokenUsage:
        """Record token usage for a single call."""
        usage = TokenUsage(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
        )
        self.usages.append(usage)
        return usage

    def estimate_cost(self, usage: TokenUsage) -> CostEstimate:
        """Estimate cost for a single usage record."""
        pricing = MODEL_PRICING.get(usage.model_id, MODEL_PRICING["default"])
        input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            model_id=usage.model_id,
        )

    def total_tokens(self) -> dict[str, int]:
        """Get total tokens by type."""
        input_total = sum(u.input_tokens for u in self.usages)
        output_total = sum(u.output_tokens for u in self.usages)
        return {"input": input_total, "output": output_total, "total": input_total + output_total}

    def total_cost(self) -> float:
        """Estimate total cost across all usages."""
        return sum(self.estimate_cost(u).total_cost for u in self.usages)

    def by_model(self) -> dict[str, dict[str, Any]]:
        """Get usage grouped by model."""
        models: dict[str, dict[str, Any]] = {}
        for usage in self.usages:
            if usage.model_id not in models:
                models[usage.model_id] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                }
            models[usage.model_id]["calls"] += 1
            models[usage.model_id]["input_tokens"] += usage.input_tokens
            models[usage.model_id]["output_tokens"] += usage.output_tokens
            models[usage.model_id]["total_tokens"] += usage.total_tokens
        return models

    def summary(self) -> dict[str, Any]:
        """Get a complete summary of usage and costs."""
        totals = self.total_tokens()
        by_model = self.by_model()

        model_costs = {}
        for model_id, usage in by_model.items():
            cost = self.estimate_cost(TokenUsage(
                model_id=model_id,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
            ))
            model_costs[model_id] = cost.to_dict()

        return {
            "total_tokens": totals,
            "total_cost_estimate": self.total_cost(),
            "by_model": by_model,
            "model_costs": model_costs,
            "session_duration_s": time.time() - self._start_time,
            "call_count": len(self.usages),
        }

    def save(self, path: Path | None = None) -> None:
        """Save usage data to JSON file."""
        if path is None:
            if self.session_dir is None:
                return
            path = self.session_dir / "usage.json"

        data = {
            "usages": [u.to_dict() for u in self.usages],
            "summary": self.summary(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        """Load usage data from JSON file."""
        if not path.exists():
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        for u in data.get("usages", []):
            self.usages.append(TokenUsage(
                model_id=u["model_id"],
                input_tokens=u["input_tokens"],
                output_tokens=u["output_tokens"],
                duration_ms=u.get("duration_ms", 0),
                timestamp=u.get("timestamp", 0),
            ))


def format_cost(cost: float) -> str:
    """Format cost as a human-readable string."""
    if cost < 0.001:
        return "<$0.001"
    elif cost < 0.01:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"


def format_tokens(tokens: int) -> str:
    """Format token count as a human-readable string."""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1_000_000:
        return f"{tokens / 1000:.1f}K"
    else:
        return f"{tokens / 1_000_000:.2f}M"
