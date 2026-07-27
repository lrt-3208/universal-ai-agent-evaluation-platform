"""Plugin schemas.

Reference: ../docs/phases/phase-7-plugin.md §7.2
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PluginMetadataResponse(BaseModel):
    """插件元数据响应."""

    id: UUID
    name: str
    version: str
    type: str
    description: str | None = None
    author: str | None = None
    entry_point: str
    status: str
    config: dict = Field(default_factory=dict)
    config_schema: dict = Field(default_factory=dict)
    error_message: str | None = None
    manifest_path: str | None = None
    loaded_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PluginListResponse(BaseModel):
    """插件列表响应."""

    items: list[PluginMetadataResponse]
    total: int


class UpdatePluginConfigRequest(BaseModel):
    """更新插件配置请求."""

    config: dict


class PluginOperationResponse(BaseModel):
    """插件操作响应."""

    success: bool
    message: str
    plugin: PluginMetadataResponse | None = None
