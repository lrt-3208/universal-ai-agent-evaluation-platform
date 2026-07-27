"""Unified API response wrapper

Reference: ../tech-spec.md §5 API Response Format
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified response format for all API endpoints"""

    code: int = 0
    message: str = "success"
    data: T | None = None
    request_id: str | None = None


class PageData(BaseModel, Generic[T]):
    """Paginated list response"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PageData[T]":
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


def success(data: Any = None, request_id: str | None = None) -> ApiResponse:
    """Create a success response"""
    return ApiResponse(code=0, message="success", data=data, request_id=request_id)


def error(
    code: int,
    message: str,
    request_id: str | None = None,
) -> ApiResponse:
    """Create an error response"""
    return ApiResponse(code=code, message=message, data=None, request_id=request_id)
