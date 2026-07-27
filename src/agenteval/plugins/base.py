"""Plugin base interface.

Reference: ../docs/phases/phase-7-plugin.md §5.1
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Plugin(ABC):
    """所有插件的基础接口."""

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """插件类型: judge | adapter | dataset | metrics | report."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称（唯一标识）."""
        pass

    @property
    def version(self) -> str:
        """插件版本."""
        return "1.0.0"

    @abstractmethod
    async def initialize(self, config: dict) -> None:
        """初始化插件（加载模型、建立连接等）.

        Args:
            config: 插件配置
        """
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """清理插件资源."""
        pass

    def get_config_schema(self) -> dict:
        """返回配置 JSON Schema."""
        return {}

    def validate_config(self, config: dict) -> list[str]:
        """校验配置，返回错误列表（空列表=通过）.

        Args:
            config: 待校验的配置

        Returns:
            错误列表，空列表表示通过
        """
        return []
