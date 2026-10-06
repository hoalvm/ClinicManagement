"""Server-side token, audit, and database preflight behavior."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest

from backend.app.core import audit, security
from backend.app.core.exceptions import AuthenticationError
from backend.app.ops.production_preflight import (
    REQUIRED_COLUMNS,
    REQUIRED_MIGRATIONS,
    REQUIRED_TABLES,
    validate_production_database,
)


@pytest.fixture
def production_jwt(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    settings = SimpleNamespace(
        app_mode="production",
        jwt_secret_value="production-test-secret-" * 4,
        jwt_algorithm="HS256",
        access_token_expire_minutes=60,
    )
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    monkeypatch.setattr(security, "record_audit_event", MagicMock())
    return settings


def test_production_token_is_persisted_and_revocable(production_jwt: SimpleNamespace) -> None:
    session = MagicMock()
    token = security.create_access_token(user_id=42, role="DOCTOR", session=session)
    payload = jwt.decode(
        token,
        production_jwt.jwt_secret_value,
        algorithms=[production_jwt.jwt_algorithm],
    )
    identity = security.decode_access_token(token)
    assert payload["jti"]
    assert identity.jti_hash == sha256(payload["jti"].encode("ascii")).hexdigest()
    assert session.execute.call_args.args[1]["jti_hash"] == identity.jti_hash
    session.commit.assert_called_once()

    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=30)
    session.execute.return_value.first.return_value = (42, future, None)
    security.validate_access_session(session, identity)

    session.execute.return_value.first.return_value = (42, future, datetime.now(UTC))
    with pytest.raises(AuthenticationError):
        security.validate_access_session(session, identity)

    security.logout_access_token(session, token, actor_role="DOCTOR")
    assert "UPDATE dbo.AuthSessions" in str(session.execute.call_args.args[0])
    assert session.commit.call_count == 2


def test_production_token_without_session_or_jti_is_rejected(production_jwt: SimpleNamespace) -> None:
    with pytest.raises(RuntimeError, match="persistent auth session"):
        security.create_access_token(user_id=42, role="PATIENT")
    old_token = jwt.encode(
        {"sub": "42", "role": "PATIENT", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        production_jwt.jwt_secret_value,
        algorithm=production_jwt.jwt_algorithm,
    )
    with pytest.raises(AuthenticationError):
        security.decode_access_token(old_token)


def test_audit_event_is_transaction_bound_and_rejects_clinical_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    session = MagicMock()
    token = audit.audit_request_id.set("a" * 32)
    try:
        audit.record_audit_event(
            session,
            actor_user_id=2,
            actor_role="STAFF",
            action="PAYMENT_RECORDED",
            entity_type="Payment",
            entity_id=17,
            clinic_id=3,
            details={"amount": Decimal("225000.00"), "payment_method": "CASH"},
        )
    finally:
        audit.audit_request_id.reset(token)
    assert "INSERT INTO dbo.AuditEvents" in str(session.execute.call_args.args[0])
    assert '"amount":"225000.00"' in session.execute.call_args.args[1]["details"]
    assert session.execute.call_args.args[1]["request_id"] == "a" * 32
    session.commit.assert_not_called()
    with pytest.raises(ValueError, match="not allowed"):
        audit.record_audit_event(
            session,
            actor_user_id=2,
            actor_role="STAFF",
            action="PAYMENT_RECORDED",
            entity_type="Payment",
            entity_id=17,
            details={"diagnosis": "sensitive narrative"},
        )


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return iter(self.value)

    def one(self):
        return self.value

    def all(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


def _preflight_connection(
    *,
    marker: int = 0,
    sample: int = 0,
    admins: int = 1,
    unresolved: int = 0,
    provenance: str | None = "EMPTY_DATABASE",
    migrations: set[str] = REQUIRED_MIGRATIONS,
    trigger: int = 1,
    permissions: tuple[int, ...] = (1, 1, 1, 1, 1, 1),
) -> MagicMock:
    connection = MagicMock()
    connection.execute.side_effect = [
        _Result("ClinicManagementDB"),
        _Result(REQUIRED_TABLES),
        _Result(migrations),
        _Result(REQUIRED_COLUMNS),
        _Result(trigger),
        _Result(
            {
                ("ChargeCatalog", "UX_ChargeCatalog_ActiveConsultation"),
                ("Payments", "UX_Payments_TransferReference"),
                ("Appointments", "UX_Appointments_ClinicDateQueue"),
            }
        ),
        _Result(provenance),
        _Result(marker),
        _Result(sample),
        _Result(unresolved),
        _Result(admins),
        _Result((0, 0, 0)),
        _Result((0, 0, 0, 0, 0)),
        _Result(permissions),
    ]
    return connection


@pytest.mark.parametrize("marker,sample", [(0, 0), (1, 0), (0, 1)])
def test_production_preflight_rejects_demo_identity(marker: int, sample: int) -> None:
    connection = _preflight_connection(marker=marker, sample=sample)
    if marker or sample:
        with pytest.raises(RuntimeError, match="demo|sample"):
            validate_production_database(connection, "ClinicManagementDB")
    else:
        validate_production_database(connection, "ClinicManagementDB")


def test_production_preflight_requires_session_and_audit_permissions() -> None:
    connection = _preflight_connection(permissions=(1, 1, 1, 0, 1, 1))
    with pytest.raises(RuntimeError, match="lacks session, audit"):
        validate_production_database(connection, "ClinicManagementDB")


def test_production_preflight_requires_bootstrapped_admin() -> None:
    connection = _preflight_connection(admins=0)
    with pytest.raises(RuntimeError, match="no active administrator"):
        validate_production_database(connection, "ClinicManagementDB")


def test_production_preflight_requires_provenance_and_historical_specialties() -> None:
    with pytest.raises(RuntimeError, match="provisioned empty"):
        validate_production_database(
            _preflight_connection(provenance=None), "ClinicManagementDB"
        )
    with pytest.raises(RuntimeError, match="unverified historical specialties"):
        validate_production_database(
            _preflight_connection(unresolved=1), "ClinicManagementDB"
        )


def test_production_preflight_requires_migrations_and_audit_trigger() -> None:
    with pytest.raises(RuntimeError, match="missing migrations"):
        validate_production_database(
            _preflight_connection(migrations={"001_demo_workflow"}), "ClinicManagementDB"
        )
    with pytest.raises(RuntimeError, match="append-only trigger"):
        validate_production_database(
            _preflight_connection(trigger=0), "ClinicManagementDB"
        )
