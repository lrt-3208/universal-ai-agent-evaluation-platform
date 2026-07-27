"""Regression Repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.infra.models.regression_model import RegressionModel


class RegressionRepository:
    """Regression 数据访问层."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, regression: RegressionModel) -> RegressionModel:
        """创建回归分析记录."""
        self.session.add(regression)
        await self.session.flush()
        return regression

    async def get_by_id(self, regression_id: UUID) -> RegressionModel | None:
        """根据 ID 获取."""
        stmt = select(RegressionModel).where(
            RegressionModel.id == regression_id,
            RegressionModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RegressionModel]:
        """按项目查询回归分析列表."""
        stmt = (
            select(RegressionModel)
            .where(
                RegressionModel.project_id == project_id,
                RegressionModel.deleted_at.is_(None),
            )
            .order_by(RegressionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_project(self, project_id: UUID) -> int:
        """统计项目的回归分析数量."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(RegressionModel).where(
            RegressionModel.project_id == project_id,
            RegressionModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
