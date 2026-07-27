"""Trace Schemas (Response DTOs)

Reference: ../docs/phases/phase-5-report.md §4.3
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TraceSpanResponse(BaseModel):
    """Single span in trace tree."""
    id: str
    trace_id: str
    parent_id: str | None = None
    span_type: str
    name: str
    input_data: dict = Field(default_factory=dict)
    output_data: dict = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    status: str = "ok"
    attributes: dict = Field(default_factory=dict)
    children: list[TraceSpanResponse] = Field(default_factory=list)


class TraceResponse(BaseModel):
    """Full trace tree response."""
    id: uuid.UUID
    span_count: int
    total_llm_calls: int
    total_tool_calls: int
    total_tokens: dict
    started_at: datetime
    completed_at: datetime | None
    root_span: TraceSpanResponse | None = None

    model_config = {"from_attributes": True}


class TimelineEvent(BaseModel):
    """Single event in timeline."""
    span_id: str
    name: str
    span_type: str
    start_ms: int  # Offset from trace start
    duration_ms: int
    depth: int
    status: str
    label: str


class TimelineResponse(BaseModel):
    """Timeline view of trace."""
    trace_id: uuid.UUID
    total_duration_ms: int
    events: list[TimelineEvent]
    lanes: dict[str, list[TimelineEvent]]  # Grouped by span_type


class SpanFlatResponse(BaseModel):
    """Flat span list item."""
    id: str
    parent_id: str | None
    span_type: str
    name: str
    duration_ms: int
    status: str
    depth: int = 0
