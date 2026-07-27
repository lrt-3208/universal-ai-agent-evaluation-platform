"""Plugin Repository.

Reference: ../docs/phases/phase-7-plugin.md §7
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.infra.models.plugin_model import PluginModel


class PluginRepository:
    """Plugin 数据访问层."""

    def __init__(self, session: AsyncSession):
        """初始化.

        Args:
            session: 数据库会话
        """
        self.session = session

    async def create(self, plugin: PluginModel) -> PluginModel:
        """创建插件记录.

        Args:
            plugin: 插件实体

        Returns:
            创建后的实体
        """
        self.session.add(plugin)
        await self.session.flush()
        return plugin

    async def get_by_id(self, plugin_id: UUID) -> PluginModel | None:
        """根据 ID 获取.

        Args:
            plugin_id: 插件 ID

        Returns:
            插件实体或 None
        """
        stmt = select(PluginModel).where(
            PluginModel.id == plugin_id,
            PluginModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> PluginModel | None:
        """根据名称获取.

        Args:
            name: 插件名称

        Returns:
            插件实体或 None
        """
        stmt = select(PluginModel).where(
            PluginModel.name == name,
            PluginModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, plugin_type: str | None = None) -> list[PluginModel]:
        """列出所有插件.

        Args:
            plugin_type: 可选的类型过滤

        Returns:
            插件列表
        """
        stmt = select(PluginModel).where(PluginModel.deleted_at.is_(None))
        if plugin_type:
            stmt = stmt.where(PluginModel.type == plugin_type)
        stmt = stmt.order_by(PluginModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        plugin_id: UUID,
        status: str,
        error_message: str | None = None,
        loaded_at=None,
    ) -> PluginModel | None:
        """更新插件状态.

        Args:
            plugin_id: 插件 ID
            status: 新状态
            error_message: 错误信息
            loaded_at: 加载时间

        Returns:
            更新后的实体或 None
        """
        plugin = await self.get_by_id(plugin_id)
        if not plugin:
            return None
        plugin.status = status
        plugin.error_message = error_message
        if loaded_at:
            plugin.loaded_at = loaded_at
        await self.session.flush()
        return plugin

    async def update_config(
        self,
        plugin_id: UUID,
        config: dict,
    ) -> PluginModel | None:
        """更新插件配置.

        Args:
            plugin_id: 插件 ID
            config: 新配置

        Returns:
            更新后的实体或 None
        """
        plugin = await self.get_by_id(plugin_id)
        if not plugin:
            return None
        plugin.config = config
        await self.session.flush()
        return plugin

    async def upsert_by_name(self, plugin: PluginModel) -> PluginModel:
        """根据名称创建或更新.

        Args:
            plugin: 插件实体

        Returns:
            插件实体
        """
        existing = await self.get_by_name(plugin.name)
        if existing:
            existing.version = plugin.version
            existing.type = plugin.type
            existing.description = plugin.description
            existing.author = plugin.author
            existing.entry_point = plugin.entry_point
            existing.config_schema = plugin.config_schema
            existing.manifest_path = plugin.manifest_path
            await self.session.flush()
            return existing
        return await self.create(plugin)
