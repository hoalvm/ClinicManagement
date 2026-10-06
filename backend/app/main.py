from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Import models so SQLAlchemy can resolve all table mappings
import backend.app.models  # noqa: F401 – side-effect import
from backend.app.api.deps import get_current_user as api_get_current_user
from backend.app.api.routes import api_router
from backend.app.core.audit import audit_request_id
from backend.app.core.clock import clinic_now
from backend.app.core.config import get_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.login_throttle import login_throttle
from backend.app.core.security import create_access_token, logout_access_token, verify_password
from backend.app.db.session import engine
from backend.app.models import User
from backend.app.ops.production_preflight import validate_production_database
from backend.app.schemas.auth import CurrentUserResponse
from backend.app.services.auth_service import DUMMY_PASSWORD_HASH, AuthService

from . import schemas
from .database import get_db
from .routers import clinics, doctor_portal, doctors, schedules, specialties, statistics, users

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Fail startup when a production instance cannot reach its database."""

    if settings.app_mode == "production":
        with engine.connect() as connection:
            validate_production_database(connection, settings.db_name)
    yield


app = FastAPI(
    title="Clinic Management API",
    docs_url=None if settings.app_mode == "production" else "/docs",
    redoc_url=None if settings.app_mode == "production" else "/redoc",
    openapi_url=None if settings.app_mode == "production" else "/openapi.json",
    lifespan=lifespan,
)

if settings.app_mode == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[urlsplit(settings.api_public_base_url).hostname, "127.0.0.1", "localhost"],
    )


@app.middleware("http")
async def security_response_headers(request: Request, call_next):
    request.state.request_id = uuid4().hex
    token = audit_request_id.set(request.state.request_id)
    try:
        response = await call_next(request)
    finally:
        audit_request_id.reset(token)
    response.headers["X-Request-ID"] = request.state.request_id
    if settings.app_mode == "production":
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
    return response

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health_check():
    if settings.app_mode == "production":
        return readiness_check()
    return {"status": "ok"}


@app.get("/health/live")
def liveness_check():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable") from exc
    return {"status": "ok", "database": "ok"}


@app.get("/api/v1/system/time")
def clinic_time():
    settings = get_settings()
    return {
        "clinic_now": clinic_now().isoformat(),
        "timezone": settings.clinic_timezone,
        "demo_mode": settings.app_mode == "demo",
        "clock_fixed": settings.app_mode == "demo" and settings.clinic_demo_now is not None,
        "project_database": settings.db_name if settings.app_mode == "demo" else None,
    }


@app.post("/auth/login", response_model=schemas.Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    login_throttle.check(request, form_data.username)
    # Use the new models package (snake_case attrs)
    from backend.app.models import User
    user = db.query(User).filter(User.username == form_data.username.strip().lower()).first()
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(form_data.password, password_hash)
    if not user or not password_valid or not user.is_active:
        login_throttle.failed(request, form_data.username)
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    if user.role == "DOCTOR" and (user.doctor is None or not user.doctor.is_active):
        login_throttle.failed(request, form_data.username)
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    if user.role == "PATIENT" and user.patient is None:
        login_throttle.failed(request, form_data.username)
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    login_throttle.succeeded(request, form_data.username)
    token = create_access_token(user_id=user.user_id, role=user.role, session=db)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=CurrentUserResponse)
def legacy_current_user(current_user: User = Depends(api_get_current_user)) -> CurrentUserResponse:
    """Share the same live account checks with the desktop legacy login path."""

    return AuthService.current_user_response(current_user)


@app.post("/auth/logout", status_code=204)
def legacy_logout(
    request: Request,
    current_user: User = Depends(api_get_current_user),
    db: Session = Depends(get_db),
) -> None:
    token = request.headers["authorization"].split(" ", 1)[1]
    logout_access_token(db, token, actor_role=current_user.role)


app.include_router(users.router)
app.include_router(doctors.router)
app.include_router(specialties.router)
app.include_router(clinics.router)
app.include_router(schedules.router)
app.include_router(statistics.router)
app.include_router(doctor_portal.router)
app.include_router(api_router)
