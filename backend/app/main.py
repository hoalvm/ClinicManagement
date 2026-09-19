"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.routes import api_router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import register_exception_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    # Traceback responses could expose SQL and application internals.  Keep
    # FastAPI's debug exception page disabled in every environment.
    debug=False,
)
register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
