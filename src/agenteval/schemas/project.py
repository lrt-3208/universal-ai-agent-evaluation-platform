"""Project request/response schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentConfigSchema(BaseModel):
    """Agent configuration schema"""
    adapter_type: str  # "http" | "openai" | "custom"
    endpoint: str
    model: str = ""
    api_key_ref: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    system_prompt: str = ""
    headers: dict = {}


class CreateProjectRequest(BaseModel):
    """Create project request body"""
    name: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=512)
    agent_config: AgentConfigSchema
    default_judge_config: dict | None = None
    tags: list[str] = Field(default=[])


class UpdateProjectRequest(BaseModel):
    """Update project request body"""
    name: str | None = None
    description: str | None = None
    agent_config: AgentConfigSchema | None = None
    default_judge_config: dict | None = None
    tags: list[str] | None = None


class ProjectResponse(BaseModel):
    """Project detail response"""
    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str | None
    agent_config: dict
    default_judge_config: dict | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
