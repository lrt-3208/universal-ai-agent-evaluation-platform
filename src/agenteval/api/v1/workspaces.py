"""Workspace API endpoints"""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.response import ApiResponse, PageData, success
from agenteval.schemas.common import PaginationParams
from agenteval.schemas.workspace import (
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest,
    WorkspaceBriefResponse,
    WorkspaceResponse,
)
from agenteval.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces")


@router.post("", status_code=201)
async def create_workspace(
    request: CreateWorkspaceRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new workspace"""
    service = WorkspaceService(session)
    result = await service.create(request)
    return JSONResponse(
        status_code=201,
        content=success(data=result).model_dump(mode="json"),
    )


@router.get("")
async def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    session: AsyncSession = Depends(get_session),
):
    """List workspaces with pagination"""
    service = WorkspaceService(session)
    items, total = await service.list(page=page, page_size=page_size, search=search)
    page_data = PageData.create(items=items, total=total, page=page, page_size=page_size)
    return success(data=page_data)


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get workspace by ID"""
    service = WorkspaceService(session)
    result = await service.get(workspace_id)
    return success(data=result)


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: uuid.UUID,
    request: UpdateWorkspaceRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update workspace"""
    service = WorkspaceService(session)
    result = await service.update(workspace_id, request)
    return success(data=result)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete workspace (cascade soft delete projects)"""
    service = WorkspaceService(session)
    await service.delete(workspace_id)
    return Response(status_code=204)
