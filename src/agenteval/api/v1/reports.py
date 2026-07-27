"""Report API endpoints

Reference: ../docs/phases/phase-5-report.md §5.1
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import async_session_factory, get_session
from agenteval.core.response import ApiResponse, PageData
from agenteval.infra.models.report_model import ReportModel
from agenteval.infra.repositories.report_repo import ReportRepository
from agenteval.schemas.report import CreateReportRequest, ReportResponse
from agenteval.services.report_generator import ReportGenerator

router = APIRouter(tags=["reports"])


async def _generate_report_background(report_id: uuid.UUID, evaluation_id: uuid.UUID, fmt: str):
    """Background task to generate report content."""
    import structlog
    logger = structlog.get_logger()

    async with async_session_factory() as session:
        try:
            repo = ReportRepository(session)
            generator = ReportGenerator()

            # Debug: check if report exists
            existing = await repo.get_by_id(report_id)
            logger.info("report.bg.start", report_id=str(report_id), exists=existing is not None)

            # Collect data
            data = await generator.collect_data(session, evaluation_id)

            # Generate content
            if fmt == "html":
                content_bytes = generator.generate_html(data)
            else:
                content_bytes = generator.generate_json(data)

            content_str = content_bytes.decode("utf-8")

            # Update report
            result = await repo.update_status(
                report_id,
                status="completed",
                content=content_str,
                summary=data.summary.model_dump(),
                metrics_snapshot=data.metrics.model_dump(),
            )
            await session.commit()
            logger.info("report.generated", report_id=str(report_id), format=fmt, updated=result is not None)

        except Exception as e:
            logger.error("report.generation.failed", report_id=str(report_id), error=str(e))
            try:
                await repo.update_status(report_id, status="failed")
                await session.commit()
            except Exception:
                await session.rollback()


@router.post(
    "/evaluations/{evaluation_id}/reports",
    response_model=ApiResponse[ReportResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_report(
    evaluation_id: uuid.UUID,
    request: CreateReportRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Generate a report for an evaluation (returns 202 Accepted)."""
    from agenteval.infra.repositories.evaluation_repo import EvaluationRepository

    eval_repo = EvaluationRepository(session)
    evaluation = await eval_repo.get_by_id(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Create report record
    repo = ReportRepository(session)
    report = ReportModel(
        id=uuid.uuid4(),
        evaluation_id=evaluation_id,
        format=request.format,
        status="generating",
    )
    report = await repo.create(report)

    # Commit immediately so background task can see the report
    await session.commit()

    # Schedule background generation
    background_tasks.add_task(
        _generate_report_background, report.id, evaluation_id, request.format
    )

    return ApiResponse(
        code=0,
        message="Report generation started",
        data=ReportResponse.model_validate(report),
    )


@router.get(
    "/evaluations/{evaluation_id}/reports",
    response_model=ApiResponse[PageData[ReportResponse]],
)
async def list_reports(
    evaluation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all reports for an evaluation."""
    repo = ReportRepository(session)
    reports = await repo.list_by_evaluation(evaluation_id)
    items = [ReportResponse.model_validate(r) for r in reports]
    return ApiResponse(
        code=0,
        data=PageData.create(items, len(items), 1, len(items) or 1),
    )


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[ReportResponse],
)
async def get_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get report metadata."""
    repo = ReportRepository(session)
    report = await repo.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiResponse(code=0, data=ReportResponse.model_validate(report))


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Download report content."""
    repo = ReportRepository(session)
    report = await repo.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report not ready")
    if not report.content:
        raise HTTPException(status_code=404, detail="Report content not found")

    if report.format == "html":
        media_type = "text/html; charset=utf-8"
        filename = f"report_{report_id}.html"
    else:
        media_type = "application/json; charset=utf-8"
        filename = f"report_{report_id}.json"

    return Response(
        content=report.content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{report_id}/preview")
async def preview_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Preview HTML report in browser."""
    repo = ReportRepository(session)
    report = await repo.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report not ready")
    if not report.content:
        raise HTTPException(status_code=404, detail="Report content not found")

    if report.format == "html":
        return HTMLResponse(content=report.content)
    else:
        return Response(
            content=report.content,
            media_type="application/json; charset=utf-8",
        )
