"""AgentEval Application Entry Point"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agenteval import __version__
from agenteval.api.v1 import router as v1_router
from agenteval.core.config import get_settings
from agenteval.core.exceptions import AgentEvalException
from agenteval.core.logging import configure_logging
from agenteval.core.middleware import AccessLogMiddleware, RequestIDMiddleware
from agenteval.core.redis import close_redis
from agenteval.core.response import ApiResponse
# Ensure all ORM models are registered before any DB operations
import agenteval.infra.models  # noqa: F401

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    settings = get_settings()
    logger.info("application.startup", app_name=settings.app_name, env=settings.app_env)

    # Register built-in adapters
    from agenteval.adapters.builtin import register_builtin_adapters
    register_builtin_adapters()
    logger.info("adapters.registered", types=["http", "openai", "custom"])

    # Register built-in judges (Phase 4)
    from agenteval.judges.builtin import register_builtin_judges
    register_builtin_judges()
    logger.info("judges.registered", types=["rule", "llm"])

    # Register LLM clients (Phase 4)
    from agenteval.llm import LLMClientRegistry
    from agenteval.llm.openai_client import OpenAILLMClient
    LLMClientRegistry.register("openai", OpenAILLMClient)
    logger.info("llm_clients.registered", types=["openai"])

    # Register derived metric providers (Phase 5)
    from agenteval.services.derived_metrics import register_builtin_providers
    register_builtin_providers()
    logger.info("derived_metrics.registered", types=["self_time_ms", "total_tokens", "tool_success_rate"])

    yield
    logger.info("application.shutdown")
    await close_redis()


# Configure logging first
configure_logging()

app = FastAPI(
    title="AgentEval",
    description="Universal AI Agent Evaluation Platform",
    version=__version__,
    lifespan=lifespan,
)

# Register middleware (order matters: outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AccessLogMiddleware)


# Register exception handlers
def _get_request_id(request: Request) -> str | None:
    """Extract request_id from scope state or request state"""
    state = request.scope.get("state", {})
    return state.get("request_id") or getattr(request.state, "request_id", None)


@app.exception_handler(AgentEvalException)
async def agenteval_exception_handler(request: Request, exc: AgentEvalException):
    """Handle all AgentEvalException subclasses"""
    request_id = _get_request_id(request)
    resp = ApiResponse(
        code=exc.code,
        message=exc.message,
        request_id=request_id,
    )
    content = resp.model_dump(mode="json")
    if exc.detail:
        content["detail"] = exc.detail
    return JSONResponse(
        status_code=exc.http_status,
        content=content,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """Handle Pydantic validation errors"""
    request_id = _get_request_id(request)
    errors = exc.errors()
    return JSONResponse(
        status_code=400,
        content=ApiResponse(
            code=40000,
            message=f"Validation error: {errors[0]['msg']}" if errors else "Validation error",
            request_id=request_id,
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception("unhandled.exception", exc_info=exc)
    request_id = _get_request_id(request)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            code=50099,
            message="Internal server error",
            request_id=request_id,
        ).model_dump(mode="json"),
    )


# Register API routes
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "AgentEval",
        "version": __version__,
        "docs": "/docs",
    }
