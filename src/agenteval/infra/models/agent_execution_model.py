"""AgentExecution ORM Model

Reference: ../docs/phases/phase-3-runner.md §8.3
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenteval.infra.models.base import BaseIdModel


class AgentExecutionModel(BaseIdModel):
    __tablename__ = "agent_executions"

    scenario_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_executions.id"), nullable=False, unique=True)
    agent_adapter_type: Mapped[str] = mapped_column(String(16), nullable=False)
    agent_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    conversation_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Serialized Conversation
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traces.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    scenario_execution: Mapped["ScenarioExecutionModel"] = relationship(
        "ScenarioExecutionModel", back_populates="agent_execution")
    trace: Mapped["TraceModel | None"] = relationship(
        "TraceModel")
