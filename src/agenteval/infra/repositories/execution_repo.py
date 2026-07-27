"""ScenarioExecution and AgentExecution Repositories

Reference: ../docs/phases/phase-3-runner.md §8.2-8.3
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.infra.models.scenario_execution_model import ScenarioExecutionModel
from agenteval.infra.models.agent_execution_model import AgentExecutionModel
from agenteval.infra.models.trace_model import TraceModel
from agenteval.infra.repositories.base_repo import BaseRepository


class ScenarioExecutionRepository(BaseRepository[ScenarioExecutionModel]):
    model = ScenarioExecutionModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_by_evaluation(self, evaluation_id: uuid.UUID) -> list[ScenarioExecutionModel]:
        stmt = select(self.model).where(
            self.model.evaluation_id == evaluation_id,
            self.model.deleted_at.is_(None),
        ).order_by(self.model.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def batch_create(self, records: list[ScenarioExecutionModel]) -> list[ScenarioExecutionModel]:
        self.session.add_all(records)
        await self.session.flush()
        for r in records:
            await self.session.refresh(r)
        return records

    async def update_status(self, exec_id: uuid.UUID, status: str,
                            error_message: str | None = None,
                            retry_count: int | None = None) -> ScenarioExecutionModel | None:
        obj = await self.get_by_id(exec_id)
        if obj is None:
            return None
        obj.status = status
        if error_message is not None:
            obj.error_message = error_message
        if retry_count is not None:
            obj.retry_count = retry_count
        if status == "running":
            obj.started_at = datetime.now(timezone.utc)
        elif status in ("completed", "failed", "timeout", "skipped"):
            obj.completed_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def skip_pending(self, evaluation_id: uuid.UUID) -> int:
        """Mark all pending executions as skipped (on cancel)."""
        stmt = (
            update(self.model)
            .where(
                self.model.evaluation_id == evaluation_id,
                self.model.status == "pending",
                self.model.deleted_at.is_(None),
            )
            .values(
                status="skipped",
                completed_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def count_by_evaluation(self, evaluation_id: uuid.UUID) -> dict[str, int]:
        """Count executions by status."""
        stmt = (
            select(self.model.status, select(ScenarioExecutionModel).filter(
                ScenarioExecutionModel.evaluation_id == evaluation_id,
                ScenarioExecutionModel.deleted_at.is_(None),
            ).correlate(None).scalar_subquery())
            .where(
                self.model.evaluation_id == evaluation_id,
                self.model.deleted_at.is_(None),
            )
            .group_by(self.model.status)
        )
        # Simpler approach
        all_execs = await self.list_by_evaluation(evaluation_id)
        counts: dict[str, int] = {}
        for e in all_execs:
            counts[e.status] = counts.get(e.status, 0) + 1
        return counts


class AgentExecutionRepository(BaseRepository[AgentExecutionModel]):
    model = AgentExecutionModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_scenario_execution(self, se_id: uuid.UUID) -> AgentExecutionModel | None:
        stmt = select(self.model).where(
            self.model.scenario_execution_id == se_id,
            self.model.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class TraceRepository(BaseRepository[TraceModel]):
    model = TraceModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_agent_execution(self, ae_id: uuid.UUID) -> TraceModel | None:
        """Find trace linked to an agent execution via trace_id FK."""
        stmt = (
            select(self.model)
            .join(AgentExecutionModel, AgentExecutionModel.trace_id == TraceModel.id)
            .where(AgentExecutionModel.id == ae_id, self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
