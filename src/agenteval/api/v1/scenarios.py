"""Scenario API endpoints"""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.response import PageData, success
from agenteval.schemas.scenario import (
    BatchCreateScenarioRequest,
    CreateScenarioRequest,
    UpdateScenarioRequest,
)
from agenteval.services.scenario_service import ScenarioService

router = APIRouter()


@router.post("/datasets/{dataset_id}/scenarios", status_code=201)
async def create_scenario(
    dataset_id: uuid.UUID,
    request: CreateScenarioRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a single scenario"""
    service = ScenarioService(session)
    result = await service.create(dataset_id, request)
    return JSONResponse(
        status_code=201,
        content=success(data=result).model_dump(mode="json"),
    )


@router.post("/datasets/{dataset_id}/scenarios/batch", status_code=201)
async def batch_create_scenarios(
    dataset_id: uuid.UUID,
    request: BatchCreateScenarioRequest,
    session: AsyncSession = Depends(get_session),
):
    """Batch create scenarios (max 100)"""
    service = ScenarioService(session)
    results = await service.batch_create(dataset_id, request.scenarios)
    return JSONResponse(
        status_code=201,
        content=success(data=results).model_dump(mode="json"),
    )


@router.get("/datasets/{dataset_id}/scenarios")
async def list_scenarios(
    dataset_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tags: str = Query("", description="Comma-separated tags, AND filter"),
    status: str = Query("", description="draft/active/archived"),
    priority_min: int = Query(0, ge=0),
    search: str = Query("", description="Search by title/external_id"),
    sort: str = Query("-priority", description="Sort field"),
    session: AsyncSession = Depends(get_session),
):
    """List scenarios with advanced filtering"""
    service = ScenarioService(session)
    items, total = await service.list_by_dataset(
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
        tags=tags,
        status=status,
        priority_min=priority_min,
        search=search,
        sort=sort,
    )
    page_data = PageData.create(items=items, total=total, page=page, page_size=page_size)
    return success(data=page_data)


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get scenario by ID"""
    service = ScenarioService(session)
    result = await service.get(scenario_id)
    return success(data=result)


@router.put("/scenarios/{scenario_id}")
async def update_scenario(
    scenario_id: uuid.UUID,
    request: UpdateScenarioRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update scenario"""
    service = ScenarioService(session)
    result = await service.update(scenario_id, request)
    return success(data=result)


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft delete scenario"""
    service = ScenarioService(session)
    await service.delete(scenario_id)
    return Response(status_code=204)
