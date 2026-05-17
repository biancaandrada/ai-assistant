"""Request ID + global error handler."""
import uuid
import time
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .errors import AppError
from .logging import get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to each request and log timing."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "unhandled exception",
                extra={"request_id": request_id, "path": request.url.path,
                       "method": request.method},
            )
            raise
        else:
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.1f}ms)",
                extra={"request_id": request_id, "path": request.url.path,
                       "method": request.method},
            )
            response.headers["x-request-id"] = request_id
            return response


def register_exception_handlers(app: FastAPI) -> None:
    """Convert AppError + uncaught exceptions to clean JSON responses."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        logger.warning(f"AppError: {exc.code} — {exc.message}", extra={"request_id": rid})
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def _handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        logger.exception("unhandled exception", extra={"request_id": rid})
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Internal server error"}},
        )
