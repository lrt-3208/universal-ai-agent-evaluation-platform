"""Plugin Manager — 插件生命周期管理.

Reference: ../docs/phases/phase-7-plugin.md §6.1
"""

from __future__ import annotations

import importlib
import sys
import tomllib
from pathlib import Path

from structlog import get_logger

from agenteval.core.exceptions import AgentEvalException
from agenteval.plugins.base import Plugin
from agenteval.plugins.metadata import PluginMetadata
from agenteval.plugins.registry import PluginRegistry
from agenteval.plugins.validator import PluginValidator

logger = get_logger(__name__)


class PluginNotFoundError(AgentEvalException):
    """插件不存在."""

    code = 41001
    http_status = 404
    message = "Plugin not found"


class PluginValidationError(AgentEvalException):
    """插件校验失败."""

    code = 41002
    http_status = 400
    message = "Plugin validation failed"


class PluginLoadError(AgentEvalException):
    """插件加载失败."""

    code = 51001
    http_status = 500
    message = "Plugin load error"


class PluginConfigError(AgentEvalException):
    """插件配置错误."""

    code = 41003
    http_status = 400
    message = "Plugin config invalid"


class PluginManager:
    """插件管理器."""

    def __init__(self, plugin_dirs: list[Path] | None = None):
        """初始化.

        Args:
            plugin_dirs: 插件目录列表
        """
        self.plugin_dirs = plugin_dirs or [
            Path("plugins"),
            Path("external_plugins"),
        ]
        self.registry = PluginRegistry()
        self.validator = PluginValidator()
        self.configs: dict[str, dict] = {}  # plugin_name → config
        self.instances: dict[str, Plugin] = {}  # plugin_name → instance
        self.metadatas: dict[str, PluginMetadata] = {}  # plugin_name → metadata

    async def discover(self) -> list[PluginMetadata]:
        """扫描插件目录，发现所有插件.

        Returns:
            插件元数据列表
        """
        metadatas = []
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            for manifest_path in plugin_dir.glob("*/plugin.toml"):
                metadata = self._parse_manifest(manifest_path)
                if metadata:
                    metadatas.append(metadata)
                    self.metadatas[metadata.name] = metadata
        return metadatas

    def _parse_manifest(self, path: Path) -> PluginMetadata | None:
        """解析 plugin.toml.

        Args:
            path: manifest 文件路径

        Returns:
            插件元数据或 None
        """
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            plugin_section = data.get("plugin", {})
            return PluginMetadata(
                name=plugin_section.get("name", ""),
                version=plugin_section.get("version", ""),
                type=plugin_section.get("type", ""),
                author=plugin_section.get("author"),
                description=plugin_section.get("description"),
                entry_point=plugin_section.get("entry_point", ""),
                min_agenteval_version=plugin_section.get("min_agenteval_version"),
                config_schema=data.get("config", {}).get("schema", "{}"),
                dependencies=data.get("dependencies", {}),
                manifest_path=str(path),
                security=data.get("security", {}),
            )
        except Exception as e:
            logger.error("plugin.manifest.parse_error", path=str(path), error=str(e))
            return None

    async def load_plugin(
        self,
        metadata: PluginMetadata,
        config: dict | None = None,
    ) -> Plugin:
        """加载单个插件.

        Args:
            metadata: 插件元数据
            config: 插件配置

        Returns:
            插件实例

        Raises:
            PluginValidationError: 校验失败
            PluginLoadError: 加载失败
        """
        # 校验元数据
        errors = self.validator.validate(metadata)
        if errors:
            raise PluginValidationError(f"Plugin manifest invalid: {errors}")

        # 动态导入
        try:
            module_path, class_name = metadata.entry_point.split(":")
            # 添加插件目录到 sys.path
            if metadata.manifest_path:
                plugin_dir = str(Path(metadata.manifest_path).parent.parent)
                if plugin_dir not in sys.path:
                    sys.path.insert(0, plugin_dir)
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
        except Exception as e:
            raise PluginLoadError(f"Plugin load error: {e}")

        # 实例化
        instance = plugin_class()
        config = config or {}

        # 校验配置
        config_errors = instance.validate_config(config)
        if config_errors:
            raise PluginConfigError(f"Plugin config invalid: {config_errors}")

        # 初始化
        try:
            await instance.initialize(config)
        except Exception as e:
            raise PluginLoadError(f"Plugin initialization error: {e}")

        # 注册
        self.registry.register(metadata.type, metadata.name, instance)
        self.configs[metadata.name] = config
        self.instances[metadata.name] = instance

        # 注册到核心系统
        await self._register_to_core(metadata.type, instance, config)

        logger.info(
            "plugin.loaded",
            name=metadata.name,
            type=metadata.type,
            version=metadata.version,
        )
        return instance

    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件.

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功卸载
        """
        instance = self.instances.get(plugin_name)
        if not instance:
            return False

        metadata = self.metadatas.get(plugin_name)
        plugin_type = metadata.type if metadata else instance.plugin_type

        # 清理资源
        try:
            await instance.teardown()
        except Exception as e:
            logger.warning("plugin.teardown_error", name=plugin_name, error=str(e))

        # 注销
        self.registry.unregister(plugin_type, plugin_name)
        del self.instances[plugin_name]
        if plugin_name in self.configs:
            del self.configs[plugin_name]

        # 从核心系统注销
        await self._unregister_from_core(plugin_type, plugin_name)

        logger.info("plugin.unloaded", name=plugin_name)
        return True

    async def reload_plugin(
        self,
        plugin_name: str,
        config: dict | None = None,
    ) -> Plugin:
        """重新加载插件（热更新）.

        Args:
            plugin_name: 插件名称
            config: 新配置（可选）

        Returns:
            插件实例

        Raises:
            PluginNotFoundError: 插件不存在
        """
        old_config = self.configs.get(plugin_name, {})
        await self.unload_plugin(plugin_name)

        # 重新发现
        metadata = self.metadatas.get(plugin_name)
        if not metadata:
            metadatas = await self.discover()
            metadata = next((m for m in metadatas if m.name == plugin_name), None)

        if not metadata:
            raise PluginNotFoundError(f"Plugin not found: {plugin_name}")

        return await self.load_plugin(metadata, config or old_config)

    def get_plugin(self, plugin_name: str) -> Plugin | None:
        """获取插件实例.

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例或 None
        """
        return self.instances.get(plugin_name)

    def get_metadata(self, plugin_name: str) -> PluginMetadata | None:
        """获取插件元数据.

        Args:
            plugin_name: 插件名称

        Returns:
            插件元数据或 None
        """
        return self.metadatas.get(plugin_name)

    def list_plugins(self, plugin_type: str | None = None) -> list[PluginMetadata]:
        """列出插件.

        Args:
            plugin_type: 可选的类型过滤

        Returns:
            插件元数据列表
        """
        if plugin_type:
            return [m for m in self.metadatas.values() if m.type == plugin_type]
        return list(self.metadatas.values())

    def is_enabled(self, plugin_name: str) -> bool:
        """检查插件是否已启用.

        Args:
            plugin_name: 插件名称

        Returns:
            是否已启用
        """
        return plugin_name in self.instances

    async def _register_to_core(
        self,
        plugin_type: str,
        instance: Plugin,
        config: dict,
    ) -> None:
        """将插件注册到核心系统.

        Args:
            plugin_type: 插件类型
            instance: 插件实例
            config: 插件配置
        """
        try:
            if plugin_type == "judge":
                from agenteval.judges import JudgeRegistry
                judge = instance.create_judge(config)  # type: ignore
                JudgeRegistry.register(instance.name, type(judge))
            elif plugin_type == "adapter":
                from agenteval.adapters import AdapterRegistry
                adapter = instance.create_adapter(config)  # type: ignore
                AdapterRegistry.register(instance.name, type(adapter))
            # dataset, metrics, report 类型暂不注册到核心系统
        except Exception as e:
            logger.warning(
                "plugin.core_register_error",
                type=plugin_type,
                name=instance.name,
                error=str(e),
            )

    async def _unregister_from_core(
        self,
        plugin_type: str,
        plugin_name: str,
    ) -> None:
        """从核心系统注销.

        Args:
            plugin_type: 插件类型
            plugin_name: 插件名称
        """
        try:
            if plugin_type == "judge":
                from agenteval.judges import JudgeRegistry
                JudgeRegistry.unregister(plugin_name)
            elif plugin_type == "adapter":
                from agenteval.adapters import AdapterRegistry
                AdapterRegistry.unregister(plugin_name)
        except Exception as e:
            logger.warning(
                "plugin.core_unregister_error",
                type=plugin_type,
                name=plugin_name,
                error=str(e),
            )


# 全局单例
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
