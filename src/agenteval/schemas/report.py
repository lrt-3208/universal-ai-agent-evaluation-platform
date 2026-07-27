"""Report Schemas (Request/Response DTOs)

Reference: ../docs/phases/phase-5-report.md §5.1
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationSummary(BaseModel):
    """Evaluation summary for report."""
    id: uuid.UUID
    name: str
    version_label: str | None = None
    dataset_name: str = ""
    dataset_version: str = ""
    agent_config: dict = Field(default_factory=dict)
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int = 0


class MetricsSnapshot(BaseModel):
    """Metrics snapshot for report."""
    scenario_count: int = 0
    executed_count: int = 0
    scored_count: int = 0
    pass_rate: float = 0.0
    metric_aggregates: dict = Field(default_factory=dict)
    cost_total_usd: float = 0.0
    latency_avg_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0


class ScenarioResultItem(BaseModel):
    """Single scenario result in report."""
    scenario_id: uuid.UUID
    external_id: str = ""
    title: str = ""
    status: str
    overall_score: float | None = None
    overall_verdict: str | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    metric_scores: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    error_message: str | None = None


class TraceHighlight(BaseModel):
    """Trace highlight item."""
    scenario_external_id: str
    span_type: str
    span_name: str
    duration_ms: int
    status: str
    detail: str


class ReportSummary(BaseModel):
    """Report summary with key findings."""
    total_scenarios: int = 0
    pass_rate: float = 0.0
    overall_score: float = 0.0
    failed_scenarios: int = 0
    top_failed_metrics: list[dict] = Field(default_factory=list)
    cost_total_usd: float = 0.0
    duration_seconds: int = 0
    key_findings: list[str] = Field(default_factory=list)


class ReportData(BaseModel):
    """Full report data for rendering."""
    evaluation: EvaluationSummary
    metrics: MetricsSnapshot
    scenario_results: list[ScenarioResultItem] = Field(default_factory=list)
    trace_highlights: list[TraceHighlight] = Field(default_factory=list)
    summary: ReportSummary


class CreateReportRequest(BaseModel):
    """Request to create a report."""
    format: str = Field(default="html", pattern=r"^(json|html)$")


class ReportResponse(BaseModel):
    """Report response DTO."""
    id: uuid.UUID
    evaluation_id: uuid.UUID
    format: str
    status: str
    content_uri: str | None = None
    summary: dict | None = None
    metrics_snapshot: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
