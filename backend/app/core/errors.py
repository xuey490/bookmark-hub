from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Business error that is rendered with the standard response envelope."""

    def __init__(self, status_code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.data = data


def envelope(code: int = 0, message: str = "ok", data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def ok(data: Any = None) -> dict[str, Any]:
    return envelope(0, "ok", data)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope(exc.status_code, exc.message, exc.data),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "request failed"
        headers = getattr(exc, "headers", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope(exc.status_code, message, None),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = "invalid request"
        if errors:
            first = errors[0]
            loc = ".".join(str(part) for part in first.get("loc", []) if part != "body")
            detail = str(first.get("msg", "invalid value"))
            message = f"{loc}: {detail}" if loc else detail
        return JSONResponse(status_code=422, content=envelope(422, message, None))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=envelope(500, "internal server error", None),
        )
