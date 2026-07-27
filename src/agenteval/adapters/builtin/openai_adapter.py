"""OpenAI Adapter — OpenAI compatible API adapter

Reference: ../contracts/adapter-spi.md §5.2
Capabilities: {"tools"} (supports function calling)
"""

import json
import time

from agenteval.adapters import AgentAdapter, AgentRequest, AgentResponse, ToolCallRecord


class OpenAIAdapter(AgentAdapter):
    """OpenAI compatible API adapter.

    Compatible with OpenAI / Azure OpenAI / other OpenAI-compatible services.
    Declares {"tools"} capability for function calling support.
    """

    def __init__(self, config: dict):
        self.model = config.get("model", "gpt-4")
        self.api_key = config.get("api_key_ref", config.get("api_key", "sk-placeholder"))
        self.base_url = config.get("endpoint", config.get("base_url", "https://api.openai.com/v1"))
        self.default_temperature = config.get("temperature", 0.7)
        self.default_max_tokens = config.get("max_tokens", 4096)
        self._client = None

    @property
    def adapter_type(self) -> str:
        return "openai"

    @property
    def capabilities(self) -> set[str]:
        return {"tools"}

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def execute(self, request: AgentRequest) -> AgentResponse:
        client = self._get_client()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(request.messages)

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools and "tools" in self.capabilities:
            kwargs["tools"] = request.tools

        started = time.monotonic()
        try:
            completion = await client.chat.completions.create(**kwargs)
            latency_ms = int((time.monotonic() - started) * 1000)
            choice = completion.choices[0]

            # Parse tool calls
            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append(ToolCallRecord(
                        tool_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                        result=None,
                        latency_ms=0,
                        status="success",
                    ))

            # Parse tokens
            tokens = {"prompt": 0, "completion": 0}
            if completion.usage:
                tokens = {
                    "prompt": completion.usage.prompt_tokens or 0,
                    "completion": completion.usage.completion_tokens or 0,
                }

            # Calculate cost (simplified)
            cost_usd = _estimate_cost(tokens, self.model)

            return AgentResponse(
                messages=[{"role": "assistant", "content": choice.message.content or ""}],
                final_message=choice.message.content or "",
                tool_calls=tool_calls,
                tokens=tokens,
                model=completion.model,
                finish_reason=choice.finish_reason or "stop",
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                raw_response=completion.model_dump(),
            )
        except Exception as e:
            from agenteval.core.exceptions import AdapterError
            raise AdapterError(f"OpenAI adapter error: {e}")

    def validate_config(self, config: dict) -> bool:
        return bool(config.get("model"))


def _estimate_cost(tokens: dict, model: str) -> float:
    """Rough cost estimation based on token counts and model pricing.

    Simplified pricing; real implementation would query pricing API.
    """
    prompt_tokens = tokens.get("prompt", 0)
    completion_tokens = tokens.get("completion", 0)

    # Default pricing per 1M tokens (USD)
    pricing = {
        "gpt-4": {"prompt": 30.0, "completion": 60.0},
        "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
        "gpt-4o": {"prompt": 5.0, "completion": 15.0},
        "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
    }
    model_prices = pricing.get(model, pricing.get("gpt-4o", {"prompt": 5.0, "completion": 15.0}))

    cost = (prompt_tokens * model_prices["prompt"] + completion_tokens * model_prices["completion"]) / 1_000_000
    return round(cost, 6)
