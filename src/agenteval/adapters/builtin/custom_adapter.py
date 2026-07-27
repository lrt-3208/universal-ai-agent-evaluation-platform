"""Custom Adapter — Python callable adapter

Reference: ../contracts/adapter-spi.md §5.3
Capabilities: set() (stateless, no tools)
"""

import asyncio

from agenteval.adapters import AgentAdapter, AgentRequest, AgentResponse


class CustomAdapter(AgentAdapter):
    """Custom function adapter.

    Accepts a Python async callable as the Agent implementation.
    Suitable for local agents, testing mocks, rapid prototyping.
    """

    def __init__(self, config: dict):
        self.handler = config.get("handler")
        self.timeout = config.get("timeout_seconds", 120)

    @property
    def adapter_type(self) -> str:
        return "custom"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        try:
            result = await asyncio.wait_for(self.handler(request), timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            from agenteval.core.exceptions import AdapterTimeoutError
            raise AdapterTimeoutError(f"Custom adapter timeout after {self.timeout}s")
        except Exception as e:
            from agenteval.core.exceptions import AdapterError
            raise AdapterError(f"Custom adapter error: {e}")

    def validate_config(self, config: dict) -> bool:
        return callable(config.get("handler"))
