"""Middleware - Request ID injection and access logging (pure ASGI)"""

import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger()


class RequestIDMiddleware:
    """Inject X-Request-ID into request state and response headers (pure ASGI)"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id: str | None = None

        # Extract request_id from headers
        headers = dict(scope.get("headers", []))
        raw = headers.get(b"x-request-id")
        if raw:
            request_id = raw.decode()
        else:
            request_id = str(uuid.uuid4())

        # Store in scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append(
                    (b"x-request-id", request_id.encode())
                )
                message["headers"] = headers_list
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class AccessLogMiddleware:
    """Log request method, path, status, and latency (pure ASGI)"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 0

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "http.request",
                method=scope.get("method", ""),
                path=scope.get("path", ""),
                status=status_code,
                latency_ms=elapsed_ms,
            )
