"""Scenario ORM model"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class ScenarioModel(BaseIdModel):
    """Scenario table model"""

    __tablename__ = "scenarios"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "external_id",
            name="uq_scenario_dataset_external_id",
        ),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    history: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    memory: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    expected: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    constraints: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    judge_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")

    # Relationships
    dataset: Mapped["DatasetModel"] = relationship(
        "DatasetModel",
        back_populates="scenarios",
    )
