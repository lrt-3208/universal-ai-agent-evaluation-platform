"""Workspace ORM model"""

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class WorkspaceModel(BaseIdModel):
    """Workspace table model"""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Relationships
    projects: Mapped[list["ProjectModel"]] = relationship(
        "ProjectModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
