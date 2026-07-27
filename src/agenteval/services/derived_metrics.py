"""Derived Metric Provider — registry-based derived metric computation.

Reference: ../docs/phases/phase-5-report.md §4.2
Access via: DerivedMetricRegistry.get("name", trace)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DerivedMetricProvider(ABC):
    """MUST: Derived metric computation provider."""

    @abstractmethod
    def name(self) -> str:
        """Metric name identifier."""
        ...

    @abstractmethod
    def compute(self, span_tree: dict) -> float | dict:
        """Compute derived metric from trace span tree."""
        ...


class DerivedMetricRegistry:
    """Provider registry for derived metrics."""

    _providers: dict[str, DerivedMetricProvider] = {}

    @classmethod
    def register(cls, provider: DerivedMetricProvider):
        """Register a metric provider."""
        cls._providers[provider.name()] = provider

    @classmethod
    def get(cls, name: str, span_tree: dict) -> float | dict:
        """Compute a specific derived metric."""
        if name not in cls._providers:
            raise KeyError(f"Unknown derived metric: {name}")
        return cls._providers[name].compute(span_tree)

    @classmethod
    def compute_all(cls, span_tree: dict) -> dict[str, float | dict]:
        """Compute all registered derived metrics."""
        return {name: p.compute(span_tree) for name, p in cls._providers.items()}

    @classmethod
    def list_metrics(cls) -> list[str]:
        """List all registered metric names."""
        return list(cls._providers.keys())


# --- Built-in Providers ---

class SelfTimeMsProvider(DerivedMetricProvider):
    """Compute total self time (excluding children) for root span."""

    def name(self) -> str:
        return "self_time_ms"

    def compute(self, span_tree: dict) -> float:
        if not span_tree:
            return 0.0
        duration = span_tree.get("duration_ms", 0)
        children = span_tree.get("children", [])
        child_duration = sum(c.get("duration_ms", 0) for c in children)
        return max(0, duration - child_duration)


class TotalTokensProvider(DerivedMetricProvider):
    """Compute total tokens from all llm_call spans."""

    def name(self) -> str:
        return "total_tokens"

    def compute(self, span_tree: dict) -> dict:
        total_prompt = 0
        total_completion = 0

        def _walk(span: dict):
            nonlocal total_prompt, total_completion
            if span.get("span_type") == "llm_call":
                tokens = span.get("output_data", {}).get("tokens", {})
                total_prompt += tokens.get("prompt", 0)
                total_completion += tokens.get("completion", 0)
            for child in span.get("children", []):
                _walk(child)

        if span_tree:
            _walk(span_tree)
        return {"prompt": total_prompt, "completion": total_completion, "total": total_prompt + total_completion}


class ToolSuccessRateProvider(DerivedMetricProvider):
    """Compute tool call success rate."""

    def name(self) -> str:
        return "tool_success_rate"

    def compute(self, span_tree: dict) -> float:
        total = 0
        success = 0

        def _walk(span: dict):
            nonlocal total, success
            if span.get("span_type") == "tool_call":
                total += 1
                if span.get("status") == "ok":
                    success += 1
            for child in span.get("children", []):
                _walk(child)

        if span_tree:
            _walk(span_tree)
        return round(success / total, 4) if total > 0 else 1.0


def register_builtin_providers():
    """Register all built-in derived metric providers."""
    DerivedMetricRegistry.register(SelfTimeMsProvider())
    DerivedMetricRegistry.register(TotalTokensProvider())
    DerivedMetricRegistry.register(ToolSuccessRateProvider())
