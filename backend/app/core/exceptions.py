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


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Remove raw inputs so validation responses never echo passwords."""

    safe_errors: list[dict[str, Any]] = []
    for error in exc.errors():
        safe_error = {
            key: value for key, value in error.items() if key in {"type", "loc", "msg", "ctx"}
        }
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
