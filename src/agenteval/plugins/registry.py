"""Plugin registry.

Reference: ../docs/phases/phase-7-plugin.md §6.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agenteval.plugins.base import Plugin


class PluginRegistry:
    """插件注册表."""

    def __init__(self):
        """初始化."""
        self._plugins: dict[str, dict[str, Plugin]] = {}
        # 结构: {plugin_type: {plugin_name: Plugin instance}}

    def register(self, plugin_type: str, name: str, instance: Plugin) -> None:
        """注册插件.

        Args:
            plugin_type: 插件类型
            name: 插件名称
            instance: 插件实例
        """
        self._plugins.setdefault(plugin_type, {})[name] = instance

    def unregister(self, plugin_type: str, name: str) -> bool:
        """注销插件.

        Args:
            plugin_type: 插件类型
            name: 插件名称

        Returns:
            是否成功注销
        """
        plugins = self._plugins.get(plugin_type, {})
        if name in plugins:
            del plugins[name]
            return True
        return False

    def get(self, plugin_type: str, name: str) -> Plugin | None:
        """获取插件实例.

        Args:
            plugin_type: 插件类型
            name: 插件名称

        Returns:
            插件实例或 None
        """
        return self._plugins.get(plugin_type, {}).get(name)

    def list_by_type(self, plugin_type: str) -> dict[str, Plugin]:
        """列出指定类型的所有插件.

        Args:
            plugin_type: 插件类型

        Returns:
            {name: Plugin} 字典
        """
        return self._plugins.get(plugin_type, {})

    def list_all(self) -> dict[str, dict[str, Plugin]]:
        """列出所有插件.

        Returns:
            {type: {name: Plugin}} 字典
        """
        return self._plugins

    def is_registered(self, plugin_type: str, name: str) -> bool:
        """检查插件是否已注册.

        Args:
            plugin_type: 插件类型
            name: 插件名称

        Returns:
            是否已注册
        """
        return name in self._plugins.get(plugin_type, {})
