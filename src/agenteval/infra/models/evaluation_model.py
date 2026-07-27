"""Evaluation ORM Model

Reference: ../docs/phases/phase-3-runner.md §8.1
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class EvaluationModel(BaseIdModel):
    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("project_id", "name", "version_label", name="uq_evaluation_project_name_version"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True)
    agent_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    judge_configs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")

    # Relationships
    scenario_executions: Mapped[list["ScenarioExecutionModel"]] = relationship(
        "ScenarioExecutionModel", back_populates="evaluation", cascade="all, delete-orphan")
