"""Plugin System — 外部插件生命周期管理.

Reference: ../docs/phases/phase-7-plugin.md
"""

from agenteval.plugins.base import Plugin
from agenteval.plugins.metadata import PluginMetadata
from agenteval.plugins.validator import PluginValidator
from agenteval.plugins.registry import PluginRegistry
from agenteval.plugins.manager import PluginManager

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginValidator",
    "PluginRegistry",
    "PluginManager",
]
