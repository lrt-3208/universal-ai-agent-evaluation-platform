"""Scenario repository"""

import uuid

from sqlalchemy import func, select

from agenteval.infra.models.scenario_model import ScenarioModel
from agenteval.infra.repositories.base_repo import BaseRepository


class ScenarioRepository(BaseRepository[ScenarioModel]):
    """Scenario-specific repository operations"""

    model = ScenarioModel

    async def get_by_dataset_and_external_id(
        self, dataset_id: uuid.UUID, external_id: str
    ) -> ScenarioModel | None:
        """Fetch scenario by dataset_id + external_id (unique constraint)"""
        stmt = (
            select(self.model)
            .where(self.model.dataset_id == dataset_id)
            .where(self.model.external_id == external_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_dataset(
        self,
        dataset_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        tags: list[str] | None = None,
        status: str | None = None,
        priority_min: int = 0,
        search: str = "",
        sort: str = "-priority",
    ) -> tuple[list[ScenarioModel], int]:
        """Paginated list with advanced filtering"""
        offset = (page - 1) * page_size
        base = (
            select(self.model)
            .where(self.model.dataset_id == dataset_id)
            .where(self.model.deleted_at.is_(None))
        )
        count_base = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.dataset_id == dataset_id)
            .where(self.model.deleted_at.is_(None))
        )

        # Tags filter (JSONB contains - AND logic)
        if tags:
            for tag in tags:
                base = base.where(self.model.tags.contains([tag]))
                count_base = count_base.where(self.model.tags.contains([tag]))

        # Status filter
        if status:
            base = base.where(self.model.status == status)
            count_base = count_base.where(self.model.status == status)

        # Priority filter
        if priority_min is not None and priority_min > 0:
            base = base.where(self.model.priority >= priority_min)
            count_base = count_base.where(self.model.priority >= priority_min)

        # Search filter (title or external_id)
        if search:
            search_filter = self.model.title.ilike(f"%{search}%") | self.model.external_id.ilike(f"%{search}%")
            base = base.where(search_filter)
            count_base = count_base.where(search_filter)

        # Sort
        if sort == "-priority":
            base = base.order_by(self.model.priority.desc())
        elif sort == "priority":
            base = base.order_by(self.model.priority.asc())
        elif sort == "-created_at":
            base = base.order_by(self.model.created_at.desc())
        elif sort == "created_at":
            base = base.order_by(self.model.created_at.asc())
        elif sort == "title":
            base = base.order_by(self.model.title.asc())
        else:
            base = base.order_by(self.model.priority.desc())

        base = base.offset(offset).limit(page_size)
        items = (await self.session.execute(base)).scalars().all()
        total = (await self.session.execute(count_base)).scalar()
        return list(items), total

    async def list_all_by_dataset(
        self, dataset_id: uuid.UUID
    ) -> list[ScenarioModel]:
        """Get all scenarios for a dataset (for export)"""
        stmt = (
            select(self.model)
            .where(self.model.dataset_id == dataset_id)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.priority.desc(), self.model.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def batch_create(self, entities: list[ScenarioModel]) -> list[ScenarioModel]:
        """Batch create scenarios"""
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def soft_delete_by_dataset(self, dataset_id: uuid.UUID) -> int:
        """Soft delete all scenarios in a dataset (cascade)"""
        from datetime import datetime, timezone

        stmt = (
            select(self.model)
            .where(self.model.dataset_id == dataset_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        scenarios = result.scalars().all()
        now = datetime.now(timezone.utc)
        count = 0
        for s in scenarios:
            s.deleted_at = now
            count += 1
        if count > 0:
            await self.session.flush()
        return count

    async def count_by_dataset(self, dataset_id: uuid.UUID) -> int:
        """Count active scenarios in a dataset"""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.dataset_id == dataset_id)
            .where(self.model.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar() or 0
