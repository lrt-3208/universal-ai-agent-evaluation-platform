"""Project service - business logic layer"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.infra.models.project_model import ProjectModel
from agenteval.infra.repositories.project_repo import ProjectRepository
from agenteval.infra.repositories.workspace_repo import WorkspaceRepository
from agenteval.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
    UpdateProjectRequest,
)

logger = structlog.get_logger()


class ProjectService:
    """Project business logic"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProjectRepository(session)
        self.workspace_repo = WorkspaceRepository(session)

    async def create(
        self, workspace_id: uuid.UUID, request: CreateProjectRequest
    ) -> ProjectResponse:
        """Create a new project within a workspace"""
        # Check workspace exists
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException(
                message=f"Workspace not found: {workspace_id}",
                code=40401,
            )

        # Check slug uniqueness within workspace
        existing = await self.repo.get_by_workspace_and_slug(workspace_id, request.slug)
        if existing:
            raise ConflictException(
                message=f"Project slug '{request.slug}' already exists in workspace",
                code=40902,
            )

        # Create project
        project = ProjectModel(
            workspace_id=workspace_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
            agent_config=request.agent_config.model_dump(),
            default_judge_config=request.default_judge_config,
            tags=request.tags,
        )
        project = await self.repo.create(project)
        logger.info(
            "project.created",
            project_id=str(project.id),
            workspace_id=str(workspace_id),
        )
        return ProjectResponse.model_validate(project)

    async def get(self, project_id: uuid.UUID) -> ProjectResponse:
        """Get project by ID"""
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise NotFoundException(
                message=f"Project not found: {project_id}",
                code=40402,
            )
        return ProjectResponse.model_validate(project)

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProjectResponse], int]:
        """List projects in a workspace"""
        # Check workspace exists
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException(
                message=f"Workspace not found: {workspace_id}",
                code=40401,
            )

        projects, total = await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )
        return [ProjectResponse.model_validate(p) for p in projects], total

    async def update(
        self, project_id: uuid.UUID, request: UpdateProjectRequest
    ) -> ProjectResponse:
        """Update project"""
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise NotFoundException(
                message=f"Project not found: {project_id}",
                code=40402,
            )

        update_data = request.model_dump(exclude_unset=True)
        if "agent_config" in update_data and update_data["agent_config"] is not None:
            update_data["agent_config"] = update_data["agent_config"].model_dump()

        project = await self.repo.update(project, **update_data)
        logger.info("project.updated", project_id=str(project_id))
        return ProjectResponse.model_validate(project)

    async def delete(self, project_id: uuid.UUID) -> None:
        """Soft delete project"""
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise NotFoundException(
                message=f"Project not found: {project_id}",
                code=40402,
            )
        await self.repo.soft_delete(project_id)
        logger.info("project.deleted", project_id=str(project_id))
