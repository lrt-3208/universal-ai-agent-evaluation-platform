"""Agent Adapter SPI — base interface, data structures, and registry

Reference: ../contracts/adapter-spi.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Type

from agenteval.core.spi import Registry


# ============================================================
# Data Structures (MUST — from adapter-spi.md §2.2-2.4)
# ============================================================

@dataclass
class ToolCallRecord:
    """Single tool call record"""
    tool_name: str
    arguments: dict
    result: dict | None = None
    latency_ms: int = 0
    status: str = "success"  # "success" | "error" | "timeout"


@dataclass
class AgentRequest:
    """Request sent to Agent"""
    messages: list[dict]              # Stateless: full history; Stateful: initial message
    system_prompt: str | None = None  # System prompt
    tools: list[dict] | None = None   # Tool definitions (declaration only)
    temperature: float = 0.7
    max_tokens: int = 4096
    metadata: dict = field(default_factory=dict)  # memory, context, session_id, etc.


@dataclass
class AgentResponse:
    """Response from Agent"""
    messages: list[dict]              # New messages (assistant reply + tool results)
    final_message: str                # Final reply text
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    tokens: dict = field(default_factory=dict)    # {"prompt": N, "completion": M}
    model: str = "unknown"
    finish_reason: str = "stop"       # "stop" | "tool_calls" | "length" | "error"
    latency_ms: int = 0
    cost_usd: float = 0.0
    raw_response: dict | None = None


# ============================================================
# Base Interface (MUST — from adapter-spi.md §2.1)
# ============================================================

class AgentAdapter(ABC):
    """Agent adapter base interface.

    Only responsible for Agent communication.
    Not aware of Trace / Judge / Metrics / Report.
    This interface MUST remain stable long-term.
    New capabilities are declared via `capabilities` set, not added to the interface.
    """

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute Agent call, return response."""
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """Validate adapter configuration."""
        ...

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Adapter type identifier."""
        ...

    @property
    def capabilities(self) -> set[str]:
        """Declare capabilities supported by this adapter. Default: empty set.

        Defined capability identifiers (extensible):
          - stateful: Agent manages session state
          - tools: Agent supports tool calling
          - streaming: Agent supports streaming (MVP not implemented)
          - vision: Agent supports image input (MVP not implemented)
          - audio: Agent supports audio input (MVP not implemented)
          - mcp: Agent supports MCP protocol (MVP not implemented)
        """
        return set()


# ============================================================
# Adapter Registry (from adapter-spi.md §4.5)
# ============================================================

class AdapterRegistry(Registry[AgentAdapter]):
    """Adapter SPI registry.

    Built-in adapters are registered at import time.
    External adapters can be registered via Plugin system (Phase 7).
    """

    @classmethod
    def create(cls, name: str, config: dict) -> AgentAdapter:
        """Create adapter instance by type name and config."""
        if name not in cls._registry:
            from agenteval.core.exceptions import UnsupportedAdapterError
            raise UnsupportedAdapterError(
                f"Unsupported adapter type: '{name}'. Available: {cls.list_registered()}")
        adapter_cls = cls._registry[name]
        adapter = adapter_cls(config)
        if not adapter.validate_config(config):
            from agenteval.core.exceptions import InvalidAdapterConfigError
            raise InvalidAdapterConfigError(f"Invalid config for adapter: '{name}'")
        return adapter
