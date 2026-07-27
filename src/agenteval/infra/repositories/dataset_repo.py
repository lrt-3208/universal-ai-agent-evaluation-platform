"""Dataset repository"""

import uuid

from sqlalchemy import func, select

from agenteval.infra.models.dataset_model import DatasetModel
from agenteval.infra.repositories.base_repo import BaseRepository


class DatasetRepository(BaseRepository[DatasetModel]):
    """Dataset-specific repository operations"""

    model = DatasetModel

    async def get_by_project_name_version(
        self, project_id: uuid.UUID, name: str, version: str
    ) -> DatasetModel | None:
        """Fetch dataset by project_id + name + version (unique constraint)"""
        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.name == name)
            .where(self.model.version == version)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DatasetModel], int]:
        """Paginated list of datasets within a project"""
        offset = (page - 1) * page_size
        base = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.deleted_at.is_(None))
        )
        count_base = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.deleted_at.is_(None))
        )
        base = base.order_by(self.model.created_at.desc()).offset(offset).limit(page_size)
        items = (await self.session.execute(base)).scalars().all()
        total = (await self.session.execute(count_base)).scalar()
        return list(items), total

    async def get_latest_by_name(
        self, project_id: uuid.UUID, name: str
    ) -> DatasetModel | None:
        """Get the latest version dataset by name in a project"""
        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.name == name)
            .where(self.model.is_latest.is_(True))
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def unset_latest(self, project_id: uuid.UUID, name: str) -> int:
        """Unset is_latest for all datasets with given name in project"""
        from datetime import datetime, timezone

        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.name == name)
            .where(self.model.is_latest.is_(True))
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        datasets = result.scalars().all()
        now = datetime.now(timezone.utc)
        count = 0
        for ds in datasets:
            ds.is_latest = False
            ds.updated_at = now
            count += 1
        if count > 0:
            await self.session.flush()
        return count

    async def soft_delete_by_project(self, project_id: uuid.UUID) -> int:
        """Soft delete all datasets in a project (cascade)"""
        from datetime import datetime, timezone

        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        datasets = result.scalars().all()
        now = datetime.now(timezone.utc)
        count = 0
        for ds in datasets:
            ds.deleted_at = now
            count += 1
        if count > 0:
            await self.session.flush()
        return count
