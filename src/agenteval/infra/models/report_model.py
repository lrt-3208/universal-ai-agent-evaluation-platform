"""Report ORM Model

Reference: ../docs/phases/phase-5-report.md §6
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.infra.models.base import BaseIdModel


class ReportModel(BaseIdModel):
    __tablename__ = "reports"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)  # json | html
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="generating")
    content_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # Inline content for MVP
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
