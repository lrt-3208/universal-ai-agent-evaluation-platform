"""Dataset Plugin SPI.

Reference: ../docs/phases/phase-7-plugin.md §5.4
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agenteval.plugins.base import Plugin


class DatasetPlugin(Plugin, ABC):
    """Dataset 插件接口：扩展 DSL 格式或数据源."""

    @property
    def plugin_type(self) -> str:
        """插件类型."""
        return "dataset"

    @abstractmethod
    def create_parser(self, config: dict):
        """创建 DSL 解析器.

        Args:
            config: 解析器配置

        Returns:
            DSLParser 实例
        """
        pass

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """支持的格式列表.

        Returns:
            格式列表 (如 ["csv", "excel"])
        """
        pass
