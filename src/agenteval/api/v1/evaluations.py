"""Evaluation API endpoints

Reference: ../docs/phases/phase-3-runner.md §9
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import async_session_factory, get_session
from agenteval.core.response import ApiResponse, PageData
from agenteval.infra.repositories.execution_repo import AgentExecutionRepository, TraceRepository
from agenteval.schemas.evaluation import (
    AgentExecutionResponse,
    CreateEvaluationRequest,
    EvaluationResponse,
    EvaluationStatusResponse,
    ScenarioExecutionResponse,
    TraceResponse,
)
from agenteval.services.evaluation_service import EvaluationService
from agenteval.services.runner import EvaluationRunner

router = APIRouter(tags=["evaluations"])


@router.post(
    "/projects/{project_id}/evaluations",
    response_model=ApiResponse[EvaluationResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_evaluation(
    project_id: uuid.UUID,
    request: CreateEvaluationRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Create and trigger evaluation (returns 202 Accepted)"""
    svc = EvaluationService(session)
    evaluation = await svc.create_evaluation(project_id, request)
    
    # Schedule runner as background task (after response is sent)
    runner = EvaluationRunner(async_session_factory)
    background_tasks.add_task(runner.run_evaluation, evaluation.id)
    
    return ApiResponse(
        code=0,
        message="Evaluation created",
        data=EvaluationResponse.model_validate(evaluation),
    )


@router.get(
    "/projects/{project_id}/evaluations",
    response_model=ApiResponse[PageData[EvaluationResponse]],
)
async def list_evaluations(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
):
    """List evaluations for a project"""
    svc = EvaluationService(session)
    items, total = await svc.list_evaluations(project_id, page, page_size, status_filter)
    return ApiResponse(
        code=0,
        message="ok",
        data=PageData.create(
            items=[EvaluationResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=ApiResponse[EvaluationResponse],
)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get evaluation details"""
    svc = EvaluationService(session)
    evaluation = await svc.get_evaluation(evaluation_id)
    return ApiResponse(code=0, message="ok", data=EvaluationResponse.model_validate(evaluation))


@router.get(
    "/evaluations/{evaluation_id}/executions",
    response_model=ApiResponse[list[ScenarioExecutionResponse]],
)
async def get_executions(
    evaluation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get scenario execution list for an evaluation"""
    svc = EvaluationService(session)
    execs = await svc.get_executions(evaluation_id)
    return ApiResponse(
        code=0,
        message="ok",
        data=[ScenarioExecutionResponse.model_validate(e) for e in execs],
    )


@router.get(
    "/evaluations/{evaluation_id}/executions/{exec_id}",
    response_model=ApiResponse[AgentExecutionResponse],
)
async def get_agent_execution(
    evaluation_id: uuid.UUID,
    exec_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get agent execution details for a scenario execution"""
    svc = EvaluationService(session)
    await svc.get_evaluation(evaluation_id)  # Validate exists
    ae_repo = AgentExecutionRepository(session)
    ae = await ae_repo.get_by_scenario_execution(exec_id)
    if not ae:
        from agenteval.core.exceptions import NotFoundException
        raise NotFoundException(f"Agent execution not found for scenario execution: {exec_id}")
    return ApiResponse(code=0, message="ok", data=AgentExecutionResponse.model_validate(ae))


@router.post(
    "/evaluations/{evaluation_id}/cancel",
    response_model=ApiResponse[EvaluationResponse],
)
async def cancel_evaluation(
    evaluation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Cancel an evaluation"""
    svc = EvaluationService(session)
    evaluation = await svc.cancel_evaluation(evaluation_id)
    return ApiResponse(code=0, message="Evaluation cancelled",
                       data=EvaluationResponse.model_validate(evaluation))


@router.get(
    "/evaluations/{evaluation_id}/status",
    response_model=ApiResponse[EvaluationStatusResponse],
)
async def get_evaluation_status(
    evaluation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get evaluation status with execution counts (polling endpoint)"""
    svc = EvaluationService(session)
    status_data = await svc.get_status(evaluation_id)
    return ApiResponse(
        code=0,
        message="ok",
        data=EvaluationStatusResponse(**status_data),
    )


@router.get(
    "/evaluations/{evaluation_id}/executions/{exec_id}/trace",
    response_model=ApiResponse[TraceResponse],
)
async def get_trace(
    evaluation_id: uuid.UUID,
    exec_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get trace for a scenario execution"""
    svc = EvaluationService(session)
    await svc.get_evaluation(evaluation_id)  # Validate exists

    # Find agent execution first
    ae_repo = AgentExecutionRepository(session)
    ae = await ae_repo.get_by_scenario_execution(exec_id)
    if not ae or not ae.trace_id:
        from agenteval.core.exceptions import NotFoundException
        raise NotFoundException(f"Trace not found for execution: {exec_id}")

    trace_repo = TraceRepository(session)
    trace = await trace_repo.get_by_id(ae.trace_id)
    if not trace:
        from agenteval.core.exceptions import NotFoundException
        raise NotFoundException(f"Trace not found: {ae.trace_id}")

    return ApiResponse(code=0, message="ok", data=TraceResponse.model_validate(trace))
