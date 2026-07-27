"""LLM Client module — system-internal LLM calling abstraction.

Reference: ../docs/contracts/judge-spi.md §2
"""

from __future__ import annotations

from agenteval.core.llm_client import LLMClient, LLMResponse
from agenteval.core.spi import Registry


class LLMClientRegistry(Registry[LLMClient]):
    """LLM Client unified registry.

    Usage:
        LLMClientRegistry.register("openai", OpenAILLMClient)
        client = LLMClientRegistry.create("openai", config={...})
    """

    @classmethod
    def create(cls, name: str, config: dict | None = None) -> LLMClient:
        """Create LLM client instance with config validation."""
        if name not in cls._registry:
            from agenteval.core.exceptions import AgentEvalException
            raise AgentEvalException(
                code=40601,
                message=f"Unknown LLM client: '{name}'. Available: {list(cls._registry.keys())}",
                http_status=400,
            )
        client_cls = cls._registry[name]
        client = client_cls(config or {})
        if not client.validate_config(config or {}):
            from agenteval.core.exceptions import AgentEvalException
            raise AgentEvalException(
                code=40602,
                message=f"Invalid LLM client config for '{name}'",
                http_status=400,
            )
        return client


__all__ = ["LLMClient", "LLMResponse", "LLMClientRegistry"]
