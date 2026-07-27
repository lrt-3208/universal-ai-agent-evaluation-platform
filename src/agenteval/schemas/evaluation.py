"""Evaluation Schemas (Request/Response DTOs)

Reference: ../docs/phases/phase-3-runner.md §9
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class EvaluationConfigSchema(BaseModel):
    max_concurrent: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=120, ge=10, le=3600)
    retry_count: int = Field(default=2, ge=0, le=5)
    retry_delay_seconds: int = Field(default=5, ge=1, le=60)
    collect_trace: bool = True
    auto_judge: bool = True  # Phase 4
    filter_tags: list[str] = Field(default_factory=list)
    filter_priority_min: int = Field(default=0, ge=0)


class CreateEvaluationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    dataset_id: uuid.UUID
    agent_config: dict = Field(description="Agent adapter configuration")
    judge_configs: list[dict] = Field(default_factory=list)
    version_label: str | None = None
    config: EvaluationConfigSchema = Field(default_factory=EvaluationConfigSchema)


class EvaluationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    dataset_id: uuid.UUID
    agent_config: dict
    judge_configs: list
    status: str
    config: dict
    version_label: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScenarioExecutionResponse(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    scenario_id: uuid.UUID
    status: str
    overall_score: float | None
    overall_verdict: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    retry_count: int

    model_config = {"from_attributes": True}


class AgentExecutionResponse(BaseModel):
    id: uuid.UUID
    scenario_execution_id: uuid.UUID
    agent_adapter_type: str
    agent_config: dict
    agent_version: str | None
    status: str
    conversation_data: dict | None
    trace_id: uuid.UUID | None
    latency_ms: int | None
    cost_usd: float | None
    retry_count: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class TraceResponse(BaseModel):
    id: uuid.UUID
    span_tree: dict
    span_count: int
    total_llm_calls: int
    total_tool_calls: int
    total_tokens: dict
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class EvaluationStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    total_scenarios: int
    completed: int
    failed: int
    timeout: int
    skipped: int
    pending: int
    running: int
