"""Dataset request/response schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CreateDatasetRequest(BaseModel):
    """Create empty dataset request"""
    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32, pattern=r"^\d+\.\d+\.\d+$")
    description: str | None = Field(default=None, max_length=512)
    tags: list[str] = Field(default=[])
    metadata: dict = Field(default={})


class ImportDatasetRequest(BaseModel):
    """Import dataset from DSL content"""
    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32, pattern=r"^\d+\.\d+\.\d+$")
    description: str | None = Field(default=None, max_length=512)
    format: str = Field(pattern=r"^(yaml|json)$")
    content: str  # DSL file content (inline)
    tags: list[str] = Field(default=[])
    metadata: dict = Field(default={})


class UpdateDatasetRequest(BaseModel):
    """Update dataset metadata"""
    description: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None


class DatasetResponse(BaseModel):
    """Dataset detail response"""
    id: UUID
    project_id: UUID
    name: str
    version: str
    description: str | None
    format: str
    source_uri: str | None
    scenario_count: int
    tags: list[str]
    metadata: dict
    is_latest: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def map_metadata(cls, data):
        if hasattr(data, "__table__"):
            # ORM object: extract metadata_ -> metadata
            vals = {c.key: getattr(data, c.key) for c in data.__table__.columns}
            vals["metadata"] = getattr(data, "metadata_", vals.get("metadata", {}))
            return vals
        if isinstance(data, dict) and "metadata_" in data and "metadata" not in data:
            data["metadata"] = data.pop("metadata_")
        return data


class DatasetBriefResponse(BaseModel):
    """Dataset brief for list view"""
    id: UUID
    name: str
    version: str
    scenario_count: int
    is_latest: bool

    model_config = {"from_attributes": True}
