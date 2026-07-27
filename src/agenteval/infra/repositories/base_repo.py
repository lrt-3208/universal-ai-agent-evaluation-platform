"""Base repository with generic CRUD template methods

Reference: ../docs/phases/phase-1-foundation.md §10
"""

import uuid
from datetime import datetime, timezone
from typing import Generic, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository base class with common CRUD operations"""

    model: Type[T]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: uuid.UUID, with_deleted: bool = False) -> T | None:
        """Fetch a single entity by ID, excluding soft-deleted by default"""
        stmt = select(self.model).where(self.model.id == id)
        if not with_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        with_deleted: bool = False,
        search: str = "",
        order_by: str = "-created_at",
    ) -> tuple[list[T], int]:
        """Paginated list with optional search and sorting"""
        offset = (page - 1) * page_size
        base = select(self.model)
        count_base = select(func.count()).select_from(self.model)

        if not with_deleted:
            base = base.where(self.model.deleted_at.is_(None))
            count_base = count_base.where(self.model.deleted_at.is_(None))

        # Apply search filter
        if search and hasattr(self.model, "name"):
            base = base.where(self.model.name.ilike(f"%{search}%"))
            count_base = count_base.where(self.model.name.ilike(f"%{search}%"))

        # Apply sorting
        if order_by and hasattr(self.model, "created_at"):
            if order_by.startswith("-"):
                base = base.order_by(self.model.created_at.desc())
            else:
                base = base.order_by(self.model.created_at.asc())

        base = base.offset(offset).limit(page_size)
        items = (await self.session.execute(base)).scalars().all()
        total = (await self.session.execute(count_base)).scalar()
        return list(items), total

    async def create(self, entity: T) -> T:
        """Create a new entity"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T, **kwargs) -> T:
        """Update entity fields"""
        for key, value in kwargs.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)
        entity.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def soft_delete(self, id: uuid.UUID) -> bool:
        """Soft delete an entity by setting deleted_at"""
        obj = await self.get_by_id(id)
        if obj is None:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True
