"""Application exceptions and safe FastAPI error responses."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """A controlled application error safe to return to API callers."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AuthenticationError(AppError):
    def __init__(self, detail: str = "Invalid or expired authentication credentials.") -> None:
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppError):
    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status.HTTP_409_CONFLICT)


class InternalServerError(AppError):
    def __init__(self, detail: str = "An unexpected server error occurred.") -> None:
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Return JSON-safe errors without echoing inputs or validator exceptions."""

    safe_errors: list[dict[str, Any]] = []
    for error in exc.errors():
        # Pydantic may put a ValueError instance in ``ctx["error"]``.  Keeping
        # that context would make JSONResponse serialization fail and turn a
        # legitimate validation failure into a 500 response.
        safe_error = {key: error[key] for key in ("type", "loc", "msg") if key in error}
        safe_errors.append(safe_error)
    return safe_errors


def register_exception_handlers(app: FastAPI) -> None:
    """Install uniform handlers without exposing database or stack details."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        headers = None
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            headers = {"WWW-Authenticate": "Bearer"}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            # Literal keeps compatibility across the supported FastAPI/
            # Starlette range (the symbolic name changed in newer releases).
            status_code=422,
            content={"detail": _safe_validation_errors(exc)},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected server error occurred."},
        )
