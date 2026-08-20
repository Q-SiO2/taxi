"""API error types and handlers shared by every endpoint family."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from taximobile_api.core.rate_limit import RateLimitUnavailable
from taximobile_api.core.logging import request_route_template


logger = logging.getLogger("taximobile_api")


def error_response(
    *, status_code: int, code: str, message: str, details: Mapping[str, Any] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def public_validation_fields(error: RequestValidationError) -> list[dict[str, str]]:
    """Reduce Pydantic errors to metadata that cannot echo submitted values.

    Pydantic's native error dictionaries include an ``input`` member and may
    include validator context. Returning those dictionaries verbatim can reflect
    passwords, tokens, coordinates, or other private request data to the caller.
    Field locations and stable error types are enough for a client to identify
    invalid controls without reproducing request content.
    """

    fields: list[dict[str, str]] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "request"
        fields.append(
            {
                "field": location,
                "code": str(item.get("type", "invalid_value")),
            }
        )
    return fields


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="The request contains invalid data.",
            details={"fields": public_validation_fields(error)},
        )

    @app.exception_handler(HTTPException)
    async def fastapi_http_error_handler(_: Request, error: HTTPException) -> JSONResponse:
        detail = error.detail if isinstance(error.detail, str) else "The request could not be completed."
        return error_response(status_code=error.status_code, code="REQUEST_REJECTED", message=detail)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_error_handler(_: Request, error: StarletteHTTPException) -> JSONResponse:
        message = "The requested resource was not found." if error.status_code == 404 else "Request failed."
        return error_response(status_code=error.status_code, code="NOT_FOUND" if error.status_code == 404 else "REQUEST_REJECTED", message=message)

    @app.exception_handler(RateLimitUnavailable)
    async def rate_limit_unavailable_handler(_: Request, __: RateLimitUnavailable) -> JSONResponse:
        return error_response(
            status_code=503,
            code="DEPENDENCY_UNAVAILABLE",
            message="The service is temporarily unavailable.",
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
        """Return a stable envelope without exposing exception text or private data."""
        request_id = getattr(request.state, "request_id", "unavailable")
        metrics = getattr(request.app.state, "metrics", None)
        if metrics is not None:
            metrics.record_unhandled_error(type(error).__name__)
        logger.error(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request_route_template(request),
                "status_code": 500,
                "error_type": type(error).__name__,
            },
        )
        response = error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
        )
        response.headers["X-Request-ID"] = request_id
        return response
