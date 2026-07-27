"""ScenarioExecution ORM Model

Reference: ../docs/phases/phase-3-runner.md §8.2
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class ScenarioExecutionModel(BaseIdModel):
    __tablename__ = "scenario_executions"
    __table_args__ = (
        Index("ix_scenario_exec_evaluation_status", "evaluation_id", "status"),
    )

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    evaluation: Mapped["EvaluationModel"] = relationship(
        "EvaluationModel", back_populates="scenario_executions")
    agent_execution: Mapped["AgentExecutionModel | None"] = relationship(
        "AgentExecutionModel", back_populates="scenario_execution", uselist=False,
        cascade="all, delete-orphan")
    judge_results: Mapped[list["JudgeResultModel"]] = relationship(
        "JudgeResultModel", back_populates="scenario_execution",
        cascade="all, delete-orphan")
