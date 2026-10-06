"""Fail-closed production configuration and login guard checks."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request

import backend.app.main as main_module
from backend.app.api import deps as api_deps
from backend.app.api.routes import auth as auth_routes
from backend.app.core.config import Settings
from backend.app.core.login_throttle import MAX_ACCOUNT_FAILURES, LoginThrottle
from backend.app.core.security import TokenPayload
from backend.app.routers import doctors as doctors_router
from backend.app.routers import users as users_router
from backend.app.schemas import DoctorCreate, DoctorUpdate, UserCreate, UserUpdate
from frontend.core.config import FrontendSettings

PRODUCTION = {
    "app_mode": "production",
    "db_name": "ClinicManagementDB",
    "db_user": "clinic_app",
    "db_password": "private-production-sql-password",
    "db_encrypt": "yes",
    "db_trust_server_certificate": "no",
    "jwt_secret": "A" * 48,
    "api_public_base_url": "https://clinic.example.test",
    "api_host": "127.0.0.1",
    "clinic_demo_now": None,
}


def _production_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **(PRODUCTION | overrides))


@pytest.mark.parametrize("license_number", [None, "DEMO-123"])
def test_production_rejects_doctor_without_verified_license(
    monkeypatch: pytest.MonkeyPatch, license_number: str | None
) -> None:
    monkeypatch.setattr(
        doctors_router, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        doctors_router.create_doctor(
            DoctorCreate(
                Username="real_doctor",
                Password="StrongPass123!",
                FullName="Bác sĩ thử",
                SpecialtyID=1,
                ClinicID=1,
                LicenseNumber=license_number,
            ),
            db=session,
            admin=SimpleNamespace(user_id=1),
        )
    assert exc.value.status_code == 422
    session.add.assert_not_called()


def test_production_cannot_clear_existing_doctor_license(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        doctors_router, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        license_number="LIC-001"
    )
    with pytest.raises(HTTPException) as exc:
        doctors_router.update_doctor(
            3,
            DoctorUpdate(LicenseNumber=None),
            db=session,
            admin=SimpleNamespace(user_id=1),
        )
    assert exc.value.status_code == 422
    session.commit.assert_not_called()


def test_production_configuration_accepts_verified_transport_and_private_secrets() -> None:
    settings = _production_settings(cors_origins="https://portal.example.test")
    assert settings.allowed_cors_origins == ["https://portal.example.test"]
    assert settings.app_mode == "production"


@pytest.mark.parametrize(
    "overrides",
    [
        {"db_name": "ClinicManagementDemoDB"},
        {"clinic_demo_now": "2026-10-05T09:59:00+07:00"},
        {"db_user": "sa"},
        {"db_password": "change_me"},
        {"db_encrypt": "no"},
        {"db_trust_server_certificate": "yes"},
        {"jwt_secret": "short"},
        {"jwt_algorithm": "none"},
        {"api_host": "0.0.0.0"},
        {"api_public_base_url": "http://clinic.example.test"},
        {"cors_origins": "*"},
        {"cors_origins": "http://portal.example.test"},
    ],
)
def test_production_configuration_rejects_unsafe_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _production_settings(**overrides)


def test_production_desktop_requires_https() -> None:
    with pytest.raises(ValidationError):
        FrontendSettings(_env_file=None, app_mode="production", api_public_base_url="http://clinic.example.test")
    assert FrontendSettings(
        _env_file=None,
        app_mode="production",
        api_public_base_url="https://clinic.example.test",
    ).api_base_url == "https://clinic.example.test"


def test_login_throttle_blocks_repeated_failures_across_login_entrypoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.core.login_throttle.get_settings",
        lambda: SimpleNamespace(app_mode="production"),
    )
    request = Request({"type": "http", "client": ("192.0.2.10", 51000), "method": "POST", "path": "/auth/login", "headers": []})
    throttle = LoginThrottle()
    for _ in range(MAX_ACCOUNT_FAILURES):
        throttle.check(request, "patient01")
        throttle.failed(request, "patient01")
    with pytest.raises(HTTPException) as exc:
        throttle.check(request, "PATIENT01")
    assert exc.value.status_code == 429
    throttle.succeeded(request, "patient01")
    throttle.check(request, "patient01")


def test_proxy_address_cannot_be_used_to_lock_out_every_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.core.login_throttle.get_settings",
        lambda: SimpleNamespace(app_mode="production"),
    )
    proxy_request = Request(
        {"type": "http", "client": ("127.0.0.1", 51000), "method": "POST", "path": "/auth/login", "headers": []}
    )
    throttle = LoginThrottle()
    for index in range(40):
        throttle.failed(proxy_request, f"unknown{index}")
    throttle.check(proxy_request, "legitimate.staff")


def test_production_admin_cannot_create_unverified_patient_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        users_router, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    request = UserCreate(
        Username="patient_verified_later",
        Password="PrivatePassword123!",
        FullName="Bệnh nhân kiểm thử",
        Role="PATIENT",
    )
    with pytest.raises(HTTPException) as rejected:
        users_router.create_user(request, db, SimpleNamespace(user_id=1, role="ADMIN"))
    assert rejected.value.status_code == 422
    db.add.assert_not_called()


def test_readiness_returns_503_without_exposing_database_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailedEngine:
        def connect(self):
            raise SQLAlchemyError("private SQL connection detail")

    monkeypatch.setattr(main_module, "engine", FailedEngine())
    with pytest.raises(HTTPException) as exc:
        main_module.readiness_check()
    assert exc.value.status_code == 503
    assert "private" not in str(exc.value.detail)


def test_production_public_registration_requires_verified_enrollment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_routes, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    with pytest.raises(HTTPException) as exc:
        auth_routes.register(None, None)
    assert exc.value.status_code == 403


def test_optional_patient_accepts_authenticated_staff_catalog_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    staff = SimpleNamespace(user_id=3, role="STAFF", is_active=True)
    monkeypatch.setattr(api_deps, "decode_access_token", lambda _token: TokenPayload(3, "STAFF", "jti"))
    monkeypatch.setattr(api_deps, "UserRepository", lambda _session: SimpleNamespace(get_by_id=lambda _uid: staff))
    validate = MagicMock()
    monkeypatch.setattr(api_deps, "validate_access_session", validate)
    monkeypatch.setattr(api_deps, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    credentials = SimpleNamespace(scheme="Bearer", credentials="token")
    assert api_deps.get_optional_patient(credentials, MagicMock()) is None
    validate.assert_called_once()


def test_production_user_role_cannot_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(users_router, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    db = MagicMock()
    user = SimpleNamespace(
        user_id=7,
        username="staff07",
        role="STAFF",
        is_active=True,
        doctor=None,
        patient=None,
    )
    db.query.return_value.filter.return_value.first.return_value = user
    with pytest.raises(HTTPException) as exc:
        users_router.update_user(
            7,
            UserUpdate(Role="ADMIN"),
            db,
            SimpleNamespace(user_id=1, role="ADMIN"),
        )
    assert exc.value.status_code == 409
    assert user.role == "STAFF"
    db.commit.assert_not_called()
