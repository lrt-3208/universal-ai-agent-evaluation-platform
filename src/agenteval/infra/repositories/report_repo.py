"""Report Repository

Reference: ../docs/phases/phase-5-report.md §6
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.infra.models.report_model import ReportModel
from agenteval.infra.repositories.base_repo import BaseRepository


class ReportRepository(BaseRepository[ReportModel]):
    model = ReportModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_by_evaluation(
        self, evaluation_id: uuid.UUID
    ) -> list[ReportModel]:
        """Get all reports for an evaluation."""
        stmt = select(self.model).where(
            self.model.evaluation_id == evaluation_id,
            self.model.deleted_at.is_(None),
        ).order_by(self.model.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        report_id: uuid.UUID,
        status: str,
        content: str | None = None,
        content_uri: str | None = None,
        summary: dict | None = None,
        metrics_snapshot: dict | None = None,
        error_message: str | None = None,
    ) -> ReportModel | None:
        """Update report status and content after generation."""
        obj = await self.get_by_id(report_id)
        if obj is None:
            return None
        obj.status = status
        if content is not None:
            obj.content = content
        if content_uri is not None:
            obj.content_uri = content_uri
        if summary is not None:
            obj.summary = summary
        if metrics_snapshot is not None:
            obj.metrics_snapshot = metrics_snapshot
        if status in ("completed", "failed"):
            obj.completed_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
