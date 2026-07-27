"""LLMClient interface - unified LLM calling abstraction

Reference: ../docs/contracts/judge-spi.md §2
Used by: Phase 4 Judge (LLM Judge), system internal LLM consumption.
Separated from AgentAdapter (which handles external agent calls).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """Standardized LLM response"""

    content: str
    model: str = ""
    tokens: dict = field(default_factory=dict)  # {"prompt": N, "completion": M}
    finish_reason: str = "stop"
    cost_usd: float = 0.0
    raw: dict | None = None


class LLMClient(ABC):
    """Abstract LLM client interface for system-internal LLM calls.

    MUST: System internal LLM calls (Judge, etc.) use this unified interface.
    Separated from AgentAdapter (which handles external agent calls).
    """

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Execute single LLM call, return response.

        Args:
            prompt: The prompt text to send
            model: Model name (None = use client default)
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum tokens in response
            response_format: e.g. {"type": "json_object"} for JSON output

        Returns:
            LLMResponse with content, model, tokens, finish_reason, cost_usd
        """
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """Validate client configuration (e.g., API key present)"""
        ...

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return provider name (e.g., 'openai', 'volcengine', 'anthropic')"""
        ...
