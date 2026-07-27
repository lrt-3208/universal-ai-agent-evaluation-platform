"""Regression API endpoints.

Reference: ../docs/phases/phase-6-regression.md §9
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.exceptions import AgentEvalException, NotFoundException
from agenteval.infra.repositories.regression_repo import RegressionRepository
from agenteval.schemas.regression import (
    CreateRegressionRequest,
    RegressionDetailResponse,
    RegressionResponse,
    ReplayRequest,
    ReplayResponse,
    ScenarioDiffResponse,
)
from agenteval.services.regression.dataset_replay import DatasetReplayService
from agenteval.services.regression.diff_report_generator import DiffReportGenerator, RegressionReportData
from agenteval.services.regression.regression_service import RegressionService

router = APIRouter()


# ============================================================================
# Regression Analysis
# ============================================================================


@router.post(
    "/projects/{project_id}/regressions",
    response_model=RegressionDetailResponse,
    status_code=201,
)
async def create_regression(
    project_id: UUID,
    request: CreateRegressionRequest,
    session: AsyncSession = Depends(get_session),
):
    """创建回归分析.

    对比两次已完成的评测，计算场景级和指标级差异。
    """
    service = RegressionService(session)
    regression = await service.create_regression(request, project_id)
    await session.commit()

    # 构建响应
    scenario_diffs = [
        ScenarioDiffResponse(**diff) for diff in (regression.scenario_diffs or [])
    ]
    return RegressionDetailResponse(
        id=regression.id,
        project_id=regression.project_id,
        name=regression.name,
        baseline_evaluation_id=regression.baseline_evaluation_id,
        target_evaluation_id=regression.target_evaluation_id,
        status=regression.status,
        overall_verdict=regression.overall_verdict,
        summary=regression.summary,
        metric_diffs=regression.metric_diffs,
        started_at=regression.started_at,
        completed_at=regression.completed_at,
        error_message=regression.error_message,
        created_at=regression.created_at,
        updated_at=regression.updated_at,
        scenario_diffs=scenario_diffs,
    )


@router.get(
    "/projects/{project_id}/regressions",
    response_model=list[RegressionResponse],
)
async def list_regressions(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """分页查询回归分析列表."""
    repo = RegressionRepository(session)
    regressions = await repo.list_by_project(project_id, limit=limit, offset=offset)
    return [RegressionResponse.model_validate(r) for r in regressions]


@router.get(
    "/regressions/{regression_id}",
    response_model=RegressionDetailResponse,
)
async def get_regression(
    regression_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """获取回归分析详情（含 scenario_diffs）."""
    repo = RegressionRepository(session)
    regression = await repo.get_by_id(regression_id)

    if not regression:
        raise NotFoundException("Regression", str(regression_id))

    scenario_diffs = [
        ScenarioDiffResponse(**diff) for diff in (regression.scenario_diffs or [])
    ]
    return RegressionDetailResponse(
        id=regression.id,
        project_id=regression.project_id,
        name=regression.name,
        baseline_evaluation_id=regression.baseline_evaluation_id,
        target_evaluation_id=regression.target_evaluation_id,
        status=regression.status,
        overall_verdict=regression.overall_verdict,
        summary=regression.summary,
        metric_diffs=regression.metric_diffs,
        started_at=regression.started_at,
        completed_at=regression.completed_at,
        error_message=regression.error_message,
        created_at=regression.created_at,
        updated_at=regression.updated_at,
        scenario_diffs=scenario_diffs,
    )


# ============================================================================
# Dataset Replay
# ============================================================================


@router.post(
    "/evaluations/{evaluation_id}/replay",
    response_model=ReplayResponse,
    status_code=201,
)
async def replay_evaluation(
    evaluation_id: UUID,
    request: ReplayRequest,
    session: AsyncSession = Depends(get_session),
):
    """数据集回放.

    使用基线评测的 Dataset + 新 Agent 配置创建新评测。
    """
    service = DatasetReplayService(session)
    new_eval_id = await service.replay(
        baseline_evaluation_id=evaluation_id,
        new_agent_config=request.agent_config,
        name=request.name,
    )
    await session.commit()

    return ReplayResponse(
        evaluation_id=new_eval_id,
        message=f"Replay evaluation created: {new_eval_id}",
    )


# ============================================================================
# Diff Report
# ============================================================================


@router.get("/regressions/{regression_id}/report")
async def get_regression_report(
    regression_id: UUID,
    format: str = Query(default="html", pattern="^(html|json)$"),
    session: AsyncSession = Depends(get_session),
):
    """生成/获取回归对比报告."""
    from fastapi.responses import HTMLResponse, Response

    from agenteval.infra.repositories.evaluation_repo import EvaluationRepository

    repo = RegressionRepository(session)
    regression = await repo.get_by_id(regression_id)

    if not regression:
        raise NotFoundException("Regression", str(regression_id))

    if regression.status != "completed":
        raise AgentEvalException(40911, "Regression analysis not completed", 409)

    # 获取评测名称
    eval_repo = EvaluationRepository(session)
    baseline_eval = await eval_repo.get_by_id(regression.baseline_evaluation_id)
    target_eval = await eval_repo.get_by_id(regression.target_evaluation_id)

    # 构建报告数据
    scenario_diffs = regression.scenario_diffs or []

    # 排序获取 Top 回归和 Top 改进
    sorted_by_delta = sorted(
        [d for d in scenario_diffs if d.get("score_delta") is not None],
        key=lambda x: x.get("score_delta", 0),
    )
    top_regressions = sorted_by_delta[:5]  # 最差的 5 个
    top_improvements = sorted_by_delta[-5:][::-1]  # 最好的 5 个

    report_data = RegressionReportData(
        regression_id=regression.id,
        name=regression.name,
        baseline_name=baseline_eval.name if baseline_eval else "Unknown",
        target_name=target_eval.name if target_eval else "Unknown",
        baseline_version=baseline_eval.version_label if baseline_eval else None,
        target_version=target_eval.version_label if target_eval else None,
        created_at=regression.created_at,
        summary=regression.summary or {},
        metric_diffs=regression.metric_diffs or {},
        scenario_diffs=scenario_diffs,
        top_regressions=top_regressions,
        top_improvements=top_improvements,
    )

    generator = DiffReportGenerator()

    if format == "json":
        content = generator.generate_json(report_data)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="regression_{regression_id}.json"'},
        )
    else:
        content = generator.generate_html(report_data)
        return HTMLResponse(content=content.decode("utf-8"))
