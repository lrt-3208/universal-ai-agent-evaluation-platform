"""Plugin API endpoints.

Reference: ../docs/phases/phase-7-plugin.md §8
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.core.response import ApiResponse
from agenteval.infra.models.plugin_model import PluginModel
from agenteval.infra.repositories.plugin_repo import PluginRepository
from agenteval.plugins.manager import (
    PluginConfigError,
    PluginLoadError,
    PluginNotFoundError,
    PluginValidationError,
    get_plugin_manager,
)
from agenteval.schemas.plugin import (
    PluginListResponse,
    PluginMetadataResponse,
    PluginOperationResponse,
    UpdatePluginConfigRequest,
)

router = APIRouter()


# ============================================================================
# Plugin Discovery & List
# ============================================================================


@router.get("/plugins", response_model=ApiResponse[PluginListResponse])
async def list_plugins(
    type: str | None = Query(default=None, description="Filter by plugin type"),
    session: AsyncSession = Depends(get_session),
):
    """列出所有已发现插件."""
    repo = PluginRepository(session)
    plugins = await repo.list_all(plugin_type=type)
    items = [PluginMetadataResponse.model_validate(p) for p in plugins]
    return ApiResponse(data=PluginListResponse(items=items, total=len(items)))


@router.get("/plugins/types/{plugin_type}", response_model=ApiResponse[PluginListResponse])
async def list_plugins_by_type(
    plugin_type: str,
    session: AsyncSession = Depends(get_session),
):
    """按类型筛选插件."""
    repo = PluginRepository(session)
    plugins = await repo.list_all(plugin_type=plugin_type)
    items = [PluginMetadataResponse.model_validate(p) for p in plugins]
    return ApiResponse(data=PluginListResponse(items=items, total=len(items)))


@router.get("/plugins/{plugin_name}", response_model=ApiResponse[PluginMetadataResponse])
async def get_plugin(
    plugin_name: str,
    session: AsyncSession = Depends(get_session),
):
    """获取插件详情."""
    repo = PluginRepository(session)
    plugin = await repo.get_by_name(plugin_name)
    if not plugin:
        raise NotFoundException(f"Plugin not found: {plugin_name}")
    return ApiResponse(data=PluginMetadataResponse.model_validate(plugin))


# ============================================================================
# Plugin Discovery
# ============================================================================


@router.post("/plugins/discover", response_model=ApiResponse[PluginListResponse])
async def discover_plugins(
    session: AsyncSession = Depends(get_session),
):
    """重新扫描插件目录."""
    manager = get_plugin_manager()
    metadatas = await manager.discover()

    repo = PluginRepository(session)
    for metadata in metadatas:
        # 解析 config_schema
        try:
            config_schema = json.loads(metadata.config_schema)
        except json.JSONDecodeError:
            config_schema = {}

        plugin_model = PluginModel(
            id=uuid4(),
            name=metadata.name,
            version=metadata.version,
            type=metadata.type,
            description=metadata.description,
            author=metadata.author,
            entry_point=metadata.entry_point,
            config_schema=config_schema,
            manifest_path=metadata.manifest_path,
            status="disabled",
        )
        await repo.upsert_by_name(plugin_model)

    await session.commit()

    plugins = await repo.list_all()
    items = [PluginMetadataResponse.model_validate(p) for p in plugins]
    return ApiResponse(data=PluginListResponse(items=items, total=len(items)))


# ============================================================================
# Plugin Lifecycle
# ============================================================================


@router.post("/plugins/{plugin_name}/enable", response_model=ApiResponse[PluginOperationResponse])
async def enable_plugin(
    plugin_name: str,
    session: AsyncSession = Depends(get_session),
):
    """启用插件."""
    repo = PluginRepository(session)
    plugin = await repo.get_by_name(plugin_name)
    if not plugin:
        raise NotFoundException(f"Plugin not found: {plugin_name}")

    if plugin.status == "enabled":
        raise ConflictException(f"Plugin already enabled: {plugin_name}")

    manager = get_plugin_manager()
    metadata = manager.get_metadata(plugin_name)

    if not metadata:
        # 从 DB 记录重建 metadata
        from agenteval.plugins.metadata import PluginMetadata
        metadata = PluginMetadata(
            name=plugin.name,
            version=plugin.version,
            type=plugin.type,
            entry_point=plugin.entry_point,
            description=plugin.description,
            author=plugin.author,
            manifest_path=plugin.manifest_path,
            config_schema=json.dumps(plugin.config_schema or {}),
        )

    try:
        await manager.load_plugin(metadata, plugin.config or {})
        await repo.update_status(
            plugin.id,
            status="enabled",
            error_message=None,
            loaded_at=datetime.now(timezone.utc),
        )
        await session.commit()

        # 重新获取更新后的 plugin
        plugin = await repo.get_by_name(plugin_name)
        return ApiResponse(data=PluginOperationResponse(
            success=True,
            message=f"Plugin '{plugin_name}' enabled successfully",
            plugin=PluginMetadataResponse.model_validate(plugin),
        ))
    except (PluginValidationError, PluginConfigError) as e:
        await repo.update_status(plugin.id, status="error", error_message=str(e))
        await session.commit()
        raise
    except PluginLoadError as e:
        await repo.update_status(plugin.id, status="error", error_message=str(e))
        await session.commit()
        raise


@router.post("/plugins/{plugin_name}/disable", response_model=ApiResponse[PluginOperationResponse])
async def disable_plugin(
    plugin_name: str,
    session: AsyncSession = Depends(get_session),
):
    """禁用插件."""
    repo = PluginRepository(session)
    plugin = await repo.get_by_name(plugin_name)
    if not plugin:
        raise NotFoundException(f"Plugin not found: {plugin_name}")

    manager = get_plugin_manager()
    await manager.unload_plugin(plugin_name)

    await repo.update_status(plugin.id, status="disabled", loaded_at=None)
    await session.commit()

    plugin = await repo.get_by_name(plugin_name)
    return ApiResponse(data=PluginOperationResponse(
        success=True,
        message=f"Plugin '{plugin_name}' disabled successfully",
        plugin=PluginMetadataResponse.model_validate(plugin),
    ))


@router.post("/plugins/{plugin_name}/reload", response_model=ApiResponse[PluginOperationResponse])
async def reload_plugin(
    plugin_name: str,
    session: AsyncSession = Depends(get_session),
):
    """重新加载插件."""
    repo = PluginRepository(session)
    plugin = await repo.get_by_name(plugin_name)
    if not plugin:
        raise NotFoundException(f"Plugin not found: {plugin_name}")

    manager = get_plugin_manager()

    try:
        await manager.reload_plugin(plugin_name, plugin.config or {})
        await repo.update_status(
            plugin.id,
            status="enabled",
            error_message=None,
            loaded_at=datetime.now(timezone.utc),
        )
        await session.commit()

        plugin = await repo.get_by_name(plugin_name)
        return ApiResponse(data=PluginOperationResponse(
            success=True,
            message=f"Plugin '{plugin_name}' reloaded successfully",
            plugin=PluginMetadataResponse.model_validate(plugin),
        ))
    except PluginNotFoundError:
        raise NotFoundException("Plugin", plugin_name)
    except (PluginLoadError, PluginConfigError) as e:
        await repo.update_status(plugin.id, status="error", error_message=str(e))
        await session.commit()
        raise


# ============================================================================
# Plugin Config
# ============================================================================


@router.put("/plugins/{plugin_name}/config", response_model=ApiResponse[PluginMetadataResponse])
async def update_plugin_config(
    plugin_name: str,
    request: UpdatePluginConfigRequest,
    session: AsyncSession = Depends(get_session),
):
    """更新插件配置."""
    repo = PluginRepository(session)
    plugin = await repo.get_by_name(plugin_name)
    if not plugin:
        raise NotFoundException(f"Plugin not found: {plugin_name}")

    # 如果插件已启用，校验配置
    manager = get_plugin_manager()
    instance = manager.get_plugin(plugin_name)
    if instance:
        errors = instance.validate_config(request.config)
        if errors:
            raise PluginConfigError(f"Config validation failed: {errors}")

    await repo.update_config(plugin.id, request.config)
    await session.commit()

    plugin = await repo.get_by_name(plugin_name)
    return ApiResponse(data=PluginMetadataResponse.model_validate(plugin))
