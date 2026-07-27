"""Report Plugin SPI.

Reference: ../docs/phases/phase-7-plugin.md §5.6
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agenteval.plugins.base import Plugin


class ReportPlugin(Plugin, ABC):
    """Report 插件接口：扩展报告格式或章节."""

    @property
    def plugin_type(self) -> str:
        """插件类型."""
        return "report"

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """支持的报告格式.

        Returns:
            格式列表 (如 ["pdf", "markdown"])
        """
        pass

    @abstractmethod
    async def generate_section(self, section_name: str, data: Any) -> str:
        """生成报告章节内容（HTML 片段）.

        Args:
            section_name: 章节名称
            data: 报告数据

        Returns:
            HTML 片段
        """
        pass

    @abstractmethod
    def get_template_path(self, format: str) -> str | None:
        """返回模板文件路径.

        Args:
            format: 报告格式

        Returns:
            模板路径或 None
        """
        pass
