"""Project repository"""

import uuid

from sqlalchemy import select

from agenteval.infra.models.project_model import ProjectModel
from agenteval.infra.repositories.base_repo import BaseRepository


class ProjectRepository(BaseRepository[ProjectModel]):
    """Project-specific repository operations"""

    model = ProjectModel

    async def get_by_workspace_and_slug(
        self, workspace_id: uuid.UUID, slug: str
    ) -> ProjectModel | None:
        """Fetch project by workspace_id and slug (must be active)"""
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .where(self.model.slug == slug)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProjectModel], int]:
        """Paginated list of projects within a workspace"""
        from sqlalchemy import func

        offset = (page - 1) * page_size
        base = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .where(self.model.deleted_at.is_(None))
        )
        count_base = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.workspace_id == workspace_id)
            .where(self.model.deleted_at.is_(None))
        )
        base = base.order_by(self.model.created_at.desc()).offset(offset).limit(page_size)
        items = (await self.session.execute(base)).scalars().all()
        total = (await self.session.execute(count_base)).scalar()
        return list(items), total

    async def soft_delete_by_workspace(self, workspace_id: uuid.UUID) -> int:
        """Soft delete all projects in a workspace (cascade)"""
        from datetime import datetime, timezone

        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        projects = result.scalars().all()
        now = datetime.now(timezone.utc)
        count = 0
        for project in projects:
            project.deleted_at = now
            count += 1
        if count > 0:
            await self.session.flush()
        return count
