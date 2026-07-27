"""Regression ORM Model

Reference: ../docs/phases/phase-6-regression.md §4.1
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.infra.models.base import BaseIdModel


class RegressionModel(BaseIdModel):
    __tablename__ = "regressions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    baseline_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False)
    target_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    scenario_diffs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    metric_diffs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    overall_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
