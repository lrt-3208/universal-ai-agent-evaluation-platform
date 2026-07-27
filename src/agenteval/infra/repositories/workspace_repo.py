"""Workspace repository"""

import uuid

from sqlalchemy import select

from agenteval.infra.models.workspace_model import WorkspaceModel
from agenteval.infra.repositories.base_repo import BaseRepository


class WorkspaceRepository(BaseRepository[WorkspaceModel]):
    """Workspace-specific repository operations"""

    model = WorkspaceModel

    async def get_by_slug(self, slug: str) -> WorkspaceModel | None:
        """Fetch workspace by slug (must be active)"""
        stmt = (
            select(self.model)
            .where(self.model.slug == slug)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
