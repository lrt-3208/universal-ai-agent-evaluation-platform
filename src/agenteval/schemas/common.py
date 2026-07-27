"""Common schema types"""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Common pagination query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str = Field(default="")
    sort: str = Field(default="-created_at")
