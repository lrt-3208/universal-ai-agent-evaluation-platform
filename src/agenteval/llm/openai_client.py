"""OpenAI-compatible LLM Client implementation.

Reference: ../docs/contracts/judge-spi.md §5.1
Supports any OpenAI-compatible API (OpenAI, Azure, local models via vLLM, etc.)
"""

from __future__ import annotations

import structlog

from agenteval.core.llm_client import LLMClient, LLMResponse

logger = structlog.get_logger()

# Simple cost estimation (per 1K tokens)
_MODEL_COSTS = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}


class OpenAILLMClient(LLMClient):
    """OpenAI-compatible LLM Client.

    Config:
        api_key: API key (or set OPENAI_API_KEY env var)
        base_url: Custom base URL for compatible APIs
        default_model: Default model name (default: "gpt-4o")
    """

    def __init__(self, config: dict):
        self._config = config
        self._api_key = config.get("api_key", "")
        self._base_url = config.get("base_url")
        self._default_model = config.get("default_model", "gpt-4o")
        self._client = None

    def _get_client(self):
        """Lazy-init AsyncOpenAI client."""
        if self._client is None:
            import openai
            kwargs = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Execute single LLM completion call."""
        client = self._get_client()
        use_model = model or self._default_model

        kwargs = {
            "model": use_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        completion = await client.chat.completions.create(**kwargs)

        choice = completion.choices[0]
        usage = completion.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = self._estimate_cost(use_model, prompt_tokens, completion_tokens)

        return LLMResponse(
            content=choice.message.content or "",
            model=completion.model,
            tokens={"prompt": prompt_tokens, "completion": completion_tokens},
            finish_reason=choice.finish_reason or "stop",
            cost_usd=cost,
            raw={"id": completion.id, "model": completion.model},
        )

    def validate_config(self, config: dict) -> bool:
        """Validate: api_key must be present or OPENAI_API_KEY env var set."""
        import os
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        return bool(api_key)

    @property
    def provider(self) -> str:
        return "openai"

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on model pricing."""
        costs = _MODEL_COSTS.get(model, {"prompt": 0.005, "completion": 0.015})
        return round(
            (prompt_tokens / 1000 * costs["prompt"]) +
            (completion_tokens / 1000 * costs["completion"]),
            6,
        )
