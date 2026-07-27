"""Built-in Adapter implementations

Reference: ../contracts/adapter-spi.md §5
"""

from agenteval.adapters import AdapterRegistry
from agenteval.adapters.builtin.http_adapter import HTTPAdapter
from agenteval.adapters.builtin.openai_adapter import OpenAIAdapter
from agenteval.adapters.builtin.custom_adapter import CustomAdapter


def register_builtin_adapters():
    """Register all built-in adapters (treated as built-in plugins)."""
    AdapterRegistry.register("http", HTTPAdapter)
    AdapterRegistry.register("openai", OpenAIAdapter)
    AdapterRegistry.register("custom", CustomAdapter)
