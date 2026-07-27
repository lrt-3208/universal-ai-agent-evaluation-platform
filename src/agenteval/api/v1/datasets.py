"""Dataset API endpoints"""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.response import ApiResponse, PageData, success
from agenteval.schemas.dataset import (
    CreateDatasetRequest,
    DatasetResponse,
    ImportDatasetRequest,
    UpdateDatasetRequest,
)
from agenteval.services.dataset_import_service import DatasetImportService
from agenteval.services.dataset_service import DatasetService

router = APIRouter()


@router.post("/projects/{project_id}/datasets", status_code=201)
async def create_dataset(
    project_id: uuid.UUID,
    request: CreateDatasetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create an empty dataset"""
    service = DatasetService(session)
    result = await service.create(project_id, request)
    return JSONResponse(
        status_code=201,
        content=success(data=result).model_dump(mode="json"),
    )


@router.get("/projects/{project_id}/datasets")
async def list_datasets(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List datasets in a project"""
    service = DatasetService(session)
    items, total = await service.list_by_project(
        project_id=project_id, page=page, page_size=page_size
    )
    page_data = PageData.create(items=items, total=total, page=page, page_size=page_size)
    return success(data=page_data)


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get dataset by ID"""
    service = DatasetService(session)
    result = await service.get(dataset_id)
    return success(data=result)


@router.put("/datasets/{dataset_id}")
async def update_dataset(
    dataset_id: uuid.UUID,
    request: UpdateDatasetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update dataset metadata"""
    service = DatasetService(session)
    result = await service.update(dataset_id, request)
    return success(data=result)


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft delete dataset (cascade scenarios)"""
    service = DatasetService(session)
    await service.delete(dataset_id)
    return Response(status_code=204)


@router.post("/projects/{project_id}/datasets/import", status_code=201)
async def import_dataset(
    project_id: uuid.UUID,
    request: ImportDatasetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Import dataset from DSL content"""
    service = DatasetImportService(session)
    result = await service.import_dataset(project_id, request)
    return JSONResponse(
        status_code=201,
        content=success(data=result).model_dump(mode="json"),
    )


@router.post("/projects/{project_id}/datasets/import/validate")
async def validate_import(
    project_id: uuid.UUID,
    request: ImportDatasetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Validate DSL content without persisting"""
    service = DatasetImportService(session)
    result = await service.validate_only(request)
    return success(data=result)


@router.get("/datasets/{dataset_id}/export")
async def export_dataset(
    dataset_id: uuid.UUID,
    format: str = Query("yaml", pattern="^(yaml|json)$"),
    session: AsyncSession = Depends(get_session),
):
    """Export dataset as DSL file"""
    from fastapi.responses import Response as FastAPIResponse

    service = DatasetImportService(session)
    content = await service.export_dataset(dataset_id, format=format)

    content_type = "application/x-yaml" if format == "yaml" else "application/json"
    return FastAPIResponse(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename=dataset.{format}"},
    )
