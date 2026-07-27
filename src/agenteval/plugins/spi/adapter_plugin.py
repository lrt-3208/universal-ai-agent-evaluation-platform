"""Adapter Plugin SPI.

Reference: ../docs/phases/phase-7-plugin.md §5.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from agenteval.plugins.base import Plugin

if TYPE_CHECKING:
    from agenteval.adapters import AgentAdapter


class AdapterPlugin(Plugin, ABC):
    """Agent Adapter 插件接口."""

    @property
    def plugin_type(self) -> str:
        """插件类型."""
        return "adapter"

    @abstractmethod
    def create_adapter(self, config: dict) -> AgentAdapter:
        """创建 AgentAdapter 实例.

        Args:
            config: Adapter 配置

        Returns:
            AgentAdapter 实例
        """
        pass
