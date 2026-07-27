"""Judge API endpoints

Reference: ../docs/phases/phase-4-judge.md §11
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import async_session_factory, get_session
from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.core.response import ApiResponse
from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
from agenteval.infra.repositories.execution_repo import ScenarioExecutionRepository
from agenteval.infra.repositories.judge_result_repo import JudgeResultRepository
from agenteval.judges import JudgeRegistry
from agenteval.schemas.judge import (
    JudgeConfigValidateRequest,
    JudgeConfigValidateResponse,
    JudgeResultResponse,
)
from agenteval.services.judge_service import JudgeService

router = APIRouter(tags=["judges"])


@router.post(
    "/evaluations/{evaluation_id}/judge",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_judge(
    evaluation_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger scoring for an evaluation (returns 202 Accepted)."""
    eval_repo = EvaluationRepository(session)
    evaluation = await eval_repo.get_by_id(evaluation_id)
    if not evaluation:
        raise NotFoundException(f"Evaluation not found: {evaluation_id}")

    if evaluation.status not in ("scoring", "completed"):
        raise ConflictException(
            f"Evaluation is not in SCORING state (current: {evaluation.status})")

    # Schedule judge service as background task
    judge_service = JudgeService(async_session_factory)
    background_tasks.add_task(judge_service.judge_evaluation, evaluation_id)

    return ApiResponse(
        code=0,
        message="Judge task scheduled",
        data={"evaluation_id": str(evaluation_id), "status": "scoring"},
    )


@router.get(
    "/scenario-executions/{exec_id}/judge-results",
    response_model=ApiResponse[dict],
)
async def get_judge_results(
    exec_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get all judge results for a scenario execution."""
    # Validate scenario execution exists
    exec_repo = ScenarioExecutionRepository(session)
    scenario_exec = await exec_repo.get_by_id(exec_id)
    if not scenario_exec:
        raise NotFoundException(f"ScenarioExecution not found: {exec_id}")

    repo = JudgeResultRepository(session)
    results = await repo.list_by_scenario_execution(exec_id)

    return ApiResponse(
        code=0,
        message="ok",
        data={
            "items": [JudgeResultResponse.model_validate(r).model_dump() for r in results],
            "total": len(results),
        },
    )


@router.get(
    "/judge-results/{result_id}",
    response_model=ApiResponse[JudgeResultResponse],
)
async def get_judge_result(
    result_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single judge result by ID."""
    repo = JudgeResultRepository(session)
    result = await repo.get_by_id(result_id)
    if not result:
        raise NotFoundException(f"JudgeResult not found: {result_id}")

    return ApiResponse(code=0, message="ok", data=JudgeResultResponse.model_validate(result))


@router.post(
    "/projects/{project_id}/judge-configs/validate",
    response_model=ApiResponse[JudgeConfigValidateResponse],
)
async def validate_judge_configs(
    project_id: uuid.UUID,
    request: JudgeConfigValidateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Validate judge configurations."""
    errors: list[str] = []
    warnings: list[str] = []

    for i, jc in enumerate(request.judge_configs):
        judge_type = jc.get("judge_type")
        if not judge_type:
            errors.append(f"Config[{i}]: missing 'judge_type'")
            continue

        # Check if judge type is registered
        try:
            judge = JudgeRegistry.create(judge_type)
        except Exception as e:
            errors.append(f"Config[{i}]: {e}")
            continue

        # Validate config
        if not judge.validate_config(jc):
            errors.append(f"Config[{i}]: invalid config for judge type '{judge_type}'")

        # Check metrics
        metrics = jc.get("metrics", [])
        if metrics:
            unsupported = [m for m in metrics if m not in judge.supported_metrics]
            if unsupported and judge.supported_metrics:
                warnings.append(
                    f"Config[{i}]: unsupported metrics for '{judge_type}': {unsupported}")

    return ApiResponse(
        code=0,
        message="ok",
        data=JudgeConfigValidateResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        ),
    )
