"""Scenario request/response schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CreateScenarioRequest(BaseModel):
    """Create scenario request"""
    external_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None
    input: dict
    history: list[dict] = Field(default=[])
    memory: dict = Field(default={})
    expected: dict = Field(default={})
    constraints: dict = Field(default={})
    judge_config: dict | None = None
    tags: list[str] = Field(default=[])
    priority: int = Field(default=0, ge=0)
    metadata: dict = Field(default={})


class BatchCreateScenarioRequest(BaseModel):
    """Batch create scenarios request (max 100)"""
    scenarios: list[CreateScenarioRequest] = Field(min_length=1, max_length=100)


class UpdateScenarioRequest(BaseModel):
    """Update scenario request"""
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    input: dict | None = None
    history: list[dict] | None = None
    memory: dict | None = None
    expected: dict | None = None
    constraints: dict | None = None
    judge_config: dict | None = None
    tags: list[str] | None = None
    priority: int | None = Field(default=None, ge=0)
    status: str | None = None


class ScenarioResponse(BaseModel):
    """Scenario detail response"""
    id: UUID
    dataset_id: UUID
    external_id: str
    title: str
    description: str | None
    input: dict
    history: list[dict]
    memory: dict
    expected: dict
    constraints: dict
    judge_config: dict | None
    tags: list[str]
    priority: int
    metadata: dict
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def map_metadata(cls, data):
        if hasattr(data, "__table__"):
            vals = {c.key: getattr(data, c.key) for c in data.__table__.columns}
            vals["input"] = getattr(data, "input_data", vals.get("input", {}))
            vals["metadata"] = getattr(data, "metadata_", vals.get("metadata", {}))
            return vals
        if isinstance(data, dict):
            if "input_data" in data and "input" not in data:
                data["input"] = data.pop("input_data")
            if "metadata_" in data and "metadata" not in data:
                data["metadata"] = data.pop("metadata_")
        return data


class ScenarioBriefResponse(BaseModel):
    """Scenario brief for list view"""
    id: UUID
    external_id: str
    title: str
    tags: list[str]
    priority: int
    status: str

    model_config = {"from_attributes": True}


class ValidationErrorDetail(BaseModel):
    """Single validation error detail"""
    scenario_external_id: str | None = None
    field: str
    message: str


class ValidationResultVO(BaseModel):
    """DSL validation result"""
    valid: bool
    errors: list[ValidationErrorDetail] = Field(default=[])
    warnings: list[str] = Field(default=[])
    scenario_count: int = 0
