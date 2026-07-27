"""JudgeResult Repository

Reference: ../docs/phases/phase-4-judge.md §10.1
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.infra.models.judge_result_model import JudgeResultModel
from agenteval.infra.repositories.base_repo import BaseRepository


class JudgeResultRepository(BaseRepository[JudgeResultModel]):
    model = JudgeResultModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_by_scenario_execution(
        self, scenario_execution_id: uuid.UUID
    ) -> list[JudgeResultModel]:
        """Get all judge results for a scenario execution."""
        stmt = select(self.model).where(
            self.model.scenario_execution_id == scenario_execution_id,
            self.model.deleted_at.is_(None),
        ).order_by(self.model.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_evaluation(
        self, evaluation_id: uuid.UUID
    ) -> list[JudgeResultModel]:
        """Get all judge results for an evaluation (via scenario_executions join)."""
        from agenteval.infra.models.scenario_execution_model import ScenarioExecutionModel
        stmt = (
            select(self.model)
            .join(ScenarioExecutionModel,
                  ScenarioExecutionModel.id == self.model.scenario_execution_id)
            .where(
                ScenarioExecutionModel.evaluation_id == evaluation_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_result(
        self,
        result_id: uuid.UUID,
        status: str,
        metric_scores: list | None = None,
        overall_score: float | None = None,
        overall_verdict: str | None = None,
        reasoning: str | None = None,
        error_message: str | None = None,
    ) -> JudgeResultModel | None:
        """Update judge result after evaluation."""
        obj = await self.get_by_id(result_id)
        if obj is None:
            return None
        obj.status = status
        if metric_scores is not None:
            obj.metric_scores = metric_scores
        if overall_score is not None:
            obj.overall_score = overall_score
        if overall_verdict is not None:
            obj.overall_verdict = overall_verdict
        if reasoning is not None:
            obj.reasoning = reasoning
        if error_message is not None:
            obj.error_message = error_message
        if status in ("completed", "failed"):
            obj.completed_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
