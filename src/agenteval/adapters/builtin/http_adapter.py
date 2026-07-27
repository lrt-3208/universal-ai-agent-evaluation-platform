"""HTTP Adapter — generic HTTP Agent adapter

Reference: ../contracts/adapter-spi.md §5.1
Capabilities: set() (stateless, no tools)
"""

import time

import httpx

from agenteval.adapters import AgentAdapter, AgentRequest, AgentResponse, ToolCallRecord


class HTTPAdapter(AgentAdapter):
    """Generic HTTP Agent adapter.

    Suitable for custom Agent services via HTTP API.
    Sends AgentRequest as JSON POST body, parses response as AgentResponse.
    """

    def __init__(self, config: dict):
        self.endpoint = config.get("endpoint", "")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout_seconds", 120)
        self.api_key_ref = config.get("api_key_ref")

    @property
    def adapter_type(self) -> str:
        return "http"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        payload = {
            "messages": request.messages,
            "system_prompt": request.system_prompt,
            "tools": request.tools,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "metadata": request.metadata,
        }
        headers = {**self.headers, "Content-Type": "application/json"}
        if self.api_key_ref:
            headers["Authorization"] = f"Bearer {self.api_key_ref}"

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.endpoint}/chat",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                latency_ms = int((time.monotonic() - started) * 1000)
                data = resp.json()

                return AgentResponse(
                    messages=data.get("messages", [{"role": "assistant", "content": data.get("response", "")}]),
                    final_message=data.get("response", ""),
                    tool_calls=[ToolCallRecord(**tc) for tc in data.get("tool_calls", [])],
                    tokens=data.get("tokens", {"prompt": 0, "completion": 0}),
                    model=data.get("model", "unknown"),
                    finish_reason=data.get("finish_reason", "stop"),
                    latency_ms=latency_ms,
                    cost_usd=data.get("cost_usd", 0.0),
                    raw_response=data,
                )
        except httpx.TimeoutException:
            from agenteval.core.exceptions import AdapterTimeoutError
            raise AdapterTimeoutError(f"HTTP adapter timeout after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            from agenteval.core.exceptions import AdapterError
            raise AdapterError(f"HTTP adapter error: {e.response.status_code} {e.response.text[:200]}")
        except Exception as e:
            from agenteval.core.exceptions import AdapterError
            raise AdapterError(f"HTTP adapter error: {e}")

    def validate_config(self, config: dict) -> bool:
        endpoint = config.get("endpoint", "")
        return bool(endpoint) and endpoint.startswith("http")
