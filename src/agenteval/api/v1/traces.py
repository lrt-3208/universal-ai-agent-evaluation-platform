"""Trace API endpoints

Reference: ../docs/phases/phase-5-report.md §4.1
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.database import get_session
from agenteval.core.exceptions import NotFoundException
from agenteval.core.response import ApiResponse
from agenteval.infra.repositories.execution_repo import AgentExecutionRepository, TraceRepository
from agenteval.schemas.trace import (
    SpanFlatResponse,
    TimelineResponse,
    TraceResponse,
    TraceSpanResponse,
)
from agenteval.services.timeline_builder import TimelineBuilder
from agenteval.services.trace_enricher import TraceEnricher

router = APIRouter(tags=["traces"])

enricher = TraceEnricher()
timeline_builder = TimelineBuilder()


def _span_dict_to_response(span: dict) -> TraceSpanResponse:
    """Convert span dict to TraceSpanResponse recursively."""
    children = [_span_dict_to_response(c) for c in span.get("children", [])]
    return TraceSpanResponse(
        id=span.get("id", ""),
        trace_id=span.get("trace_id", ""),
        parent_id=span.get("parent_id"),
        span_type=span.get("span_type", ""),
        name=span.get("name", ""),
        input_data=span.get("input_data", {}),
        output_data=span.get("output_data", {}),
        started_at=span.get("started_at"),
        completed_at=span.get("completed_at"),
        duration_ms=span.get("duration_ms", 0),
        status=span.get("status", "ok"),
        attributes=span.get("attributes", {}),
        children=children,
    )


def _flatten_spans(span: dict, depth: int = 0) -> list[SpanFlatResponse]:
    """Flatten span tree to list."""
    result = [SpanFlatResponse(
        id=span.get("id", ""),
        parent_id=span.get("parent_id"),
        span_type=span.get("span_type", ""),
        name=span.get("name", ""),
        duration_ms=span.get("duration_ms", 0),
        status=span.get("status", "ok"),
        depth=depth,
    )]
    for child in span.get("children", []):
        result.extend(_flatten_spans(child, depth + 1))
    return result


@router.get(
    "/traces/{trace_id}",
    response_model=ApiResponse[TraceResponse],
)
async def get_trace(
    trace_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get full trace tree with enriched attributes."""
    repo = TraceRepository(session)
    trace = await repo.get_by_id(trace_id)
    if not trace:
        raise NotFoundException(f"Trace not found: {trace_id}")

    # Enrich span tree
    span_tree = enricher.enrich(trace.span_tree)

    # Build response
    root_span = _span_dict_to_response(span_tree) if span_tree else None

    return ApiResponse(
        code=0,
        message="ok",
        data=TraceResponse(
            id=trace.id,
            span_count=trace.span_count,
            total_llm_calls=trace.total_llm_calls,
            total_tool_calls=trace.total_tool_calls,
            total_tokens=trace.total_tokens,
            started_at=trace.started_at,
            completed_at=trace.completed_at,
            root_span=root_span,
        ),
    )


@router.get(
    "/traces/{trace_id}/spans",
    response_model=ApiResponse[list[SpanFlatResponse]],
)
async def get_trace_spans(
    trace_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get flat span list for a trace."""
    repo = TraceRepository(session)
    trace = await repo.get_by_id(trace_id)
    if not trace:
        raise NotFoundException(f"Trace not found: {trace_id}")

    spans = _flatten_spans(trace.span_tree) if trace.span_tree else []
    return ApiResponse(code=0, message="ok", data=spans)


@router.get(
    "/traces/{trace_id}/timeline",
    response_model=ApiResponse[TimelineResponse],
)
async def get_trace_timeline(
    trace_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get timeline view for a trace."""
    repo = TraceRepository(session)
    trace = await repo.get_by_id(trace_id)
    if not trace:
        raise NotFoundException(f"Trace not found: {trace_id}")

    timeline = timeline_builder.build(
        trace_id=trace.id,
        span_tree=trace.span_tree,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
    )
    return ApiResponse(code=0, message="ok", data=timeline)


@router.get(
    "/agent-executions/{exec_id}/trace",
    response_model=ApiResponse[TraceResponse],
)
async def get_execution_trace(
    exec_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get trace for an agent execution."""
    ae_repo = AgentExecutionRepository(session)
    ae = await ae_repo.get_by_id(exec_id)
    if not ae:
        raise NotFoundException(f"AgentExecution not found: {exec_id}")
    if not ae.trace_id:
        raise NotFoundException(f"No trace for execution: {exec_id}")

    trace_repo = TraceRepository(session)
    trace = await trace_repo.get_by_id(ae.trace_id)
    if not trace:
        raise NotFoundException(f"Trace not found: {ae.trace_id}")

    span_tree = enricher.enrich(trace.span_tree)
    root_span = _span_dict_to_response(span_tree) if span_tree else None

    return ApiResponse(
        code=0,
        message="ok",
        data=TraceResponse(
            id=trace.id,
            span_count=trace.span_count,
            total_llm_calls=trace.total_llm_calls,
            total_tool_calls=trace.total_tool_calls,
            total_tokens=trace.total_tokens,
            started_at=trace.started_at,
            completed_at=trace.completed_at,
            root_span=root_span,
        ),
    )
