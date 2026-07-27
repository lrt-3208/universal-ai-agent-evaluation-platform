"""Workspace service - business logic layer"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.infra.models.workspace_model import WorkspaceModel
from agenteval.infra.repositories.project_repo import ProjectRepository
from agenteval.infra.repositories.workspace_repo import WorkspaceRepository
from agenteval.schemas.workspace import (
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest,
    WorkspaceBriefResponse,
    WorkspaceResponse,
)

logger = structlog.get_logger()


class WorkspaceService:
    """Workspace business logic"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WorkspaceRepository(session)

    async def create(
        self, request: CreateWorkspaceRequest, owner_id: str = "system"
    ) -> WorkspaceResponse:
        """Create a new workspace"""
        # Check slug uniqueness
        existing = await self.repo.get_by_slug(request.slug)
        if existing:
            raise ConflictException(
                message=f"Workspace slug already exists: {request.slug}",
                code=40901,
            )

        # Create workspace
        workspace = WorkspaceModel(
            name=request.name,
            slug=request.slug,
            description=request.description,
            owner_id=owner_id,
        )
        workspace = await self.repo.create(workspace)
        logger.info("workspace.created", workspace_id=str(workspace.id), slug=workspace.slug)
        return WorkspaceResponse.model_validate(workspace)

    async def get(self, workspace_id: uuid.UUID) -> WorkspaceResponse:
        """Get workspace by ID"""
        workspace = await self.repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException(
                message=f"Workspace not found: {workspace_id}",
                code=40401,
            )
        return WorkspaceResponse.model_validate(workspace)

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str = "",
    ) -> tuple[list[WorkspaceBriefResponse], int]:
        """List workspaces with pagination"""
        workspaces, total = await self.repo.list(page=page, page_size=page_size, search=search)

        # Enrich with project count
        briefs = []
        project_repo = ProjectRepository(self.session)
        for ws in workspaces:
            _, project_count = await project_repo.list_by_workspace(ws.id)
            briefs.append(
                WorkspaceBriefResponse(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    project_count=project_count,
                )
            )
        return briefs, total

    async def update(
        self, workspace_id: uuid.UUID, request: UpdateWorkspaceRequest
    ) -> WorkspaceResponse:
        """Update workspace"""
        workspace = await self.repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException(
                message=f"Workspace not found: {workspace_id}",
                code=40401,
            )

        update_data = request.model_dump(exclude_unset=True)
        workspace = await self.repo.update(workspace, **update_data)
        logger.info("workspace.updated", workspace_id=str(workspace.id))
        return WorkspaceResponse.model_validate(workspace)

    async def delete(self, workspace_id: uuid.UUID) -> None:
        """Delete workspace (cascade soft delete projects)"""
        workspace = await self.repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException(
                message=f"Workspace not found: {workspace_id}",
                code=40401,
            )

        # Cascade soft delete projects
        project_repo = ProjectRepository(self.session)
        await project_repo.soft_delete_by_workspace(workspace_id)

        # Soft delete workspace
        await self.repo.soft_delete(workspace_id)
        logger.info("workspace.deleted", workspace_id=str(workspace_id))
