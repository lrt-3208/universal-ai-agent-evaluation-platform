"""Evaluation Repository

Reference: ../docs/phases/phase-3-runner.md §8.1
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.infra.models.evaluation_model import EvaluationModel
from agenteval.infra.repositories.base_repo import BaseRepository


class EvaluationRepository(BaseRepository[EvaluationModel]):
    model = EvaluationModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[EvaluationModel], int]:
        offset = (page - 1) * page_size
        base = select(self.model).where(
            self.model.project_id == project_id,
            self.model.deleted_at.is_(None),
        )
        count_base = select(func.count()).select_from(self.model).where(
            self.model.project_id == project_id,
            self.model.deleted_at.is_(None),
        )
        if status:
            base = base.where(self.model.status == status)
            count_base = count_base.where(self.model.status == status)
        base = base.order_by(self.model.created_at.desc()).offset(offset).limit(page_size)
        items = (await self.session.execute(base)).scalars().all()
        total = (await self.session.execute(count_base)).scalar()
        return list(items), total

    async def update_status(self, eval_id: uuid.UUID, status: str, error_message: str | None = None) -> EvaluationModel | None:
        obj = await self.get_by_id(eval_id)
        if obj is None:
            return None
        obj.status = status
        if error_message:
            obj.error_message = error_message
        if status == "running":
            obj.started_at = datetime.now(timezone.utc)
        elif status in ("completed", "failed", "cancelled", "scoring"):
            obj.completed_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
