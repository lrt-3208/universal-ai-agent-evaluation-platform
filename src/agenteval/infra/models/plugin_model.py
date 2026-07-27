"""Plugin ORM Model.

Reference: ../docs/phases/phase-7-plugin.md §7.1
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.infra.models.base import BaseIdModel


class PluginModel(BaseIdModel):
    """插件持久化记录."""

    __tablename__ = "plugins"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(128))
    entry_point: Mapped[str] = mapped_column(String(256), nullable=False)
    config_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="disabled")
    error_message: Mapped[str | None] = mapped_column(Text)
    manifest_path: Mapped[str | None] = mapped_column(String(512))
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
