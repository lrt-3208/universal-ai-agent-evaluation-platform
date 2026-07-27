"""Regression schemas.

Reference: ../docs/phases/phase-6-regression.md §4.2
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateRegressionRequest(BaseModel):
    """创建回归分析请求."""

    name: str = Field(min_length=1, max_length=128)
    baseline_evaluation_id: UUID
    target_evaluation_id: UUID
    # 可选：指定对比的指标子集
    metrics_filter: list[str] = Field(default_factory=list)
    # 可选：回归阈值（低于此 delta 视为 unchanged）
    regression_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    # 可选：Flaky 检测窗口（对比最近 N 次同场景评测）
    flaky_window: int = Field(default=0, ge=0, le=10)


class RegressionResponse(BaseModel):
    """回归分析响应."""

    id: UUID
    project_id: UUID
    name: str
    baseline_evaluation_id: UUID
    target_evaluation_id: UUID
    status: str
    overall_verdict: str | None = None
    summary: dict | None = None
    metric_diffs: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScenarioDiffResponse(BaseModel):
    """场景差异响应."""

    scenario_id: UUID
    external_id: str
    title: str = ""
    baseline_score: float | None = None
    target_score: float | None = None
    score_delta: float | None = None
    baseline_verdict: str | None = None
    target_verdict: str | None = None
    verdict: str  # improved | regressed | unchanged | flaky
    metric_deltas: dict[str, float] = Field(default_factory=dict)
    notes: str | None = None


class RegressionDetailResponse(RegressionResponse):
    """回归分析详情响应（含 scenario_diffs）."""

    scenario_diffs: list[ScenarioDiffResponse] = Field(default_factory=list)


class ReplayRequest(BaseModel):
    """数据集回放请求."""

    agent_config: dict
    name: str | None = None


class ReplayResponse(BaseModel):
    """数据集回放响应."""

    evaluation_id: UUID
    message: str
