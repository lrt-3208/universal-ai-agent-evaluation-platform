"""Workspace request/response schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateWorkspaceRequest(BaseModel):
    """Create workspace request body"""
    name: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=512)


class UpdateWorkspaceRequest(BaseModel):
    """Update workspace request body"""
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class WorkspaceResponse(BaseModel):
    """Workspace detail response"""
    id: UUID
    name: str
    slug: str
    description: str | None
    owner_id: str
    settings: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceBriefResponse(BaseModel):
    """Workspace brief for list view"""
    id: UUID
    name: str
    slug: str
    project_count: int = 0

    model_config = {"from_attributes": True}
