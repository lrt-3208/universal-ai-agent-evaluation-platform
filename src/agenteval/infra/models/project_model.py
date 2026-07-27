"""Project ORM model"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class ProjectModel(BaseIdModel):
    """Project table model"""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_project_workspace_slug"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    agent_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    default_judge_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # Relationships
    workspace: Mapped["WorkspaceModel"] = relationship(
        "WorkspaceModel",
        back_populates="projects",
    )
    datasets: Mapped[list["DatasetModel"]] = relationship(
        "DatasetModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )
