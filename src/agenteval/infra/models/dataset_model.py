"""Dataset ORM model"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class DatasetModel(BaseIdModel):
    """Dataset table model"""

    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "name", "version",
            name="uq_dataset_project_name_version",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="yaml")
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scenario_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tags: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel",
        back_populates="datasets",
    )
    scenarios: Mapped[list["ScenarioModel"]] = relationship(
        "ScenarioModel",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
