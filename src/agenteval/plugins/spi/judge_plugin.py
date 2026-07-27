"""Judge Plugin SPI.

Reference: ../docs/phases/phase-7-plugin.md §5.2
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from agenteval.plugins.base import Plugin

if TYPE_CHECKING:
    from agenteval.judges import Judge


class JudgePlugin(Plugin, ABC):
    """Judge 插件接口."""

    @property
    def plugin_type(self) -> str:
        """插件类型."""
        return "judge"

    @abstractmethod
    def create_judge(self, config: dict) -> Judge:
        """创建 Judge 实例.

        Args:
            config: Judge 配置

        Returns:
            Judge 实例
        """
        pass

    @abstractmethod
    def supported_metrics(self) -> list[str]:
        """支持的指标列表.

        Returns:
            指标 key 列表
        """
        pass
