"""Judge Schemas (Request/Response DTOs)

Reference: ../docs/phases/phase-4-judge.md §11
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MetricScoreResponse(BaseModel):
    metric_key: str
    metric_name: str
    score: float
    weight: float = 1.0
    max_score: float = 1.0
    detail: dict = Field(default_factory=dict)
    reasoning: str | None = None


class JudgeResultResponse(BaseModel):
    id: uuid.UUID
    scenario_execution_id: uuid.UUID
    judge_type: str
    judge_config: dict
    status: str
    metric_scores: list
    overall_score: float | None
    overall_verdict: str | None
    reasoning: str | None
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class JudgeConfigValidateRequest(BaseModel):
    judge_configs: list[dict] = Field(description="List of judge configurations to validate")


class JudgeConfigValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
