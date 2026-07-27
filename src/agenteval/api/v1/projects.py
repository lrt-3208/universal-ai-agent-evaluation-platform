"""Project API endpoints"""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.response import ApiResponse, PageData, success
from agenteval.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
    UpdateProjectRequest,
)
from agenteval.services.project_service import ProjectService

router = APIRouter()


@router.post("/workspaces/{workspace_id}/projects", status_code=201)
async def create_project(
    workspace_id: uuid.UUID,
    request: CreateProjectRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new project in a workspace"""
    service = ProjectService(session)
    result = await service.create(workspace_id, request)
    return JSONResponse(
        status_code=201,
        content=success(data=result).model_dump(mode="json"),
    )


@router.get("/workspaces/{workspace_id}/projects")
async def list_projects(
    workspace_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List projects in a workspace"""
    service = ProjectService(session)
    items, total = await service.list_by_workspace(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
    )
    page_data = PageData.create(items=items, total=total, page=page, page_size=page_size)
    return success(data=page_data)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get project by ID"""
    service = ProjectService(session)
    result = await service.get(project_id)
    return success(data=result)


@router.put("/projects/{project_id}")
async def update_project(
    project_id: uuid.UUID,
    request: UpdateProjectRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update project"""
    service = ProjectService(session)
    result = await service.update(project_id, request)
    return success(data=result)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft delete project"""
    service = ProjectService(session)
    await service.delete(project_id)
    return Response(status_code=204)
