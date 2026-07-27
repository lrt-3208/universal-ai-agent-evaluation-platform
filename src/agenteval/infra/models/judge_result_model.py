"""JudgeResult ORM Model

Reference: ../docs/phases/phase-4-judge.md §10.1
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class JudgeResultModel(BaseIdModel):
    __tablename__ = "judge_results"

    scenario_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_executions.id"), nullable=False)
    judge_type: Mapped[str] = mapped_column(String(16), nullable=False)
    judge_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    metric_scores: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    scenario_execution: Mapped["ScenarioExecutionModel"] = relationship(
        "ScenarioExecutionModel", back_populates="judge_results")
